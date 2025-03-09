# utils/config_manager.py

import os
import json
import uuid
from utils.path_manager import get_config_path, get_settings_path


class ConfigManager:
    def __init__(self):
        # Bisheriger Verweis auf script_config.json
        self.config_file = get_config_path()
        self.data = {
            "hotfolders": []
        }
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.save_config()
        except Exception as e:
            print(f"Error loading config file {self.config_file}: {e}")

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config file {self.config_file}: {e}")

    def get_hotfolders(self):
        return self.data.get("hotfolders", [])

    def add_hotfolder(self, hotfolder):
        self.data.setdefault("hotfolders", []).append(hotfolder)
        self.save_config()

    def remove_hotfolder(self, hotfolder_id):
        hotfolders = self.data.get("hotfolders", [])
        new_list = [hf for hf in hotfolders if hf.get("id") != hotfolder_id]
        self.data["hotfolders"] = new_list
        self.save_config()

    def update_hotfolder(self, hotfolder_id, updated_data):
        hotfolders = self.data.get("hotfolders", [])
        for hf in hotfolders:
            if hf.get("id") == hotfolder_id:
                hf.update(updated_data)
                break
        self.save_config()

    def get_hotfolder_by_id(self, hotfolder_id):
        hotfolders = self.data.get("hotfolders", [])
        for hf in hotfolders:
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
            print("Hotfolders exported successfully.")
        except Exception as e:
            print(f"Error exporting hotfolders to {export_path}: {e}")

    def import_hotfolders(self, import_path):
        try:
            if os.path.exists(import_path):
                with open(import_path, "r", encoding="utf-8") as f:
                    hotfolders = json.load(f)
                self.data["hotfolders"] = hotfolders
                self.save_config()
                print("Hotfolders imported successfully.")
            else:
                print(f"Import file not found: {import_path}")
        except Exception as e:
            print(f"Error importing hotfolders from {import_path}: {e}")


#
# ========== Existierende Top-Level-Funktionen für Settings (aus früherer Anpassung) ==========
#

def load_settings():
    """
    Lädt 'settings.json' aus ~/Library/Application Support/PRisM-CC/
    und gibt den Inhalt als Dict zurück.
    """
    path = get_settings_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            debug_print(f"Error reading settings.json: {e}")
    return {}


def save_settings(data):
    """
    Speichert das Dict 'data' in 'settings.json'
    unter ~/Library/Application Support/PRisM-CC/.
    """
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        debug_print(f"Error saving settings.json: {e}")


def debug_print(msg):
    """
    Einfacher Debug-Print, kann nach Bedarf angepasst werden.
    """
    print(f"[DEBUG] {msg}")


#
# ========== NEU: Diese beiden Funktionen ergänzen wir, um den ImportError zu beheben. ==========
#

def get_recent_dirs():
    """
    Liest die Liste der 'recent_dirs' aus settings.json (wenn vorhanden)
    und gibt sie als Liste zurück.
    """
    settings = load_settings()
    return settings.get("recent_dirs", [])


def update_recent_dirs(new_dir):
    """
    Aktualisiert die 'recent_dirs' in settings.json, damit
    z.B. zuletzt genutzte Verzeichnisse gespeichert werden.

    Konkrete Logik kannst du anpassen:
    - Du könntest begrenzen, wie viele Pfade du speicherst.
    - Du könntest Duplikate entfernen etc.
    """
    settings = load_settings()
    recent = settings.get("recent_dirs", [])

    # Beispielhafte Logik: füge den Pfad hinzu, wenn er nicht vorhanden ist
    if new_dir not in recent:
        recent.insert(0, new_dir)

        # Option: Begrenze auf 10 Einträge (nur ein Beispiel)
        recent = recent[:10]

    settings["recent_dirs"] = recent
    save_settings(settings)