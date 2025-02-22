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
            # Beispielhafte Extraktion von Meta-Daten anhand von Schlüsselwörtern:
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


def open_in_photoshop(file_path):
    """
    Opens the given file in Adobe Photoshop on macOS.
    Hier wird das Kommando "open -a" genutzt.
    """
    try:
        photoshop_app = "Adobe Photoshop 2025"
        subprocess.run(["open", "-a", photoshop_app, file_path], check=True)
        debug_print(f"Opened {file_path} in Photoshop.")
        return True
    except Exception as e:
        debug_print(f"Error opening {file_path} in Photoshop: {e}")
        return False


def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    """
    Führt ein JSX-Skript in Photoshop aus (basierend auf dem funktionierenden Beispiel)
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


def move_file(src, dest):
    """
    Moves a file from src to dest.
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
    Checks if the file size remains constant over a given interval.
    """
    try:
        prev_size = os.path.getsize(file_path)
        for _ in range(attempts):
            time.sleep(interval)
            current_size = os.path.getsize(file_path)
            if current_size != prev_size:
                debug_print(f"File {file_path} is not stable: size changed from {prev_size} to {current_size}.")
                return False
            prev_size = current_size
        debug_print(f"File {file_path} is stable.")
        return True
    except Exception as e:
        debug_print(f"Error checking file stability for {file_path}: {e}")
        return False


if __name__ == "__main__":
    # Zum Testen: Pfad zu einer Testdatei und zu einem Logfile anpassen.
    test_file = "path/to/test_file.txt"
    log_file = "path/to/test_file_log.json"
    save_content_check_log(test_file, log_file)