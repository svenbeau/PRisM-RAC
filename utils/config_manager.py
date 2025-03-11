import os
import json
from utils.path_manager import get_settings_path

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

def get_recent_dirs(category):
    """
    Liest aus 'settings.json' unter dem Schlüssel "recent_paths" (als Dictionary)
    die Liste der zuletzt verwendeten Verzeichnisse für die gegebene Kategorie.
    Falls für die Kategorie nichts vorhanden ist, wird als Fallback [os.path.expanduser("~")] zurückgegeben.
    Beispielkategorien: "monitor", "success", "fault", "logfiles"
    """
    settings = load_settings()
    recent_paths = settings.get("recent_paths", {})
    return recent_paths.get(category, [os.path.expanduser("~")])

def update_recent_dirs(category, new_dir):
    """
    Aktualisiert die Liste der zuletzt verwendeten Verzeichnisse für die angegebene Kategorie in 'settings.json'.
    Wenn new_dir noch nicht in der Liste vorhanden ist, wird er an den Anfang der Liste eingefügt.
    Die Liste wird auf maximal 10 Einträge begrenzt.
    Anschließend werden die aktualisierten Einstellungen gespeichert.
    """
    settings = load_settings()
    recent_paths = settings.get("recent_paths", {})
    current_list = recent_paths.get(category, [])
    if new_dir not in current_list:
        current_list.insert(0, new_dir)
        current_list = current_list[:10]
    recent_paths[category] = current_list
    settings["recent_paths"] = recent_paths
    save_settings(settings)