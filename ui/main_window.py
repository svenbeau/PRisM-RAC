#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5 import QtWidgets, QtGui, QtCore

from config.config_manager import load_settings, save_settings, debug_print
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget  # Unser neues Widget

DEBUG_OUTPUT = True

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-RAC")
        self.resize(1200, 1000)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # Obere Leiste: Logo links, Debug Start/Stop Button rechts
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        # Logo (linksbündig, 200x21px, proportional)
        logo_label = QtWidgets.QLabel()
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QtGui.QPixmap(logo_path)
            pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")
        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)

        top_bar.addStretch()

        # Debug Start/Stop Button
        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # Hauptbereich (horizontal): Links Buttons, rechts StackedWidget
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        # Linker Bereich: Buttons "Hotfolder", "Logfile", "JSON Editor"
        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.json_editor_btn = QtWidgets.QPushButton("JSON Editor")

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        # Rechter Bereich: StackedWidget für Hotfolder, Logfile und JSON Editor
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

        # Default: Hotfolder
        self.stack.setCurrentIndex(0)

        # Button-Klicks -> Index wechseln
        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))

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
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()