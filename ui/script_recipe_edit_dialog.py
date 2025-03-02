#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore
from config.script_config_manager import debug_print, list_photoshop_action_sets

class ScriptRecipeEditDialog(QtWidgets.QDialog):
    def __init__(self, recipe_data: dict, parent=None):
        """
        recipe_data: Ein Dictionary mit
          {
            "script_path": "...",
            "json_folder": "...",
            "actionFolderName": "...",
            "basicWandFiles": "...",
            "csvWandFile": "...",
            "wandFileSavePath": "..."
          }
        """
        super().__init__(parent)
        self.setWindowTitle("Script/Rezept bearbeiten")
        self.recipe_data = recipe_data.copy()  # lokales Exemplar

        self.init_ui()
        self.load_values()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        # Script Path
        self.script_path_edit = QtWidgets.QLineEdit()
        self.script_browse_btn = QtWidgets.QPushButton("Browse")
        self.script_browse_btn.clicked.connect(self.browse_script)
        script_layout = QtWidgets.QHBoxLayout()
        script_layout.addWidget(self.script_path_edit, stretch=1)
        script_layout.addWidget(self.script_browse_btn)
        form_layout.addRow("Script Path:", script_layout)

        # JSON Folder
        self.json_folder_edit = QtWidgets.QLineEdit()
        self.json_browse_btn = QtWidgets.QPushButton("Browse")
        self.json_browse_btn.clicked.connect(self.browse_json_folder)
        json_layout = QtWidgets.QHBoxLayout()
        json_layout.addWidget(self.json_folder_edit, stretch=1)
        json_layout.addWidget(self.json_browse_btn)
        form_layout.addRow("JSON Folder:", json_layout)

        # Action Folder Name (Dropdown aus list_photoshop_action_sets)
        self.action_folder_combo = QtWidgets.QComboBox()
        # Wir befüllen das Combo mit den Werten aus list_photoshop_action_sets()
        action_sets = list_photoshop_action_sets()
        self.action_folder_combo.addItems(action_sets)
        form_layout.addRow("Action Folder Name:", self.action_folder_combo)

        # BasicWandFiles
        self.basic_wand_edit = QtWidgets.QLineEdit()
        self.basic_wand_btn = QtWidgets.QPushButton("Browse")
        self.basic_wand_btn.clicked.connect(self.browse_basic_wand)
        wand_layout = QtWidgets.QHBoxLayout()
        wand_layout.addWidget(self.basic_wand_edit, stretch=1)
        wand_layout.addWidget(self.basic_wand_btn)
        form_layout.addRow("Basic Wand Files:", wand_layout)

        # CSVWandFile
        self.csv_wand_edit = QtWidgets.QLineEdit()
        self.csv_wand_btn = QtWidgets.QPushButton("Browse")
        self.csv_wand_btn.clicked.connect(self.browse_csv_wand)
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csv_wand_edit, stretch=1)
        csv_layout.addWidget(self.csv_wand_btn)
        form_layout.addRow("CSV Wand File:", csv_layout)

        # WandFileSavePath
        self.wand_save_edit = QtWidgets.QLineEdit()
        self.wand_save_btn = QtWidgets.QPushButton("Browse")
        self.wand_save_btn.clicked.connect(self.browse_wand_save)
        save_layout = QtWidgets.QHBoxLayout()
        save_layout.addWidget(self.wand_save_edit, stretch=1)
        save_layout.addWidget(self.wand_save_btn)
        form_layout.addRow("Wand File Save Path:", save_layout)

        layout.addLayout(form_layout)

        # Buttons OK / Cancel
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def load_values(self):
        self.script_path_edit.setText(self.recipe_data.get("script_path", ""))
        self.json_folder_edit.setText(self.recipe_data.get("json_folder", ""))

        # actionFolderName ins Combo
        action_name = self.recipe_data.get("actionFolderName", "")
        idx = self.action_folder_combo.findText(action_name)
        if idx >= 0:
            self.action_folder_combo.setCurrentIndex(idx)

        self.basic_wand_edit.setText(self.recipe_data.get("basicWandFiles", ""))
        self.csv_wand_edit.setText(self.recipe_data.get("csvWandFile", ""))
        self.wand_save_edit.setText(self.recipe_data.get("wandFileSavePath", ""))

    def browse_script(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Script auswählen", "", "JSX Files (*.jsx);;All Files (*)")
        if fname:
            self.script_path_edit.setText(fname)

    def browse_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON-Folder auswählen", "")
        if folder:
            self.json_folder_edit.setText(folder)

    def browse_basic_wand(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Basic Wand Ordner auswählen", "")
        if folder:
            self.basic_wand_edit.setText(folder)

    def browse_csv_wand(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV Wand File auswählen", "", "CSV Files (*.csv);;All Files (*)")
        if fname:
            self.csv_wand_edit.setText(fname)

    def browse_wand_save(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "WandFileSavePath auswählen", "")
        if folder:
            self.wand_save_edit.setText(folder)

    def get_data(self):
        """
        Gibt das aktualisierte Dictionary zurück, z.B.:
        {
          "script_path": "...",
          "json_folder": "...",
          "actionFolderName": "...",
          "basicWandFiles": "...",
          "csvWandFile": "...",
          "wandFileSavePath": "..."
        }
        """
        result = {}
        result["script_path"] = self.script_path_edit.text().strip()
        result["json_folder"] = self.json_folder_edit.text().strip()
        result["actionFolderName"] = self.action_folder_combo.currentText().strip()
        result["basicWandFiles"] = self.basic_wand_edit.text().strip()
        result["csvWandFile"] = self.csv_wand_edit.text().strip()
        result["wandFileSavePath"] = self.wand_save_edit.text().strip()
        return result