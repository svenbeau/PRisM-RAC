#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print
# Hier importieren wir NICHT load_settings, save_settings,
# sondern die Skript-spezifischen Funktionen:
from utils.script_config_manager import load_script_config, save_script_config

class ScriptListWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Skript-Konfigurationen.
    Statt "self.settings['scripts']" verwenden wir nun "self.script_data['scripts']",
    das aus script_config.json geladen wird.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Lädt die Skriptkonfiguration aus script_config.json
        # Falls du "settings" noch für andere Zwecke brauchst, kannst du es hier optional reinreichen.
        self.script_data = load_script_config({})  # {} = leeres dict als 'settings'
        # Wir erwarten "scripts" als Liste
        if "scripts" not in self.script_data:
            self.script_data["scripts"] = []

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Button-Leiste
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Script hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Script entfernen")
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

        # Tabelle
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Script", "JSON Ordner", "Action Folder",
            "Basic Wand Files", "CSV Wand File",
            "Wand File Save Path", "Bearbeiten", "Löschen"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 150)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 100)

        main_layout.addWidget(self.table)

        # Signalverbindungen
        self.add_btn.clicked.connect(self.add_script)
        self.del_btn.clicked.connect(self.delete_selected_script)
        self.save_btn.clicked.connect(self.update_scripts_from_table)

        self.load_scripts()

    def load_scripts(self):
        """
        Lädt die Liste aus self.script_data["scripts"] und befüllt die Tabelle.
        """
        self.table.setRowCount(0)
        scripts = self.script_data.get("scripts", [])
        for script in scripts:
            self.add_script_row(script)

    def add_script_row(self, script):
        """
        Fügt eine Zeile in die Tabelle ein, basierend auf dem Dictionary 'script'.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Spalte 0: Script (script_path)
        script_name = os.path.basename(script.get("script_path", ""))
        item_script = QtWidgets.QTableWidgetItem(script_name)
        item_script.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 0, item_script)

        # Spalte 1: JSON Folder
        json_folder = script.get("json_folder", "")
        item_json = QtWidgets.QTableWidgetItem(self.get_short_path(json_folder))
        item_json.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_json.setToolTip(json_folder)
        self.table.setItem(row, 1, item_json)

        # Spalte 2: Action Folder
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
        if len(parts) > 2:
            return os.sep.join(parts[-2:])
        return full_path

    def add_script(self):
        """
        Erzeugt ein neues Script-Dict und öffnet den Bearbeiten-Dialog.
        """
        new_script = {
            "id": str(uuid.uuid4()),
            "script_path": "",
            "scripts_folder": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        }
        self.script_data.setdefault("scripts", []).append(new_script)
        save_script_config(self.script_data)  # <-- Speichert in script_config.json
        self.load_scripts()
        self.edit_script(self.table.rowCount() - 1)

    def delete_script(self, row):
        scripts = self.script_data.setdefault("scripts", [])
        if 0 <= row < len(scripts):
            del scripts[row]
            save_script_config(self.script_data)  # <-- Speichert in script_config.json
            self.load_scripts()

    def delete_selected_script(self):
        selected = self.table.currentRow()
        if selected >= 0:
            self.delete_script(selected)

    def edit_script(self, row):
        scripts = self.script_data.setdefault("scripts", [])
        if 0 <= row < len(scripts):
            script_config = scripts[row]
            from script_config_widget import ScriptConfigWidget
            dlg = ScriptConfigWidget(script_config, parent=self)
            if dlg.exec_():
                # Benutzer hat OK gedrückt -> script_config wurde aktualisiert
                save_script_config(self.script_data)  # <-- in script_config.json
                self.load_scripts()

    def update_scripts_from_table(self):
        """
        Liest die Spalten 0..5 aus dem Tabellen-Widget und schreibt sie in self.script_data["scripts"].
        Dann ruft save_script_config(self.script_data) auf.
        """
        scripts = self.script_data.setdefault("scripts", [])
        row_count = self.table.rowCount()
        for row in range(row_count):
            if row < len(scripts):
                script = scripts[row]
                # Spalte 0: Script (script_path)
                item_script = self.table.item(row, 0)
                if item_script:
                    script["script_path"] = item_script.text().strip()

                # Spalte 1: JSON Folder
                item_json = self.table.item(row, 1)
                if item_json:
                    script["json_folder"] = item_json.text().strip()

                # Spalte 2: Action Folder
                item_action = self.table.item(row, 2)
                if item_action:
                    script["actionFolderName"] = item_action.text().strip()

                # Spalte 3: Basic Wand Files
                item_basic = self.table.item(row, 3)
                if item_basic:
                    script["basicWandFiles"] = item_basic.text().strip()

                # Spalte 4: CSV Wand File
                item_csv = self.table.item(row, 4)
                if item_csv:
                    script["csvWandFile"] = item_csv.text().strip()

                # Spalte 5: Wand File Save Path
                item_wand = self.table.item(row, 5)
                if item_wand:
                    script["wandFileSavePath"] = item_wand.text().strip()

        save_script_config(self.script_data)  # <-- Schreibt in script_config.json
        debug_print("Scripts updated from table and saved to script_config.json.")
        QtWidgets.QMessageBox.information(self, "Script-Rezepte gespeichert.", "Script-Rezepte gespeichert.")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Falls du "settings" noch brauchst, kannst du es optional laden, aber
    # wir verwenden jetzt script_config_manager für Skript-Daten
    widget = ScriptListWidget(parent=None)
    widget.show()
    sys.exit(app.exec_())