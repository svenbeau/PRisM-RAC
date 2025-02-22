import os
import time
import subprocess
import shutil

# Globaler Debug-Schalter
DEBUG_OUTPUT = True

def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

def open_in_photoshop(file_path: str) -> bool:
    """
    Öffnet die angegebene Datei in Photoshop über den macOS 'open'-Befehl.
    """
    cmd = ["open", "-b", "com.adobe.Photoshop", file_path]
    debug_print("Opening file in Photoshop: " + str(cmd))
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        debug_print("Error opening file in Photoshop: " + str(e))
        return False

def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    """
    Führt ein JSX-Skript in Photoshop aus, indem ein AppleScript-Befehl aufgerufen wird.
    """
    cmd_jsx = f'tell application id "com.adobe.Photoshop" to do javascript file "{jsx_script_path}"'
    debug_print("Executing JSX: " + cmd_jsx)
    try:
        result = subprocess.run(["osascript", "-e", cmd_jsx], capture_output=True, text=True)
        debug_print("JSX execution result: RC=" + str(result.returncode))
        if result.stdout:
            debug_print("JSX stdout: " + result.stdout)
        if result.stderr:
            debug_print("JSX stderr: " + result.stderr)
        return result.returncode == 0
    except Exception as e:
        debug_print("Error executing JSX: " + str(e))
        return False

def move_file(src: str, dst_dir: str):
    """
    Verschiebt die Datei 'src' in den Ordner 'dst_dir'. Falls der Zielordner nicht existiert, wird dieser angelegt.
    """
    try:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        dst = os.path.join(dst_dir, os.path.basename(src))
        shutil.move(src, dst)
        debug_print("Datei verschoben nach: " + dst)
    except Exception as e:
        debug_print("Fehler beim Verschieben der Datei: " + str(e))

def is_file_stable(file_path: str, interval=1.0, retries=3) -> bool:
    """
    Überprüft, ob sich die Dateigröße über mehrere Abfragen nicht ändert – das heißt, ob die Datei stabil ist.
    """
    if not os.path.exists(file_path):
        return False
    last_size = os.path.getsize(file_path)
    stable_count = 0
    while stable_count < retries:
        time.sleep(interval)
        if not os.path.exists(file_path):
            return False
        current_size = os.path.getsize(file_path)
        if current_size == last_size:
            stable_count += 1
        else:
            stable_count = 0
            last_size = current_size
        debug_print(f"Checking file stability for {file_path}: size {current_size}, stable_count {stable_count}")
    return True