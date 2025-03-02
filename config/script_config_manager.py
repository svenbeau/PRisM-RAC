#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Config Manager for PRisM-RAC.
Lädt und speichert die Skript‑Rezept Konfiguration in script_config.json.
Alle Konfigurationsdateien liegen im Ordner config.
"""

import os
import json
import tempfile
import subprocess

DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

# Basisverzeichnis des Projekts (einmalig ermitteln)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_CONFIG_FILE = os.path.join(BASE_DIR, "config", "script_config.json")

def load_script_config(settings=None):
    """
    Lädt die script_config.json.
    Falls die Datei nicht existiert, wird ein leeres Dictionary mit dem Schlüssel "scripts" zurückgegeben.
    """
    if not os.path.isfile(SCRIPT_CONFIG_FILE):
        debug_print("script_config.json not found: " + SCRIPT_CONFIG_FILE)
        return {"scripts": []}
    try:
        with open(SCRIPT_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        debug_print("Error loading script_config.json: " + str(e))
        return {"scripts": []}

def save_script_config(data: dict):
    """
    Speichert das Dictionary data in script_config.json.
    """
    try:
        with open(SCRIPT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        debug_print("Script configuration saved to " + SCRIPT_CONFIG_FILE)
    except Exception as e:
        debug_print("Error saving script_config.json: " + str(e))

def list_photoshop_action_sets():
    """
    Liest über ein ExtendScript-Snippet die verfügbaren Photoshop-Aktions-Sets aus und gibt sie als Liste zurück.
    (Falls nicht verwendet, kann diese Funktion später erweitert werden.)
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
        debug_print("Error parsing Photoshop action sets: " + str(e))
        return []

def run_jsx_script(jsx_code: str):
    """
    Schreibt den übergebenen JSX-Code in eine temporäre Datei und führt ihn über AppleScript in Photoshop aus.
    Gibt die Standardausgabe zurück.
    """
    tmp_jsx = tempfile.NamedTemporaryFile(delete=False, suffix=".jsx", mode="w", encoding="utf-8")
    tmp_jsx.write(jsx_code)
    tmp_jsx.close()
    safe_path = tmp_jsx.name.replace('"', '\\"')
    apple_script = f'''tell application "Adobe Photoshop 2025"
    do javascript file "{safe_path}"
end tell'''
    try:
        result = subprocess.run(["osascript", "-e", apple_script],
                                capture_output=True, text=True, timeout=15)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        debug_print("run_jsx_script stdout: " + stdout)
        debug_print("run_jsx_script stderr: " + stderr)
        if result.returncode != 0:
            debug_print("Error in run_jsx_script, return code: " + str(result.returncode))
        return stdout
    except Exception as e:
        debug_print("Exception in run_jsx_script: " + str(e))
        return ""
    finally:
        if os.path.exists(tmp_jsx.name):
            os.remove(tmp_jsx.name)