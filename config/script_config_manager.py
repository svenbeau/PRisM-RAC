#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import tempfile

DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

SCRIPT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "script_config.json")

def load_script_config():
    """
    Lädt die script_config.json, wenn vorhanden.
    """
    if not os.path.isfile(SCRIPT_CONFIG_FILE):
        debug_print(f"script_config.json nicht gefunden: {SCRIPT_CONFIG_FILE}")
        return {"scripts": []}
    try:
        with open(SCRIPT_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        debug_print(f"Fehler beim Laden von script_config.json: {e}")
        return {"scripts": []}

def save_script_config(data: dict):
    """
    Speichert das Dictionary in script_config.json.
    """
    try:
        with open(SCRIPT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        debug_print(f"Script config gespeichert nach {SCRIPT_CONFIG_FILE}")
    except Exception as e:
        debug_print(f"Fehler beim Speichern von script_config.json: {e}")

def run_jsx_script(jsx_code: str):
    tmp_jsx = tempfile.NamedTemporaryFile(delete=False, suffix=".jsx", mode="w", encoding="utf-8")
    tmp_jsx.write(jsx_code)
    tmp_jsx.close()
    safe_path = tmp_jsx.name.replace('"','\\"')
    apple_script = f'''tell application "Adobe Photoshop 2025"
    do javascript "{safe_path}"
end tell'''
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
    Ruft ein ExtendScript-Snippet auf, das die vorhandenen ActionSets in Photoshop ausliest und als JSON-String zurückgibt.
    Gibt eine Liste von Strings zurück.
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
        return sets_list if isinstance(sets_list, list) else []
    except Exception as e:
        debug_print(f"Fehler beim Parsen der ActionSets: {e}")
        return []

if __name__ == "__main__":
    config = load_script_config()
    debug_print("Loaded script config:")
    debug_print(json.dumps(config, indent=4))
    actions = list_photoshop_action_sets()
    debug_print("Photoshop action sets:")
    debug_print(actions)