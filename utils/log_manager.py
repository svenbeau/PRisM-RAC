#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
from utils.path_manager import get_log_path
from utils.config_manager import debug_print


def ensure_log_directory_exists():
    """
    Stellt sicher, dass der Ordner für die Logdatei existiert.
    """
    path = get_log_path()
    log_dir = os.path.dirname(path)
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            debug_print(f"[LOG_MANAGER] Created log directory: {log_dir}")
        except Exception as e:
            debug_print(f"[LOG_MANAGER] Error creating log directory {log_dir}: {e}")


def load_global_log():
    """
    Lädt das globale Log aus ~/Library/Application Support/PRisM-CC/logs/global_log.json
    und gibt eine Liste von Einträgen zurück.
    Wenn die Datei nicht existiert oder 'entries' nicht vorhanden ist, wird eine leere Liste zurückgegeben.
    """
    ensure_log_directory_exists()
    path = get_log_path()
    if not os.path.exists(path):
        debug_print(f"[LOG_MANAGER] Global log file not found at {path}. Returning empty list.")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            debug_print("[LOG_MANAGER] Warning: 'entries' in global_log.json is not a list. Returning empty list.")
            return []
        debug_print(f"[LOG_MANAGER] Loaded {len(entries)} log entries from {path}")
        return entries
    except Exception as e:
        debug_print(f"[LOG_MANAGER] Error reading global log: {e}")
        return []


def save_global_log(entries):
    """
    Speichert die übergebene Liste von Einträgen in ~/Library/Application Support/PRisM-CC/logs/global_log.json.
    Zusätzlich wird 'log_counter' aktualisiert.
    """
    ensure_log_directory_exists()
    path = get_log_path()
    log_data = {
        "log_counter": len(entries),
        "entries": entries
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        debug_print(f"[LOG_MANAGER] Global log saved successfully to {path}. Log count: {len(entries)}")
        if os.path.exists(path):
            debug_print(f"[LOG_MANAGER] Confirmed: Log file exists at {path}")
        else:
            debug_print(f"[LOG_MANAGER] Log file does not exist after saving!")
    except Exception as e:
        debug_print(f"[LOG_MANAGER] Error saving global log: {e}")


def reset_global_log():
    """
    Setzt das globale Log zurück (leert es), indem eine leere Liste von Einträgen geschrieben wird.
    """
    debug_print("[LOG_MANAGER] Resetting global log...")
    ensure_log_directory_exists()
    path = get_log_path()
    log_data = {
        "log_counter": 0,
        "entries": []
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        debug_print(f"[LOG_MANAGER] Global log reset successfully at {path}")
    except Exception as e:
        debug_print(f"[LOG_MANAGER] Error resetting global log: {e}")


def add_log_entry(entry):
    """
    Fügt einen neuen Eintrag zum globalen Log hinzu und stellt sicher,
    dass der Eintrag die gewünschte Struktur besitzt.

    Gewünschte Felder:
      - timestamp: ISO-Format (aktuelle Zeit, falls nicht angegeben)
      - filename: Dateiname (Standard: leerer String)
      - metadata: Dictionary mit Metadaten (Standard: leeres Dict)
      - checkType: z. B. "Standard" (Standard: "Standard")
      - status: z. B. "Fail" oder "OK" (Standard: "OK")
      - applied_script: Name des angewendeten Skripts (Standard: "(none)")
      - details: Dictionary mit Details (Standard: leeres Dict)
      - id: Automatisch generierte ID (7-stellig, falls nicht angegeben)

    Bestehende Einträge in 'entry' werden beibehalten.
    """
    entries = load_global_log()

    new_entry = {}
    new_entry["timestamp"] = entry.get("timestamp", datetime.now().isoformat())
    new_entry["filename"] = entry.get("filename", "")
    new_entry["metadata"] = entry.get("metadata", {})
    new_entry["checkType"] = entry.get("checkType", "Standard")
    new_entry["status"] = entry.get("status", "OK")
    new_entry["applied_script"] = entry.get("applied_script", "(none)")
    new_entry["details"] = entry.get("details", {})

    # Generiere eine neue ID, falls nicht vorhanden
    if "id" in entry:
        new_entry["id"] = entry["id"]
    else:
        new_entry["id"] = f"{len(entries) + 1:07d}"

    entries.append(new_entry)
    save_global_log(entries)
    debug_print(f"Neuer Eintrag angehängt: ID={new_entry['id']}")


if __name__ == '__main__':
    # Testcode: Füge einen Testlogeintrag hinzu und lade anschließend alle Einträge.
    test_entry = {
        "timestamp": "2025-03-06T12:00:00",
        "filename": "TestDatei.tif",
        "metadata": {
            "documentTitle": "undefined",
            "author": "TestAuthor",
            "authorPosition": "TestPosition",
            "description": "TestDescription",
            "descriptionWriter": "undefined",
            "keywords": "000",
            "copyrightNotice": "TestCopyright",
            "copyrightURL": "undefined",
            "city": "undefined",
            "stateProvince": "undefined",
            "country": "undefined",
            "creditLine": "undefined",
            "source": "undefined",
            "headline": "undefined",
            "instructions": "undefined",
            "transmissionRef": "undefined"
        },
        "checkType": "Standard",
        "status": "Fail",
        "applied_script": "(none)",
        "details": {
            "layers": {
                "Freisteller": "yes",
                "Messwerte": "no",
                "Korrektur": "no"
            },
            "missingLayers": [
                "Messwerte",
                "Korrektur"
            ],
            "missingMetadata": [],
            "layerStatus": "FAIL",
            "metaStatus": "OK",
            "checkType": "Standard",
            "keywordCheck": {
                "enabled": True,
                "keyword": "Rueckseite"
            }
        }
        # 'id' wird automatisch generiert, falls nicht angegeben.
    }
    add_log_entry(test_entry)
    logs = load_global_log()
    debug_print(f"[LOG_MANAGER] Current global log entries: {logs}")
    print("Current global log entries:", logs)