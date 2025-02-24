#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
from utils.utils import debug_print

LOGFILE_PATH = os.path.join("logs", "global_log.json")

def _ensure_log_structure():
    """
    Stellt sicher, dass global_log.json existiert und die folgende Struktur besitzt:
    {
      "log_counter": 1,
      "entries": []
    }
    Gibt das geladene Dictionary zurück.
    """
    if not os.path.exists(LOGFILE_PATH):
        os.makedirs(os.path.dirname(LOGFILE_PATH), exist_ok=True)
        initial_data = {
            "log_counter": 1,
            "entries": []
        }
        with open(LOGFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=4, ensure_ascii=False)
        return initial_data
    else:
        try:
            with open(LOGFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "log_counter" not in data or "entries" not in data:
                data = {"log_counter": 1, "entries": []}
        except Exception as e:
            debug_print(f"Fehler beim Laden von {LOGFILE_PATH}: {e}")
            data = {"log_counter": 1, "entries": []}
        return data

def load_global_log() -> list:
    """
    Lädt die Einträge aus global_log.json und gibt die Liste zurück.
    """
    data = _ensure_log_structure()
    return data.get("entries", [])

def save_global_log(data: dict):
    """
    Speichert das gesamte Log-Dictionary (log_counter und entries) in global_log.json.
    """
    os.makedirs(os.path.dirname(LOGFILE_PATH), exist_ok=True)
    try:
        with open(LOGFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        debug_print("Globales Log gespeichert.")
    except Exception as e:
        debug_print(f"Fehler beim Speichern des globalen Logs: {e}")

def append_log_entry(entry: dict):
    """
    Fügt einen neuen Eintrag hinzu. Die fortlaufende 7-stellige ID wird basierend auf log_counter vergeben.
    """
    data = _ensure_log_structure()
    counter = data.get("log_counter", 1)
    entry["id"] = str(counter).zfill(7)  # z. B. "0000001"
    data["log_counter"] = counter + 1
    data["entries"].append(entry)
    save_global_log(data)
    debug_print(f"Neuer Eintrag angehängt: ID={entry['id']}")

def reset_global_log():
    """
    Setzt das globale Log zurück: log_counter = 1 und entries = [].
    """
    new_data = {"log_counter": 1, "entries": []}
    save_global_log(new_data)
    debug_print("Globales Logfile zurückgesetzt.")