#!/usr/bin/env python3
"""
hotfolder_monitor.py
Überwacht den Monitor-Ordner und verarbeitet neu hinzugefügte Dateien.
Versteckte Dateien (z.B. .DS_Store) werden übersprungen.
Das Script zum Auslesen der Keywords, Metadaten und Ebenen wird nach dem Öffnen
der Datei in Photoshop gestartet, und anhand des generierten Logs wird der Zielordner gewählt.
"""

import os
import time
import shutil
import subprocess
import threading
import json
import tempfile
from utils import debug_print, open_in_photoshop, run_jsx_in_photoshop, move_file, is_file_stable

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
    Erzeugt eine temporäre JSX-Datei, in die zu Beginn zwei Zeilen injiziert werden:
      var keywordCheckEnabled = true/false;
      var keywordCheckWord = "Rueckseite";
    Anschließend wird der Inhalt des Basis-JSX-Scripts angehängt.
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

def close_in_photoshop():
    """
    Schließt das aktuell geöffnete Dokument in Photoshop ohne zu speichern.
    """
    try:
        photoshop_app = "Adobe Photoshop 2025"
        cmd = 'tell application id "com.adobe.Photoshop" to close front document saving no'
        subprocess.run(["osascript", "-e", cmd], check=True)
        debug_print("Active document closed in Photoshop (without saving).")
        return True
    except Exception as e:
        debug_print(f"Error closing active document in Photoshop: {e}")
        return False

def process_file(file_path, config, jsx_script_path, on_status_update=None):
    """
    Verarbeitet eine einzelne Datei:
      - Überspringt versteckte Dateien.
      - Prüft, ob die Datei stabil ist.
      - Ruft on_status_update mit "Processing: ..." auf.
      - Öffnet die Datei in Photoshop.
      - Führt ein temporäres JSX-Script für den Contentcheck aus und löscht es anschließend.
      - Liest das Log aus und prüft, ob layerStatus und metaStatus == "OK".
      - Falls OK, werden nacheinander "selected_jsx" (ComboBox) und "additional_jsx" (manuell) ausgeführt.
      - Danach wird das Dokument in Photoshop ohne Speichern geschlossen.
      - Datei wird in Success bzw. Fault verschoben.
    """
    success_dir = config.get("success_dir")
    fault_dir = config.get("fault_dir")
    logfiles_dir = config.get("logfiles_dir")

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

    keyword_check_enabled = config.get("keyword_check_enabled", False)
    keyword_check_word = config.get("keyword_check_word", "")

    tmp_jsx_path = create_temp_jsx_with_keyword_check(jsx_script_path, keyword_check_enabled, keyword_check_word)
    if not tmp_jsx_path:
        debug_print("Could not create dynamic JSX. Aborting content check.")
        dest = os.path.join(fault_dir, os.path.basename(file_path))
        move_file(file_path, dest)
        if on_status_update:
            on_status_update(f"Processed (no script): {os.path.basename(file_path)}", True)
        close_in_photoshop()
        return

    # Führe Contentcheck-JSX aus
    if run_jsx_in_photoshop(tmp_jsx_path):
        debug_print(f"Executed temporary JSX script: {tmp_jsx_path}")
    else:
        debug_print(f"Failed to execute temporary JSX script: {tmp_jsx_path}")

    # Entferne temporäre Datei
    try:
        os.remove(tmp_jsx_path)
    except Exception as e:
        debug_print(f"Error removing temporary JSX script {tmp_jsx_path}: {e}")

    time.sleep(2)  # Warte, bis die Log-Datei erstellt wurde

    baseName = os.path.basename(file_path).rsplit(".", 1)[0]
    logPath = os.path.join(logfiles_dir, baseName + "_01_log_contentcheck.json")
    contentCheck = read_json_file(logPath)
    debug_print(f"ContentCheck Log ({logPath}): {contentCheck}")

    # Bestimme, ob Contentcheck erfolgreich war
    content_ok = False
    if contentCheck:
        details = contentCheck.get("details", {})
        layerStatus = details.get("layerStatus", "FAIL")
        metaStatus = details.get("metaStatus", "FAIL")
        if layerStatus == "OK" and metaStatus == "OK":
            content_ok = True
            debug_print("Contentcheck OK.")
        else:
            debug_print("Contentcheck FAIL.")
    else:
        debug_print("Kein Contentcheck Log gefunden (FAIL).")

    # Bei Erfolg: Nacheinander "selected_jsx" und "additional_jsx" ausführen
    if content_ok:
        # Skript aus ComboBox
        script_combo = config.get("selected_jsx", "").strip()
        # Manuelles Skript
        script_manual = config.get("additional_jsx", "").strip()

        # Liste aller Skripte, die ausgeführt werden sollen
        scripts_to_run = []
        if script_combo:
            scripts_to_run.append(script_combo)
        if script_manual:
            scripts_to_run.append(script_manual)

        for script_path in scripts_to_run:
            if run_jsx_in_photoshop(script_path):
                debug_print(f"Executed additional JSX: {script_path}")
            else:
                debug_print(f"Failed to execute additional JSX: {script_path}")

        dest_dir = success_dir
    else:
        dest_dir = fault_dir

    # Photoshop-Dokument ohne Speichern schließen
    close_in_photoshop()

    # Datei verschieben
    dest = os.path.join(dest_dir, os.path.basename(file_path))
    if move_file(file_path, dest):
        debug_print(f"Moved file from {file_path} to {dest}")
    else:
        debug_print(f"Error moving file from {file_path} to {dest}")

    if on_status_update:
        on_status_update(f"Processed: {os.path.basename(file_path)}", True)

class HotfolderMonitor:
    """
    Klasse zur Überwachung eines Hotfolder-Verzeichnisses.
    Akzeptiert ein hf_config-Dictionary, aus dem die Pfade für monitor_dir, success_dir,
    fault_dir, logfiles_dir und optional "jsx_script_path" extrahiert werden.
    Zusätzlich werden Callbacks on_status_update und on_file_processing unterstützt.
    """
    def __init__(self, hf_config, parent=None, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir")
        self.success_dir = hf_config.get("success_dir")
        self.fault_dir = hf_config.get("fault_dir")
        self.logfiles_dir = hf_config.get("logfiles_dir")
        self.jsx_script_path = hf_config.get("jsx_script_path")
        if not self.jsx_script_path:
            self.jsx_script_path = os.path.join(os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx")
        self.parent = parent
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing
        self._running = False
        self._thread = None

    @property
    def active(self):
        return self._running

    def _monitor_loop(self):
        processed_files = set()
        while self._running:
            try:
                for filename in os.listdir(self.monitor_dir):
                    file_path = os.path.join(self.monitor_dir, filename)
                    if os.path.isfile(file_path) and file_path not in processed_files:
                        if is_hidden(file_path):
                            debug_print("Skipping hidden file: " + file_path)
                            processed_files.add(file_path)
                        else:
                            process_file(file_path, self.hf_config, self.jsx_script_path, on_status_update=self.on_status_update)
                            processed_files.add(file_path)
                            if self.on_file_processing:
                                self.on_file_processing(file_path)
                time.sleep(1)
            except Exception as e:
                debug_print(f"Error in HotfolderMonitor: {e}")
                time.sleep(1)

    def start(self):
        self._running = True
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
        "jsx_script_path": "",  # leer -> Standardpfad wird genutzt
        "keyword_check_enabled": True,
        "keyword_check_word": "Rueckseite"
    }
    monitor = HotfolderMonitor(hf_config)
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()