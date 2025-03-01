#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import save_settings, debug_print


class ScriptRecipeWidget(QtWidgets.QWidget):
    """
    Widget zur Konfiguration der "Script › Rezept Zuordnung". Jede Zeile entspricht
    einer Konfiguration für ein Script, das folgende Felder enthält:
      - Script: kombiniertes Widget (QComboBox + Browse-Button), das den Dateinamen anzeigt; der volle Pfad ist als Tooltip hinterlegt.
      - JSON Folder: kombiniertes Widget (Dropdown + Browse-Button).
      - Action Folder Name: QLineEdit.
      - Basic Wand Files: kombiniertes Widget (Dropdown + Browse-Button).
      - CSV Wand File: kombiniertes Widget (Dropdown + Browse-Button).
      - Wand File Save Path: kombiniertes Widget (Dropdown + Browse-Button).

    Zusätzlich gibt es "Add", "Remove" und "Save" Buttons, mit denen die Konfigurationen (in settings["script_configs"]) bearbeitet werden können.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.script_configs = self.settings.get("script_configs", [])
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Script", "JSON Folder", "Action Folder", "Basic Wand Files", "CSV Wand File", "Wand File Save Path"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        # Setze initiale Spaltenbreiten
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 300)
        self.table.setColumnWidth(4, 300)
        self.table.setColumnWidth(5, 300)
        layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add")
        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.save_btn = QtWidgets.QPushButton("Save")
        self.add_btn.setFixedWidth(100)
        self.remove_btn.setFixedWidth(100)
        self.save_btn.setFixedWidth(100)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_row)
        self.remove_btn.clicked.connect(self.remove_selected_row)
        self.save_btn.clicked.connect(self.save_config)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for config in self.script_configs:
            self.add_row_from_config(config)

    def add_row_from_config(self, config):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Spalte 0: Script
        script_widget = self.create_combo_with_browse(
            config.get("script_path", ""), file_mode=QtWidgets.QFileDialog.ExistingFile, file_filter="JSX Files (*.jsx)"
        )
        self.table.setCellWidget(row, 0, script_widget)

        # Spalte 1: JSON Folder
        json_widget = self.create_combo_with_browse(
            config.get("json_folder", ""), file_mode=QtWidgets.QFileDialog.Directory
        )
        self.table.setCellWidget(row, 1, json_widget)

        # Spalte 2: Action Folder Name (QLineEdit)
        action_edit = QtWidgets.QLineEdit(config.get("actionFolderName", ""))
        self.table.setCellWidget(row, 2, action_edit)

        # Spalte 3: Basic Wand Files
        basic_widget = self.create_combo_with_browse(
            config.get("basicWandFiles", ""), file_mode=QtWidgets.QFileDialog.Directory
        )
        self.table.setCellWidget(row, 3, basic_widget)

        # Spalte 4: CSV Wand File
        csv_widget = self.create_combo_with_browse(
            config.get("csvWandFile", ""), file_mode=QtWidgets.QFileDialog.ExistingFile, file_filter="CSV Files (*.csv)"
        )
        self.table.setCellWidget(row, 4, csv_widget)

        # Spalte 5: Wand File Save Path
        wand_widget = self.create_combo_with_browse(
            config.get("wandFileSavePath", ""), file_mode=QtWidgets.QFileDialog.Directory
        )
        self.table.setCellWidget(row, 5, wand_widget)

    def create_combo_with_browse(self, initial_path, file_mode, file_filter="All Files (*)"):
        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(5)
        combo = QtWidgets.QComboBox()
        combo.setEditable(False)
        combo.setMinimumWidth(200)
        if initial_path:
            combo.addItem(os.path.basename(initial_path))
            combo.setToolTip(initial_path)
        else:
            combo.addItem("Choose your value...")
            combo.setToolTip("")
        btn = QtWidgets.QPushButton("Browse")
        btn.setFixedWidth(100)
        btn.clicked.connect(lambda: self.browse_for_path(combo, file_mode, file_filter))
        h_layout.addWidget(combo)
        h_layout.addWidget(btn)
        return container

    def browse_for_path(self, combo, file_mode, file_filter):
        current_path = combo.toolTip() if combo.toolTip() else os.path.expanduser("~")
        if file_mode == QtWidgets.QFileDialog.ExistingFile:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", current_path, file_filter)
        elif file_mode == QtWidgets.QFileDialog.Directory:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", current_path)
        else:
            path = ""
        if path:
            combo.clear()
            combo.addItem(os.path.basename(path))
            combo.setToolTip(path)

    def add_row(self):
        new_config = {
            "script_path": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.script_configs.append(new_config)
        self.add_row_from_config(new_config)

    def remove_selected_row(self):
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)
            if row < len(self.script_configs):
                del self.script_configs[row]

    def save_config(self):
        configs = []
        for row in range(self.table.rowCount()):
            script_widget = self.table.cellWidget(row, 0)
            json_widget = self.table.cellWidget(row, 1)
            action_widget = self.table.cellWidget(row, 2)  # QLineEdit direkt
            basic_widget = self.table.cellWidget(row, 3)
            csv_widget = self.table.cellWidget(row, 4)
            wand_widget = self.table.cellWidget(row, 5)

            script_path = script_widget.findChild(QtWidgets.QComboBox).toolTip()
            json_folder = json_widget.findChild(QtWidgets.QComboBox).toolTip()
            action_folder = action_widget.text()  # direkt
            basic_folder = basic_widget.findChild(QtWidgets.QComboBox).toolTip()
            csv_file = csv_widget.findChild(QtWidgets.QComboBox).toolTip()
            wand_folder = wand_widget.findChild(QtWidgets.QComboBox).toolTip()

            config = {
                "script_path": script_path,
                "json_folder": json_folder,
                "actionFolderName": action_folder,
                "basicWandFiles": basic_folder,
                "csvWandFile": csv_file,
                "wandFileSavePath": wand_folder
            }
            configs.append(config)
        self.settings["script_configs"] = configs
        save_settings(self.settings)
        debug_print("Script configuration saved.")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    test_settings = {"script_configs": []}
    widget = ScriptRecipeWidget(test_settings)
    widget.show()
    sys.exit(app.exec_())