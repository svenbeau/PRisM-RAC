#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from utils.path_manager import get_log_path
from utils.config_manager import debug_print

def load_global_log():
    """
    Lädt das globale Log aus ~/Library/Application Support/PRisM-CC/logs/global_log.json
    und gibt eine Liste von Einträgen zurück.
    Wenn die Datei nicht existiert oder 'entries' nicht vorhanden ist, wird eine leere Liste zurückgegeben.
    """
    path = get_log_path()
    if not os.path.exists(path):
        debug_print(f"Global log file not found at {path}. Returning empty list.")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Wir gehen davon aus, dass data so aussieht:
        # {
        #   "log_counter": 123,
        #   "entries": [ {...}, {...}, ... ]
        # }
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            debug_print("Warning: 'entries' in global_log.json ist kein Array. Gebe leere Liste zurück.")
            return []
        return entries
    except Exception as e:
        debug_print(f"Error reading global log: {e}")
        return []

def save_global_log(entries):
    """
    Speichert die übergebene Liste von Einträgen in ~/Library/Application Support/PRisM-CC/logs/global_log.json.
    Zusätzlich kannst du bei Bedarf 'log_counter' oder andere Felder aktualisieren.
    """
    path = get_log_path()
    log_data = {
        "log_counter": len(entries),
        "entries": entries
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        debug_print(f"Error saving global log: {e}")

def reset_global_log():
    """
    Setzt das globale Log zurück (leert es), indem eine leere Liste von Einträgen geschrieben wird.
    """
    debug_print("Resetting global log...")
    path = get_log_path()
    log_data = {
        "log_counter": 0,
        "entries": []
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        debug_print(f"Error resetting global log: {e}")

def add_log_entry(entry):
    """
    Beispiel-Funktion: Fügt einen neuen Eintrag hinzu.
    Hier könntest du 'timestamp' oder 'id' generieren und dann in entries einfügen.
    """
    entries = load_global_log()
    entries.append(entry)
    save_global_log(entries)