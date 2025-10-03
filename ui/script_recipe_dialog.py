#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from PySide6 import QtWidgets, QtCore
from utils.script_config_manager import debug_print, ScriptConfigManager

class ScriptRecipeDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten eines Script-Eintrags.
    Analog zum HotfolderConfigDialog, mit ID-Logik für script_config.json
    """
    def __init__(self, script_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Script-Rezept bearbeiten")
        self.resize(600, 400)
        self.script_data = script_data
        debug_print("ScriptRecipeDialog init: " + str(self.script_data))
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        layout.addLayout(form_layout)

        # Name
        self.name_edit = QtWidgets.QLineEdit(self.script_data.get("name", "Neues Skript"))
        form_layout.addRow("Name:", self.name_edit)

        # Script Path
        self.script_edit = QtWidgets.QLineEdit(self.script_data.get("script_path", ""))
        self.script_browse_btn = QtWidgets.QPushButton("Browse")
        script_hlay = QtWidgets.QHBoxLayout()
        script_hlay.addWidget(self.script_edit, stretch=1)
        script_hlay.addWidget(self.script_browse_btn)
        form_layout.addRow("Script:", script_hlay)
        self.script_browse_btn.clicked.connect(self.browse_script)

        # JSON Folder
        self.json_edit = QtWidgets.QLineEdit(self.script_data.get("json_folder", ""))
        self.json_browse_btn = QtWidgets.QPushButton("Browse")
        json_hlay = QtWidgets.QHBoxLayout()
        json_hlay.addWidget(self.json_edit, stretch=1)
        json_hlay.addWidget(self.json_browse_btn)
        form_layout.addRow("JSON Folder:", json_hlay)
        self.json_browse_btn.clicked.connect(self.browse_json_folder)

        # Action Folder
        self.action_edit = QtWidgets.QLineEdit(self.script_data.get("actionFolderName", ""))
        form_layout.addRow("Action Folder Name:", self.action_edit)

        # Basic Wand Files
        self.basic_edit = QtWidgets.QLineEdit(self.script_data.get("basicWandFiles", ""))
        self.basic_browse_btn = QtWidgets.QPushButton("Browse")
        basic_hlay = QtWidgets.QHBoxLayout()
        basic_hlay.addWidget(self.basic_edit, stretch=1)
        basic_hlay.addWidget(self.basic_browse_btn)
        form_layout.addRow("Basic Wand Files:", basic_hlay)
        self.basic_browse_btn.clicked.connect(lambda: self.browse_path(self.basic_edit, mode="Folder"))

        # CSV Wand File
        self.csv_edit = QtWidgets.QLineEdit(self.script_data.get("csvWandFile", ""))
        self.csv_browse_btn = QtWidgets.QPushButton("Browse")
        csv_hlay = QtWidgets.QHBoxLayout()
        csv_hlay.addWidget(self.csv_edit, stretch=1)
        csv_hlay.addWidget(self.csv_browse_btn)
        form_layout.addRow("CSV Wand File:", csv_hlay)
        self.csv_browse_btn.clicked.connect(lambda: self.browse_path(self.csv_edit, mode="File"))

        # Wand File Save Path
        self.save_edit = QtWidgets.QLineEdit(self.script_data.get("wandFileSavePath", ""))
        self.save_browse_btn = QtWidgets.QPushButton("Browse")
        save_hlay = QtWidgets.QHBoxLayout()
        save_hlay.addWidget(self.save_edit, stretch=1)
        save_hlay.addWidget(self.save_browse_btn)
        form_layout.addRow("Wand File Save Path:", save_hlay)
        self.save_browse_btn.clicked.connect(lambda: self.browse_path(self.save_edit, mode="Folder"))

        # Buttons "Konfiguration speichern"/"Konfiguration laden"
        btn_save_load_layout = QtWidgets.QHBoxLayout()
        self.btn_save_config = QtWidgets.QPushButton("Konfiguration speichern")
        self.btn_load_config = QtWidgets.QPushButton("Konfiguration laden")
        btn_save_load_layout.addWidget(self.btn_save_config)
        btn_save_load_layout.addWidget(self.btn_load_config)
        btn_save_load_layout.addStretch()
        layout.addLayout(btn_save_load_layout)

        self.btn_save_config.clicked.connect(self.save_configuration_to_file)
        self.btn_load_config.clicked.connect(self.load_configuration_from_file)

        # OK/Cancel
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def browse_script(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Script auswählen", "",
            "JSX Files (*.jsx);;All Files (*)"
        )
        if path:
            self.script_edit.setText(path)

    def browse_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON-Folder auswählen", "")
        if folder:
            self.json_edit.setText(folder)

    def browse_path(self, line_edit, mode="Folder"):
        if mode == "Folder":
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", "")
            if folder:
                line_edit.setText(folder)
        else:
            file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Datei auswählen", "")
            if file:
                line_edit.setText(file)

    def save_configuration_to_file(self):
        """
        Exportiert die aktuelle Script-Konfiguration als JSON in eine Datei.
        """
        self.update_script_data_from_fields()
        options = QtWidgets.QFileDialog.Options()
        default_name = "ScriptConfig_" + self.script_data.get("name", "").strip() + ".json"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Konfiguration speichern", default_name,
            "JSON Files (*.json)", options=options
        )
        if filename:
            if not filename.lower().endswith(".json"):
                filename += ".json"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.script_data, f, indent=4)
                QtWidgets.QMessageBox.information(self, "Erfolg", "Konfiguration erfolgreich gespeichert.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {e}")

    def load_configuration_from_file(self):
        """
        Lädt eine Script-Konfiguration aus einer JSON-Datei und aktualisiert die Felder.
        """
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Konfiguration laden", "",
            "JSON Files (*.json)", options=options
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.script_data.update(config)
                self.update_fields_from_script_data()
                QtWidgets.QMessageBox.information(self, "Erfolg", "Konfiguration erfolgreich geladen.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Laden: {e}")

    def accept(self):
        """
        Wird aufgerufen, wenn der Nutzer "OK" klickt.
        Hier setzen wir ggf. eine ID und aktualisieren script_config.json
        via ScriptConfigManager.
        """
        self.update_script_data_from_fields()

        # Falls noch keine ID vorhanden ist, erzeugen wir eine
        if not self.script_data.get("id"):
            new_id = str(uuid.uuid4())
            self.script_data["id"] = new_id
            debug_print(f"Keine ID vorhanden. Neue ID: {new_id}")

        mgr = ScriptConfigManager()
        existing = mgr.get_script_by_id(self.script_data["id"])
        if existing:
            # Update
            debug_print(f"Script mit ID={self.script_data['id']} existiert bereits. Führe update_script durch.")
            mgr.update_script(self.script_data["id"], self.script_data)
        else:
            # Add
            debug_print(f"Kein Script mit ID={self.script_data['id']} gefunden. Füge neues Script hinzu.")
            mgr.add_script(self.script_data)

        super().accept()

    def update_script_data_from_fields(self):
        """
        Übernimmt alle Felder in self.script_data, bevor wir in accept() speichern.
        """
        self.script_data["name"] = self.name_edit.text().strip()
        self.script_data["script_path"] = self.script_edit.text().strip()
        self.script_data["json_folder"] = self.json_edit.text().strip()
        self.script_data["actionFolderName"] = self.action_edit.text().strip()
        self.script_data["basicWandFiles"] = self.basic_edit.text().strip()
        self.script_data["csvWandFile"] = self.csv_edit.text().strip()
        self.script_data["wandFileSavePath"] = self.save_edit.text().strip()

    def update_fields_from_script_data(self):
        self.name_edit.setText(self.script_data.get("name", "Neues Skript"))
        self.script_edit.setText(self.script_data.get("script_path", ""))
        self.json_edit.setText(self.script_data.get("json_folder", ""))
        self.action_edit.setText(self.script_data.get("actionFolderName", ""))
        self.basic_edit.setText(self.script_data.get("basicWandFiles", ""))
        self.csv_edit.setText(self.script_data.get("csvWandFile", ""))
        self.save_edit.setText(self.script_data.get("wandFileSavePath", ""))