#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Recipe List Widget

Dieses Widget stellt eine Tabelle zur Verwaltung der Script‑Rezept‑Zuordnungen bereit.
Jede Zeile entspricht einer Konfiguration, in der u.a. der Script‑Pfad, der JSON‑Ordner,
der Action Folder Name, die Basic Wand Files, das CSV Wand File und der Wand File Save Path
konfiguriert werden können.

Die Funktionalität entspricht weitgehend der Hotfolder‑Konfiguration.
"""

import os
from PyQt5 import QtWidgets, QtCore


class ScriptRecipeListWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        """
        Initialisiert das Widget.

        :param settings: Das Settings-Dictionary (aus settings.json), in dem z. B. auch
                         'recentScriptPaths' und 'scriptRecipeMappings' stehen.
        :param parent: Optionaler Parent.
        """
        super().__init__(parent)
        self.settings = settings
        # Wir erwarten hier, dass in den Einstellungen der Schlüssel "scriptRecipeMappings" existiert.
        # Falls nicht, initialisieren wir eine leere Liste.
        self.recipes = self.settings.get("scriptRecipeMappings", [])
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Tabellenansicht zur Darstellung der Rezept-Zuordnungen
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Script", "JSON Folder", "Action Folder",
            "Basic Wand Files", "CSV Wand File", "Wand File Save Path"
        ])
        header = self.table.horizontalHeader()
        # Setze die Spaltenbreiten (z.B. Buttons-Spalten auf 100-150px, Textfelder breiter)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)  # Script
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)  # JSON Folder
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)  # Action Folder
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)  # Basic Wand Files
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Interactive)  # CSV Wand File
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Interactive)  # Wand File Save Path
        # Hier kannst Du bei Bedarf Standardbreiten vorgeben:
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 300)
        self.table.setColumnWidth(4, 300)
        self.table.setColumnWidth(5, 300)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        layout.addWidget(self.table)

        # Button-Leiste (Hinzufügen, Löschen, Bearbeiten)
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add Recipe")
        self.delete_btn = QtWidgets.QPushButton("Delete Recipe")
        self.edit_btn = QtWidgets.QPushButton("Edit Recipe")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.edit_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_recipe)
        self.delete_btn.clicked.connect(self.delete_selected_recipe)
        self.edit_btn.clicked.connect(self.edit_selected_recipe)

        self.load_table()

    def load_table(self):
        """Lädt die vorhandenen Rezept-Konfigurationen in die Tabelle."""
        self.table.setRowCount(0)
        for recipe in self.recipes:
            self.add_row(recipe)

    def add_row(self, recipe):
        """Fügt eine Zeile zur Tabelle hinzu."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Spalte 0: Script – als Dropdown, basierend auf den zuletzt verwendeten Script-Pfaden
        script_cb = QtWidgets.QComboBox(self)
        available_scripts = self.settings.get("recentScriptPaths", [])
        script_cb.addItems(available_scripts)
        if recipe.get("script_path"):
            index = script_cb.findText(recipe["script_path"])
            if index >= 0:
                script_cb.setCurrentIndex(index)
            else:
                script_cb.setCurrentText(recipe["script_path"])
        self.table.setCellWidget(row, 0, script_cb)

        # Spalte 1: JSON Folder – Widget zur Ordnerauswahl
        json_folder_widget = self.create_folder_selector(recipe.get("json_folder", ""))
        self.table.setCellWidget(row, 1, json_folder_widget)

        # Spalte 2: Action Folder – Einfache QLineEdit zur Eingabe
        action_edit = QtWidgets.QLineEdit(recipe.get("actionFolderName", ""), self)
        self.table.setCellWidget(row, 2, action_edit)

        # Spalte 3: Basic Wand Files – Ordner-Auswahl-Widget
        basic_wand_widget = self.create_folder_selector(recipe.get("basicWandFiles", ""))
        self.table.setCellWidget(row, 3, basic_wand_widget)

        # Spalte 4: CSV Wand File – Datei-Auswahl-Widget (nur .csv)
        csv_widget = self.create_file_selector(recipe.get("csvWandFile", ""), "CSV Files (*.csv)")
        self.table.setCellWidget(row, 4, csv_widget)

        # Spalte 5: Wand File Save Path – Ordner-Auswahl-Widget
        wand_save_widget = self.create_folder_selector(recipe.get("wandFileSavePath", ""))
        self.table.setCellWidget(row, 5, wand_save_widget)

    def create_folder_selector(self, initial_path):
        """Erzeugt ein Widget mit einem QLineEdit (schreibgeschützt) und einem 'Browse'-Button zur Ordnerauswahl."""
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = QtWidgets.QLineEdit(initial_path, widget)
        line_edit.setReadOnly(True)
        btn = QtWidgets.QPushButton("Browse", widget)
        btn.setFixedWidth(100)
        btn.clicked.connect(lambda: self.browse_folder(line_edit))
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        return widget

    def create_file_selector(self, initial_path, file_filter="All Files (*)"):
        """Erzeugt ein Widget mit einem QLineEdit (schreibgeschützt) und einem 'Browse'-Button zur Dateiauswahl."""
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = QtWidgets.QLineEdit(initial_path, widget)
        line_edit.setReadOnly(True)
        btn = QtWidgets.QPushButton("Browse", widget)
        btn.setFixedWidth(100)
        btn.clicked.connect(lambda: self.browse_file(line_edit, file_filter))
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        return widget

    def browse_folder(self, line_edit):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder",
                                                            line_edit.text() or QtCore.QDir.homePath())
        if folder:
            line_edit.setText(folder)

    def browse_file(self, line_edit, file_filter):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File",
                                                             line_edit.text() or QtCore.QDir.homePath(), file_filter)
        if file_path:
            line_edit.setText(file_path)

    def add_recipe(self):
        """Fügt einen leeren Eintrag hinzu und aktualisiert die Tabelle."""
        new_recipe = {
            "script_path": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.recipes.append(new_recipe)
        self.add_row(new_recipe)

    def delete_selected_recipe(self):
        """Löscht die aktuell in der Tabelle markierte Zeile."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        self.table.removeRow(row)
        del self.recipes[row]

    def edit_selected_recipe(self):
        """Öffnet einen Dialog zum Bearbeiten der ausgewählten Zeile.
           (Hier könntest Du ein separates Bearbeitungs-Widget aufrufen.)"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        # Hier könnte man z. B. einen Dialog öffnen, um den Eintrag zu bearbeiten.
        QtWidgets.QMessageBox.information(self, "Edit Recipe", f"Edit row {row} not implemented yet.")

    def get_config_data(self):
        """Extrahiert die Konfiguration aus der Tabelle und liefert ein Dictionary zurück."""
        config_data = {"scripts": []}
        for row in range(self.table.rowCount()):
            row_data = {}
            # Script
            script_cb = self.table.cellWidget(row, 0)
            row_data["script_path"] = script_cb.currentText() if script_cb else ""
            # JSON Folder
            json_widget = self.table.cellWidget(row, 1)
            line_edit = json_widget.findChild(QtWidgets.QLineEdit) if json_widget else None
            row_data["json_folder"] = line_edit.text() if line_edit else ""
            # Action Folder
            action_edit = self.table.cellWidget(row, 2)
            row_data["actionFolderName"] = action_edit.text() if action_edit else ""
            # Basic Wand Files
            basic_widget = self.table.cellWidget(row, 3)
            line_edit = basic_widget.findChild(QtWidgets.QLineEdit) if basic_widget else None
            row_data["basicWandFiles"] = line_edit.text() if line_edit else ""
            # CSV Wand File
            csv_widget = self.table.cellWidget(row, 4)
            line_edit = csv_widget.findChild(QtWidgets.QLineEdit) if csv_widget else None
            row_data["csvWandFile"] = line_edit.text() if line_edit else ""
            # Wand File Save Path
            wand_widget = self.table.cellWidget(row, 5)
            line_edit = wand_widget.findChild(QtWidgets.QLineEdit) if wand_widget else None
            row_data["wandFileSavePath"] = line_edit.text() if line_edit else ""
            config_data["scripts"].append(row_data)
        return config_data

    def save_config(self):
        """Speichert die aktuellen Rezept-Konfigurationen über den script_config_manager."""
        config_data = self.get_config_data()
        from config.script_config_manager import save_script_config, debug_print
        save_script_config(config_data)
        debug_print("Script configuration saved.")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = ScriptRecipeListWidget({})
    widget.show()
    sys.exit(app.exec_())