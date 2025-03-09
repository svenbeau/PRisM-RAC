# utils/log_manager.py

import os
import json
from datetime import datetime
from utils.path_manager import get_log_path

class LogManager:
    def __init__(self):
        self.log_file_path = get_log_path()
        self.log_data = {
            "log_counter": 0,
            "entries": []
        }
        self.load_log()

    def load_log(self):
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    self.log_data = json.load(f)
            except Exception as e:
                print(f"Error reading log file {self.log_file_path}: {e}")
        else:
            self.save_log()

    def save_log(self):
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                json.dump(self.log_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving log file {self.log_file_path}: {e}")

    def add_entry(self, filename, metadata, check_type, status, applied_script, details):
        self.log_data["log_counter"] += 1
        entry_id = f"{self.log_data['log_counter']:07d}"
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "metadata": metadata,
            "checkType": check_type,
            "status": status,
            "applied_script": applied_script,
            "details": details,
            "id": entry_id
        }
        self.log_data["entries"].append(new_entry)
        self.save_log()

    def get_all_entries(self):
        return self.log_data.get("entries", [])

    def get_log_counter(self):
        return self.log_data.get("log_counter", 0)

    def find_entries_by_filename(self, filename):
        return [entry for entry in self.log_data.get("entries", []) if entry["filename"] == filename]

    def clear_log(self):
        self.log_data["log_counter"] = 0
        self.log_data["entries"] = []
        self.save_log()

    def remove_entry_by_id(self, entry_id):
        entries = self.log_data.get("entries", [])
        filtered_entries = [e for e in entries if e["id"] != entry_id]
        self.log_data["entries"] = filtered_entries
        self.save_log()


#
# === NEUE Top-Level-Funktionen, um den Import-Fehler zu beheben ===
#
def load_global_log():
    """
    Lädt den kompletten globalen Log (log_data) mittels einer
    LogManager-Instanz und gibt diesen zurück.
    """
    lm = LogManager()
    return lm.log_data

def reset_global_log():
    """
    Setzt den globalen Log zurück, indem clear_log() aufgerufen wird.
    """
    lm = LogManager()
    lm.clear_log()