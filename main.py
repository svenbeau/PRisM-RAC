#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6 import QtWidgets, QtGui, QtCore

from utils.config_manager import load_settings, save_settings, debug_print
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget
from utils.log_manager import add_log_entry, load_global_log

DEBUG_OUTPUT = True

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-RAC")
        self.resize(1200, 900)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        # Haupt-Widget + Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # Obere Leiste: Logo links, Debug-Button rechts
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        # Logo (linksbündig, 200x21px)
        logo_label = QtWidgets.QLabel()
        # Verbesserte Pfadsuche für das Logo
        logo_paths = [
            os.path.join("assets", "logo.png"),  # Relativer Pfad
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png"),  # Absoluter Pfad vom Skript
            os.path.join(os.path.dirname(sys.executable), "assets", "logo.png"),  # Pfad vom Executable
            os.path.join(os.path.abspath("."), "assets", "logo.png"),  # Aktuelles Arbeitsverzeichnis
        ]

        logo_found = False
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                debug_print(f"Logo gefunden unter: {logo_path}")
                pixmap = QtGui.QPixmap(logo_path)
                pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                logo_found = True
                break

        if not logo_found:
            debug_print("Logo konnte nicht gefunden werden. Gesuchte Pfade:")
            for path in logo_paths:
                debug_print(f" - {path}")
            logo_label.setText("LOGO")

        # Diese Zeilen sind wichtig für das Layout!
        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)
        top_bar.addStretch()

        # Debug-Button
        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # Hauptbereich (horizontal): Links Buttons, rechts StackedWidget
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        # Linke Buttons
        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.json_editor_btn = QtWidgets.QPushButton("JSON-Editor")
        self.settings_btn = QtWidgets.QPushButton("Einstellungen")

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addWidget(self.settings_btn)
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        # Rechter Bereich: StackedWidget
        self.stack = QtWidgets.QStackedWidget()
        main_hlayout.addWidget(self.stack, stretch=1)

        # Widget 0: Hotfolder
        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.hotfolder_list_widget)

        # Widget 1: Logfile
        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.logfile_widget)

        # Widget 2: JSON Explorer
        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.json_explorer_widget)

        # Widget 3: Settings
        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.settings_widget)

        # Standard: Hotfolder (Index 0)
        self.stack.setCurrentIndex(0)

        # Button-Klicks
        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))

    def toggle_debug(self):
        global DEBUG_OUTPUT
        if self.debug_toggle_btn.isChecked():
            DEBUG_OUTPUT = True
            self.debug_toggle_btn.setText("Debug Stop")
        else:
            DEBUG_OUTPUT = False
            self.debug_toggle_btn.setText("Debug Start")
        debug_print(f"DEBUG_OUTPUT={DEBUG_OUTPUT}")

    def closeEvent(self, event):
        save_settings(self.settings)
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


def run():
    """
    Diese Funktion wird vom Wrapper aufgerufen und startet die Anwendung.
    Sie dient als Einstiegspunkt für die kompilierte Version.
    """
    print("PRisM-RAC wird gestartet...")
    try:
        app = QtWidgets.QApplication(sys.argv)
        win = MainWindow()
        win.show()
        return app.exec()
    except Exception as e:
        print(f"Fehler beim Starten der Anwendung: {e}")
        return 1


if __name__ == "__main__":
    main()