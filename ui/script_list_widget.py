#!/usr/bin/env python3
# -*- coding: utf-8 -*-

DEBUG_OUTPUT = True

import os
import uuid
from PySide6 import QtWidgets, QtCore
from utils.script_config_manager import load_script_config, save_script_config
from utils.config_manager import debug_print

class ScriptListWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Skript-Konfigurationen.
    Jede Zeile repräsentiert ein Skript mit den zugehörigen Einstellungen:
      - Script (Dateiname), JSON Ordner, Action Folder,
        Basic Wand Files, CSV Wand File, Wand File Save Path
      - Buttons zum Bearbeiten und Löschen
    Änderungen in der Tabelle werden erst mit "Einstellungen speichern" dauerhaft übernommen.
    Die Daten werden in script_config.json abgelegt.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Laden der Skriptkonfiguration aus script_config.json
        self.script_data = load_script_config({})
        if "scripts" not in self.script_data:
            self.script_data["scripts"] = []
        debug_print(f"[INIT] Initial script_data loaded: {self.script_data}")
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Obere Button-Leiste
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
        """Lädt die Skriptliste aus self.script_data["scripts"] und befüllt die Tabelle."""
        self.table.setRowCount(0)
        scripts = self.script_data.get("scripts", [])
        debug_print(f"[LOAD] Loading {len(scripts)} scripts into table.")
        for script in scripts:
            self.add_script_row(script)

    def add_script_row(self, script):
        """Fügt eine Zeile in die Tabelle ein, basierend auf dem Dictionary 'script'."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Spalte 0: Script (verwende "script_path")
        script_name = os.path.basename(script.get("script_path", ""))
        item_script = QtWidgets.QTableWidgetItem(script_name)
        item_script.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # Setze die Zelle als editierbar
        item_script.setFlags(item_script.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 0, item_script)

        # Spalte 1: JSON Ordner
        json_folder = script.get("json_folder", "")
        # Hier zeigen wir den verkürzten Pfad, aber speichern später den tatsächlichen Inhalt,
        # falls der Benutzer die Zelle ändert, wird der neue Text übernommen.
        item_json = QtWidgets.QTableWidgetItem(self.get_short_path(json_folder))
        item_json.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # Setze den vollen Pfad als Tooltip
        item_json.setToolTip(json_folder)
        item_json.setFlags(item_json.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 1, item_json)

        # Spalte 2: Action Folder
        action_folder = script.get("actionFolderName", "")
        item_action = QtWidgets.QTableWidgetItem(action_folder)
        item_action.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_action.setFlags(item_action.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 2, item_action)

        # Spalte 3: Basic Wand Files
        basic_wand = script.get("basicWandFiles", "")
        item_basic = QtWidgets.QTableWidgetItem(self.get_short_path(basic_wand))
        item_basic.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_basic.setToolTip(basic_wand)
        item_basic.setFlags(item_basic.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 3, item_basic)

        # Spalte 4: CSV Wand File
        csv_wand = script.get("csvWandFile", "")
        item_csv = QtWidgets.QTableWidgetItem(self.get_short_path(csv_wand))
        item_csv.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_csv.setToolTip(csv_wand)
        item_csv.setFlags(item_csv.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 4, item_csv)

        # Spalte 5: Wand File Save Path
        wand_save = script.get("wandFileSavePath", "")
        item_wand = QtWidgets.QTableWidgetItem(self.get_short_path(wand_save))
        item_wand.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        item_wand.setToolTip(wand_save)
        item_wand.setFlags(item_wand.flags() | QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 5, item_wand)

        # Spalte 6: Bearbeiten-Button
        btn_edit = QtWidgets.QPushButton("Bearbeiten")
        btn_edit.setFixedWidth(100)
        btn_edit.clicked.connect(lambda _, r=row: self.edit_script(r))
        self.table.setCellWidget(row, 6, btn_edit)

        # Spalte 7: Löschen-Button
        btn_delete = QtWidgets.QPushButton("Löschen")
        btn_delete.setFixedWidth(100)
        btn_delete.clicked.connect(lambda _, r=row: self.delete_script(r))
        self.table.setCellWidget(row, 7, btn_delete)

    def get_short_path(self, full_path):
        """Gibt die letzten zwei Komponenten des Pfades zurück."""
        if not full_path:
            return ""
        parts = full_path.split(os.sep)
        if len(parts) > 2:
            return os.sep.join(parts[-2:])
        return full_path

    def add_script(self):
        """Erzeugt ein neues Script-Dict, speichert es und öffnet den Bearbeiten-Dialog."""
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
        save_script_config(self.script_data)
        debug_print(f"[ADD] New script added: {new_script}")
        self.load_scripts()
        self.edit_script(self.table.rowCount() - 1)

    def delete_script(self, row):
        """Entfernt den Eintrag in Zeile 'row' aus der Skriptliste."""
        scripts = self.script_data.setdefault("scripts", [])
        if 0 <= row < len(scripts):
            debug_print(f"[DEL] Deleting script at row {row}: {scripts[row]}")
            del scripts[row]
            save_script_config(self.script_data)
            self.load_scripts()

    def delete_selected_script(self):
        """Löscht das aktuell ausgewählte Script."""
        selected = self.table.currentRow()
        if selected >= 0:
            self.delete_script(selected)

    def edit_script(self, row):
        """Öffnet den Bearbeitungsdialog (ScriptConfigWidget) für den Eintrag in Zeile 'row'."""
        scripts = self.script_data.setdefault("scripts", [])
        if 0 <= row < len(scripts):
            script_config = scripts[row]
            debug_print(f"[EDIT] Before editing, row {row}: {script_config}")
            from script_config_widget import ScriptConfigWidget
            dlg = ScriptConfigWidget(script_config, parent=self)
            if dlg.exec_():
                debug_print(f"[EDIT] After editing, row {row}: {script_config}")
                save_script_config(self.script_data)
                self.load_scripts()
            else:
                debug_print(f"[EDIT] Editing cancelled for row {row}")

    def update_scripts_from_table(self):
        """
        Liest die Inhalte der Spalten 0 bis 5 aus der Tabelle aus und überträgt sie
        in self.script_data["scripts"]. Anschließend wird gespeichert.
        """
        scripts = self.script_data.setdefault("scripts", [])
        row_count = self.table.rowCount()
        debug_print(f"[UPDATE] Updating scripts from table, total rows: {row_count}")
        for row in range(row_count):
            if row < len(scripts):
                script = scripts[row]
                # Spalte 0: Script (script_path)
                item_script = self.table.item(row, 0)
                if item_script:
                    value = item_script.text().strip()
                    script["script_path"] = value
                    debug_print(f"[UPDATE] Row {row} - script_path: {value}")
                # Spalte 1: JSON Folder (verwende Zelleninhalt)
                item_json = self.table.item(row, 1)
                if item_json:
                    value = item_json.text().strip()
                    script["json_folder"] = value
                    debug_print(f"[UPDATE] Row {row} - json_folder: {value}")
                # Spalte 2: Action Folder
                item_action = self.table.item(row, 2)
                if item_action:
                    value = item_action.text().strip()
                    script["actionFolderName"] = value
                    debug_print(f"[UPDATE] Row {row} - actionFolderName: {value}")
                # Spalte 3: Basic Wand Files
                item_basic = self.table.item(row, 3)
                if item_basic:
                    value = item_basic.text().strip()
                    script["basicWandFiles"] = value
                    debug_print(f"[UPDATE] Row {row} - basicWandFiles: {value}")
                # Spalte 4: CSV Wand File
                item_csv = self.table.item(row, 4)
                if item_csv:
                    value = item_csv.text().strip()
                    script["csvWandFile"] = value
                    debug_print(f"[UPDATE] Row {row} - csvWandFile: {value}")
                # Spalte 5: Wand File Save Path
                item_wand = self.table.item(row, 5)
                if item_wand:
                    value = item_wand.text().strip()
                    script["wandFileSavePath"] = value
                    debug_print(f"[UPDATE] Row {row} - wandFileSavePath: {value}")
        save_script_config(self.script_data)
        debug_print(f"[UPDATE] Final script_data: {self.script_data}")
        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")

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
        self.script_list = ScriptListWidget(parent=self)
        layout.addWidget(self.script_list)
        layout.addStretch()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    from utils.config_manager import load_settings
    settings = load_settings()  # Globale Settings werden hier geladen, aber Skriptdaten kommen aus script_config.json
    widget = ScriptSettingsWidget(settings)
    widget.show()
    sys.exit(app.exec_())