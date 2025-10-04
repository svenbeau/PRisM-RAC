#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
import json
from datetime import datetime
from typing import Optional

from utils.utils import (
    debug_print,
    is_file_stable,
    open_in_photoshop,
    run_jsx_in_photoshop,
    move_file,
    close_current_document_in_photoshop,
)
from utils.contentcheck_email_notifier import send_fail_email_from_content

# WEG A: zentralen Generator (Contentcheck) nutzen
from dynamic_jsx_generator import create_temp_jsx_with_config

# WEG B: zentralen Recipe-Injektor (für Produktions-JSX) nutzen
from utils.dynamic_jsx_recipe_injector import create_temp_jsx_with_recipe

IDLE_THRESHOLD = 60  # Sekunden Inaktivität bis zum Idle-Zustand

# Pfade für Script-Recipe-Config im User Application Support
APP_SUPPORT_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PRisM-CC")
APP_SUPPORT_SCRIPT_CONFIG = os.path.join(APP_SUPPORT_DIR, "config", "script_config.json")


def _load_script_config() -> Optional[dict]:
    """
    Lädt die zentrale Script-Recipe-Konfiguration.
    Gibt ein dict zurück oder None bei Fehler / nicht vorhanden.
    """
    try:
        if not os.path.exists(APP_SUPPORT_SCRIPT_CONFIG):
            debug_print(f"Script config not found: {APP_SUPPORT_SCRIPT_CONFIG}")
            return None
        with open(APP_SUPPORT_SCRIPT_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        debug_print(f"Error reading script config {APP_SUPPORT_SCRIPT_CONFIG}: {e}")
        return None


def _find_recipe_for_script(script_path: str) -> Optional[dict]:
    """
    Sucht im Script-Config nach dem passenden Recipe für ein gegebenes JSX-Skript.
    Matching-Regeln:
      1) Pfad-normalisiert (case-insensitive, / vs \\) – enthält / ist enthalten
      2) Fallback: Basename (Dateiname) identisch
    Rückgabe: Recipe-Dict oder None.
    """
    cfg = _load_script_config()
    if not cfg:
        return None

    scripts = cfg.get("scripts", [])
    if not isinstance(scripts, list):
        return None

    sp_norm = script_path.replace("\\", "/").lower()
    sp_name = os.path.basename(sp_norm)

    # 1) Pfad-Containment
    for entry in scripts:
        try:
            ep = str(entry.get("script_path", "")).replace("\\", "/").lower()
            if not ep:
                continue
            if sp_norm in ep or ep in sp_norm:
                return entry
        except Exception:
            continue

    # 2) Fallback: Basename
    for entry in scripts:
        try:
            ep = str(entry.get("script_path", "")).replace("\\", "/").lower()
            if not ep:
                continue
            if os.path.basename(ep) == sp_name:
                return entry
        except Exception:
            continue

    return None


def _run_jsx_with_recipe_injection(script_path: str, *, debug_output: bool = False) -> bool:
    """
    Führt ein Produktions-JSX aus. Falls ein passendes Recipe in script_config.json
    gefunden wird, wird zuerst eine temporäre, injizierte JSX erstellt und diese ausgeführt.
    Fallback: direktes Ausführen von script_path.
    """
    try:
        recipe = _find_recipe_for_script(script_path)
        if recipe:
            debug_print(f"[RecipeInjector] Recipe gefunden für {script_path}: "
                        f"name={recipe.get('name','(no-name)')}")
            if 'csvWandFile' in recipe:
                debug_print(f"[RecipeInjector] Using csvWandFile={recipe.get('csvWandFile')}")
            tmp_jsx = create_temp_jsx_with_recipe(
                recipe=recipe,
                base_jsx_path=script_path,
                extra=None,
                debug_output=debug_output,
            )
            if tmp_jsx:
                try:
                    ok = run_jsx_in_photoshop(tmp_jsx)
                    return ok
                finally:
                    try:
                        os.remove(tmp_jsx)
                    except Exception as e:
                        debug_print(f"[RecipeInjector] Konnte Temp-JSX nicht löschen: {tmp_jsx} ({e})")
            else:
                debug_print(f"[RecipeInjector] Erzeugen der temporären JSX fehlgeschlagen für: {script_path}")
        else:
            debug_print(f"[RecipeInjector] Kein Recipe gefunden für {script_path}. Fallback auf Direktaufruf.")
    except Exception as e:
        debug_print(f"[RecipeInjector] Fehler bei der Injektion für {script_path}: {e}")

    # Fallback: direkt ausführen
    return run_jsx_in_photoshop(script_path)


def is_hidden(file_path: str) -> bool:
    """Prüft, ob der Dateiname mit einem Punkt beginnt."""
    return os.path.basename(file_path).startswith(".")


def read_json_file(file_path: str):
    """Liest eine JSON-Datei und gibt das Objekt zurück."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Error reading JSON file {file_path}: {e}")
        return None


def process_file(file_path, hf_config, contentcheck_jsx_path, on_status_update=None):
    """
    Verarbeitet eine Datei:
      - Überspringt versteckte Dateien und wartet, bis die Datei stabil ist.
      - Öffnet die Datei in Photoshop.
      - Erstellt eine dynamische JSX (per Template + Injektion).
      - Führt das Script aus und liest das generierte Log.
      - Bei OK: optionale Folge-Skripte ausführen, Datei -> Success.
      - Bei FAIL/Fehler: E-Mail versenden, Datei -> Fault.
      - Dokument schließen, Datei verschieben, Status updaten.
    """
    success_dir = hf_config.get("success_dir")
    fault_dir = hf_config.get("fault_dir")
    logfiles_dir = hf_config.get("logfiles_dir")

    # Flags/Keyword für die Entscheidung IM JSX
    keyword_check_enabled = hf_config.get("keyword_check_enabled", False)
    keyword_check_word = hf_config.get("keyword_check_word", "")

    # Beide Sets IMMER durchreichen (JSX entscheidet Standard vs. Keyword-based)
    required_layers = hf_config.get("required_layers", []) or []
    required_metadata = hf_config.get("required_metadata", []) or []
    keyword_layers = hf_config.get("keyword_layers", []) or []
    keyword_metadata = hf_config.get("keyword_metadata", []) or []

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
        debug_print(f"Opened {file_path} in Photoshop (open -a).")
    else:
        debug_print(f"Failed to open {file_path} in Photoshop.")

    # Dynamisches JSX mit BEIDEN Sets erzeugen (aus dynamic_jsx_generator.py)
    tmp_jsx_path = create_temp_jsx_with_config(
        base_jsx_path=contentcheck_jsx_path,
        keyword_check_enabled=keyword_check_enabled,
        keyword_check_word=keyword_check_word,
        required_layers=required_layers,
        required_metadata=required_metadata,
        keyword_layers=keyword_layers,
        keyword_metadata=keyword_metadata,
        logfiles_dir=logfiles_dir,
        debug_output=False,
    )
    if not tmp_jsx_path:
        debug_print("Could not create dynamic JSX. Aborting content check.")
        dest = os.path.join(fault_dir, os.path.basename(file_path))
        move_file(file_path, dest)
        if on_status_update:
            on_status_update(f"Processed (no script): {os.path.basename(file_path)}", True)
        send_fail_email_from_content({}, file_path)
        return

    if run_jsx_in_photoshop(tmp_jsx_path):
        debug_print(f"Executed JSX script: {tmp_jsx_path}")
    else:
        debug_print(f"Failed to execute JSX script: {tmp_jsx_path}")

    # Temp-Datei entfernen
    try:
        os.remove(tmp_jsx_path)
    except Exception as e:
        debug_print(f"Error removing temporary JSX script {tmp_jsx_path}: {e}")

    # Logfile abwarten (max. 10s)
    baseName = os.path.basename(file_path).rsplit(".", 1)[0]
    contentLogPath = os.path.join(logfiles_dir, baseName + "_01_log_contentcheck.json")
    timeout = 10.0
    waited = 0.0
    interval = 0.5
    while not os.path.exists(contentLogPath) and waited < timeout:
        time.sleep(interval)
        waited += interval
    if waited >= timeout:
        debug_print(f"Timeout: Logfile {contentLogPath} wurde nach {timeout} Sekunden nicht gefunden.")

    contentCheck = read_json_file(contentLogPath)
    debug_print(f"ContentCheck Log ({contentLogPath}): {contentCheck}")

    # Erfolg/Fehlschlag entscheiden
    if contentCheck:
        details = contentCheck.get("details", {})
        layerStatus = details.get("layerStatus", "FAIL")
        metaStatus = details.get("metaStatus", "FAIL")
        if layerStatus == "OK" and metaStatus == "OK":
            dest_dir = success_dir
            debug_print("Contentcheck OK: Datei -> Success")

            # Produktions-JSX: jetzt mit automatischer Recipe-Injektion
            selected_jsx = hf_config.get("selected_jsx", "")
            additional_jsx = hf_config.get("additional_jsx", "")

            if selected_jsx:
                debug_print(f"Running selected JSX script (with optional recipe injection): {selected_jsx}")
                if not _run_jsx_with_recipe_injection(selected_jsx, debug_output=False):
                    debug_print(f"Failed to execute selected_jsx: {selected_jsx}")

            if additional_jsx:
                debug_print(f"Running additional JSX script (with optional recipe injection): {additional_jsx}")
                if not _run_jsx_with_recipe_injection(additional_jsx, debug_output=False):
                    debug_print(f"Failed to execute additional_jsx: {additional_jsx}")

        else:
            dest_dir = fault_dir
            debug_print("Contentcheck FAIL: Datei -> Fault")
            send_fail_email_from_content(contentCheck, file_path)
    else:
        dest_dir = fault_dir
        debug_print("No Contentcheck Log found: Datei -> Fault")
        send_fail_email_from_content({}, file_path)

    # PS-Dokument schließen (ohne Speichern)
    if not close_current_document_in_photoshop():
        debug_print("Error closing document in Photoshop.")

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
    Überwacht ein Verzeichnis (monitor_dir) und verarbeitet neu hinzugefügte Dateien.
    Schaltet in den Idle-Modus, wenn für einen bestimmten Zeitraum keine Dateien gefunden werden.
    Hinweis: Auto-Delete/Retention wird NICHT mehr vom Monitor durchgeführt, sondern ausschließlich
    vom plan_cleaner.py (logbasiert).
    """
    def __init__(self, hf_config, parent=None, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir")
        self.success_dir = hf_config.get("success_dir")
        self.fault_dir = hf_config.get("fault_dir")
        self.logfiles_dir = hf_config.get("logfiles_dir")

        # Checkbox-/Stundenwerte bleiben in der HF-Konfig erhalten und werden vom plan_cleaner.py genutzt.
        self.auto_delete_success_enabled = hf_config.get("auto_delete_success_enabled", False)
        self.auto_delete_success_hours = int(hf_config.get("auto_delete_success_hours", 24))
        self.auto_delete_fault_enabled = hf_config.get("auto_delete_fault_enabled", False)
        self.auto_delete_fault_hours = int(hf_config.get("auto_delete_fault_hours", 72))

        jsx_folder = hf_config.get("jsx_folder")
        if jsx_folder and os.path.isdir(jsx_folder):
            candidate = os.path.join(jsx_folder, "contentcheck_template.jsx")
            if os.path.exists(candidate):
                self.contentcheck_jsx_path = candidate
            else:
                self.contentcheck_jsx_path = os.path.join(
                    os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx"
                )
        else:
            self.contentcheck_jsx_path = os.path.join(
                os.path.dirname(__file__), "jsx_templates", "contentcheck_template.jsx"
            )

        self.selected_jsx = hf_config.get("selected_jsx", "")
        self.additional_jsx = hf_config.get("additional_jsx", "")
        self.parent = parent
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing
        self._running = False
        self._thread = None
        self.last_activity_time = time.time()
        self.idle = False

        # Früher: Rate-Limit und Aufruf der Auto-Delete-Routine hier.
        # Jetzt: KEIN Auto-Delete mehr im Monitor – ausschließlich plan_cleaner.py!

    @property
    def active(self):
        return self._running

    def _monitor_loop(self):
        processed_files = set()

        # Klarer Hinweis beim Start: Retention läuft NICHT hier.
        debug_print("[Retention] HotfolderMonitor: Auto-Delete im Monitor deaktiviert – "
                    "Retention erfolgt durch plan_cleaner.py (logbasiert).")

        while self._running:
            try:
                files_found = False

                # KEIN Auto-Delete mehr hier!

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

                            process_file(
                                file_path,
                                self.hf_config,
                                self.contentcheck_jsx_path,
                                on_status_update=self.on_status_update,
                            )
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

    def run_auto_delete_now(self):
        """
        (Legacy-Hook) – bleibt aus Kompatibilitätsgründen erhalten, macht aber nichts mehr.
        """
        debug_print("[Retention] run_auto_delete_now() ignoriert – Retention läuft über plan_cleaner.py.")

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
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    hf_config = {
        "monitor_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/01_Monitor/11_BoYinRa",
        "success_dir": "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/02_Success",
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
        "keyword_metadata": ["author", "description"],
        # Diese Flags werden NICHT mehr vom Monitor benutzt – nur noch vom plan_cleaner.py
        "auto_delete_success_enabled": False,
        "auto_delete_success_hours": 24,
        "auto_delete_fault_enabled": False,
        "auto_delete_fault_hours": 72,
    }
    monitor = HotfolderMonitor(hf_config)
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()