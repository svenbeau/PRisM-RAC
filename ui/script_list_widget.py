#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import load_settings, save_settings, debug_print

class ScriptListWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Skript-Konfigurationen.
    Jede Zeile repräsentiert ein Skript mit den zugehörigen Einstellungen:
      - Das ausgewählte Skript (Dateiname; Tooltip zeigt den vollständigen Pfad)
      - Der JSON-Ordner (als verkürzte Darstellung mit Tooltip)
      - Action Folder Name, Basic Wand Files, CSV Wand File, Wand File Save Path
      - Buttons zum Bearbeiten und Löschen der Konfiguration
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        if "scripts" not in self.settings:
            self.settings["scripts"] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        # Button-Leiste
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Script hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Script entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        # Tabelle für die Skript-Konfigurationen
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Script", "JSON Ordner", "Action Folder", "Basic Wand Files", "CSV Wand File", "Wand File Save Path", "Bearbeiten", "Löschen"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        # Setze Spaltenbreiten: Buttons 150px, Script und JSON Spalten 300px, weitere Buttons 100px
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 150)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 100)
        main_layout.addWidget(self.table)
        self.add_btn.clicked.connect(self.add_script)
        self.del_btn.clicked.connect(self.delete_selected_script)
        self.load_scripts()

    def load_scripts(self):
        self.table.setRowCount(0)
        scripts = self.settings.get("scripts", [])
        for script in scripts:
            self.add_script_row(script)

    def add_script_row(self, script):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Spalte 0: Script (ausgewähltes JSX)
        script_name = os.path.basename(script.get("selected_jsx", ""))
        item_script = QtWidgets.QTableWidgetItem(script_name)
        item_script.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 0, item_script)
        # Spalte 1: JSON Ordner (verkürzt, Tooltip mit vollem Pfad)
        json_folder = script.get("json_folder", "")
        item_json = QtWidgets.QTableWidgetItem(self.get_short_path(json_folder))
        item_json.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_json.setToolTip(json_folder)
        self.table.setItem(row, 1, item_json)
        # Spalte 2: Action Folder Name
        action_folder = script.get("actionFolderName", "")
        item_action = QtWidgets.QTableWidgetItem(action_folder)
        item_action.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 2, item_action)
        # Spalte 3: Basic Wand Files
        basic_wand = script.get("basicWandFiles", "")
        item_basic = QtWidgets.QTableWidgetItem(self.get_short_path(basic_wand))
        item_basic.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_basic.setToolTip(basic_wand)
        self.table.setItem(row, 3, item_basic)
        # Spalte 4: CSV Wand File
        csv_wand = script.get("csvWandFile", "")
        item_csv = QtWidgets.QTableWidgetItem(self.get_short_path(csv_wand))
        item_csv.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_csv.setToolTip(csv_wand)
        self.table.setItem(row, 4, item_csv)
        # Spalte 5: Wand File Save Path
        wand_save = script.get("wandFileSavePath", "")
        item_wand = QtWidgets.QTableWidgetItem(self.get_short_path(wand_save))
        item_wand.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_wand.setToolTip(wand_save)
        self.table.setItem(row, 5, item_wand)
        # Spalte 6: Edit Button
        btn_edit = QtWidgets.QPushButton("Bearbeiten")
        btn_edit.setFixedWidth(100)
        btn_edit.clicked.connect(lambda _, r=row: self.edit_script(r))
        self.table.setCellWidget(row, 6, btn_edit)
        # Spalte 7: Delete Button
        btn_delete = QtWidgets.QPushButton("Löschen")
        btn_delete.setFixedWidth(100)
        btn_delete.clicked.connect(lambda _, r=row: self.delete_script(r))
        self.table.setCellWidget(row, 7, btn_delete)

    def get_short_path(self, full_path):
        if not full_path:
            return ""
        parts = full_path.split(os.sep)
        # Zeige standardmäßig die letzten zwei Komponenten
        if len(parts) > 2:
            return os.sep.join(parts[-2:])
        return full_path

    def add_script(self):
        new_script = {
            "id": str(uuid.uuid4()),
            "selected_jsx": "",
            "scripts_folder": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.settings.setdefault("scripts", []).append(new_script)
        save_settings(self.settings)
        self.load_scripts()
        self.edit_script(self.table.rowCount() - 1)

    def delete_script(self, row):
        scripts = self.settings.get("scripts", [])
        if 0 <= row < len(scripts):
            del scripts[row]
            save_settings(self.settings)
            self.load_scripts()

    def delete_selected_script(self):
        selected = self.table.currentRow()
        if selected >= 0:
            self.delete_script(selected)

    def edit_script(self, row):
        scripts = self.settings.get("scripts", [])
        if 0 <= row < len(scripts):
            script_config = scripts[row]
            from script_config_dialog import ScriptConfigDialog
            dlg = ScriptConfigDialog(script_config, parent=self)
            if dlg.exec_():
                save_settings(self.settings)
                self.load_scripts()

class ScriptSettingsWidget(QtWidgets.QWidget):
    """
    Kombiniertes Widget für die Skript-Konfiguration.
    Enthält eine Kategorieüberschrift ("Script › Rezeptzuordnung") und das ScriptListWidget.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        cat_label = QtWidgets.QLabel("Script › Rezeptzuordnung")
        cat_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        layout.addWidget(cat_label)
        self.script_list = ScriptListWidget(self.settings, parent=self)
        layout.addWidget(self.script_list)
        layout.addStretch()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    settings = load_settings()
    widget = ScriptSettingsWidget(settings)
    widget.show()
    sys.exit(app.exec_())