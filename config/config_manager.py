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
        return settings
    except Exception as e:
        debug_print(f"Error loading settings from {SETTINGS_FILE}: {e}")
        return {}


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