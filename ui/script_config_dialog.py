#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
from PyQt5 import QtWidgets, QtCore
from config.config_manager import load_settings, save_settings, debug_print

class ScriptConfigDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten einer einzelnen Skript-Konfiguration.
    Hier können Sie:
      - Den Ordner wählen, in dem die Skripte liegen (über einen Browse-Button)
      - Aus dem Dropdown-Menü das gewünschte Script auswählen (Anzeige erfolgt als Dateiname)
      - Einen JSON-Ordner für dieses Script auswählen (über einen separaten Browse-Button)
      - Zusätzliche Parameter wie "actionFolderName", "basicWandFiles", "csvWandFile" und "wandFileSavePath" eingeben.
    """
    def __init__(self, script_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Script Konfiguration bearbeiten")
        self.resize(600, 400)
        self.script_config = script_config
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        # Skripte-Ordner: Anzeige als Dropdown (nur der Ordnername wird im Dropdown angezeigt)
        self.scripts_folder_edit = QtWidgets.QLineEdit(self.script_config.get("scripts_folder", ""))
        self.scripts_folder_edit.setReadOnly(True)
        self.browse_scripts_folder_btn = QtWidgets.QPushButton("Browse Folder")
        self.browse_scripts_folder_btn.setFixedWidth(100)
        scripts_folder_layout = QtWidgets.QHBoxLayout()
        scripts_folder_layout.addWidget(self.scripts_folder_edit)
        scripts_folder_layout.addWidget(self.browse_scripts_folder_btn)
        form_layout.addRow("Skripte Ordner:", scripts_folder_layout)

        # Dropdown für Skriptauswahl (Dateinamen, rechtsbündig dargestellt)
        self.script_dropdown = QtWidgets.QComboBox()
        self.script_dropdown.setEditable(False)
        form_layout.addRow("Script:", self.script_dropdown)

        # JSON Ordner
        self.json_folder_edit = QtWidgets.QLineEdit(self.script_config.get("json_folder", ""))
        self.json_folder_edit.setReadOnly(True)
        self.browse_json_folder_btn = QtWidgets.QPushButton("Browse Folder")
        self.browse_json_folder_btn.setFixedWidth(100)
        json_folder_layout = QtWidgets.QHBoxLayout()
        json_folder_layout.addWidget(self.json_folder_edit)
        json_folder_layout.addWidget(self.browse_json_folder_btn)
        form_layout.addRow("JSON Ordner:", json_folder_layout)

        # Zusätzliche Parameter
        self.actionFolderName_edit = QtWidgets.QLineEdit(self.script_config.get("actionFolderName", ""))
        form_layout.addRow("Action Folder Name:", self.actionFolderName_edit)

        self.basicWandFiles_edit = QtWidgets.QLineEdit(self.script_config.get("basicWandFiles", ""))
        form_layout.addRow("Basic Wand Files:", self.basicWandFiles_edit)

        self.csvWandFile_edit = QtWidgets.QLineEdit(self.script_config.get("csvWandFile", ""))
        form_layout.addRow("CSV Wand File:", self.csvWandFile_edit)

        self.wandFileSavePath_edit = QtWidgets.QLineEdit(self.script_config.get("wandFileSavePath", ""))
        form_layout.addRow("Wand File Save Path:", self.wandFileSavePath_edit)

        main_layout.addLayout(form_layout)

        # OK / Cancel Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        main_layout.addWidget(btn_box)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # Verbindungen
        self.browse_scripts_folder_btn.clicked.connect(self.browse_scripts_folder)
        self.browse_json_folder_btn.clicked.connect(self.browse_json_folder)
        self.update_script_dropdown()

    def browse_scripts_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Skripte Ordner auswählen", self.scripts_folder_edit.text() or QtCore.QDir.homePath())
        if folder:
            self.scripts_folder_edit.setText(folder)
            self.update_script_dropdown()

    def update_script_dropdown(self):
        folder = self.scripts_folder_edit.text()
        self.script_dropdown.clear()
        if folder and os.path.isdir(folder):
            # Liste aller .jsx-Dateien im Ordner
            scripts = [f for f in os.listdir(folder) if f.lower().endswith(".jsx")]
            # Wir möchten die Darstellung von hinten beginnen: Wir sortieren die Dateinamen so, dass der letzte Teil (z. B. der Scriptname) sichtbar ist.
            # Hier sortieren wir alphabetisch; bei Bedarf kann hier eine andere Logik implementiert werden.
            scripts.sort()
            self.script_dropdown.addItems(scripts)
            current_script = os.path.basename(self.script_config.get("selected_jsx", ""))
            if current_script in scripts:
                idx = self.script_dropdown.findText(current_script)
                self.script_dropdown.setCurrentIndex(idx)
        else:
            self.script_dropdown.addItem("")

    def browse_json_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSON Ordner auswählen", self.json_folder_edit.text() or QtCore.QDir.homePath())
        if folder:
            self.json_folder_edit.setText(folder)

    def accept(self):
        self.script_config["scripts_folder"] = self.scripts_folder_edit.text()
        selected_script = self.script_dropdown.currentText()
        if self.scripts_folder_edit.text():
            self.script_config["selected_jsx"] = os.path.join(self.scripts_folder_edit.text(), selected_script)
        else:
            self.script_config["selected_jsx"] = ""
        self.script_config["json_folder"] = self.json_folder_edit.text()
        self.script_config["actionFolderName"] = self.actionFolderName_edit.text()
        self.script_config["basicWandFiles"] = self.basicWandFiles_edit.text()
        self.script_config["csvWandFile"] = self.csvWandFile_edit.text()
        self.script_config["wandFileSavePath"] = self.wandFileSavePath_edit.text()
        super().accept()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    # Testkonfiguration
    test_config = {
        "id": str(uuid.uuid4()),
        "selected_jsx": "",
        "scripts_folder": "",
        "json_folder": "",
        "actionFolderName": "",
        "basicWandFiles": "",
        "csvWandFile": "",
        "wandFileSavePath": ""
    }
    dlg = ScriptConfigDialog(test_config)
    if dlg.exec_():
        print("Gespeicherte Skript-Konfiguration:")
        print(test_config)
    else:
        print("Abgebrochen")
    sys.exit(app.exec_())