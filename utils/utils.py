#!/usr/bin/env python3
"""
Utilities for PRisM-RAC project.
"""

import os
import json
import re
import shutil
import time
import subprocess

DEBUG = True

def debug_print(message):
    """
    Prints a debug message if debugging is enabled.
    """
    if DEBUG:
        print("[DEBUG]", message)

def extract_metadata(file_path):
    """
    Extracts metadata from the given file.
    Diese Funktion sollte entsprechend dem Dateiformat implementiert werden.
    Hier wird eine Beispielimplementierung verwendet, die nach bestimmten
    Mustern im Text sucht.
    """
    metadata = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            m = re.search(r"DocumentTitle:\s*(.+)", content)
            metadata["documentTitle"] = m.group(1).strip() if m else "undefined"

            m = re.search(r"Author:\s*(.+)", content)
            metadata["author"] = m.group(1).strip() if m else "undefined"

            m = re.search(r"Description:\s*(.+)", content)
            metadata["description"] = m.group(1).strip() if m else "undefined"

            m = re.search(r"Keywords:\s*(.+)", content)
            metadata["keywords"] = m.group(1).strip() if m else "undefined"

            m = re.search(r"Headline:\s*(.+)", content)
            metadata["headline"] = m.group(1).strip() if m else "undefined"

            # Weitere Meta-Daten können hier ergänzt werden.
    except Exception as e:
        debug_print(f"Error extracting metadata from {file_path}: {e}")
    return metadata

def extract_layers(file_path):
    """
    Extracts layer information from the given file.
    Diese Funktion parst die Datei und gibt eine Liste der erkannten Ebenen zurück.
    Hier wird exemplarisch nach Zeilen gesucht, die mit 'Layer:' beginnen.
    """
    layers = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r"Layer:\s*(.+)", line)
                if match:
                    layer_name = match.group(1).strip()
                    layers.append(layer_name)
    except Exception as e:
        debug_print(f"Error extracting layers from {file_path}: {e}")
    return layers

def perform_content_check(file_path):
    """
    Performs content check on the given file by extracting metadata and layers.
    Returns a dictionary with keys 'metadata' and 'layers'.
    """
    metadata = extract_metadata(file_path)
    layers = extract_layers(file_path)
    result = {
        "metadata": metadata,
        "layers": layers
    }
    return result

def save_content_check_log(file_path, log_path):
    """
    Performs content check on the file and saves the result as a JSON log.
    """
    result = perform_content_check(file_path)
    try:
        with open(log_path, 'w', encoding='utf-8') as log_file:
            json.dump(result, log_file, indent=4)
        debug_print(f"Content check log saved to {log_path}.")
    except Exception as e:
        debug_print(f"Error saving content check log to {log_path}: {e}")

def run_jsx_in_photoshop_raw_code(js_code: str) -> str:
    """
    Führt rohen JSX-Code in Photoshop aus und gibt den stdout als String zurück.
    Nutzt AppleScript (osascript), um das Skript an Photoshop zu senden.
    """
    safe_js = js_code.replace('"', '\\"')
    applescript_lines = [
        'tell application id "com.adobe.Photoshop"',
        f'set jsCode to "{safe_js}"',
        'do javascript jsCode',
        'end tell'
    ]
    applescript_code = "\n".join(applescript_lines)

    try:
        result = subprocess.run(["osascript", "-e", applescript_code],
                                capture_output=True,
                                text=True)
        if result.stderr:
            debug_print(f"JSX stderr (raw code): {result.stderr}")
        if result.stdout:
            debug_print(f"JSX stdout (raw code): {result.stdout}")
        return result.stdout if result.stdout else ""
    except Exception as e:
        debug_print(f"Error executing raw JSX code: {e}")
        return ""

def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    """
    Führt ein JSX-Skript in Photoshop aus (basierend auf dem funktionierenden Beispiel).
    """
    try:
        cmd_jsx = f'tell application id "com.adobe.Photoshop" to do javascript file "{jsx_script_path}"'
        result = subprocess.run(["osascript", "-e", cmd_jsx],
                                capture_output=True,
                                text=True)
        debug_print(f"JSX execution result: RC={result.returncode}")
        if result.stdout:
            debug_print(f"JSX stdout: {result.stdout}")
        if result.stderr:
            debug_print(f"JSX stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        debug_print(f"Error executing JSX: {e}")
        return False

def get_photoshop_document_count():
    """
    Ruft per AppleScript die Anzahl der geöffneten Dokumente in Photoshop ab.
    """
    try:
        applescript = 'tell application "Adobe Photoshop 2025" to get count of documents'
        result = subprocess.run(["osascript", "-e", applescript],
                                capture_output=True,
                                text=True)
        count_str = result.stdout.strip()
        debug_print(f"Photoshop document count: {count_str}")
        return int(count_str)
    except Exception as e:
        debug_print(f"Error getting document count: {e}")
        return 0

def open_in_photoshop(file_path, wait_for_doc=True, timeout=60):
    """
    Öffnet das gegebene file_path in Adobe Photoshop.
    Wartet bis zu 'timeout' Sekunden, bis mindestens ein Dokument in Photoshop geöffnet ist.
    """
    try:
        photoshop_app = "Adobe Photoshop 2025"
        subprocess.run(["open", "-a", photoshop_app, file_path], check=True)
        debug_print(f"Opened {file_path} in Photoshop (open -a).")
    except Exception as e:
        debug_print(f"Error opening {file_path} in Photoshop: {e}")
        return False

    if not wait_for_doc:
        return True

    start_time = time.time()
    while time.time() - start_time < timeout:
        doc_count = get_photoshop_document_count()
        if doc_count > 0:
            debug_print(f"Photoshop reports {doc_count} document(s) open.")
            return True
        time.sleep(1)

    debug_print(f"Timeout: Photoshop did not report an open document within {timeout}s.")
    return False

def close_current_document_in_photoshop(save=False):
    """
    Schließt das aktuell geöffnete Dokument in Photoshop ohne zu speichern (save=False).
    """
    save_mode = "yes" if save else "no"
    applescript_code = f'''
    tell application id "com.adobe.Photoshop"
        if (documents is not {{}}) then
            close current document saving {save_mode}
        end if
    end tell
    '''
    try:
        result = subprocess.run(["osascript", "-e", applescript_code],
                                capture_output=True,
                                text=True)
        if result.stderr:
            debug_print(f"close_current_document_in_photoshop stderr: {result.stderr}")
        if result.stdout:
            debug_print(f"close_current_document_in_photoshop stdout: {result.stdout}")
    except Exception as e:
        debug_print(f"Error closing current document in Photoshop: {e}")

def move_file(src, dest):
    """
    Verschiebt eine Datei von src nach dest.
    """
    try:
        shutil.move(src, dest)
        debug_print(f"Moved file from {src} to {dest}.")
        return True
    except Exception as e:
        debug_print(f"Error moving file from {src} to {dest}: {e}")
        return False

def is_file_stable(file_path, interval=1.0, attempts=3):
    """
    Prüft, ob die Dateigröße über 'attempts' Versuche konstant bleibt.
    """
    try:
        prev_size = os.path.getsize(file_path)
        for _ in range(attempts):
            time.sleep(interval)
            current_size = os.path.getsize(file_path)
            if current_size != prev_size:
                debug_print(f"File {file_path} not stable: size changed from {prev_size} to {current_size}.")
                return False
            prev_size = current_size
        debug_print(f"File {file_path} is stable.")
        return True
    except Exception as e:
        debug_print(f"Error checking file stability for {file_path}: {e}")
        return False

if __name__ == "__main__":
    test_file = "/path/to/test.psd"
    if open_in_photoshop(test_file):
        debug_print("File opened and detected in Photoshop.")
        time.sleep(3)
        close_current_document_in_photoshop(save=False)
        debug_print("Document closed in Photoshop (no save).")
    else:
        debug_print("Failed to open file in Photoshop or no document detected.")