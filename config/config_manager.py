#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

# Pfad zur settings.json relativ zum config-Ordner
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "settings.json")

def load_settings():
    """Lädt die Einstellungen aus settings.json. Gibt ein Dictionary zurück."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Error loading settings: {e}")
        return {}

def save_settings(settings: dict):
    """Speichert die Einstellungen in settings.json."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        debug_print("Settings saved.")
    except Exception as e:
        debug_print(f"Error saving settings: {e}")

def get_recent_dirs(folder_type: str) -> list:
    """
    Gibt eine Liste der zuletzt verwendeten Ordner für den angegebenen Typ zurück.
    Mögliche Typen: "monitor", "success", "fault", "logfiles"
    """
    settings = load_settings()
    recent = settings.setdefault("recent_paths", {
        "monitor": [],
        "success": [],
        "fault": [],
        "logfiles": []
    })
    return recent.get(folder_type, [])

def update_recent_dirs(folder_type: str, new_path: str):
    """
    Aktualisiert die Liste der zuletzt verwendeten Ordner für den angegebenen Typ,
    indem new_path an den Anfang gesetzt wird (maximal 5 Einträge).
    """
    settings = load_settings()
    recent = settings.setdefault("recent_paths", {
        "monitor": [],
        "success": [],
        "fault": [],
        "logfiles": []
    })
    if new_path in recent.get(folder_type, []):
        recent[folder_type].remove(new_path)
    recent.setdefault(folder_type, []).insert(0, new_path)
    recent[folder_type] = recent[folder_type][:5]
    save_settings(settings)