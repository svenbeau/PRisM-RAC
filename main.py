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
from ui.ftp_transfer_widget import FtpTransferWidget
from ui.script_recipe_list_widget import ScriptRecipeListWidget
from ui.transfer_plan_list_widget import TransferPlanListWidget

from datetime import datetime, timedelta

DEBUG_OUTPUT = True

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-CC")
        self.resize(1200, 900)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        # Zentrales Widget + Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # (A) Obere Leiste: Logo links, Debug-Button rechts
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        logo_label = QtWidgets.QLabel()
        logo_paths = [
            os.path.join("assets", "logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png"),
            os.path.join(os.path.dirname(sys.executable), "assets", "logo.png"),
            os.path.join(os.path.abspath("."), "assets", "logo.png"),
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

        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)
        top_bar.addStretch()

        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # (B) Hauptbereich (horizontal): Links Buttons, rechts StackedWidget
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        # Reihenfolge der Buttons
        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.script_recipe_btn = QtWidgets.QPushButton("Script › Rezept")
        self.json_editor_btn = QtWidgets.QPushButton("JSON-Editor")
        self.ftp_transfer_btn = QtWidgets.QPushButton("FTP-Transfer")
        self.plan_btn = QtWidgets.QPushButton("Transfer-Pläne")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.settings_btn = QtWidgets.QPushButton("Einstellungen")

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.script_recipe_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addWidget(self.ftp_transfer_btn)
        left_vlayout.addWidget(self.plan_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.settings_btn)
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        # Rechter Bereich: QStackedWidget
        self.stack = QtWidgets.QStackedWidget()
        main_hlayout.addWidget(self.stack, stretch=1)

        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.script_recipe_list_widget = ScriptRecipeListWidget(self.settings, parent=self.stack)
        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.ftp_transfer_widget = FtpTransferWidget(parent=self.stack)
        self.transfer_plan_list_widget = TransferPlanListWidget(self.settings, parent=self.stack)
        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)

        self.stack.addWidget(self.hotfolder_list_widget)         # Index 0
        self.stack.addWidget(self.script_recipe_list_widget)       # Index 1
        self.stack.addWidget(self.json_explorer_widget)            # Index 2
        self.stack.addWidget(self.ftp_transfer_widget)             # Index 3
        self.stack.addWidget(self.transfer_plan_list_widget)       # Index 4
        self.stack.addWidget(self.logfile_widget)                  # Index 5
        self.stack.addWidget(self.settings_widget)                 # Index 6

        self.stack.setCurrentIndex(0)

        # Button-Klicks
        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.script_recipe_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.ftp_transfer_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.plan_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(5))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(6))

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
        from utils.config_manager import save_settings
        save_settings(self.settings)
        super().closeEvent(event)


def run():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


# Damit auch wrapper.py auf main.run zugreifen kann:
run = run

if __name__ == "__main__":
    run()