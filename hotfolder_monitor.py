#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hotfolder_monitor.py
Überwacht den Monitor-Ordner und verarbeitet neu hinzugefügte Dateien.
Versteckte Dateien (z.B. .DS_Store) werden übersprungen.
Das Script zum Auslesen der Keywords, Metadaten und Ebenen wird nach dem Öffnen
der Datei in Photoshop gestartet, und anhand des generierten Logs wird der Zielordner gewählt.
Mit Idle-Zustand: Wenn für einen definierten Zeitraum keine Dateien gefunden werden,
geht der Monitor in einen Idle-Modus, der automatisch wieder aktiviert wird,
sobald neue Dateien eintreffen.
"""

import os
import time
import threading
import json
from datetime import datetime

from utils.utils import (
    debug_print,
    is_file_stable,
    open_in_photoshop,
    run_jsx_in_photoshop,
    move_file,
    close_current_document_in_photoshop
)
from utils.log_manager import append_log_entry

IDLE_THRESHOLD = 60  # Sekunden bis zum Wechsel in den Idle-Zustand

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

def create_temp_jsx_with_keyword_check(base_jsx_path, keyword_check_enabled, keyword_check_word):
    """
    Baut ein temporäres JSX-Skript zusammen, indem wir am Anfang:
      var keywordCheckEnabled = true/false;
      var keywordCheckWord = "Rueckseite";
    injizieren und anschließend das Basis-JSX anhängen.
    """
    if not base_jsx_path or not os.path.exists(base_jsx_path):
        debug_print(f"Error: Base JSX script not found at {base_jsx_path}")
        return None
    try:
        with open(base_jsx_path, "r", encoding="utf-8") as f:
            base_jsx_code = f.read()
    except Exception as e:
        debug_print(f"Error reading base JSX script {base_jsx_path}: {e}")
        return None

    import tempfile
    import json
    var_line = "var keywordCheckEnabled = " + str(keyword_check_enabled).lower() + ";\n"
    var_line2 = "var keywordCheckWord = " + json.dumps(keyword_check_word) + ";\n"
    combined_code = var_line + var_line2 + base_jsx_code

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(tmp_fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            tmp_f.write(combined_code)
        debug_print(f"Temporary JSX created: {tmp_path} (keywordCheckEnabled={keyword_check_enabled}, keywordCheckWord={keyword_check_word})")
        return tmp_path
    except Exception as e:
        debug_print(f"Error writing temporary JSX script: {e}")
        return None

def process_file(file_path, config, jsx_script_path, on_status_update=None):
    """
    Verarbeitet eine einzelne Datei synchron:
      1. Öffnet die Datei in Photoshop.
      2. Führt den Contentcheck per dynamisch generiertem JSX-Skript aus.
      3. Liest das Contentcheck-Log und entscheidet, ob die Datei in Success oder Fault verschoben wird.
      4. Falls der Contentcheck erfolgreich ist, werden zusätzlich ausgewählte JSX-Skripte ausgeführt.
      5. Schließt das Dokument in Photoshop ohne Speichern und verschiebt die Datei.
      6. Fügt einen Log-Eintrag im globalen Log hinzu.
    """
    success_dir = config.get("success_dir", "")
    fault_dir = config.get("fault_dir", "")
    logfiles_dir = config.get("logfiles_dir", "")
    keyword_check_enabled = config.get("keyword_check_enabled", False)
    keyword_check_word = config.get("keyword_check_word", "")

    selected_jsx = config.get("selected_jsx", "")
    additional_jsx = config.get("additional_jsx", "")

    if on_status_update:
        on_status_update(f"Aktiv (Verarbeite: {os.path.basename(file_path)})", True)

    # 1) Datei in Photoshop öffnen
    if open_in_photoshop(file_path):
        debug_print(f"Opened {file_path} in Photoshop.")
    else:
        debug_print(f"Failed to open {file_path} in Photoshop.")
        dest = os.path.join(fault_dir, os.path.basename(file_path))
        move_file(file_path, dest)
        if on_status_update:
            on_status_update(f"Processed (open failed): {os.path.basename(file_path)}", True)
        return

    # 2) Dynamisches JSX-Skript (Contentcheck) erzeugen und ausführen
    tmp_jsx_path = create_temp_jsx_with_keyword_check(jsx_script_path, keyword_check_enabled, keyword_check_word)
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

    # 3) Contentcheck-Log einlesen
    baseName = os.path.basename(file_path).rsplit(".", 1)[0]
    logPath = os.path.join(logfiles_dir, baseName + "_01_log_contentcheck.json")
    contentCheck = read_json_file(logPath)
    debug_print(f"ContentCheck Log ({logPath}): {contentCheck}")

    dest_dir = fault_dir
    contentcheck_ok = False
    details = {}

    if contentCheck:
        details = contentCheck.get("details", {})
        layerStatus = details.get("layerStatus", "FAIL")
        metaStatus = details.get("metaStatus", "FAIL")
        if layerStatus == "OK" and metaStatus == "OK":
            debug_print("Contentcheck OK: Datei -> Success")
            dest_dir = success_dir
            contentcheck_ok = True
        else:
            debug_print("Contentcheck FAIL: Datei -> Fault")
    else:
        debug_print("No Contentcheck Log found -> Fault")

    # 4) Falls Contentcheck OK, führe ausgewählte zusätzliche Skripte aus
    if contentcheck_ok:
        if selected_jsx:
            debug_print(f"Running selected JSX script: {selected_jsx}")
            if run_jsx_in_photoshop(selected_jsx):
                debug_print(f"Executed selected_jsx: {selected_jsx}")
            else:
                debug_print(f"Failed to execute selected_jsx: {selected_jsx}")
        if additional_jsx:
            debug_print(f"Running additional JSX script: {additional_jsx}")
            if run_jsx_in_photoshop(additional_jsx):
                debug_print(f"Executed additional_jsx: {additional_jsx}")
            else:
                debug_print(f"Failed to execute additional_jsx: {additional_jsx}")

    # 5) Schließe das aktuell geöffnete Dokument in Photoshop (ohne Speichern)
    close_current_document_in_photoshop(save=False)
    debug_print("Dokument in Photoshop geschlossen (ohne Speichern).")

    # 6) Verschiebe die Datei in den entsprechenden Ordner
    dest = os.path.join(dest_dir, os.path.basename(file_path))
    if move_file(file_path, dest):
        debug_print(f"Moved file from {file_path} to {dest}")
    else:
        debug_print(f"Error moving file from {file_path} to {dest}")

    # 7) Erstelle Log-Eintrag im globalen Log
    status_str = "Success" if contentcheck_ok else "Fail"
    checkType = details.get("checkType", "Standard") if contentCheck else "Unknown"
    metadata = contentCheck.get("metadata", {}) if contentCheck else {}
    script_name = "(none)"
    if contentcheck_ok and selected_jsx:
        script_name = os.path.basename(selected_jsx)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "filename": os.path.basename(file_path),
        "metadata": metadata,
        "checkType": checkType,
        "status": status_str,
        "applied_script": script_name,
        "details": details
    }
    append_log_entry(log_entry)
    debug_print(f"Appended log entry (script={script_name}) to global_log.json.")

    if on_status_update:
        on_status_update(f"Processed: {os.path.basename(file_path)}", True)

def read_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Error reading JSON file {file_path}: {e}")
        return None

class HotfolderMonitor:
    """
    Klasse zur Überwachung eines Hotfolder-Verzeichnisses.
    Verarbeitet neu hinzugefügte Dateien synchron (FIFO) aus einer Pending-Queue.
    Unterstützt einen Idle-Zustand, der nach einer definierten Inaktivitätsdauer aktiviert wird.
    """
    def __init__(self, hf_config, parent=None, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir", "")
        self.success_dir = hf_config.get("success_dir", "")
        self.fault_dir = hf_config.get("fault_dir", "")
        self.logfiles_dir = hf_config.get("logfiles_dir", "")
        self.jsx_script_path = hf_config.get("jsx_script_path", "")
        if not self.jsx_script_path:
            # Falls kein Pfad angegeben, verwende den Standardpfad zum contentcheck_template.jsx
            self.jsx_script_path = os.path.join(os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx")
        self.parent = parent
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing

        self._running = False
        self._thread = None
        self.last_activity_time = time.time()
        self.idle = False
        self.pending_files = set()

    @property
    def active(self):
        return self._running

    def _monitor_loop(self):
        while self._running:
            try:
                # Neue Dateien zur Queue hinzufügen
                for fname in os.listdir(self.monitor_dir):
                    fpath = os.path.join(self.monitor_dir, fname)
                    if os.path.isfile(fpath) and not is_hidden(fpath):
                        if fpath not in self.pending_files:
                            self.pending_files.add(fpath)
                            debug_print(f"New file found, adding to queue: {fpath}")

                # Wenn Dateien in der Queue, verarbeite jeweils die älteste
                if self.pending_files:
                    file_to_process = sorted(self.pending_files)[0]
                    self.pending_files.remove(file_to_process)

                    # Prüfe, ob die Datei stabil ist
                    if not is_file_stable(file_to_process):
                        debug_print(f"File {file_to_process} is not stable -> moving to Fault.")
                        move_file(file_to_process, os.path.join(self.fault_dir, os.path.basename(file_to_process)))
                    else:
                        self.last_activity_time = time.time()
                        if self.idle:
                            self.idle = False
                            debug_print("Monitor was idle; waking up.")
                            if self.on_status_update:
                                self.on_status_update("Aktiv (Aufgewacht)", True)

                        debug_print(f"Processing: {file_to_process}")
                        process_file(file_to_process, self.hf_config, self.jsx_script_path,
                                     on_status_update=self.on_status_update)
                        if self.on_file_processing:
                            self.on_file_processing(file_to_process)
                else:
                    # Wenn keine Dateien, prüfe Idle-Zustand
                    elapsed = time.time() - self.last_activity_time
                    if elapsed >= IDLE_THRESHOLD and not self.idle:
                        self.idle = True
                        debug_print(f"Monitor enters Idle state after {elapsed:.2f} seconds of inactivity.")
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
        "monitor_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/01_Monitor",
        "success_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/02_Success",
        "fault_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/03_Fault",
        "logfiles_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/04_Logfiles",
        "jsx_script_path": "",  # Leer -> Default wird verwendet
        "keyword_check_enabled": True,
        "keyword_check_word": "Rueckseite",
        "selected_jsx": "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/scripts/GRIS_Render_2025.jsx",
        "additional_jsx": ""
    }
    monitor = HotfolderMonitor(hf_config)
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()