#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5 import QtWidgets, QtGui, QtCore

from config.config_manager import load_config, save_config
from ui.hotfolder_widget import HotfolderWidget

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-RAC")
        self.resize(1200, 700)
        self.config_data = load_config()
        self.init_ui()

    def init_ui(self):
        # Zentrales Widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Obere Zeile: Logo + Debug-Button
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(5, 5, 5, 5)

        logo_label = QtWidgets.QLabel()
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QtGui.QPixmap(logo_path)
            # Logo proportional auf 200×21 skalieren
            pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")

        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)
        top_bar.addStretch()

        # "Disable Debug" als Toggle-Button
        self.debug_button = QtWidgets.QPushButton("Disable Debug")
        self.debug_button.setCheckable(True)
        self.debug_button.setChecked(False)
        self.debug_button.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_button, alignment=QtCore.Qt.AlignRight)

        main_layout.addLayout(top_bar)

        # Zeile für "Hotfolder hinzufügen" und "Hotfolder entfernen"
        hf_button_layout = QtWidgets.QHBoxLayout()
        hf_button_layout.setContentsMargins(5, 0, 5, 0)
        self.add_hf_btn = QtWidgets.QPushButton("Hotfolder hinzufügen")
        self.del_hf_btn = QtWidgets.QPushButton("Hotfolder entfernen")

        hf_button_layout.addWidget(self.add_hf_btn)
        hf_button_layout.addWidget(self.del_hf_btn)
        hf_button_layout.addStretch()

        main_layout.addLayout(hf_button_layout)

        # Scroll-Bereich für HotfolderWidgets
        self.hf_scroll = QtWidgets.QScrollArea()
        self.hf_scroll.setWidgetResizable(True)
        self.hf_container = QtWidgets.QWidget()
        self.hf_layout = QtWidgets.QVBoxLayout(self.hf_container)
        self.hf_layout.setContentsMargins(0, 0, 0, 0)
        self.hf_layout.setSpacing(10)
        self.hf_scroll.setWidget(self.hf_container)
        main_layout.addWidget(self.hf_scroll, stretch=1)

        # Signale
        self.add_hf_btn.clicked.connect(self.add_hotfolder)
        self.del_hf_btn.clicked.connect(self.delete_hotfolder)

        self.load_hotfolders()

    def toggle_debug(self):
        global DEBUG_OUTPUT
        if self.debug_button.isChecked():
            DEBUG_OUTPUT = False
            self.debug_button.setText("Enable Debug")
        else:
            DEBUG_OUTPUT = True
            self.debug_button.setText("Disable Debug")
        debug_print(f"DEBUG_OUTPUT={DEBUG_OUTPUT}")

    def load_hotfolders(self):
        # Vorhandene Widgets entfernen
        for i in reversed(range(self.hf_layout.count())):
            item = self.hf_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.config_data = load_config()
        hotfolders = self.config_data.get("hotfolders", [])

        for hf in hotfolders:
            widget = HotfolderWidget(hf, parent=self.hf_container)
            self.hf_layout.addWidget(widget)

        self.hf_layout.addStretch()

    def add_hotfolder(self):
        hf_template = {
            "name": "Neuer Hotfolder",
            "monitor_dir": "01_Monitor",
            "success_dir": "02_Success",
            "fault_dir": "03_Fault",
            "logfiles_dir": "04_Logfiles",
            "required_layers": [],
            "required_metadata": [],
            "additional_jsx": ""
        }
        self.config_data.setdefault("hotfolders", []).append(hf_template)
        save_config(self.config_data)
        self.load_hotfolders()

    def delete_hotfolder(self):
        hotfolders = self.config_data.get("hotfolders", [])
        if not hotfolders:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Hotfolder vorhanden.")
            return

        index, ok = QtWidgets.QInputDialog.getInt(
            self, "Hotfolder entfernen",
            "Index des Hotfolders eingeben (1-basiert):",
            1, 1, len(hotfolders)
        )
        if ok:
            idx = index - 1
            if 0 <= idx < len(hotfolders):
                del hotfolders[idx]
                save_config(self.config_data)
                self.load_hotfolders()

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()