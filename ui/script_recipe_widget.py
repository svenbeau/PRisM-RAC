#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Recipe Widget for PRisM-RAC.
Dieses Widget ermöglicht es, für jedes Script (z. B. GRIS_Render_2025.jsx,
GRIS_C_ReadWriteCSV.jsx, GRIS_Wandabbildungen_2024.jsx) eine individuelle
Konfiguration zu speichern. Folgende Felder sind konfigurierbar:
    - Script (über Dropdown – der vollständige Pfad wird intern zusammengesetzt)
    - JSON Folder (Ordner, in dem die zu verwendenden JSON-Dateien liegen)
    - Action Folder Name
    - Basic Wand Files (Ordner)
    - CSV Wand File (Datei)
    - Wand File Save Path (Ordner)
Die Konfiguration wird in config/script_config.json gespeichert.
"""

import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui

from config.script_config_manager import load_script_config, save_script_config, list_photoshop_action_sets, debug_print

class ScriptRecipeWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        """
        Konstruktor: Erwartet ein settings-Dictionary als ersten Parameter.
        """
        super().__init__(parent)
        self.settings = settings
        # Lade die Script-Konfiguration aus script_config.json
        self.script_config = load_script_config()  # Erwartet ein Dictionary z. B. {"scripts": [...]}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        title_label = QtWidgets.QLabel("Script › Rezept Zuordnung")
        title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        layout.addWidget(title_label)

        # Tabelle, in der die Konfigurationen angezeigt werden
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Script", "JSON Folder", "Action Folder",
            "Basic Wand Files", "CSV Wand File", "Wand File Save Path"
        ])
        # Spaltenbreiten anpassbar (Beispielwerte)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Interactive)
        layout.addWidget(self.table)

        # Button-Leiste
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Hinzufügen")
        self.remove_btn = QtWidgets.QPushButton("Löschen")
        self.edit_btn = QtWidgets.QPushButton("Bearbeiten")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.edit_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_recipe)
        self.remove_btn.clicked.connect(self.remove_recipe)
        self.edit_btn.clicked.connect(self.edit_recipe)

        self.load_table()

    def load_table(self):
        recipes = self.script_config.get("scripts", [])
        self.table.setRowCount(len(recipes))
        for row, recipe in enumerate(recipes):
            # Erstelle Tabellenitems für jedes Feld
            script_item = QtWidgets.QTableWidgetItem(recipe.get("script_path", ""))
            json_item = QtWidgets.QTableWidgetItem(recipe.get("json_folder", ""))
            action_item = QtWidgets.QTableWidgetItem(recipe.get("actionFolderName", ""))
            basic_item = QtWidgets.QTableWidgetItem(recipe.get("basicWandFiles", ""))
            csv_item = QtWidgets.QTableWidgetItem(recipe.get("csvWandFile", ""))
            wand_item = QtWidgets.QTableWidgetItem(recipe.get("wandFileSavePath", ""))

            # Richte die Textausrichtung in den Pfadspalten rechtsbündig ein
            for item in [script_item, json_item, action_item, basic_item, csv_item, wand_item]:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            self.table.setItem(row, 0, script_item)
            self.table.setItem(row, 1, json_item)
            self.table.setItem(row, 2, action_item)
            self.table.setItem(row, 3, basic_item)
            self.table.setItem(row, 4, csv_item)
            self.table.setItem(row, 5, wand_item)

    def add_recipe(self):
        # Füge einen neuen leeren Eintrag hinzu
        new_recipe = {
            "script_path": "Choose your script here...",
            "json_folder": "Set your JSON folder...",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.script_config.setdefault("scripts", []).append(new_recipe)
        save_script_config(self.script_config)
        self.load_table()

    def remove_recipe(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            del self.script_config["scripts"][current_row]
            save_script_config(self.script_config)
            self.load_table()

    def edit_recipe(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QtWidgets.QMessageBox.warning(self, "Warnung", "Bitte wähle einen Eintrag aus, um ihn zu bearbeiten.")
            return
        recipe = self.script_config["scripts"][current_row]
        dialog = RecipeEditDialog(recipe, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            save_script_config(self.script_config)
            self.load_table()

class RecipeEditDialog(QtWidgets.QDialog):
    def __init__(self, recipe, parent=None):
        super().__init__(parent)
        self.recipe = recipe
        self.setWindowTitle("Rezept bearbeiten")
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QFormLayout(self)

        # Script Dropdown: Suche im globalen Skriptordner
        self.script_combo = QtWidgets.QComboBox(self)
        global_script_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
        if os.path.isdir(global_script_folder):
            scripts = [f for f in os.listdir(global_script_folder) if f.lower().endswith(".jsx")]
            self.script_combo.addItems(scripts)
        current_script = os.path.basename(self.recipe.get("script_path", ""))
        index = self.script_combo.findText(current_script)
        if index >= 0:
            self.script_combo.setCurrentIndex(index)
        layout.addRow("Script:", self.script_combo)

        # JSON Folder
        self.json_folder_line = QtWidgets.QLineEdit(self)
        self.json_folder_line.setText(self.recipe.get("json_folder", ""))
        self.json_folder_btn = QtWidgets.QPushButton("Durchsuchen", self)
        self.json_folder_btn.clicked.connect(self.select_json_folder)
        json_layout = QtWidgets.QHBoxLayout()
        json_layout.addWidget(self.json_folder_line)
        json_layout.addWidget(self.json_folder_btn)
        layout.addRow("JSON Folder:", json_layout)

        # Action Folder Name
        self.action_folder_line = QtWidgets.QLineEdit(self)
        self.action_folder_line.setText(self.recipe.get("actionFolderName", ""))
        layout.addRow("Action Folder Name:", self.action_folder_line)

        # Basic Wand Files
        self.basic_wand_line = QtWidgets.QLineEdit(self)
        self.basic_wand_line.setText(self.recipe.get("basicWandFiles", ""))
        self.basic_wand_btn = QtWidgets.QPushButton("Durchsuchen", self)
        self.basic_wand_btn.clicked.connect(self.select_basic_wand_folder)
        basic_layout = QtWidgets.QHBoxLayout()
        basic_layout.addWidget(self.basic_wand_line)
        basic_layout.addWidget(self.basic_wand_btn)
        layout.addRow("Basic Wand Files:", basic_layout)

        # CSV Wand File
        self.csv_wand_line = QtWidgets.QLineEdit(self)
        self.csv_wand_line.setText(self.recipe.get("csvWandFile", ""))
        self.csv_wand_btn = QtWidgets.QPushButton("Durchsuchen", self)
        self.csv_wand_btn.clicked.connect(self.select_csv_wand_file)
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csv_wand_line)
        csv_layout.addWidget(self.csv_wand_btn)
        layout.addRow("CSV Wand File:", csv_layout)

        # Wand File Save Path
        self.wand_save_line = QtWidgets.QLineEdit(self)
        self.wand_save_line.setText(self.recipe.get("wandFileSavePath", ""))
        self.wand_save_btn = QtWidgets.QPushButton("Durchsuchen", self)
        self.wand_save_btn.clicked.connect(self.select_wand_save_folder)
        save_layout = QtWidgets.QHBoxLayout()
        save_layout.addWidget(self.wand_save_line)
        save_layout.addWidget(self.wand_save_btn)
        layout.addRow("Wand File Save Path:", save_layout)

        # Dialog-Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def select_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON Folder auswählen", self.json_folder_line.text())
        if folder:
            self.json_folder_line.setText(folder)

    def select_basic_wand_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Basic Wand Files Folder auswählen", self.basic_wand_line.text())
        if folder:
            self.basic_wand_line.setText(folder)

    def select_csv_wand_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV Wand File auswählen", self.csv_wand_line.text(), "CSV Files (*.csv)")
        if file_path:
            self.csv_wand_line.setText(file_path)

    def select_wand_save_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wand File Save Path auswählen", self.wand_save_line.text())
        if folder:
            self.wand_save_line.setText(folder)

    def accept(self):
        global_script_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
        selected_script = self.script_combo.currentText()
        self.recipe["script_path"] = os.path.join(global_script_folder, selected_script)
        self.recipe["json_folder"] = self.json_folder_line.text()
        self.recipe["actionFolderName"] = self.action_folder_line.text()
        self.recipe["basicWandFiles"] = self.basic_wand_line.text()
        self.recipe["csvWandFile"] = self.csv_wand_line.text()
        self.recipe["wandFileSavePath"] = self.wand_save_line.text()
        super().accept()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = ScriptRecipeWidget({}, parent=None)
    widget.show()
    sys.exit(app.exec_())