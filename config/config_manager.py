#!/usr/bin/env python3
"""
Config Manager for PRisM-RAC.
Handles loading and saving persistent settings to settings.json.
"""

import os
import json
import time

# Bestimme den Basisordner (das Projektverzeichnis)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# Standardpfade relativ zum Projektstamm
DEFAULT_PATHS = {
    "scripts": os.path.join(BASE_DIR, "scripts"),
    "jsx_templates": os.path.join(BASE_DIR, "jsx_templates"),
    "config": os.path.join(BASE_DIR, "config"),
    "logs": os.path.join(BASE_DIR, "logs")
}

def debug_print(message):
    """
    Gibt eine Debug-Nachricht aus.
    """
    print("[DEBUG]", message)

def load_settings():
    """
    Lädt die Einstellungen aus der persistenten settings.json.

    Returns:
        dict: Das Dictionary mit den geladenen Einstellungen.
    """
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        # Falls der Schlüssel resource_paths noch nicht existiert, setze ihn auf die Standardwerte
        if "resource_paths" not in settings:
            settings["resource_paths"] = DEFAULT_PATHS.copy()
        return settings
    except Exception as e:
        debug_print(f"Error loading settings from {SETTINGS_FILE}: {e}")
        return {"resource_paths": DEFAULT_PATHS.copy()}

def save_settings(settings):
    """
    Speichert das übergebene Settings-Dictionary in die persistent settings.json.

    Args:
        settings (dict): Die Einstellungen, die gespeichert werden sollen.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        debug_print(f"Settings saved to {SETTINGS_FILE}.")
    except Exception as e:
        debug_print(f"Error saving settings to {SETTINGS_FILE}: {e}")

def get_recent_dirs(settings):
    """
    Gibt die Liste der zuletzt verwendeten Verzeichnisse zurück.

    Args:
        settings (dict or str): Wenn ein Dictionary, wird direkt nach dem Schlüssel "recent_dirs" gesucht.
                                 Wenn ein String übergeben wird, wird settings.json geladen.

    Returns:
        list: Liste der zuletzt verwendeten Verzeichnisse oder eine leere Liste, falls nicht vorhanden.
    """
    if isinstance(settings, str):
        loaded = load_settings()
        return loaded.get("recent_dirs", [])
    elif isinstance(settings, dict):
        return settings.get("recent_dirs", [])
    else:
        return []

def update_recent_dirs(settings, new_dir):
    """
    Fügt ein neues Verzeichnis in die Liste der zuletzt verwendeten Verzeichnisse ein,
    falls es noch nicht vorhanden ist, und gibt das aktualisierte Settings-Dictionary zurück.

    Args:
        settings (dict): Das Settings-Dictionary.
        new_dir (str): Das neue Verzeichnis, das hinzugefügt werden soll.

    Returns:
        dict: Das aktualisierte Settings-Dictionary.
    """
    recent_dirs = settings.get("recent_dirs", [])
    if new_dir not in recent_dirs:
        recent_dirs.append(new_dir)
        settings["recent_dirs"] = recent_dirs
    return settings

def get_resource_path(key):
    """
    Gibt den Ressourcypfad zurück, der dem übergebenen Schlüssel zugeordnet ist.

    Args:
        key (str): Der Schlüssel für den Ressourcypfad.

    Returns:
        str: Der Ressourcypfad.
    """
    settings = load_settings()
    return settings.get("resource_paths", {}).get(key, DEFAULT_PATHS.get(key, ""))

def update_resource_path(key, new_path):
    """
    Aktualisiert den Ressourcypfad für den übergebenen Schlüssel und speichert die Einstellungen.

    Args:
        key (str): Der Schlüssel für die Ressource.
        new_path (str): Der neue Pfad, der gesetzt werden soll.

    Returns:
        str: Der aktualisierte Pfad.
    """
    settings = load_settings()
    settings.setdefault("resource_paths", {})[key] = new_path
    save_settings(settings)
    return new_path

def get_base_dir():
    """
    Gibt den Basisordner des Projekts zurück.

    Returns:
        str: Der Basisordner.
    """
    return BASE_DIR

if __name__ == "__main__":
    # Testcode: Einstellungen laden, einen Testwert hinzufügen und wieder speichern.
    settings = load_settings()
    debug_print("Loaded settings:")
    debug_print(json.dumps(settings, indent=4))
    # Beispiel: Füge den aktuellen Arbeitsordner als recent_dir hinzu.
    import os
    current_dir = os.getcwd()
    settings = update_recent_dirs(settings, current_dir)
    settings["last_saved"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_settings(settings)