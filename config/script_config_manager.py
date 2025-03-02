#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Config Manager for PRisM-RAC.
Handles loading and saving script_config.json in the config/ folder.
Optionally can list Photoshop Action Sets via ExtendScript.
"""

import os
import json
import subprocess
import sys

DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

# Bestimme den Basisordner (das Projektverzeichnis)
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

SCRIPT_CONFIG_FILE = os.path.join(BASE_DIR, "config", "script_config.json")
debug_print(f"BASE_DIR: {BASE_DIR}")
debug_print(f"Script Config File will be stored at: {SCRIPT_CONFIG_FILE}")

def load_script_config(settings):
    """
    Lädt die script_config.json. Falls nicht vorhanden, gibt es ein Grundgerüst zurück.
    Die Einträge liegen üblicherweise in data["scripts"], z. B.:
    {
      "scripts": [
        {
          "script_path": "...",
          "json_folder": "...",
          "actionFolderName": "...",
          "basicWandFiles": "...",
          "csvWandFile": "...",
          "wandFileSavePath": "..."
        }
      ]
    }

    settings (dict): Falls du aus den allgemeinen Einstellungen (settings.json)
                     einen alternativen Pfad lesen willst, könntest du hier
                     "SCRIPT_CONFIG_PATH" auswerten.
    """
    # Optional: Schau nach, ob es in settings einen alternativen Pfad gibt:
    override_path = settings.get("SCRIPT_CONFIG_PATH", "")
    if override_path:
        config_file = override_path
        debug_print(f"Using override script_config path: {config_file}")
    else:
        config_file = SCRIPT_CONFIG_FILE

    if not os.path.isfile(config_file):
        debug_print(f"script_config.json not found at {config_file}, returning default.")
        return {"scripts": []}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        debug_print("Script Config loaded successfully.")
        return data
    except Exception as e:
        debug_print(f"Error loading script_config from {config_file}: {e}")
        return {"scripts": []}

def save_script_config(data, settings):
    """
    Speichert das Dictionary data in script_config.json (oder Override).
    """
    override_path = settings.get("SCRIPT_CONFIG_PATH", "")
    if override_path:
        config_file = override_path
    else:
        config_file = SCRIPT_CONFIG_FILE

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        debug_print("Script configuration saved.")
    except Exception as e:
        debug_print(f"Error saving script_config.json: {e}")


# Optional: ExtendScript-Aufruf, um Photoshop-Action-Sets auszulesen.
def list_photoshop_action_sets():
    """
    Ruft ein ExtendScript-Snippet auf, das die vorhandenen ActionSets in Photoshop
    ausliest und als JSON-String zurückgibt.
    Gibt eine Python-Liste mit Strings zurück, z.B. ["Grisebach 2025", "Standard Actions", ...].
    """
    jsx_code = r'''
#target photoshop

function getActionSetsJSON() {
    // Polyfill falls JSON fehlt:
    if (typeof JSON === 'undefined') {
        // minimaler Polyfill
        JSON = {};
        JSON.stringify = function(obj){/*...*/ return "[\"Custom Actions\"]";}; 
        // Falls man in Photoshop 2025 ggf. modernere JSON-Features hat, kann man das weglassen
    }

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
    try:
        import tempfile
        tmp_jsx = tempfile.NamedTemporaryFile(delete=False, suffix=".jsx", mode="w", encoding="utf-8")
        tmp_jsx.write(jsx_code)
        tmp_jsx.close()

        safe_path = tmp_jsx.name.replace('"','\\"')
        apple_script = f'''tell application "Adobe Photoshop 2025"
    do javascript "{safe_path}"
end tell
'''
        result = subprocess.run(["osascript", "-e", apple_script],
                                capture_output=True, text=True, timeout=10)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        debug_print(f"list_photoshop_action_sets stdout: {stdout}")
        debug_print(f"list_photoshop_action_sets stderr: {stderr}")
        if result.returncode != 0:
            debug_print(f"Error in list_photoshop_action_sets, rc={result.returncode}")
        # Versuch, stdout als JSON zu interpretieren:
        import json
        sets_list = json.loads(stdout)
        if isinstance(sets_list, list):
            return sets_list
        else:
            return []
    except Exception as e:
        debug_print(f"Exception in list_photoshop_action_sets: {e}")
        return ["Grisebach 2025","Standard Actions","Custom Actions"]