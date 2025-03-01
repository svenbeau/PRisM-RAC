#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import save_settings, debug_print

class SettingsWidget(QtWidgets.QWidget):
    """
    A simple widget for configuring global settings,
    including the 'GB_Config_Render.json' style fields:
      - actionFolderName
      - basicWandFiles
      - csvWandFile
      - wandFileSavePath
      etc.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        # We'll store them in a dict:
        self.render_config = self.settings.setdefault("renderConfig", {
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": ""
        })

        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        title_label = QtWidgets.QLabel("Global Einstellungen")
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        form_layout = QtWidgets.QFormLayout()
        layout.addLayout(form_layout)

        # actionFolderName
        self.actionFolder_edit = QtWidgets.QLineEdit(self.render_config.get("actionFolderName", ""))
        form_layout.addRow("Action Folder Name:", self.actionFolder_edit)

        # basicWandFiles
        self.basicWandFiles_edit = QtWidgets.QLineEdit(self.render_config.get("basicWandFiles", ""))
        bw_browse_btn = QtWidgets.QPushButton("Browse")
        bw_browse_btn.clicked.connect(self.on_browse_basic_wand)
        bw_layout = QtWidgets.QHBoxLayout()
        bw_layout.addWidget(self.basicWandFiles_edit, 1)
        bw_layout.addWidget(bw_browse_btn, 0)
        form_layout.addRow("Basic Wand Files:", bw_layout)

        # csvWandFile
        self.csvWandFile_edit = QtWidgets.QLineEdit(self.render_config.get("csvWandFile", ""))
        csv_browse_btn = QtWidgets.QPushButton("Browse")
        csv_browse_btn.clicked.connect(self.on_browse_csv)
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csvWandFile_edit, 1)
        csv_layout.addWidget(csv_browse_btn, 0)
        form_layout.addRow("CSV Wand File:", csv_layout)

        # wandFileSavePath
        self.wandFileSavePath_edit = QtWidgets.QLineEdit(self.render_config.get("wandFileSavePath", ""))
        wand_browse_btn = QtWidgets.QPushButton("Browse")
        wand_browse_btn.clicked.connect(self.on_browse_wand_save)
        wand_layout = QtWidgets.QHBoxLayout()
        wand_layout.addWidget(self.wandFileSavePath_edit, 1)
        wand_layout.addWidget(wand_browse_btn, 0)
        form_layout.addRow("WandFile SavePath:", wand_layout)

        # Save button
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QtWidgets.QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def on_browse_basic_wand(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Basic Wand Files Folder", "")
        if path:
            self.basicWandFiles_edit.setText(path)

    def on_browse_csv(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV Wand File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.csvWandFile_edit.setText(file_path)

    def on_browse_wand_save(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Wand Save Path", "")
        if path:
            self.wandFileSavePath_edit.setText(path)

    def on_save(self):
        self.render_config["actionFolderName"] = self.actionFolder_edit.text().strip()
        self.render_config["basicWandFiles"] = self.basicWandFiles_edit.text().strip()
        self.render_config["csvWandFile"] = self.csvWandFile_edit.text().strip()
        self.render_config["wandFileSavePath"] = self.wandFileSavePath_edit.text().strip()

        self.settings["renderConfig"] = self.render_config
        save_settings(self.settings)
        QtWidgets.QMessageBox.information(self, "Saved", "Einstellungen gespeichert.")