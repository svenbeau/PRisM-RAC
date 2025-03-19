#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore
from utils.config_manager import save_settings, debug_print

class SettingsWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        if "resource_paths" not in self.settings:
            self.settings["resource_paths"] = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # Allgemeine Einstellungen Tab
        self.general_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.general_tab, "Allgemein")
        gen_layout = QtWidgets.QVBoxLayout(self.general_tab)
        gen_layout.setContentsMargins(5, 5, 5, 5)
        gen_layout.setSpacing(5)

        self.general_group = QtWidgets.QGroupBox("Allgemeine Einstellungen")
        self.general_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        group_layout = QtWidgets.QFormLayout(self.general_group)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(5)

        # (A1) JSX-Templates-Pfad
        self.jsx_templates_edit = QtWidgets.QLineEdit()
        self.jsx_templates_edit.setFixedWidth(500)
        current_jsx_path = self.settings["resource_paths"].get("jsx_templates", "")
        self.jsx_templates_edit.setText(current_jsx_path)
        self.jsx_browse_btn = QtWidgets.QPushButton("Browse")
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_folder)
        jsx_layout = QtWidgets.QHBoxLayout()
        jsx_layout.addWidget(self.jsx_templates_edit, stretch=1)
        jsx_layout.addWidget(self.jsx_browse_btn, stretch=0)
        group_layout.addRow("JSX Templates:", jsx_layout)

        # (A2) Logfiles Directory-Pfad
        self.logfiles_edit = QtWidgets.QLineEdit()
        self.logfiles_edit.setFixedWidth(500)
        current_logfiles = self.settings["resource_paths"].get("logfiles_dir", "")
        self.logfiles_edit.setText(current_logfiles)
        self.logfiles_browse_btn = QtWidgets.QPushButton("Browse")
        self.logfiles_browse_btn.clicked.connect(self.browse_logfiles_folder)
        logfiles_layout = QtWidgets.QHBoxLayout()
        logfiles_layout.addWidget(self.logfiles_edit, stretch=1)
        logfiles_layout.addWidget(self.logfiles_browse_btn, stretch=0)
        group_layout.addRow("Logfiles Directory:", logfiles_layout)

        gen_layout.addWidget(self.general_group)
        gen_layout.addStretch()

        btn_hlay = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")
        btn_hlay.addStretch()
        btn_hlay.addWidget(self.save_btn)
        gen_layout.addLayout(btn_hlay)

        self.save_btn.clicked.connect(self.on_save)

    def browse_jsx_folder(self):
        start_dir = self.jsx_templates_edit.text() or QtCore.QDir.homePath()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSX-Templates-Ordner auswählen", start_dir)
        if folder:
            self.jsx_templates_edit.setText(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Info", "Kein gültiger Ordner ausgewählt.")

    def browse_logfiles_folder(self):
        start_dir = self.logfiles_edit.text() or QtCore.QDir.homePath()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Logfiles Directory auswählen", start_dir)
        if folder:
            self.logfiles_edit.setText(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Info", "Kein gültiger Ordner ausgewählt.")

    def on_save(self):
        new_jsx_path = self.jsx_templates_edit.text().strip()
        if new_jsx_path:
            self.settings["resource_paths"]["jsx_templates"] = new_jsx_path
        else:
            if "jsx_templates" in self.settings["resource_paths"]:
                del self.settings["resource_paths"]["jsx_templates"]

        new_logfiles_dir = self.logfiles_edit.text().strip()
        if new_logfiles_dir:
            self.settings["resource_paths"]["logfiles_dir"] = new_logfiles_dir
        else:
            if "logfiles_dir" in self.settings["resource_paths"]:
                del self.settings["resource_paths"]["logfiles_dir"]

        save_settings(self.settings)
        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")