#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui

from config.script_config_manager import (
    load_script_config,
    save_script_config,
    list_photoshop_action_sets,
    debug_print
)

class ScriptRecipeWidget(QtWidgets.QWidget):
    """
    Zeigt eine Tabelle mit den konfigurierten Skript-Rezept-Zuordnungen
    (script_config.json).
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.script_config = load_script_config(self.settings)  # => {"scripts": [...]}
        self.scripts_data = self.script_config.get("scripts", [])
        # Evtl. Action-Sets einlesen:
        self.available_action_sets = list_photoshop_action_sets()

        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Überschrift:
        title_label = QtWidgets.QLabel("Script › Rezept Einstellungen")
        title_font = QtGui.QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Tabelle
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Script", "JSON Folder", "Action Folder", "Basic Wand Files",
            "CSV Wand File", "Wand File SavePath", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        # Spaltenbreite anpassen: (erste 6 Spalten 300px, letzte 150px)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 300)
        self.table.setColumnWidth(4, 300)
        self.table.setColumnWidth(5, 300)
        self.table.setColumnWidth(6, 150)

        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.table, stretch=1)

        # Buttons (Add, Remove, Save)
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Hinzufügen")
        self.remove_btn = QtWidgets.QPushButton("Löschen")
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        # Connect
        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)
        self.save_btn.clicked.connect(self.on_save)

        # Tabelle füllen
        self.load_table()

    def load_table(self):
        self.table.setRowCount(0)
        for entry in self.scripts_data:
            self.add_row(entry)

    def add_row(self, entry):
        """
        entry = {
          "script_path": "...",
          "json_folder": "...",
          "actionFolderName": "...",
          "basicWandFiles": "...",
          "csvWandFile": "...",
          "wandFileSavePath": "..."
        }
        """
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)

        # Script (Combo + Browse)
        script_item = self.create_script_cell(entry.get("script_path", ""))
        self.table.setCellWidget(row_idx, 0, script_item)

        # JSON Folder (Combo + Browse)
        json_item = self.create_path_cell(entry.get("json_folder", ""), "Folder")
        self.table.setCellWidget(row_idx, 1, json_item)

        # Action Folder (Dropdown der Action-Sets)
        action_item = self.create_actionset_cell(entry.get("actionFolderName",""))
        self.table.setCellWidget(row_idx, 2, action_item)

        # Basic Wand Files
        bw_item = self.create_path_cell(entry.get("basicWandFiles",""), "Folder")
        self.table.setCellWidget(row_idx, 3, bw_item)

        # CSV Wand File
        csv_item = self.create_path_cell(entry.get("csvWandFile",""), "File")
        self.table.setCellWidget(row_idx, 4, csv_item)

        # Wand File SavePath
        wfs_item = self.create_path_cell(entry.get("wandFileSavePath",""), "Folder")
        self.table.setCellWidget(row_idx, 5, wfs_item)

        # Actions (Edit + Remove)
        actions_widget = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(actions_widget)
        hl.setContentsMargins(0, 0, 0, 0)

        edit_btn = QtWidgets.QPushButton("Edit")
        remove_btn = QtWidgets.QPushButton("Remove")

        edit_btn.clicked.connect(lambda _, r=row_idx: self.on_edit(r))
        remove_btn.clicked.connect(lambda _, r=row_idx: self.on_remove_specific(r))

        hl.addWidget(edit_btn)
        hl.addWidget(remove_btn)
        self.table.setCellWidget(row_idx, 6, actions_widget)

    def create_script_cell(self, initial_path):
        """
        Erzeugt ein Widget, das ein QComboBox + "..."-Button enthält,
        um eine Script-Datei zu wählen.
        """
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)

        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setMinimumWidth(300)
        combo.addItem(initial_path if initial_path else "Choose script...")

        browse_btn = QtWidgets.QPushButton("...")
        browse_btn.setFixedWidth(100)

        def on_browse():
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Script auswählen", initial_path or "", "JSX Files (*.jsx);;All Files (*)")
            if path:
                combo.clear()
                combo.addItem(path)
                combo.setCurrentIndex(0)

        browse_btn.clicked.connect(on_browse)

        hl.addWidget(combo)
        hl.addWidget(browse_btn)
        return w

    def create_path_cell(self, initial_path, mode="Folder"):
        """
        Erzeugt ein Widget (Combo + "..."), je nach mode Folder oder File.
        """
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)

        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setMinimumWidth(300)
        combo.addItem(initial_path if initial_path else (f"Choose {mode}..."))

        browse_btn = QtWidgets.QPushButton("...")
        browse_btn.setFixedWidth(100)

        def on_browse():
            if mode == "Folder":
                folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", initial_path or "")
                if folder:
                    combo.clear()
                    combo.addItem(folder)
                    combo.setCurrentIndex(0)
            else:
                file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Datei auswählen", initial_path or "")
                if file:
                    combo.clear()
                    combo.addItem(file)
                    combo.setCurrentIndex(0)

        browse_btn.clicked.connect(on_browse)

        hl.addWidget(combo)
        hl.addWidget(browse_btn)
        return w

    def create_actionset_cell(self, initial_value):
        """
        Erzeugt ein ComboBox mit den ActionSets aus Photoshop (falls ermittelt),
        plus ggf. manuelle Eingabe.
        """
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)

        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setMinimumWidth(300)

        # Fülle die ActionSets
        for aset in self.available_action_sets:
            combo.addItem(aset)

        if initial_value and initial_value not in self.available_action_sets:
            combo.insertItem(0, initial_value)
            combo.setCurrentIndex(0)
        else:
            idx = combo.findText(initial_value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        hl.addWidget(combo)
        return w

    def on_add(self):
        """
        Fügt einen neuen Eintrag mit Default-Werten hinzu.
        """
        new_entry = {
            "script_path": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.scripts_data.append(new_entry)
        self.add_row(new_entry)

    def on_remove(self):
        """
        Entfernt den ausgewählten Eintrag.
        """
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        if row < len(self.scripts_data):
            self.scripts_data.pop(row)

    def on_remove_specific(self, row):
        """
        Entfernt eine Zeile, wenn man in der Actions-Spalte auf 'Remove' klickt.
        """
        if row < 0 or row >= self.table.rowCount():
            return
        self.table.removeRow(row)
        if row < len(self.scripts_data):
            self.scripts_data.pop(row)

    def on_edit(self, row):
        """
        Öffnet einen Detail-Dialog, in dem man die Einträge genauer bearbeiten kann,
        ähnlich wie beim Hotfolder-Edit.
        """
        if row < 0 or row >= len(self.scripts_data):
            return
        entry = self.scripts_data[row]
        dlg = RecipeEditDialog(entry, self.available_action_sets, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.scripts_data[row] = dlg.get_data()
            self.table.removeRow(row)
            self.table.insertRow(row)
            self.add_row(self.scripts_data[row])

    def on_save(self):
        """
        Speichert die aktuelle Tabelle in script_config.json.
        """
        data = {"scripts": self.scripts_data}
        save_script_config(data, self.settings)
        QtWidgets.QMessageBox.information(self, "Info", "Script-Rezepte gespeichert.")


class RecipeEditDialog(QtWidgets.QDialog):
    """
    Optionaler Detaildialog, wie bei HotfolderConfigDialog.
    """
    def __init__(self, entry, action_sets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rezept bearbeiten")
        self.entry = dict(entry)  # Kopie
        self.action_sets = action_sets
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QFormLayout(self)

        # Script Path
        self.script_edit = QtWidgets.QComboBox()
        self.script_edit.setEditable(True)
        self.script_edit.setMinimumWidth(300)
        if self.entry.get("script_path"):
            self.script_edit.addItem(self.entry["script_path"])
        browse_script_btn = QtWidgets.QPushButton("Browse")
        browse_script_btn.setFixedWidth(100)
        browse_script_btn.clicked.connect(self.browse_script)
        script_hlay = QtWidgets.QHBoxLayout()
        script_hlay.addWidget(self.script_edit, stretch=1)
        script_hlay.addWidget(browse_script_btn)
        layout.addRow("Script Path:", script_hlay)

        # JSON Folder
        self.json_edit = QtWidgets.QComboBox()
        self.json_edit.setEditable(True)
        self.json_edit.setMinimumWidth(300)
        if self.entry.get("json_folder"):
            self.json_edit.addItem(self.entry["json_folder"])
        browse_json_btn = QtWidgets.QPushButton("Browse")
        browse_json_btn.setFixedWidth(100)
        browse_json_btn.clicked.connect(self.browse_json_folder)
        json_hlay = QtWidgets.QHBoxLayout()
        json_hlay.addWidget(self.json_edit, stretch=1)
        json_hlay.addWidget(browse_json_btn)
        layout.addRow("JSON Folder:", json_hlay)

        # Action Folder Name
        self.action_combo = QtWidgets.QComboBox()
        self.action_combo.setEditable(True)
        self.action_combo.setMinimumWidth(300)
        for aset in self.action_sets:
            self.action_combo.addItem(aset)
        if self.entry.get("actionFolderName"):
            idx = self.action_combo.findText(self.entry["actionFolderName"])
            if idx < 0:
                self.action_combo.insertItem(0, self.entry["actionFolderName"])
                self.action_combo.setCurrentIndex(0)
            else:
                self.action_combo.setCurrentIndex(idx)
        layout.addRow("Action Folder Name:", self.action_combo)

        # Basic Wand Files
        self.basic_edit = QtWidgets.QComboBox()
        self.basic_edit.setEditable(True)
        self.basic_edit.setMinimumWidth(300)
        if self.entry.get("basicWandFiles"):
            self.basic_edit.addItem(self.entry["basicWandFiles"])
        browse_basic_btn = QtWidgets.QPushButton("Browse")
        browse_basic_btn.setFixedWidth(100)
        browse_basic_btn.clicked.connect(lambda: self.browse_path(self.basic_edit, mode="Folder"))
        basic_hlay = QtWidgets.QHBoxLayout()
        basic_hlay.addWidget(self.basic_edit, stretch=1)
        basic_hlay.addWidget(browse_basic_btn)
        layout.addRow("Basic Wand Files:", basic_hlay)

        # CSV Wand File
        self.csv_edit = QtWidgets.QComboBox()
        self.csv_edit.setEditable(True)
        self.csv_edit.setMinimumWidth(300)
        if self.entry.get("csvWandFile"):
            self.csv_edit.addItem(self.entry["csvWandFile"])
        browse_csv_btn = QtWidgets.QPushButton("Browse")
        browse_csv_btn.setFixedWidth(100)
        browse_csv_btn.clicked.connect(lambda: self.browse_path(self.csv_edit, mode="File"))
        csv_hlay = QtWidgets.QHBoxLayout()
        csv_hlay.addWidget(self.csv_edit, stretch=1)
        csv_hlay.addWidget(browse_csv_btn)
        layout.addRow("CSV Wand File:", csv_hlay)

        # Wand File Save Path
        self.wand_save_edit = QtWidgets.QComboBox()
        self.wand_save_edit.setEditable(True)
        self.wand_save_edit.setMinimumWidth(300)
        if self.entry.get("wandFileSavePath"):
            self.wand_save_edit.addItem(self.entry["wandFileSavePath"])
        browse_wand_btn = QtWidgets.QPushButton("Browse")
        browse_wand_btn.setFixedWidth(100)
        browse_wand_btn.clicked.connect(lambda: self.browse_path(self.wand_save_edit, mode="Folder"))
        wand_hlay = QtWidgets.QHBoxLayout()
        wand_hlay.addWidget(self.wand_save_edit, stretch=1)
        wand_hlay.addWidget(browse_wand_btn)
        layout.addRow("Wand File Save Path:", wand_hlay)

        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def browse_script(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Script auswählen", "", "JSX Files (*.jsx);;All Files (*)")
        if path:
            self.script_edit.clear()
            self.script_edit.addItem(path)
            self.script_edit.setCurrentIndex(0)

    def browse_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON-Folder auswählen", "")
        if folder:
            self.json_edit.clear()
            self.json_edit.addItem(folder)
            self.json_edit.setCurrentIndex(0)

    def browse_path(self, combo, mode="Folder"):
        if mode == "Folder":
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", "")
            if folder:
                combo.clear()
                combo.addItem(folder)
                combo.setCurrentIndex(0)
        else:
            file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Datei auswählen", "")
            if file:
                combo.clear()
                combo.addItem(file)
                combo.setCurrentIndex(0)

    def get_data(self):
        return {
            "script_path": self.script_edit.currentText(),
            "json_folder": self.json_edit.currentText(),
            "actionFolderName": self.action_combo.currentText(),
            "basicWandFiles": self.basic_edit.currentText(),
            "csvWandFile": self.csv_edit.currentText(),
            "wandFileSavePath": self.wand_save_edit.currentText()
        }