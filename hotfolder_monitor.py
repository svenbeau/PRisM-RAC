#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfolder Monitor – mit Queue (Warteschlange) für sequenzielle Verarbeitung
und vollständigem Contentcheck (inkl. detailliertem Fail-Log).

1) Dateien werden in die Queue gelegt (on_created / on_modified).
2) Ein Worker-Thread verarbeitet sie nacheinander (process_file).
3) Der Contentcheck wird anhand der konfigurierten Kriterien ausgewertet:
   - Falls contentcheck_enabled false ist, wird der Check übersprungen.
   - Ansonsten werden Standard-Kriterien (required_layers, required_metadata)
     oder, falls keyword_check_enabled aktiv und im "keywords" Feld das definierte
     Keyword vorkommt, die keyword-spezifischen Kriterien (keyword_layers, keyword_metadata)
     geprüft.
4) Fehlende Kriterien werden in einem Dictionary gesammelt und in das Fail‑Log geschrieben.
   Nur wenn alle Kriterien erfüllt sind, wird die Datei in den Success‑Ordner verschoben.
"""

import os
import time
import shutil
import json
import subprocess
import threading
import queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from dynamic_jsx_generator import generate_jsx_script

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

def open_in_photoshop(file_path: str) -> bool:
    cmd_open = ["open", "-b", "com.adobe.Photoshop", file_path]
    debug_print("Opening file in Photoshop: " + str(cmd_open))
    try:
        subprocess.run(cmd_open, check=True)
        return True
    except subprocess.CalledProcessError as e:
        debug_print("Error opening file in Photoshop: " + str(e))
        return False

def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    try:
        cmd_jsx = f'tell application id "com.adobe.Photoshop" to do javascript file "{jsx_script_path}"'
        result = subprocess.run(["osascript", "-e", cmd_jsx],
                                  capture_output=True,
                                  text=True)
        debug_print(f"JSX execution result: RC={result.returncode}")
        if result.stdout:
            debug_print(f"JSX stdout: {result.stdout}")
        if result.stderr:
            debug_print(f"JSX stderr: {result.stderr}")
        return (result.returncode == 0)
    except Exception as e:
        debug_print(f"Error executing JSX: {e}")
        return False

def is_file_stable(file_path: str, interval=1.0, retries=3) -> bool:
    if not os.path.exists(file_path):
        return False
    last_size = os.path.getsize(file_path)
    stable_count = 0
    while stable_count < retries:
        time.sleep(interval)
        if not os.path.exists(file_path):
            return False
        current_size = os.path.getsize(file_path)
        if current_size == last_size:
            stable_count += 1
        else:
            stable_count = 0
            last_size = current_size
        debug_print(f"Checking file stability for {file_path}: size={current_size}, stable_count={stable_count}")
    return True

def move_file(src_path, dest_dir):
    try:
        if not os.path.exists(src_path):
            debug_print(f"Datei {src_path} existiert nicht mehr. Überspringe Verschiebung.")
            return
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest_path = os.path.join(dest_dir, os.path.basename(src_path))
        shutil.move(src_path, dest_path)
        debug_print(f"Datei verschoben nach: {dest_path}")
    except Exception as e:
        debug_print(f"Fehler beim Verschieben der Datei: {e}")

def is_hidden(file_path: str) -> bool:
    return os.path.basename(file_path).startswith('.')

class HotfolderEventHandler(FileSystemEventHandler):
    def __init__(self, monitor_instance):
        super().__init__()
        self.monitor = monitor_instance

    def on_created(self, event):
        if event.is_directory or is_hidden(event.src_path):
            return
        debug_print(f"File created: {event.src_path}")
        self.monitor.enqueue_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory or is_hidden(event.src_path):
            return
        debug_print(f"File modified: {event.src_path}")
        self.monitor.enqueue_file(event.src_path)

class HotfolderMonitor:
    def __init__(self, hf_config: dict, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir", "")
        self.observer = None
        self.active = False
        self.file_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing

    def start(self):
        if not self.monitor_dir or not os.path.exists(self.monitor_dir):
            debug_print(f"Hotfolder existiert nicht: {self.monitor_dir}")
            return
        debug_print(f"Starte HotfolderMonitor für: {self.monitor_dir}")
        self.observer = Observer()
        event_handler = HotfolderEventHandler(self)
        self.observer.schedule(event_handler, self.monitor_dir, recursive=True)
        self.observer.start()
        self.active = True
        if self.on_status_update:
            self.on_status_update("Aktiv", True)
        for root, dirs, files in os.walk(self.monitor_dir):
            for file in files:
                file_path = os.path.join(root, file)
                debug_print(f"Found existing file: {file_path}")
                self.enqueue_file(file_path)
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        if self.active:
            debug_print(f"Stoppe HotfolderMonitor für: {self.monitor_dir}")
            self.stop_event.set()
            self.file_queue.put(None)  # Poison Pill
            if self.observer:
                self.observer.stop()
                self.observer.join()
            if self.worker_thread:
                self.worker_thread.join()
            self.active = False
            if self.on_status_update:
                self.on_status_update("Inaktiv", False)

    def enqueue_file(self, file_path: str):
        if file_path:
            debug_print(f"Enqueue file: {file_path}")
            self.file_queue.put(file_path)

    def worker_loop(self):
        while not self.stop_event.is_set():
            try:
                file_path = self.file_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if file_path is None:
                break
            self.process_file(file_path)
            self.file_queue.task_done()

    def process_file(self, file_path: str):
        if self.on_file_processing:
            self.on_file_processing(os.path.basename(file_path))
        debug_print(f"Verarbeite Datei: {file_path}")
        if not is_file_stable(file_path):
            debug_print(f"Datei ist nicht stabil (noch im Kopiervorgang?): {file_path}")
            if self.on_file_processing:
                self.on_file_processing(None)
            return
        if not open_in_photoshop(file_path):
            debug_print("Fehler beim Öffnen der Datei in Photoshop.")
            if self.on_file_processing:
                self.on_file_processing(None)
            return
        file_name = os.path.basename(file_path)
        jsx_script_path = generate_jsx_script(self.hf_config, file_name)
        success_jsx = run_jsx_in_photoshop(jsx_script_path)
        if not success_jsx:
            debug_print("Fehler beim Ausführen des Contentcheck-JSX.")
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)
            if self.on_file_processing:
                self.on_file_processing(None)
            return
        logfiles_dir = self.hf_config.get("logfiles_dir", "")
        log_file = os.path.join(logfiles_dir, file_name.rsplit(".", 1)[0] + "_log_contentcheck.json")
        debug_print("Erwarte Logfile: " + log_file)
        timeout = 30
        elapsed = 0
        while elapsed < timeout:
            if os.path.exists(log_file):
                break
            time.sleep(1)
            elapsed += 1
        if not os.path.exists(log_file):
            debug_print("Contentcheck-Logfile wurde nicht erzeugt, verschiebe Datei in Fault.")
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)
            if self.on_file_processing:
                self.on_file_processing(None)
            return
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                contentcheck = json.load(f)
        except Exception as e:
            debug_print("Fehler beim Lesen des Logfiles: " + str(e))
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)
            if self.on_file_processing:
                self.on_file_processing(None)
            return

        missing_dict = self.evaluate_contentcheck(contentcheck)
        if not missing_dict:
            debug_print("Contentcheck erfolgreich. Verschiebe Datei in Success.")
            success_dir = self.hf_config.get("success_dir", "")
            move_file(file_path, success_dir)
        else:
            debug_print("Contentcheck fehlgeschlagen. Fehlende Kriterien: " + json.dumps(missing_dict))
            log_fail_file = os.path.join(logfiles_dir, file_name.rsplit(".", 1)[0] + "_01_log_fail.json")
            with open(log_fail_file, "w", encoding="utf-8") as ff:
                json.dump(missing_dict, ff, indent=4, ensure_ascii=False)
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)

        if self.on_file_processing:
            self.on_file_processing(None)

    def evaluate_contentcheck(self, contentcheck: dict) -> dict:
        missing = {}
        # Globaler Contentcheck-Schalter
        if not self.hf_config.get("contentcheck_enabled", True):
            debug_print("Globaler Contentcheck deaktiviert.")
            return missing  # Check bestanden

        # Standard-Kriterien
        standard_layers = self.hf_config.get("required_layers", [])
        standard_meta = self.hf_config.get("required_metadata", [])
        # Keyword-Check
        kw_enabled = self.hf_config.get("keyword_check_enabled", False)
        kw_word = self.hf_config.get("keyword_check_word", "Rueckseite").lower()

        meta_dict = contentcheck.get("metadata", {})
        details = contentcheck.get("details", {})
        layer_dict = details.get("layers", {})

        is_keyword = False
        if kw_enabled and "keywords" in meta_dict:
            raw_keywords = meta_dict["keywords"]
            if isinstance(raw_keywords, str):
                if kw_word in raw_keywords.lower():
                    debug_print("Keyword-basierter Check: Keyword erkannt.")
                    is_keyword = True
            elif isinstance(raw_keywords, list):
                joined = ", ".join(raw_keywords)
                if kw_word in joined.lower():
                    debug_print("Keyword-basierter Check: Keyword erkannt.")
                    is_keyword = True

        if is_keyword:
            used_layers = self.hf_config.get("keyword_layers", [])
            used_meta = self.hf_config.get("keyword_metadata", [])
        else:
            used_layers = standard_layers
            used_meta = standard_meta

        if not used_layers and not used_meta:
            debug_print("Keine Contentcheck-Kriterien definiert, Check übersprungen.")
            return missing

        # Ebenen-Prüfung
        missing_layers = []
        for layer in used_layers:
            val = layer_dict.get(layer, "no")
            if val.lower() != "yes":
                missing_layers.append(layer)
        if missing_layers:
            missing["layers"] = missing_layers

        # Metadaten-Prüfung
        missing_meta = []
        for meta in used_meta:
            val = meta_dict.get(meta, "undefined")
            if val.strip().lower() in ["undefined", "no", ""]:
                missing_meta.append(meta)
        if missing_meta:
            missing["metadata"] = missing_meta

        return missing