import os
import json
from utils.path_manager import get_settings_path

def debug_print(msg):
    print("[DEBUG]", msg)

def migrate_settings(settings):
    """
    Entfernt alle Schlüssel, die nicht mehr benötigt werden,
    und stellt sicher, dass 'recent_dirs' als Dictionary (für Hotfolder)
    und 'recent_json_dirs' als Liste (für den JSON-Explorer) existieren.
    Zudem behalten wir in 'resource_paths' nur die relevanten Einträge.
    """
    # Liste der veralteten Schlüssel, die entfernt werden sollen
    keys_to_remove = [
        "hotfolders",
        "script_configs",
        "scripts",
        "global_config",
        "script_json_map",
        "recentScriptPaths",
        "scriptPaths",
        "script_json_mapping",
        "script_settings",
        "renderConfig",
        "scriptsConfig",
        "scriptRecipeMappings",
        "global_script_folder",
        "scripts_base_folder"
    ]
    for key in keys_to_remove:
        if key in settings:
            debug_print(f"Removing key '{key}' from settings.")
            del settings[key]

    #
    # 1) Für die Hotfolder: recent_dirs als Dictionary
    #
    recent = settings.get("recent_dirs", {})
    if not isinstance(recent, dict):
        # Wir legen leere Listen an, damit wir nicht versehentlich
        # Strings als Ordner interpretieren.
        recent = {
            "monitor": [os.path.expanduser("~")],
            "success": [os.path.expanduser("~")],
            "fault":   [os.path.expanduser("~")],
            "logfiles":[os.path.expanduser("~")]
        }
    else:
        # Stelle sicher, dass alle 4 Kategorien vorhanden sind
        for cat in ["monitor", "success", "fault", "logfiles"]:
            if cat not in recent:
                recent[cat] = [os.path.expanduser("~")]
    settings["recent_dirs"] = recent

    #
    # 2) Für den JSON-Explorer: recent_json_dirs als Liste
    #
    if "recent_json_dirs" not in settings:
        # Standardmäßig ein Eintrag: Home-Verzeichnis
        settings["recent_json_dirs"] = [os.path.expanduser("~")]
    else:
        # Stelle sicher, dass recent_json_dirs wirklich eine Liste ist
        if not isinstance(settings["recent_json_dirs"], list):
            settings["recent_json_dirs"] = [os.path.expanduser("~")]

    #
    # 3) resource_paths: Nur relevanten Eintrag behalten
    #
    if "resource_paths" in settings:
        resource_paths = settings["resource_paths"]
        new_resource_paths = {}
        if "jsx_templates" in resource_paths:
            new_resource_paths["jsx_templates"] = resource_paths["jsx_templates"]
        settings["resource_paths"] = new_resource_paths
    else:
        settings["resource_paths"] = {}

    return settings

def load_settings():
    """
    Lädt die Einstellungen aus settings.json, führt die Migration durch
    und speichert die bereinigten Daten sofort wieder.
    """
    path = get_settings_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception as e:
            debug_print(f"Error reading settings.json: {e}")
            settings = {}
    else:
        settings = {}
    settings = migrate_settings(settings)
    save_settings(settings)
    return settings

def save_settings(data):
    """
    Schreibt 'data' in die settings.json.
    """
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        debug_print(f"Error saving settings.json: {e}")

#
# ========== Hotfolder-Funktionen (Dictionary) ==========
#
def get_recent_dirs(category):
    """
    Liefert die Liste der zuletzt verwendeten Verzeichnisse für die angegebene Kategorie
    (z. B. 'monitor', 'success', 'fault', 'logfiles') für Hotfolder.
    """
    settings = load_settings()
    recent = settings.get("recent_dirs", {})
    return recent.get(category, [os.path.expanduser("~")])

def update_recent_dirs(category, new_dir):
    """
    Aktualisiert die Liste der zuletzt verwendeten Verzeichnisse für die angegebene Kategorie
    (z. B. 'monitor', 'success', 'fault', 'logfiles') in der settings.json.
    """
    settings = load_settings()
    recent = settings.get("recent_dirs", {})
    if category not in recent:
        recent[category] = []
    if new_dir not in recent[category]:
        recent[category].insert(0, new_dir)
        recent[category] = recent[category][:10]
    settings["recent_dirs"] = recent
    save_settings(settings)

#
# ========== JSON-Explorer-Funktionen (Liste) ==========
#
def get_recent_json_dirs():
    """
    Gibt die Liste der zuletzt verwendeten Verzeichnisse für den JSON-Explorer zurück.
    """
    settings = load_settings()
    if "recent_json_dirs" not in settings:
        settings["recent_json_dirs"] = [os.path.expanduser("~")]
        save_settings(settings)
    return settings["recent_json_dirs"]

def update_recent_json_dirs(new_dir):
    """
    Fügt 'new_dir' an erster Stelle in die Liste der zuletzt verwendeten Verzeichnisse
    für den JSON-Explorer ein, begrenzt die Liste auf 10 Einträge und speichert.
    """
    settings = load_settings()
    if "recent_json_dirs" not in settings:
        settings["recent_json_dirs"] = []
    if new_dir not in settings["recent_json_dirs"]:
        settings["recent_json_dirs"].insert(0, new_dir)
        settings["recent_json_dirs"] = settings["recent_json_dirs"][:10]
    save_settings(settings)