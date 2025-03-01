#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Recipe Widget for PRisM-RAC.
Dieses Widget ermöglicht es, für jedes Script (z. B. GRIS_Render_2025.jsx,
GRIS_C_ReadWriteCSV.jsx, GRIS_Wandabbildungen_2024.jsx) eine individuelle
Konfiguration zu speichern. Folgende Felder sind konfigurierbar:
    - Script Folder (Dropdown, über den Finder auswählbar)
    - Script (Dropdown, basierend auf den .jsx-Dateien im Script Folder)
    - JSON Folder (Dropdown mit "recent" Einträgen + Durchsuchen)
    - Action Folder Name (Textfeld)
    - Basic Wand Files (Dropdown + Durchsuchen)
    - CSV Wand File (Dropdown + Durchsuchen)
    - Wand File Save Path (Dropdown + Durchsuchen)
Die Konfiguration wird in config/script_config.json gespeichert.
"""

import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui

from config.script_config_manager import (
    load_script_config,
    save_script_config,
    list_photoshop_action_sets,
    debug_print
)
from config.config_manager import load_settings  # Falls wir "recent" Einträge benötigen

class ScriptRecipeWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        """
        Konstruktor: Erwartet ein settings-Dictionary als ersten Parameter.
        """
        super().__init__(parent)
        self.settings = settings
        # Lade die Script-Konfiguration aus script_config.json
        self.script_config = load_script_config()  # Erwartet z. B. {"scripts": [ { ... }, ... ]}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        title_label = QtWidgets.QLabel("Script › Rezept Zuordnung")
        title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        layout.addWidget(title_label)

        # Tabelle zur Anzeige der Konfigurationen
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Script Folder", "Script", "JSON Folder",
            "Action Folder", "Basic Wand Files", "CSV Wand File", "Wand File Save Path"
        ])
        header = self.table.horizontalHeader()
        # Spaltenbreite von 180 auf 360 verdoppelt
        for i in range(7):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Interactive)
            header.resizeSection(i, 360)
        layout.addWidget(self.table)

        # Button-Leiste: Hinzufügen, Löschen, Bearbeiten
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
            items = []
            # Reihenfolge wie in setHorizontalHeaderLabels
            for key in [
                "script_folder", "script_path", "json_folder",
                "actionFolderName", "basicWandFiles", "csvWandFile", "wandFileSavePath"
            ]:
                text = recipe.get(key, "")
                item = QtWidgets.QTableWidgetItem(text)
                # Rechtsbündig + vertikal zentriert
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                items.append(item)
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

    def add_recipe(self):
        new_recipe = {
            "script_folder": "Choose your script folder...",
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
        # Dialog anzeigen
        dialog = RecipeEditDialog(recipe, self.settings, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Speichern
            save_script_config(self.script_config)
            self.load_table()


class RecipeEditDialog(QtWidgets.QDialog):
    def __init__(self, recipe, settings, parent=None):
        """
        Konstruktor: Erwartet ein Rezept-Dictionary und das settings-Dictionary.
        """
        super().__init__(parent)
        self.recipe = recipe
        self.settings = settings
        self.setWindowTitle("Rezept bearbeiten")
        # Mache das Dialog-Fenster breiter
        self.resize(1000, 400)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QFormLayout(self)

        # 1) Script Folder (Dropdown + Browse)
        self.script_folder_combo = QtWidgets.QComboBox(self)
        self.script_folder_combo.setEditable(True)
        # Dropdown doppelt so breit
        self.script_folder_combo.setMinimumWidth(400)
        recent_script_folders = self.settings.get("recent_script_folders", [])
        if not recent_script_folders:
            recent_script_folders = [os.path.expanduser("~")]
        self.script_folder_combo.addItems(recent_script_folders)
        self.script_folder_combo.setCurrentText(self.recipe.get("script_folder", recent_script_folders[0]))

        browse_script_folder_btn = QtWidgets.QPushButton("Durchsuchen", self)
        browse_script_folder_btn.setFixedWidth(100)
        browse_script_folder_btn.clicked.connect(self.select_script_folder)

        script_folder_layout = QtWidgets.QHBoxLayout()
        script_folder_layout.addWidget(self.script_folder_combo)
        script_folder_layout.addWidget(browse_script_folder_btn)
        layout.addRow("Script Folder:", script_folder_layout)

        # 2) Script (Dropdown) basierend auf dem Ordner
        self.script_combo = QtWidgets.QComboBox(self)
        self.script_combo.setEditable(True)
        self.script_combo.setMinimumWidth(400)  # doppelt so breit
        self.populate_script_combo(self.script_folder_combo.currentText())

        current_script_base = os.path.basename(self.recipe.get("script_path", ""))
        idx = self.script_combo.findText(current_script_base)
        if idx >= 0:
            self.script_combo.setCurrentIndex(idx)
        layout.addRow("Script:", self.script_combo)

        # 3) JSON Folder
        self.json_combo = QtWidgets.QComboBox(self)
        self.json_combo.setEditable(True)
        self.json_combo.setMinimumWidth(400)
        recent_json = self.settings.get("recent_json_folders", [])
        if not recent_json:
            recent_json = [os.path.expanduser("~")]
        self.json_combo.addItems(recent_json)
        self.json_combo.setCurrentText(self.recipe.get("json_folder", ""))
        json_btn = QtWidgets.QPushButton("Durchsuchen", self)
        json_btn.setFixedWidth(100)
        json_btn.clicked.connect(self.select_json_folder)
        json_layout = QtWidgets.QHBoxLayout()
        json_layout.addWidget(self.json_combo)
        json_layout.addWidget(json_btn)
        layout.addRow("JSON Folder:", json_layout)

        # 4) Action Folder Name (LineEdit)
        self.action_line = QtWidgets.QLineEdit(self)
        self.action_line.setMinimumWidth(400)
        self.action_line.setText(self.recipe.get("actionFolderName", ""))
        layout.addRow("Action Folder Name:", self.action_line)

        # 5) Basic Wand Files
        self.basic_combo = QtWidgets.QComboBox(self)
        self.basic_combo.setEditable(True)
        self.basic_combo.setMinimumWidth(400)
        recent_basic = self.settings.get("recent_basic_wand_folders", [])
        if not recent_basic:
            recent_basic = [os.path.expanduser("~")]
        self.basic_combo.addItems(recent_basic)
        self.basic_combo.setCurrentText(self.recipe.get("basicWandFiles", ""))
        basic_btn = QtWidgets.QPushButton("Durchsuchen", self)
        basic_btn.setFixedWidth(100)
        basic_btn.clicked.connect(self.select_basic_wand_folder)
        basic_layout = QtWidgets.QHBoxLayout()
        basic_layout.addWidget(self.basic_combo)
        basic_layout.addWidget(basic_btn)
        layout.addRow("Basic Wand Files:", basic_layout)

        # 6) CSV Wand File
        self.csv_combo = QtWidgets.QComboBox(self)
        self.csv_combo.setEditable(True)
        self.csv_combo.setMinimumWidth(400)
        recent_csv = self.settings.get("recent_csv_files", [])
        if not recent_csv:
            recent_csv = [os.path.expanduser("~")]
        self.csv_combo.addItems(recent_csv)
        self.csv_combo.setCurrentText(self.recipe.get("csvWandFile", ""))
        csv_btn = QtWidgets.QPushButton("Durchsuchen", self)
        csv_btn.setFixedWidth(100)
        csv_btn.clicked.connect(self.select_csv_wand_file)
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csv_combo)
        csv_layout.addWidget(csv_btn)
        layout.addRow("CSV Wand File:", csv_layout)

        # 7) Wand File Save Path
        self.wand_combo = QtWidgets.QComboBox(self)
        self.wand_combo.setEditable(True)
        self.wand_combo.setMinimumWidth(400)
        recent_wand = self.settings.get("recent_wand_save_paths", [])
        if not recent_wand:
            recent_wand = [os.path.expanduser("~")]
        self.wand_combo.addItems(recent_wand)
        self.wand_combo.setCurrentText(self.recipe.get("wandFileSavePath", ""))
        wand_btn = QtWidgets.QPushButton("Durchsuchen", self)
        wand_btn.setFixedWidth(100)
        wand_btn.clicked.connect(self.select_wand_save_folder)
        wand_layout = QtWidgets.QHBoxLayout()
        wand_layout.addWidget(self.wand_combo)
        wand_layout.addWidget(wand_btn)
        layout.addRow("Wand File Save Path:", wand_layout)

        # Dialog-Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def populate_script_combo(self, folder):
        """
        Liest alle .jsx-Dateien aus dem angegebenen Ordner aus und befüllt self.script_combo.
        """
        self.script_combo.clear()
        if os.path.isdir(folder):
            scripts = [f for f in os.listdir(folder) if f.lower().endswith(".jsx")]
            scripts.sort()
            self.script_combo.addItems(scripts)

    def select_script_folder(self):
        """
        Öffnet einen QFileDialog, um einen Script-Ordner auszuwählen.
        Anschließend wird die script_combo neu befüllt.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Script Folder auswählen", self.script_folder_combo.currentText()
        )
        if folder:
            self.script_folder_combo.setCurrentText(folder)
            # Re-populate the script combo
            self.populate_script_combo(folder)

    def select_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "JSON Folder auswählen", self.json_combo.currentText()
        )
        if folder:
            self.json_combo.setCurrentText(folder)

    def select_basic_wand_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Basic Wand Files auswählen", self.basic_combo.currentText()
        )
        if folder:
            self.basic_combo.setCurrentText(folder)

    def select_csv_wand_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "CSV Wand File auswählen", self.csv_combo.currentText(), "CSV Files (*.csv)"
        )
        if file_path:
            self.csv_combo.setCurrentText(file_path)

    def select_wand_save_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Wand File Save Path auswählen", self.wand_combo.currentText()
        )
        if folder:
            self.wand_combo.setCurrentText(folder)

    def accept(self):
        """
        Beim Bestätigen werden alle Felder in self.recipe übernommen.
        """
        self.recipe["script_folder"] = self.script_folder_combo.currentText()
        selected_script_name = self.script_combo.currentText()  # z. B. "GRIS_Render_2025.jsx"
        # Falls der script_folder existiert, Pfade zusammenbauen
        script_folder = self.recipe["script_folder"]
        if os.path.isdir(script_folder):
            script_path = os.path.join(script_folder, selected_script_name)
        else:
            script_path = selected_script_name  # Fallback
        self.recipe["script_path"] = script_path

        self.recipe["json_folder"] = self.json_combo.currentText()
        self.recipe["actionFolderName"] = self.action_line.text()
        self.recipe["basicWandFiles"] = self.basic_combo.currentText()
        self.recipe["csvWandFile"] = self.csv_combo.currentText()
        self.recipe["wandFileSavePath"] = self.wand_combo.currentText()
        super().accept()


# Kleiner Test bei direktem Aufruf:
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Beispiel-Settings-Dict mit "recent" Einträgen
    test_settings = {
        "recent_script_folders": ["/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/scripts"],
        "recent_json_folders": ["/path/to/json1", "/path/to/json2"],
        "recent_basic_wand_folders": ["/path/to/basic1", "/path/to/basic2"],
        "recent_csv_files": ["/path/to/csv1.csv", "/path/to/csv2.csv"],
        "recent_wand_save_paths": ["/path/to/wand1", "/path/to/wand2"]
    }
    widget = ScriptRecipeWidget(test_settings, parent=None)
    widget.show()
    sys.exit(app.exec_())