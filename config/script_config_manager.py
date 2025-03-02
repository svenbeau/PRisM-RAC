#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

def load_script_config(settings):
    """
    Lädt script_config.json aus dem 'config'-Ordner oder aus dem Pfad, der in settings gespeichert ist.
    Gibt ein Dict zurück: {"scripts": [...]}
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    debug_print(f"BASE_DIR: {base_dir}")

    # Falls Du in settings einen Schlüssel 'script_config_path' hast:
    script_config_path = settings.get("script_config_path", "")
    if not script_config_path:
        # Standardpfad
        script_config_path = os.path.join(base_dir, "config", "script_config.json")

    debug_print(f"Script Config File will be stored at: {script_config_path}")

    if not os.path.isfile(script_config_path):
        debug_print("script_config.json nicht gefunden, erzeuge leere Struktur.")
        return {"scripts": []}

    try:
        with open(script_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        debug_print("Script Config loaded successfully.")
        return data
    except Exception as e:
        debug_print(f"Fehler beim Laden script_config.json: {e}")
        return {"scripts": []}

def save_script_config(data, settings):
    """
    Speichert das Dict 'data' in script_config.json.
    Nutzt den Pfad aus settings['script_config_path'] oder <base>/config/script_config.json
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_config_path = settings.get("script_config_path", "")
    if not script_config_path:
        script_config_path = os.path.join(base_dir, "config", "script_config.json")

    try:
        with open(script_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        debug_print("Script configuration saved.")
    except Exception as e:
        debug_print(f"Fehler beim Speichern script_config.json: {e}")