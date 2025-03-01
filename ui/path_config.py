#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore
import os
from config.config_manager import get_resource_path, update_resource_path, debug_print, save_settings, load_settings

class PathConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen – Ressourcypfade")
        self.resize(500, 300)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.fields = {}
        # Erstelle ein Eingabefeld für jeden wichtigen Pfad
        for key, default in self.settings.get("resource_paths", {}).items():
            hlayout = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(f"{key.capitalize()}-Pfad:")
            lineEdit = QtWidgets.QLineEdit(self)
            lineEdit.setText(default)
            browseButton = QtWidgets.QPushButton("Browse", self)
            browseButton.clicked.connect(lambda checked, k=key, le=lineEdit: self.browse_path(k, le))
            hlayout.addWidget(label)
            hlayout.addWidget(lineEdit)
            hlayout.addWidget(browseButton)
            layout.addLayout(hlayout)
            self.fields[key] = lineEdit

        # OK / Cancel Buttons
        btnBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

    def browse_path(self, key, lineEdit):
        start_dir = os.path.expanduser("~")
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, f"Wähle {key}-Pfad", start_dir)
        if folder:
            lineEdit.setText(folder)

    def accept(self):
        # Speichere die neuen Pfade in den Einstellungen
        for key, lineEdit in self.fields.items():
            new_path = lineEdit.text().strip()
            update_resource_path(key, new_path)
        super().accept()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = PathConfigDialog()
    if dlg.exec_():
        print("Einstellungen gespeichert.")
    else:
        print("Abgebrochen.")