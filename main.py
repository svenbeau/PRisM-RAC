# main.py

import sys
import os
import json

# Wenn du in main_window.py PySide6 nutzt, sollte hier auch PySide6 importiert werden.
# Falls in den anderen Dialogen PyQt5 vorkommt, kann es zu Konflikten führen.
# Idealerweise konsolidierst du dein Projekt auf EINE Qt-Bibliothek.
from PySide6.QtWidgets import QApplication
from utils.log_manager import LogManager
from utils.config_manager import ConfigManager
from utils.path_manager import get_settings_path

# Aus ui/ importieren wir die MainWindow-Klasse
from ui.main_window import MainWindow

# Wir setzen eine globale Konstante, um den Pfad zu settings.json (im App-Support-Verzeichnis) zu bestimmen
SETTINGS_FILE = get_settings_path()

def load_settings():
    """
    Lädt ein JSON-Dict aus ~/Library/Application Support/PRisM-CC/settings.json
    (oder gibt ein leeres Dict zurück, wenn nicht vorhanden).
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings file {SETTINGS_FILE}: {e}")
            return {}
    else:
        return {}

def save_settings(settings_data):
    """
    Speichert 'settings_data' als JSON in ~/Library/Application Support/PRisM-CC/settings.json.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings file {SETTINGS_FILE}: {e}")

def main():
    app = QApplication(sys.argv)

    # Erzeuge ConfigManager und LogManager (aus utils/)
    config_manager = ConfigManager()
    log_manager = LogManager()

    # Hauptfenster erstellen (MainWindow erwartet config_manager und log_manager)
    main_window = MainWindow(config_manager, log_manager)
    main_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()