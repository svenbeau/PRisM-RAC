import os
import json
import uuid
from utils.path_manager import get_hotfolder_config_path

def debug_print(msg):
    print(f"[DEBUG] {msg}")

class HotfolderConfigManager:
    """
    Manager für die Hotfolder-Konfiguration.
    Die Konfiguration wird ausschließlich in der Datei
    hotfolder_config.json im Konfigurationsverzeichnis gespeichert.
    """
    def __init__(self):
        self.config_file = get_hotfolder_config_path()
        self.data = {"hotfolders": []}
        self.load_config()

    def load_config(self):
        """
        Lädt die Hotfolder-Konfiguration aus hotfolder_config.json.
        Falls die Datei nicht existiert, wird ein leeres Dict zurückgegeben.
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                debug_print(f"Error loading hotfolder config {self.config_file}: {e}")
        else:
            self.save_config()

    def save_config(self):
        """
        Speichert die aktuelle Hotfolder-Konfiguration in hotfolder_config.json.
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            debug_print(f"Error saving hotfolder config {self.config_file}: {e}")

    def get_hotfolders(self):
        return self.data.get("hotfolders", [])

    def add_hotfolder(self, hotfolder):
        self.data.setdefault("hotfolders", []).append(hotfolder)
        self.save_config()

    def remove_hotfolder(self, hotfolder_id):
        hotfolders = self.data.get("hotfolders", [])
        self.data["hotfolders"] = [hf for hf in hotfolders if hf.get("id") != hotfolder_id]
        self.save_config()

    def update_hotfolder(self, hotfolder_id, updated_data):
        for hf in self.data.get("hotfolders", []):
            if hf.get("id") == hotfolder_id:
                hf.update(updated_data)
                break
        self.save_config()

    def get_hotfolder_by_id(self, hotfolder_id):
        for hf in self.data.get("hotfolders", []):
            if hf.get("id") == hotfolder_id:
                return hf
        return None

    def generate_hotfolder_id(self):
        return str(uuid.uuid4())

    def export_hotfolders(self, export_path):
        try:
            hotfolders = self.data.get("hotfolders", [])
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(hotfolders, f, indent=4, ensure_ascii=False)
            debug_print("Hotfolders exported successfully.")
        except Exception as e:
            debug_print(f"Error exporting hotfolders to {export_path}: {e}")

    def import_hotfolders(self, import_path):
        try:
            if os.path.exists(import_path):
                with open(import_path, "r", encoding="utf-8") as f:
                    hotfolders = json.load(f)
                self.data["hotfolders"] = hotfolders
                self.save_config()
                debug_print("Hotfolders imported successfully.")
            else:
                debug_print(f"Import file not found: {import_path}")
        except Exception as e:
            debug_print(f"Error importing hotfolders from {import_path}: {e}")