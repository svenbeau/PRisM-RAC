#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import json
from PyQt5 import QtWidgets, QtCore
from config.config_manager import debug_print, save_settings, load_settings

class ScriptRecipeConfigDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten eines einzelnen Script-Eintrags (Skriptpfad, JSON-Ordner, Action-Folder-Name).
    """
    def __init__(self, script_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Script-Rezept Konfiguration")
        self.resize(600, 300)

        # Direkte Referenz; Änderungen wirken direkt im übergebenen Dictionary
        self.script_data = script_data
        debug_print("ScriptRecipeConfigDialog init: " + str(self.script_data))

        self.current_config = load_settings()
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # (A) Formulardaten
        form_layout = QtWidgets.QFormLayout()

        # ID (nur zur Info)
        self.id_label = QtWidgets.QLabel(self.script_data.get("id", "NO-ID"))
        form_layout.addRow("ID:", self.id_label)

        # Script Path
        self.script_path_edit = QtWidgets.QLineEdit(self.script_data.get("script_path", ""))
        self.browse_script_btn = QtWidgets.QPushButton("Browse")
        script_layout = QtWidgets.QHBoxLayout()
        script_layout.addWidget(self.script_path_edit, stretch=1)
        script_layout.addWidget(self.browse_script_btn)
        form_layout.addRow("Script-Pfad:", script_layout)

        # JSON Folder
        self.json_folder_edit = QtWidgets.QLineEdit(self.script_data.get("json_folder", ""))
        self.browse_json_btn = QtWidgets.QPushButton("Browse")
        json_layout = QtWidgets.QHBoxLayout()
        json_layout.addWidget(self.json_folder_edit, stretch=1)
        json_layout.addWidget(self.browse_json_btn)
        form_layout.addRow("JSON-Ordner:", json_layout)

        # Action Folder Name
        self.action_folder_edit = QtWidgets.QLineEdit(self.script_data.get("action_folder", ""))
        form_layout.addRow("Action-Folder-Name:", self.action_folder_edit)

        main_layout.addLayout(form_layout)

        # (B) OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        main_layout.addWidget(btn_box)

        # Signals
        self.browse_script_btn.clicked.connect(self.on_browse_script)
        self.browse_json_btn.clicked.connect(self.on_browse_json)
        btn_box.accepted.connect(self.save_and_close)
        btn_box.rejected.connect(self.reject)

    def on_browse_script(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Wähle Skript", "", "JSX Files (*.jsx);;Alle Dateien (*)"
        )
        if file_path:
            self.script_path_edit.setText(file_path)

    def on_browse_json(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle JSON-Ordner", "")
        if folder:
            self.json_folder_edit.setText(folder)

    def save_and_close(self):
        debug_print("Vor save_and_close - ScriptRecipe war: " + str(self.script_data))

        # Übernehme Felder in self.script_data
        self.script_data["script_path"] = self.script_path_edit.text().strip()
        self.script_data["json_folder"] = self.json_folder_edit.text().strip()
        self.script_data["action_folder"] = self.action_folder_edit.text().strip()

        # Falls kein ID vorhanden, erzeuge neue
        if not self.script_data.get("id"):
            new_id = str(uuid.uuid4())
            self.script_data["id"] = new_id
            debug_print("Keine ID vorhanden. Neue ID: " + new_id)

        debug_print("In save_and_close - ScriptRecipe neu: " + str(self.script_data))

        # Hier könntest du optional direkt die globale settings.json aktualisieren,
        # aber in der Regel macht das ListWidget das Speichern.
        self.accept()