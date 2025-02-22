import os
import time
import threading
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dynamic_jsx_generator import generate_jsx_script
from utils import debug_print, open_in_photoshop, run_jsx_in_photoshop, move_file, is_file_stable

class HotfolderEventHandler(FileSystemEventHandler):
    def __init__(self, hf_config, on_status_update=None, on_file_processing=None):
        super().__init__()
        self.hf_config = hf_config
        # Falls vorhanden, Callback-Funktionen speichern
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing

    def process_file(self, file_path: str):
        # Verhindere Mehrfachverarbeitung einer Datei
        processed = self.hf_config.setdefault("processed_files", set())
        if file_path in processed:
            debug_print(f"Datei {file_path} wurde bereits verarbeitet. Überspringe.")
            return
        processed.add(file_path)

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

        # Auswertung des Logfiles gemäß neuer JSON-Struktur
        criteria_met = True
        var_missing = {}
        if "layers" in contentcheck:
            # Falls das Logfile einen "layers"-Key enthält, wird davon ausgegangen, dass bestimmte Ebenen fehlen.
            criteria_met = False
            var_missing["layers"] = contentcheck["layers"]
        elif "metadata" in contentcheck:
            metadata = contentcheck["metadata"]
            required_fields = self.hf_config.get("required_metadata", [])
            for field in required_fields:
                value = str(metadata.get(field, "")).strip().lower()
                if value == "undefined" or value == "":
                    criteria_met = False
                    var_missing[field] = metadata.get(field, "undefined")
        else:
            criteria_met = False
            var_missing["error"] = "Unbekannte JSON-Struktur"

        if criteria_met:
            debug_print("Contentcheck erfolgreich. Verschiebe Datei in Success.")
            additional_jsx = self.hf_config.get("additional_jsx", "").strip()
            if additional_jsx and os.path.exists(additional_jsx):
                add_success = run_jsx_in_photoshop(additional_jsx)
                if not add_success:
                    debug_print("Zusätzliches JSX-Skript schlug fehl (wird aber ignoriert).")
            success_dir = self.hf_config.get("success_dir", "")
            move_file(file_path, success_dir)
        else:
            debug_print("Contentcheck fehlgeschlagen. Fehlende Kriterien: " + json.dumps(var_missing))
            fail_log_file = os.path.join(logfiles_dir, file_name.rsplit(".", 1)[0] + "_log_fail.json")
            with open(fail_log_file, "w", encoding="utf-8") as f:
                json.dump(var_missing, f, indent=4, ensure_ascii=False)
            fault_dir = self.hf_config.get("fault_dir", "")
            move_file(file_path, fault_dir)

        if self.on_file_processing:
            self.on_file_processing(None)

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

class HotfolderMonitor:
    def __init__(self, hf_config: dict, on_status_update=None, on_file_processing=None):
        self.hf_config = hf_config
        self.monitor_dir = hf_config.get("monitor_dir", "")
        self.observer = Observer()
        self.event_handler = HotfolderEventHandler(
            hf_config,
            on_status_update=on_status_update,
            on_file_processing=on_file_processing
        )
        self.active = False

    def start(self):
        if not os.path.exists(self.monitor_dir):
            debug_print("Hotfolder does not exist: " + self.monitor_dir)
            return
        for root, dirs, files in os.walk(self.monitor_dir):
            for file in files:
                file_path = os.path.join(root, file)
                self.event_handler.process_file(file_path)
        self.observer.schedule(self.event_handler, self.monitor_dir, recursive=True)
        self.observer.start()
        debug_print("Observer started on: " + self.monitor_dir)
        self.active = True

    def stop(self):
        self.observer.stop()
        self.observer.join()
        debug_print("Observer stopped.")
        self.active = False

    def worker_loop(self):
        while True:
            time.sleep(1)