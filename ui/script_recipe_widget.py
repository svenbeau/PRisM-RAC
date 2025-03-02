#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.script_config_manager import (
    load_script_config,
    save_script_config,
    debug_print
)

class ScriptRecipeWidget(QtWidgets.QWidget):
    """
    Stellt eine Tabelle dar, in der man pro Script:
      - Script Path
      - JSON Folder
      - Action Folder
      - BasicWandFiles
      - CSVWandFile
      - WandFileSavePath
    konfigurieren kann.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # script_config.json laden:
        self.script_config = load_script_config(self.settings)  # dict mit Schlüssel "scripts": [...]
        # Standard: self.script_config["scripts"] = Liste von Rezept-Objekten
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Tabelle
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        headers = [
            "Script Path",
            "JSON Folder",
            "Action Folder",
            "Basic Wand Files",
            "CSV Wand File",
            "Wand File Save Path"
        ]
        self.table.setHorizontalHeaderLabels(headers)

        # Resizing + Scrollbars
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table, stretch=1)

        # Buttons Add/Remove
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add")
        self.btn_remove = QtWidgets.QPushButton("Remove")
        self.btn_save = QtWidgets.QPushButton("Script-Rezepte speichern")

        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove.clicked.connect(self.remove_row)
        self.btn_save.clicked.connect(self.save_config)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Tabelle füllen
        self.load_table()

    def load_table(self):
        scripts_list = self.script_config.get("scripts", [])
        self.table.setRowCount(len(scripts_list))

        for row, recipe in enumerate(scripts_list):
            # Script Path
            item_script = QtWidgets.QTableWidgetItem(recipe.get("script_path", ""))
            self.table.setItem(row, 0, item_script)

            # JSON Folder
            item_json = QtWidgets.QTableWidgetItem(recipe.get("json_folder", ""))
            self.table.setItem(row, 1, item_json)

            # Action Folder
            item_action = QtWidgets.QTableWidgetItem(recipe.get("actionFolderName", ""))
            self.table.setItem(row, 2, item_action)

            # Basic Wand Files
            item_basic = QtWidgets.QTableWidgetItem(recipe.get("basicWandFiles", ""))
            self.table.setItem(row, 3, item_basic)

            # CSV Wand File
            item_csv = QtWidgets.QTableWidgetItem(recipe.get("csvWandFile", ""))
            self.table.setItem(row, 4, item_csv)

            # Wand File Save Path
            item_wand = QtWidgets.QTableWidgetItem(recipe.get("wandFileSavePath", ""))
            self.table.setItem(row, 5, item_wand)

    def add_row(self):
        rowcount = self.table.rowCount()
        self.table.insertRow(rowcount)
        # Default-Einträge
        self.table.setItem(rowcount, 0, QtWidgets.QTableWidgetItem("Choose your script..."))
        self.table.setItem(rowcount, 1, QtWidgets.QTableWidgetItem("Set your JSON folder..."))
        self.table.setItem(rowcount, 2, QtWidgets.QTableWidgetItem("Grisebach 2025"))
        self.table.setItem(rowcount, 3, QtWidgets.QTableWidgetItem(""))
        self.table.setItem(rowcount, 4, QtWidgets.QTableWidgetItem(""))
        self.table.setItem(rowcount, 5, QtWidgets.QTableWidgetItem(""))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_config(self):
        """
        Liest die Tabelle aus und speichert sie in script_config.json
        """
        rowcount = self.table.rowCount()
        new_list = []
        for row in range(rowcount):
            script_path = self.get_item_text(row, 0)
            json_folder = self.get_item_text(row, 1)
            action_folder = self.get_item_text(row, 2)
            basic_wand = self.get_item_text(row, 3)
            csv_wand = self.get_item_text(row, 4)
            wand_save = self.get_item_text(row, 5)

            entry = {
                "script_path": script_path,
                "json_folder": json_folder,
                "actionFolderName": action_folder,
                "basicWandFiles": basic_wand,
                "csvWandFile": csv_wand,
                "wandFileSavePath": wand_save
            }
            new_list.append(entry)

        self.script_config["scripts"] = new_list
        save_script_config(self.script_config, self.settings)  # Speichert in config/script_config.json
        QtWidgets.QMessageBox.information(self, "Info", "Script-Konfiguration gespeichert.")

    def get_item_text(self, row, col):
        item = self.table.item(row, col)
        if item is None:
            return ""
        return item.text().strip()