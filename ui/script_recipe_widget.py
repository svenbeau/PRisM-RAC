#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import save_settings, debug_print

class ScriptRecipeWidget(QtWidgets.QWidget):
    """
    Displays a list of scripts and their associated JSON folder, plus some extra fields:
      - actionFolderName
      - basicWandFiles
      - csvWandFile
      - wandFileSavePath
    Allows Add/Remove scripts, saving to self.settings['scriptsConfig'] or similar.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # We'll store config in e.g. self.settings.setdefault("scriptsConfig", [])
        self.scripts_config = self.settings.setdefault("scriptsConfig", [])

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        title_label = QtWidgets.QLabel("Script › Rezeptzuordnung")
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        main_layout.addWidget(title_label, 0, QtCore.Qt.AlignLeft)

        # Table
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        headers = [
            "Script",
            "JSON Folder",
            "ActionFolderName",
            "Wand CSV",
            "Browse",
            "Remove"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        # Make columns a bit wide
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 80)

        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table.verticalHeader().setVisible(False)

        main_layout.addWidget(self.table, 1)

        # Buttons at bottom
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Neues Script hinzufügen")
        self.add_btn.clicked.connect(self.add_script)
        btn_layout.addWidget(self.add_btn)

        btn_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton("Save Config")
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

        self.load_table()

    def load_table(self):
        self.table.setRowCount(0)
        for row_index, cfg in enumerate(self.scripts_config):
            self.add_table_row(cfg)

    def add_table_row(self, cfg=None):
        """
        Creates a new row in the table.
        cfg is a dict with e.g.:
        {
            "scriptPath": "...",
            "jsonFolder": "...",
            "actionFolderName": "...",
            "csvWandFile": "..."
        }
        """
        if cfg is None:
            cfg = {
                "scriptPath": "",
                "jsonFolder": "",
                "actionFolderName": "",
                "csvWandFile": ""
            }

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Script path item
        script_item = QtWidgets.QTableWidgetItem(cfg.get("scriptPath", ""))
        self.table.setItem(row, 0, script_item)

        # JSON folder item
        json_item = QtWidgets.QTableWidgetItem(cfg.get("jsonFolder", ""))
        self.table.setItem(row, 1, json_item)

        # actionFolderName
        action_item = QtWidgets.QTableWidgetItem(cfg.get("actionFolderName", ""))
        self.table.setItem(row, 2, action_item)

        # csvWandFile
        csv_item = QtWidgets.QTableWidgetItem(cfg.get("csvWandFile", ""))
        self.table.setItem(row, 3, csv_item)

        # Browse button
        browse_btn = QtWidgets.QPushButton("...")
        browse_btn.clicked.connect(lambda checked, r=row: self.on_browse(r))
        self.table.setCellWidget(row, 4, browse_btn)

        # Remove button
        remove_btn = QtWidgets.QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
        self.table.setCellWidget(row, 5, remove_btn)

    def add_script(self):
        # Just add an empty row
        self.add_table_row()

    def remove_row(self, row):
        # Remove from data
        if row < len(self.scripts_config):
            self.scripts_config.pop(row)
        # Remove from table
        self.table.removeRow(row)

    def on_browse(self, row):
        # Example: let user pick a script or JSON folder or both, etc.
        # For demonstration, let's say we pick a script file:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Script", "", "JSX Files (*.jsx);;All Files (*)")
        if path:
            item = self.table.item(row, 0)
            if item:
                item.setText(path)

    def on_save(self):
        # Rebuild self.scripts_config from table
        new_config = []
        for row in range(self.table.rowCount()):
            scriptPath = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            jsonFolder = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            actionFolderName = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            csvWandFile = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            new_config.append({
                "scriptPath": scriptPath,
                "jsonFolder": jsonFolder,
                "actionFolderName": actionFolderName,
                "csvWandFile": csvWandFile
            })
        self.scripts_config = new_config
        self.settings["scriptsConfig"] = self.scripts_config
        save_settings(self.settings)
        QtWidgets.QMessageBox.information(self, "Saved", "Script-Recipe config saved.")