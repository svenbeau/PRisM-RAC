#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScriptRecipeWidget – ermöglicht die Konfiguration der Script › Rezept Zuordnungen.
Hier kannst Du für jedes Script individuell den Script-Pfad, den zugehörigen JSON-Ordner,
Basic-Wand-Files, CSV-Wand-File, Wand-File-Save-Path sowie den Action Folder Name konfigurieren.
Die Benutzeroberfläche ähnelt der Hotfolder-Konfiguration (Dropdowns, Browse-Buttons etc.).
"""

from PyQt5 import QtWidgets, QtCore
import os
from config.script_config_manager import load_script_config, save_script_config, debug_print


class ScriptRecipeWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Lade die Skript-Konfiguration – diese wird in script_config.json gespeichert
        self.script_config = load_script_config(self.settings)
        if not self.script_config:
            self.script_config = {"scripts": []}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Titel
        title = QtWidgets.QLabel("Script › Rezept Zuordnung")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Tabelle für die Konfiguration
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Script", "JSON Folder", "Basic Wand Files", "CSV Wand File", "Wand File Save Path", "Action Folder Name"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # Setze Standardbreiten
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 300)
        self.table.setColumnWidth(4, 300)
        self.table.setColumnWidth(5, 300)
        layout.addWidget(self.table)

        # Button-Leiste zum Hinzufügen/Löschen
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add")
        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.edit_btn = QtWidgets.QPushButton("Edit Selected")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.edit_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_row_dialog)
        self.remove_btn.clicked.connect(self.remove_selected_row)
        self.edit_btn.clicked.connect(self.edit_selected_row)

        self.load_table()

    def load_table(self):
        self.table.setRowCount(0)
        for entry in self.script_config.get("scripts", []):
            self.add_row(entry)

    def add_row(self, entry):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Erstelle für jede Spalte ein „Path-Widget“ (Dropdown + Browse-Button)
        script_widget = self.create_path_widget(entry.get("script_path", ""), file_mode=True, file_filter="*.jsx")
        self.table.setCellWidget(row, 0, script_widget)

        json_widget = self.create_path_widget(entry.get("json_folder", ""), file_mode=False)
        self.table.setCellWidget(row, 1, json_widget)

        basic_widget = self.create_path_widget(entry.get("basicWandFiles", ""), file_mode=False)
        self.table.setCellWidget(row, 2, basic_widget)

        csv_widget = self.create_path_widget(entry.get("csvWandFile", ""), file_mode=True, file_filter="*.csv")
        self.table.setCellWidget(row, 3, csv_widget)

        wand_widget = self.create_path_widget(entry.get("wandFileSavePath", ""), file_mode=False)
        self.table.setCellWidget(row, 4, wand_widget)

        action_line = QtWidgets.QLineEdit(entry.get("actionFolderName", ""))
        self.table.setCellWidget(row, 5, action_line)

    def create_path_widget(self, path, file_mode=False, file_filter="*"):
        """
        Erstellt ein Widget, das einen Dropdown (mit dem Basisnamen) und einen Browse‑Button enthält.
        Der vollständige Pfad wird als Tooltip bzw. in einem versteckten QLabel gespeichert.
        """
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        combo = QtWidgets.QComboBox()
        combo.setEditable(False)
        base = os.path.basename(path) if path else "Not set"
        combo.addItem(base)
        layout.addWidget(combo)
        btn = QtWidgets.QPushButton("Browse")
        btn.setFixedWidth(100)
        layout.addWidget(btn)
        # Verwende ein QLabel, um den vollen Pfad zu speichern (nicht sichtbar)
        label = QtWidgets.QLabel(path)
        label.setVisible(False)
        widget.label = label  # Als Eigenschaft speichern
        layout.addWidget(label)
        if file_mode:
            btn.clicked.connect(lambda: self.browse_file(combo, label, file_filter))
        else:
            btn.clicked.connect(lambda: self.browse_folder(combo, label))
        return widget

    def browse_file(self, combo, label, file_filter):
        options = QtWidgets.QFileDialog.Options()
        file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", file_filter, options=options)
        if file:
            combo.clear()
            combo.addItem(os.path.basename(file))
            label.setText(file)

    def browse_folder(self, combo, label):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            combo.clear()
            combo.addItem(os.path.basename(folder))
            label.setText(folder)

    def add_row_dialog(self):
        new_entry = {
            "script_path": "",
            "json_folder": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": "",
            "actionFolderName": ""
        }
        self.script_config.setdefault("scripts", []).append(new_entry)
        self.add_row(new_entry)

    def remove_selected_row(self):
        selected = self.table.selectedIndexes()
        if selected:
            row = selected[0].row()
            self.table.removeRow(row)
            if "scripts" in self.script_config and row < len(self.script_config["scripts"]):
                self.script_config["scripts"].pop(row)

    def edit_selected_row(self):
        # Optional: Hier könnte ein Dialog zur detaillierten Bearbeitung einer Zeile geöffnet werden.
        # Zurzeit speichern wir direkt die aktuell in den Widgets enthaltenen Werte.
        self.save_config()

    def save_config(self):
        scripts = []
        for row in range(self.table.rowCount()):
            script_widget = self.table.cellWidget(row, 0)
            json_widget = self.table.cellWidget(row, 1)
            basic_widget = self.table.cellWidget(row, 2)
            csv_widget = self.table.cellWidget(row, 3)
            wand_widget = self.table.cellWidget(row, 4)
            action_widget = self.table.cellWidget(row, 5)

            script_path = script_widget.label.text() if hasattr(script_widget, "label") else ""
            json_folder = json_widget.label.text() if hasattr(json_widget, "label") else ""
            basic_wand = basic_widget.label.text() if hasattr(basic_widget, "label") else ""
            csv_file = csv_widget.label.text() if hasattr(csv_widget, "label") else ""
            wand_save = wand_widget.label.text() if hasattr(wand_widget, "label") else ""
            action_folder = action_widget.text() if isinstance(action_widget, QtWidgets.QLineEdit) else ""

            entry = {
                "script_path": script_path,
                "json_folder": json_folder,
                "basicWandFiles": basic_wand,
                "csvWandFile": csv_file,
                "wandFileSavePath": wand_save,
                "actionFolderName": action_folder
            }
            scripts.append(entry)
        self.script_config["scripts"] = scripts
        save_script_config(self.script_config)
        debug_print("Script configuration saved.")

# Ende ScriptRecipeWidget