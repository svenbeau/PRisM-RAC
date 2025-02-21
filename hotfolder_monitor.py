#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfolder Monitor – Überwacht einen definierten Ordner und führt bei Dateiänderungen folgende Schritte aus:
1. Überprüft, ob die Datei vollständig (stabile Dateigröße) kopiert wurde.
2. Öffnet die Datei in Adobe Photoshop.
3. Führt das dynamisch generierte Contentcheck-JSX aus (und ggf. ein zusätzliches JSX).
4. Wertet das Ergebnis (Logfile) aus.
5. Verschiebt die Datei in Success oder Fault und erstellt ggf. ein Fail-Log.
"""

__all__ = ["HotfolderMonitor", "debug_print"]

import os
import time
import shutil
import json
import subprocess
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from dynamic_jsx_generator import generate_jsx_script, debug_print

DEBUG_OUTPUT = True
def debug_print(message):
    if DEBUG_OUTPUT:
        print("[DEBUG]", message)

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
        result = subprocess.run(["osascript", "-e", cmd_jsx], capture_output=True, text=True)
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
        threading.Thread(target=self.monitor.process_file, args=(event.src_path,)).start()

    def on_modified(self, event):
        if event.is_directory or is_hidden(event.src_path):
            return
        debug_print(f"File modified: {event.src_path}")
        threading.Thread(target=self.monitor.process_file, args=(event.src_path,)).start()

class HotfolderMonitor:
    def __init__(self, hf_config: dict, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir", "")
        self.observer = None
        self.active = False
        self.processed_files = set()  # Verarbeitete Dateien

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
                debug_print(f"Processing existing file: {file_path}")
                self.process_file(file_path)

    def stop(self):
        if self.observer and self.active:
            debug_print(f"Stoppe HotfolderMonitor für: {self.monitor_dir}")
            self.observer.stop()
            self.observer.join()
            self.active = False
            if self.on_status_update:
                self.on_status_update("Inaktiv", False)

    def process_file(self, file_path: str):
        # Falls Datei bereits verarbeitet, überspringen
        if file_path in self.processed_files:
            debug_print(f"Datei {file_path} wurde bereits verarbeitet. Überspringe.")
            return
        self.processed_files.add(file_path)

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
        success = run_jsx_in_photoshop(jsx_script_path)
        if not success:
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

        # Vergleiche die ausgewählten Metadaten-Felder (required_metadata) mit den Werten im Log
        var_required = self.hf_config.get("required_metadata", [])
        var_missing = {}
        for field in var_required:
            if "metadata" in contentcheck and field in contentcheck["metadata"]:
                val = contentcheck["metadata"][field]
            else:
                val = "undefined"
            if val.strip().lower() == "undefined" or val.strip() == "":
                var_missing[field] = val

        if len(var_missing) == 0:
            criteria_met = True
        else:
            criteria_met = False

        if criteria_met:
            debug_print("Contentcheck erfolgreich. Führe zusätzliches JSX aus und verschiebe Datei in Success.")
            additional_jsx = self.hf_config.get("additional_jsx", "").strip()
            if additional_jsx and os.path.exists(additional_jsx):
                add_success = run_jsx_in_photoshop(additional_jsx)
                if not add_success:
                    debug_print("Zusätzliches JSX-Skript schlug fehl (wird aber ignoriert).")
            success_dir = self.hf_config.get("success_dir", "")
            move_file(file_path, success_dir)
        else:
            debug_print("Contentcheck fehlgeschlagen. Fehlende Felder: " + json.dumps(var_missing))
            debug_print("Erzeuge Fail-Log und verschiebe Datei in Fault.")
            fail_log_file = os.path.join(logfiles_dir, file_name.rsplit(".", 1)[0] + "_01_log_fail.json")
            with open(fail_log_file, "w", encoding="utf-8") as f:
                json.dump({"missing": var_missing}, f, indent=4, ensure_ascii=False)
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)

        if self.on_file_processing:
            self.on_file_processing(None)