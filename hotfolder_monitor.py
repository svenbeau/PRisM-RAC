#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
import json
import tempfile
import shutil
from utils.utils import debug_print, is_file_stable, open_in_photoshop, run_jsx_in_photoshop, move_file, close_current_document_in_photoshop

IDLE_THRESHOLD = 60  # Sekunden Inaktivität bis zum Idle-Zustand

def is_hidden(file_path):
    """Prüft, ob der Dateiname mit einem Punkt beginnt."""
    return os.path.basename(file_path).startswith(".")

def read_json_file(file_path):
    """Liest eine JSON-Datei und gibt das Objekt zurück."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Error reading JSON file {file_path}: {e}")
        return None

def create_temp_jsx_with_config(base_jsx_path, keyword_check_enabled, keyword_check_word, effective_layers, effective_metadata, logfiles_dir):
    """
    Erzeugt eine temporäre JSX-Datei, in der folgende Platzhalter im Basis‑JSX‑Template ersetzt werden:
      /*PYTHON_INSERT_LAYERS*/    -> JSON-string der effektiven Ebenen
      /*PYTHON_INSERT_METADATA*/  -> JSON-string der effektiven Metadaten
      /*PYTHON_INSERT_LOGFOLDER*/ -> JSON-string des Logfile-Verzeichnisses
    Zusätzlich wird am Anfang Code injiziert, der die Variablen DEBUG_OUTPUT, keywordCheckEnabled und keywordCheckWord deklariert.
    """
    if not base_jsx_path or not os.path.exists(base_jsx_path):
        debug_print(f"Error: Base JSX script not found at {base_jsx_path}")
        return None
    try:
        with open(base_jsx_path, "r", encoding="utf-8") as f:
            jsx_template = f.read()
    except Exception as e:
        debug_print(f"Error reading base JSX script {base_jsx_path}: {e}")
        return None

    # Erzeuge die Strings für den Austausch der Platzhalter
    layers_str = json.dumps(effective_layers)
    metadata_str = json.dumps(effective_metadata)
    logfiles_str = json.dumps(logfiles_dir)

    # Ersetze die Platzhalter im Template
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_LAYERS*/", layers_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_METADATA*/", metadata_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_LOGFOLDER*/", logfiles_str)

    # Injektions-Code: Definiere DEBUG_OUTPUT, keywordCheckEnabled und keywordCheckWord
    injection = ""
    injection += "var DEBUG_OUTPUT = false;\n"
    injection += "var keywordCheckEnabled = " + str(keyword_check_enabled).lower() + ";\n"
    injection += "var keywordCheckWord = " + json.dumps(keyword_check_word) + ";\n"

    combined_code = injection + jsx_template

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(tmp_fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            tmp_f.write(combined_code)
        debug_print(f"Temporary JSX created: {tmp_path} (keywordCheckEnabled={keyword_check_enabled}, keywordCheckWord={keyword_check_word}, effective_layers={effective_layers}, effective_metadata={effective_metadata}, logFolderPath={logfiles_dir})")
        return tmp_path
    except Exception as e:
        debug_print(f"Error writing temporary JSX script: {e}")
        return None

def process_file(file_path, hf_config, contentcheck_jsx_path, on_status_update=None):
    """
    Verarbeitet eine Datei:
      - Überspringt versteckte Dateien und wartet, bis die Datei stabil ist.
      - Öffnet die Datei in Photoshop.
      - Erstellt ein dynamisches JSX-Skript (basierend auf dem Template) mit den konfigurierten Werten.
      - Führt das dynamische Script aus und liest das generierte Log.
      - Bei Erfolg werden (falls konfiguriert) nacheinander die in "selected_jsx" und "additional_jsx" hinterlegten Scripts ausgeführt.
      - Schließt das aktuell geöffnete Photoshop-Dokument (ohne Speichern) und verschiebt die Datei in den Success- bzw. Fault-Ordner.
    """
    success_dir = hf_config.get("success_dir")
    fault_dir = hf_config.get("fault_dir")
    logfiles_dir = hf_config.get("logfiles_dir")
    keyword_check_enabled = hf_config.get("keyword_check_enabled", False)
    keyword_check_word = hf_config.get("keyword_check_word", "")

    # Für den effektiven Check: Bei aktiviertem Keyword-Check werden die keyword_* Arrays verwendet,
    # sonst die Standardwerte
    if keyword_check_enabled:
        effective_layers = hf_config.get("keyword_layers", [])
        effective_metadata = hf_config.get("keyword_metadata", [])
    else:
        effective_layers = hf_config.get("required_layers", [])
        effective_metadata = hf_config.get("required_metadata", [])

    if is_hidden(file_path):
        debug_print(f"Skipping hidden file: {file_path}")
        return

    if not is_file_stable(file_path):
        debug_print(f"File not stable: {file_path}")
        return

    if on_status_update:
        on_status_update(f"Processing: {os.path.basename(file_path)}", True)
    debug_print(f"Processing file: {file_path}")

    if open_in_photoshop(file_path):
        debug_print(f"Opened {file_path} in Photoshop.")
    else:
        debug_print(f"Failed to open {file_path} in Photoshop.")

    tmp_jsx_path = create_temp_jsx_with_config(contentcheck_jsx_path, keyword_check_enabled, keyword_check_word, effective_layers, effective_metadata, logfiles_dir)
    if not tmp_jsx_path:
        debug_print("Could not create dynamic JSX. Aborting content check.")
        dest = os.path.join(fault_dir, os.path.basename(file_path))
        move_file(file_path, dest)
        if on_status_update:
            on_status_update(f"Processed (no script): {os.path.basename(file_path)}", True)
        return

    if run_jsx_in_photoshop(tmp_jsx_path):
        debug_print(f"Executed JSX script: {tmp_jsx_path}")
    else:
        debug_print(f"Failed to execute JSX script: {tmp_jsx_path}")

    try:
        os.remove(tmp_jsx_path)
    except Exception as e:
        debug_print(f"Error removing temporary JSX script {tmp_jsx_path}: {e}")

    time.sleep(2)
    baseName = os.path.basename(file_path).rsplit(".", 1)[0]
    contentLogPath = os.path.join(logfiles_dir, baseName + "_01_log_contentcheck.json")
    contentCheck = read_json_file(contentLogPath)
    debug_print(f"ContentCheck Log ({contentLogPath}): {contentCheck}")

    if contentCheck:
        details = contentCheck.get("details", {})
        layerStatus = details.get("layerStatus", "FAIL")
        metaStatus = details.get("metaStatus", "FAIL")
        if layerStatus == "OK" and metaStatus == "OK":
            dest_dir = success_dir
            debug_print("Contentcheck OK: Datei -> Success")
            selected_jsx = hf_config.get("selected_jsx", "")
            additional_jsx = hf_config.get("additional_jsx", "")
            if selected_jsx:
                debug_print(f"Running selected JSX script: {selected_jsx}")
                if not run_jsx_in_photoshop(selected_jsx):
                    debug_print(f"Failed to execute selected_jsx: {selected_jsx}")
            if additional_jsx:
                debug_print(f"Running additional JSX script: {additional_jsx}")
                if not run_jsx_in_photoshop(additional_jsx):
                    debug_print(f"Failed to execute additional_jsx: {additional_jsx}")
        else:
            dest_dir = fault_dir
            debug_print("Contentcheck FAIL: Datei -> Fault")
    else:
        dest_dir = fault_dir
        debug_print("No Contentcheck Log found: Datei -> Fault")

    if not close_current_document_in_photoshop():
        debug_print("Error closing document in Photoshop.")

    dest = os.path.join(dest_dir, os.path.basename(file_path))
    if move_file(file_path, dest):
        debug_print(f"Moved file from {file_path} to {dest}")
    else:
        debug_print(f"Error moving file from {file_path} to {dest}")

    if on_status_update:
        on_status_update(f"Processed: {os.path.basename(file_path)}", True)

class HotfolderMonitor:
    """
    Überwacht ein Verzeichnis (monitor_dir) und verarbeitet neu hinzugefügte Dateien.
    Schaltet in den Idle-Modus, wenn für einen bestimmten Zeitraum keine Dateien gefunden werden.
    """
    def __init__(self, hf_config, parent=None, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir")
        self.success_dir = hf_config.get("success_dir")
        self.fault_dir = hf_config.get("fault_dir")
        self.logfiles_dir = hf_config.get("logfiles_dir")
        jsx_folder = hf_config.get("jsx_folder")
        if jsx_folder and os.path.isdir(jsx_folder):
            candidate = os.path.join(jsx_folder, "contentcheck_template.jsx")
            if os.path.exists(candidate):
                self.contentcheck_jsx_path = candidate
            else:
                self.contentcheck_jsx_path = os.path.join(os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx")
        else:
            self.contentcheck_jsx_path = os.path.join(os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx")
        self.selected_jsx = hf_config.get("selected_jsx", "")
        self.additional_jsx = hf_config.get("additional_jsx", "")
        self.parent = parent
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing
        self._running = False
        self._thread = None
        self.last_activity_time = time.time()
        self.idle = False

    @property
    def active(self):
        return self._running

    def _monitor_loop(self):
        processed_files = set()
        while self._running:
            try:
                files_found = False
                for filename in os.listdir(self.monitor_dir):
                    file_path = os.path.join(self.monitor_dir, filename)
                    if os.path.isfile(file_path) and file_path not in processed_files:
                        files_found = True
                        if is_hidden(file_path):
                            debug_print(f"Skipping hidden file: {file_path}")
                            processed_files.add(file_path)
                        else:
                            if not is_file_stable(file_path):
                                debug_print(f"File {file_path} is not yet stable.")
                                continue
                            debug_print(f"File {file_path} is stable, processing.")
                            self.last_activity_time = time.time()
                            if self.idle:
                                debug_print("Monitor was idle; waking up.")
                                self.idle = False
                                if self.on_status_update:
                                    self.on_status_update("Aktiv (Aufgewacht)", True)
                            process_file(file_path, self.hf_config, self.contentcheck_jsx_path,
                                         on_status_update=self.on_status_update)
                            processed_files.add(file_path)
                            if self.on_file_processing:
                                self.on_file_processing(file_path)
                if not files_found:
                    elapsed = time.time() - self.last_activity_time
                    if elapsed >= IDLE_THRESHOLD and not self.idle:
                        self.idle = True
                        debug_print(f"Monitor enters Idle state after {elapsed} seconds of inactivity.")
                        if self.on_status_update:
                            self.on_status_update("Idle", True)
                time.sleep(1)
            except Exception as e:
                debug_print(f"Error in HotfolderMonitor: {e}")
                time.sleep(1)

    def start(self):
        self._running = True
        self.last_activity_time = time.time()
        self.idle = False
        debug_print(f"HotfolderMonitor starting for directory: {self.monitor_dir}")
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        debug_print("HotfolderMonitor stopped.")

if __name__ == "__main__":
    hf_config = {
        "monitor_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/01_Monitor/02_Wand",
        "success_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/02_Success/02_Wand",
        "fault_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/03_Fault",
        "logfiles_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/04_Logfiles",
        "jsx_folder": "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/scripts",
        "selected_jsx": "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/scripts/GRIS_C_ReadWriteCSV.jsx",
        "additional_jsx": "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/scripts/GRIS_Wandabbildungen_2024.jsx",
        "contentcheck_enabled": True,
        "required_layers": ["Freisteller"],
        "required_metadata": ["author", "description", "keywords"],
        "keyword_check_enabled": True,
        "keyword_check_word": "Rueckseite",
        "keyword_layers": [],
        "keyword_metadata": ["author", "description"]
    }
    monitor = HotfolderMonitor(hf_config)
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()