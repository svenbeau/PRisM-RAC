#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Config Manager for PRisM-RAC.
Handles loading and saving persistent script configuration to script_config.json.
Alle Konfigurationsdateien werden zentral im Ordner "config" abgelegt.
"""

import os
import json
import subprocess
import tempfile

DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

# Bestimme das Basisverzeichnis: Das übergeordnete Verzeichnis des config-Ordners.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Speichere die script_config.json im config-Verzeichnis
SCRIPT_CONFIG_FILE = os.path.join(BASE_DIR, "config", "script_config.json")

debug_print(f"BASE_DIR: {BASE_DIR}")
debug_print(f"Script Config File will be stored at: {SCRIPT_CONFIG_FILE}")

def load_script_config():
    """
    Lädt die script_config.json, wenn vorhanden.
    Gibt ein Dictionary zurück, z. B.:
    {
        "scripts": [
            {
                "script_path": "...",
                "json_folder": "...",
                "actionFolderName": "",
                "basicWandFiles": "",
                "csvWandFile": "",
                "wandFileSavePath": ""
            },
            ...
        ]
    }
    """
    if not os.path.isfile(SCRIPT_CONFIG_FILE):
        debug_print(f"script_config.json nicht gefunden: {SCRIPT_CONFIG_FILE}")
        return {"scripts": []}
    try:
        with open(SCRIPT_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        debug_print("Script Config loaded successfully.")
        return data
    except Exception as e:
        debug_print(f"Fehler beim Laden von script_config.json: {e}")
        return {"scripts": []}

def save_script_config(data: dict):
    """
    Speichert das übergebene Dictionary in script_config.json.
    Dabei wird sichergestellt, dass das Verzeichnis config existiert.
    """
    try:
        config_dir = os.path.join(BASE_DIR, "config")
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir)
            debug_print(f"Config-Verzeichnis erstellt: {config_dir}")
        with open(SCRIPT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        debug_print(f"Script-Config gespeichert nach {SCRIPT_CONFIG_FILE}")
    except Exception as e:
        debug_print(f"Fehler beim Speichern von script_config.json: {e}")

def run_jsx_script(jsx_code: str):
    """
    Schreibt den übergebenen ExtendScript-Code in eine temporäre Datei,
    führt ihn über AppleScript in Photoshop 2025 aus und gibt die Ausgabe zurück.
    """
    tmp_jsx = tempfile.NamedTemporaryFile(delete=False, suffix=".jsx", mode="w", encoding="utf-8")
    tmp_jsx.write(jsx_code)
    tmp_jsx.close()

    safe_path = tmp_jsx.name.replace('"','\\"')
    apple_script = f"""tell application "Adobe Photoshop 2025"
    do javascript "{safe_path}"
end tell
"""

    try:
        result = subprocess.run(["osascript", "-e", apple_script],
                                capture_output=True, text=True, timeout=15)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        debug_print(f"run_jsx_script stdout: {stdout}")
        debug_print(f"run_jsx_script stderr: {stderr}")
        if result.returncode != 0:
            debug_print(f"Fehler bei run_jsx_script, rc={result.returncode}")
        return stdout
    except Exception as e:
        debug_print(f"run_jsx_script Exception: {e}")
        return ""
    finally:
        if os.path.exists(tmp_jsx.name):
            os.remove(tmp_jsx.name)

def list_photoshop_action_sets():
    """
    Ruft ein ExtendScript-Snippet auf, das die in Photoshop geladenen Aktions-Sets
    als JSON-String zurückgibt, und gibt eine Python-Liste mit den Namen zurück.
    """
    jsx_code = r'''
#target photoshop

function getActionSetsJSON() {
    var sets = [];
    var count = app.actionSets.length;
    for (var i = 0; i < count; i++) {
        sets.push(app.actionSets[i].name);
    }
    return JSON.stringify(sets);
}

var result = getActionSetsJSON();
$.writeln(result);
'''
    output = run_jsx_script(jsx_code)
    if not output:
        return []
    try:
        sets_list = json.loads(output)
        if isinstance(sets_list, list):
            return sets_list
        else:
            return []
    except Exception as e:
        debug_print(f"Fehler beim JSON-Parse der ActionSets: {e}")
        return []