import os
import time
import subprocess
from queue import Queue, Empty
from threading import Thread, Event
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dynamic_jsx_generator import DynamicJSXGenerator


def debug_print(message):
    """Debug-Ausgabe-Funktion"""
    print(f"[DEBUG] {message}")


def run_jsx_in_photoshop(jsx_script_path: str) -> bool:
    """
    Führt ein JSX-Skript in Photoshop aus über AppleScript
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


class HotfolderEventHandler(FileSystemEventHandler):
    def __init__(self, file_queue):
        self.file_queue = file_queue
        super().__init__()

    def on_created(self, event):
        if not event.is_directory:
            debug_print(f"File created: {event.src_path}")
            self.file_queue.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            debug_print(f"File modified: {event.src_path}")
            self.file_queue.put(event.src_path)


class HotfolderMonitor:
    def __init__(self,
                 monitor_dir=None,
                 hf_config=None,
                 folder_path=None,
                 on_status_update=None,
                 on_file_processing=None):
        """
        Initialisiert den HotfolderMonitor

        Args:
            monitor_dir: (Veraltet) Pfad zum zu überwachenden Ordner
            hf_config: Konfiguration für den Hotfolder
            folder_path: (Neu) Pfad zum zu überwachenden Ordner
            on_status_update: Callback-Funktion für Status-Updates (optional)
            on_file_processing: Callback-Funktion für Dateiverarbeitung-Updates (optional)
        """
        # Verwende folder_path falls gesetzt, sonst monitor_dir
        if folder_path is None and monitor_dir is None:
            raise ValueError("Entweder folder_path oder monitor_dir muss angegeben werden")

        self.folder_path = os.path.abspath(folder_path if folder_path is not None else monitor_dir)
        self.hf_config = hf_config or {}
        self.on_status_update = on_status_update
        self.on_file_processing = on_file_processing
        self.file_queue = Queue()
        self.stop_event = Event()
        self.observer = None
        self.worker_thread = None

    def update_status(self, message):
        """
        Aktualisiert den Status über den Callback
        """
        if self.on_status_update:
            self.on_status_update(message)
        debug_print(message)

    def update_file_processing(self, file_path, status):
        """
        Aktualisiert den Dateiverarbeitungsstatus über den Callback
        """
        if self.on_file_processing:
            self.on_file_processing(file_path, status)

    def start(self):
        """Startet die Überwachung des Hotfolders"""
        self.update_status(f"Starte HotfolderMonitor für: {self.folder_path}")

        # Erstelle und starte den Observer
        event_handler = HotfolderEventHandler(self.file_queue)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.folder_path, recursive=False)
        self.observer.start()

        # Überprüfe existierende Dateien
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(file_path):
                self.update_status(f"Found existing file: {file_path}")
                self.file_queue.put(file_path)

        # Starte Worker-Thread
        self.worker_thread = Thread(target=self.worker_loop)
        self.worker_thread.start()

    def stop(self):
        """Stoppt die Überwachung des Hotfolders"""
        self.update_status(f"Stoppe HotfolderMonitor für: {self.folder_path}")
        self.stop_event.set()

        if self.observer:
            self.observer.stop()
            self.observer.join()

        if self.worker_thread:
            self.worker_thread.join()

    def worker_loop(self):
        """Worker-Loop zur Verarbeitung der Dateien"""
        while not self.stop_event.is_set():
            try:
                # Warte auf neue Dateien (mit Timeout)
                try:
                    file_path = self.file_queue.get(timeout=1.0)
                    self.update_status(f"Enqueue file: {file_path}")
                    self.process_file(file_path)
                except Empty:
                    continue

            except Exception as e:
                self.update_status(f"Error in worker loop: {e}")

            finally:
                self.file_queue.task_done()

    def wait_for_file_stability(self, file_path, check_interval=1.0, required_stable_checks=3):
        """
        Wartet, bis eine Datei stabil ist (nicht mehr verändert wird)
        """
        last_size = None
        stable_count = 0

        while stable_count < required_stable_checks:
            try:
                current_size = os.path.getsize(file_path)
                self.update_status(
                    f"Checking file stability for {file_path}: size={current_size}, stable_count={stable_count}")

                if current_size == last_size:
                    stable_count += 1
                else:
                    stable_count = 0

                last_size = current_size
                time.sleep(check_interval)

            except OSError:
                self.update_status(f"Error checking file stability: {file_path}")
                return False

        return True

    def process_file(self, file_path):
        """
        Verarbeitet eine Datei im Hotfolder
        """
        try:
            self.update_status(f"Verarbeite Datei: {file_path}")
            self.update_file_processing(file_path, "processing")

            # Warte bis die Datei stabil ist
            if not self.wait_for_file_stability(file_path):
                self.update_status(f"Datei ist nicht stabil (noch im Kopiervorgang?): {file_path}")
                self.update_file_processing(file_path, "unstable")
                return

            # Öffne die Datei in Photoshop
            self.update_status(f"Opening file in Photoshop: {['open', '-b', 'com.adobe.Photoshop', file_path]}")
            subprocess.run(['open', '-b', 'com.adobe.Photoshop', file_path])

            # Generiere und führe JSX Script aus
            generator = DynamicJSXGenerator(debug_output=True)  # oder False je nach Bedarf
            jsx_content = generator.generate_contentcheck_jsx(
                image_path=file_path,
                check_settings=self.hf_config,
                output_path=os.path.join(os.path.dirname(file_path), 'output')
            )

            # Speichere JSX Script
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            jsx_script_path = os.path.join(temp_dir, f'check_{os.path.basename(file_path)}.jsx')
            generator.save_jsx_script(jsx_content, jsx_script_path)

            # Führe JSX Script aus
            if not run_jsx_in_photoshop(jsx_script_path):
                self.update_status("Fehler beim Ausführen des Contentcheck-JSX.")
                self.update_file_processing(file_path, "error")
                self.move_to_fault_folder(file_path)
                return

            self.update_file_processing(file_path, "success")
            # Weitere Verarbeitung...

        except Exception as e:
            self.update_status(f"Error processing file: {e}")
            self.update_file_processing(file_path, "error")
            self.move_to_fault_folder(file_path)

    def move_to_fault_folder(self, file_path):
        """
        Verschiebt eine Datei in den Fault-Ordner
        """
        try:
            fault_folder = os.path.join(os.path.dirname(os.path.dirname(file_path)), '03_Fault')
            os.makedirs(fault_folder, exist_ok=True)

            fault_path = os.path.join(fault_folder, os.path.basename(file_path))
            os.rename(file_path, fault_path)
            self.update_status(f"Datei verschoben nach: {fault_path}")

        except Exception as e:
            self.update_status(f"Error moving file to fault folder: {e}")