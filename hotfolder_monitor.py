#!/usr/bin/env python3
"""
Hotfolder Monitor – Überwacht einen definierten Ordner und führt bei Dateiänderungen folgende Schritte aus:
1. Überprüft, ob die Datei vollständig (stabile Dateigröße) kopiert wurde.
2. Öffnet die Datei in Adobe Photoshop (mittels Terminal-Befehl).
3. Führt ein ausgewähltes JSX-Skript in Photoshop aus.
4. Ein UI (mit Tkinter) ermöglicht das Festlegen des Hotfolder-Pfads, das Auswählen eines JSX-Skripts
   (über einen Finder-Dialog) sowie das Aktivieren/Deaktivieren der Überwachung.

Die Debug-Ausgabe wird global über die Variable DEBUG_OUTPUT gesteuert.
"""

import os
import time
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Globaler Debug-Schalter
DEBUG_OUTPUT = True


def debug_print(message):
    if DEBUG_OUTPUT:
        print("[DEBUG]", message)


def open_in_photoshop(file_path: str) -> bool:
    """
    Öffnet die angegebene Datei in Adobe Photoshop mittels des Terminal-Befehls.
    """
    cmd_open = ["open", "-b", "com.adobe.Photoshop", file_path]
    debug_print("Opening file in Photoshop: " + str(cmd_open))
    try:
        subprocess.run(cmd_open, check=True)
        return True
    except subprocess.CalledProcessError as e:
        debug_print("Error opening file in Photoshop: " + str(e))
        return False


def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    """
    Führt ein JSX-Skript in Photoshop aus (basierend auf dem funktionierenden Beispiel).
    """
    try:
        cmd_jsx = f'tell application id "com.adobe.Photoshop" to do javascript file "{jsx_script_path}"'
        result = subprocess.run(
            ["osascript", "-e", cmd_jsx],
            capture_output=True,
            text=True
        )

        debug_print(f"JSX execution result: RC={result.returncode}")
        if result.stdout:
            debug_print(f"JSX stdout: {result.stdout}")
        if result.stderr:
            debug_print(f"JSX stderr: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        debug_print(f"Error executing JSX: {e}")
        return False


def is_file_stable(file_path: str, interval=1.0, retries=3) -> bool:
    """
    Prüft, ob eine Datei stabil ist (d.h. die Dateigröße ändert sich nicht über mehrere Abfragen).
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


class HotfolderEventHandler(FileSystemEventHandler):
    """
    Event-Handler für Dateiänderungen im Hotfolder.
    Bei Erzeugung oder Modifikation einer Datei wird geprüft, ob die Datei stabil ist,
    anschließend in Photoshop geöffnet und das JSX-Skript ausgeführt.
    """

    def __init__(self, jsx_script_path_getter, hotfolder_path):
        super().__init__()
        self.jsx_script_path_getter = jsx_script_path_getter
        self.hotfolder_path = hotfolder_path

    def process_file(self, file_path):
        debug_print("Processing file: " + file_path)
        # Warte, bis die Datei vollständig kopiert wurde.
        if is_file_stable(file_path):
            # Öffne die Datei in Photoshop
            if open_in_photoshop(file_path):
                # Führe das ausgewählte JSX-Skript in Photoshop aus.
                jsx_script = self.jsx_script_path_getter()
                if jsx_script and os.path.exists(jsx_script):
                    run_jsx_in_photoshop(jsx_script)
                else:
                    debug_print("Kein gültiges JSX-Skript ausgewählt.")
        else:
            debug_print("Datei ist nicht stabil: " + file_path)

    def on_created(self, event):
        if not event.is_directory:
            debug_print("File created: " + event.src_path)
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            debug_print("File modified: " + event.src_path)
            self.process_file(event.src_path)


class HotfolderMonitor:
    """
    Verwaltet die Überwachung eines Hotfolders mithilfe des Watchdog-Observers.
    Bei Start werden zunächst alle existierenden Dateien verarbeitet.
    """

    def __init__(self, hotfolder_path, jsx_script_path_getter):
        self.hotfolder_path = hotfolder_path
        self.jsx_script_path_getter = jsx_script_path_getter
        self.observer = Observer()
        self.event_handler = HotfolderEventHandler(jsx_script_path_getter, hotfolder_path)
        self.monitoring = False

    def start(self):
        if not os.path.exists(self.hotfolder_path):
            debug_print("Hotfolder does not exist: " + self.hotfolder_path)
            return
        self.monitoring = True
        debug_print("Starting hotfolder monitor on: " + self.hotfolder_path)
        # Alle vorhandenen Dateien im Hotfolder werden initial verarbeitet.
        for root, dirs, files in os.walk(self.hotfolder_path):
            for file in files:
                file_path = os.path.join(root, file)
                debug_print("Processing existing file: " + file_path)
                self.event_handler.process_file(file_path)
        self.observer.schedule(self.event_handler, self.hotfolder_path, recursive=True)
        self.observer.start()
        debug_print("Observer started.")

    def stop(self):
        if self.monitoring:
            debug_print("Stopping hotfolder monitor.")
            self.observer.stop()
            self.observer.join()
            self.monitoring = False


class Application(tk.Tk):
    """
    Ein einfaches UI, das:
     - Den Hotfolder-Pfad festlegt.
     - Über einen Button ein Dropdown ermöglicht, um ein JSX-Skript auszuwählen (Finder-Dialog).
     - Einen Schalter zur Aktivierung/Deaktivierung der Überwachung bietet.
    """

    def __init__(self):
        super().__init__()
        self.title("Hotfolder Monitor")
        self.geometry("500x200")
        # Globale Variablen
        self.jsx_script_path = None
        self.hotfolder_path = None

        # UI-Elemente
        self.create_widgets()

        self.monitor = None
        self.monitor_thread = None

    def create_widgets(self):
        # Eingabefeld für den Hotfolder-Pfad
        tk.Label(self, text="Hotfolder Pfad:").pack(pady=5)
        self.hotfolder_entry = tk.Entry(self, width=50)
        self.hotfolder_entry.pack(pady=5)
        # Button, um einen Hotfolder auszuwählen
        tk.Button(self, text="Hotfolder auswählen", command=self.choose_hotfolder).pack(pady=5)

        # Button zur Auswahl eines JSX-Skripts über einen Finder-Dialog
        self.jsx_button = tk.Button(self, text="JSX-Skript auswählen", command=self.choose_jsx_script)
        self.jsx_button.pack(pady=5)

        # Checkbox, um die Überwachung zu aktivieren/deaktivieren
        self.monitor_var = tk.BooleanVar(value=False)
        self.monitor_check = tk.Checkbutton(self, text="Hotfolder Überwachung aktivieren", variable=self.monitor_var,
                                            command=self.toggle_monitoring)
        self.monitor_check.pack(pady=5)

    def choose_hotfolder(self):
        folder = filedialog.askdirectory(title="Hotfolder auswählen")
        if folder:
            self.hotfolder_entry.delete(0, tk.END)
            self.hotfolder_entry.insert(0, folder)
            self.hotfolder_path = folder
            debug_print("Hotfolder ausgewählt: " + folder)

    def choose_jsx_script(self):
        script = filedialog.askopenfilename(title="JSX-Skript auswählen", filetypes=[("JSX Dateien", "*.jsx")])
        if script:
            self.jsx_script_path = script
            # Button-Beschriftung mit dem Namen des ausgewählten Skripts aktualisieren
            self.jsx_button.config(text=os.path.basename(script))
            debug_print("JSX-Skript ausgewählt: " + script)

    def get_jsx_script_path(self):
        return self.jsx_script_path

    def toggle_monitoring(self):
        if self.monitor_var.get():
            # Starten der Überwachung
            if not self.hotfolder_path:
                messagebox.showerror("Fehler", "Bitte wählen Sie zuerst einen Hotfolder aus.")
                self.monitor_var.set(False)
                return
            if not self.jsx_script_path:
                messagebox.showerror("Fehler", "Bitte wählen Sie zuerst ein JSX-Skript aus.")
                self.monitor_var.set(False)
                return
            # Erstelle und starte den Monitor in einem separaten Thread
            self.monitor = HotfolderMonitor(self.hotfolder_path, self.get_jsx_script_path)
            self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
            self.monitor_thread.start()
            debug_print("Monitoring gestartet.")
        else:
            # Stoppen der Überwachung
            if self.monitor:
                self.monitor.stop()
                debug_print("Monitoring gestoppt.")


if __name__ == "__main__":
    app = Application()
    app.mainloop()