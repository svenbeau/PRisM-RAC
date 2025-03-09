#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore

# Falls du debug_print oder andere Funktionen brauchst:
from utils.config_manager import debug_print

class ScriptConfigWidget(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten einer Skript-Konfiguration.
    Erwartet ein Dictionary 'script_config', z.B.:
    {
      "id": "...",
      "script_path": "...",
      "json_folder": "...",
      "actionFolderName": "...",
      "basicWandFiles": "...",
      "csvWandFile": "...",
      "wandFileSavePath": "..."
    }
    Änderungen werden beim Klick auf OK in script_config übernommen.
    """
    def __init__(self, script_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rezept bearbeiten")
        self.script_config = script_config  # Referenz auf das Dictionary
        self.init_ui()
        self.load_values()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        # Script Path
        self.script_path_edit = QtWidgets.QLineEdit()
        self.script_browse_btn = QtWidgets.QPushButton("Browse")
        self.script_browse_btn.clicked.connect(self.browse_script)
        script_layout = QtWidgets.QHBoxLayout()
        script_layout.addWidget(self.script_path_edit, stretch=1)
        script_layout.addWidget(self.script_browse_btn)
        form_layout.addRow("Script Path:", script_layout)

        # JSON Folder
        self.json_folder_edit = QtWidgets.QLineEdit()
        self.json_browse_btn = QtWidgets.QPushButton("Browse")
        self.json_browse_btn.clicked.connect(self.browse_json_folder)
        json_layout = QtWidgets.QHBoxLayout()
        json_layout.addWidget(self.json_folder_edit, stretch=1)
        json_layout.addWidget(self.json_browse_btn)
        form_layout.addRow("JSON Folder:", json_layout)

        # Action Folder Name
        self.action_folder_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Action Folder Name:", self.action_folder_edit)

        # Basic Wand Files
        self.basic_wand_edit = QtWidgets.QLineEdit()
        self.basic_wand_btn = QtWidgets.QPushButton("Browse")
        self.basic_wand_btn.clicked.connect(self.browse_basic_wand)
        basic_wand_layout = QtWidgets.QHBoxLayout()
        basic_wand_layout.addWidget(self.basic_wand_edit, stretch=1)
        basic_wand_layout.addWidget(self.basic_wand_btn)
        form_layout.addRow("Basic Wand Files:", basic_wand_layout)

        # CSV Wand File
        self.csv_wand_edit = QtWidgets.QLineEdit()
        self.csv_wand_btn = QtWidgets.QPushButton("Browse")
        self.csv_wand_btn.clicked.connect(self.browse_csv_wand)
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csv_wand_edit, stretch=1)
        csv_layout.addWidget(self.csv_wand_btn)
        form_layout.addRow("CSV Wand File:", csv_layout)

        # Wand File Save Path
        self.wand_save_edit = QtWidgets.QLineEdit()
        self.wand_save_btn = QtWidgets.QPushButton("Browse")
        self.wand_save_btn.clicked.connect(self.browse_wand_save)
        wand_save_layout = QtWidgets.QHBoxLayout()
        wand_save_layout.addWidget(self.wand_save_edit, stretch=1)
        wand_save_layout.addWidget(self.wand_save_btn)
        form_layout.addRow("Wand File Save Path:", wand_save_layout)

        layout.addLayout(form_layout)

        # OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def load_values(self):
        """
        Lädt die Werte aus self.script_config in die Felder.
        """
        self.script_path_edit.setText(self.script_config.get("script_path", ""))
        self.json_folder_edit.setText(self.script_config.get("json_folder", ""))
        self.action_folder_edit.setText(self.script_config.get("actionFolderName", ""))
        self.basic_wand_edit.setText(self.script_config.get("basicWandFiles", ""))
        self.csv_wand_edit.setText(self.script_config.get("csvWandFile", ""))
        self.wand_save_edit.setText(self.script_config.get("wandFileSavePath", ""))

    def accept(self):
        """
        Übernimmt die Werte aus den Feldern in self.script_config und schließt mit OK.
        """
        self.script_config["script_path"] = self.script_path_edit.text().strip()
        self.script_config["json_folder"] = self.json_folder_edit.text().strip()
        self.script_config["actionFolderName"] = self.action_folder_edit.text().strip()
        self.script_config["basicWandFiles"] = self.basic_wand_edit.text().strip()
        self.script_config["csvWandFile"] = self.csv_wand_edit.text().strip()
        self.script_config["wandFileSavePath"] = self.wand_save_edit.text().strip()

        super().accept()

    def browse_script(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Script auswählen", "", "JSX Files (*.jsx);;All Files (*)"
        )
        if fname:
            self.script_path_edit.setText(fname)

    def browse_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON-Folder auswählen", "")
        if folder:
            self.json_folder_edit.setText(folder)

    def browse_basic_wand(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Basic Wand Ordner auswählen", "")
        if folder:
            self.basic_wand_edit.setText(folder)

    def browse_csv_wand(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV Wand File auswählen", "", "CSV Files (*.csv);;All Files (*)")
        if fname:
            self.csv_wand_edit.setText(fname)

    def browse_wand_save(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wand File Save Path auswählen", "")
        if folder:
            self.wand_save_edit.setText(folder)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Test
    test_config = {
        "id": "1234",
        "script_path": "/Users/xyz/SomeScript.jsx",
        "json_folder": "/Users/xyz/jsonfolder",
        "actionFolderName": "Grisebach 2025",
        "basicWandFiles": "/path/to/wandfiles",
        "csvWandFile": "/path/to/wand.csv",
        "wandFileSavePath": "/save/path"
    }
    dlg = ScriptConfigWidget(test_config)
    if dlg.exec_():
        print("OK clicked, script_config now:", test_config)
    else:
        print("Cancel clicked.")
    sys.exit(0)