#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore
from config.config_manager import load_config, save_config, get_recent_dirs, update_recent_dirs

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class HotfolderConfigDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten eines einzelnen Hotfolders.
    """
    def __init__(self, hotfolder_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hotfolder Konfiguration")
        self.resize(600, 500)
        self.hotfolder = hotfolder_data
        self.current_config = load_config()
        self.recent_dirs = self.current_config.get("recent_paths", {
            "monitor": [],
            "success": [],
            "fault": [],
            "logfiles": []
        })
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        self.name_edit = QtWidgets.QLineEdit(self.hotfolder.get("name", ""))
        form_layout.addRow("Name:", self.name_edit)

        self.path_edit = QtWidgets.QLineEdit(self.hotfolder.get("path", ""))
        self.browse_main_btn = QtWidgets.QPushButton("Browse")
        main_path_layout = QtWidgets.QHBoxLayout()
        main_path_layout.addWidget(self.path_edit)
        main_path_layout.addWidget(self.browse_main_btn)
        form_layout.addRow("Hauptpfad:", main_path_layout)

        self.monitor_combo = QtWidgets.QComboBox()
        self.monitor_combo.setEditable(True)
        for d in self.recent_dirs.get("monitor", []):
            self.monitor_combo.addItem(d)
        var_monitor = self.hotfolder.get("monitor_dir", "")
        if (var_monitor) and (var_monitor not in self.recent_dirs["monitor"]):
            self.monitor_combo.insertItem(0, var_monitor)
        self.monitor_combo.setCurrentText(var_monitor)

        self.browse_monitor_btn = QtWidgets.QPushButton("Browse")
        monitor_layout = QtWidgets.QHBoxLayout()
        monitor_layout.addWidget(self.monitor_combo)
        monitor_layout.addWidget(self.browse_monitor_btn)
        form_layout.addRow("01_Monitor:", monitor_layout)

        self.success_combo = QtWidgets.QComboBox()
        self.success_combo.setEditable(True)
        for d in self.recent_dirs.get("success", []):
            self.success_combo.addItem(d)
        var_success = self.hotfolder.get("success_dir", "")
        if (var_success) and (var_success not in self.recent_dirs["success"]):
            self.success_combo.insertItem(0, var_success)
        self.success_combo.setCurrentText(var_success)

        self.browse_success_btn = QtWidgets.QPushButton("Browse")
        success_layout = QtWidgets.QHBoxLayout()
        success_layout.addWidget(self.success_combo)
        success_layout.addWidget(self.browse_success_btn)
        form_layout.addRow("02_Succes:", success_layout)

        self.fault_combo = QtWidgets.QComboBox()
        self.fault_combo.setEditable(True)
        for d in self.recent_dirs.get("fault", []):
            self.fault_combo.addItem(d)
        var_fault = self.hotfolder.get("fault_dir", "")
        if (var_fault) and (var_fault not in self.recent_dirs["fault"]):
            self.fault_combo.insertItem(0, var_fault)
        self.fault_combo.setCurrentText(var_fault)

        self.browse_fault_btn = QtWidgets.QPushButton("Browse")
        fault_layout = QtWidgets.QHBoxLayout()
        fault_layout.addWidget(self.fault_combo)
        fault_layout.addWidget(self.browse_fault_btn)
        form_layout.addRow("03_Fault:", fault_layout)

        self.logfiles_combo = QtWidgets.QComboBox()
        self.logfiles_combo.setEditable(True)
        for d in self.recent_dirs.get("logfiles", []):
            self.logfiles_combo.addItem(d)
        var_logfiles = self.hotfolder.get("logfiles_dir", "")
        if (var_logfiles) and (var_logfiles not in self.recent_dirs["logfiles"]):
            self.logfiles_combo.insertItem(0, var_logfiles)
        self.logfiles_combo.setCurrentText(var_logfiles)

        self.browse_logfiles_btn = QtWidgets.QPushButton("Browse")
        logfiles_layout = QtWidgets.QHBoxLayout()
        logfiles_layout.addWidget(self.logfiles_combo)
        logfiles_layout.addWidget(self.browse_logfiles_btn)
        form_layout.addRow("04_Logfiles:", logfiles_layout)

        self.layer_checks = {}
        layer_group = QtWidgets.QGroupBox("Erforderliche Ebenen")
        layer_layout = QtWidgets.QVBoxLayout()
        for layer in ["Freisteller", "Messwerte", "Korrektur", "Freisteller_Wand", "Bildausschnitt"]:
            cb = QtWidgets.QCheckBox(layer)
            if layer in self.hotfolder.get("required_layers", []):
                cb.setChecked(True)
            layer_layout.addWidget(cb)
            self.layer_checks[layer] = cb
        layer_group.setLayout(layer_layout)
        form_layout.addRow(layer_group)

        self.meta_checks = {}
        meta_group = QtWidgets.QGroupBox("Erforderliche Metadaten")
        meta_layout = QtWidgets.QVBoxLayout()
        for meta in ["author", "description", "keywords", "headline"]:
            cb = QtWidgets.QCheckBox(meta)
            if meta in self.hotfolder.get("required_metadata", []):
                cb.setChecked(True)
            meta_layout.addWidget(cb)
            self.meta_checks[meta] = cb
        meta_group.setLayout(meta_layout)
        form_layout.addRow(meta_group)

        self.additional_jsx_edit = QtWidgets.QLineEdit(self.hotfolder.get("additional_jsx", ""))
        self.jsx_browse_btn = QtWidgets.QPushButton("JSX durchsuchen")
        jsx_layout = QtWidgets.QHBoxLayout()
        jsx_layout.addWidget(self.additional_jsx_edit)
        jsx_layout.addWidget(self.jsx_browse_btn)
        form_layout.addRow("Zusätzliches JSX:", jsx_layout)

        layout.addLayout(form_layout)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)

        self.browse_main_btn.clicked.connect(self.browse_main_path)
        self.browse_monitor_btn.clicked.connect(lambda: self.browse_folder("monitor"))
        self.browse_success_btn.clicked.connect(lambda: self.browse_folder("success"))
        self.browse_fault_btn.clicked.connect(lambda: self.browse_folder("fault"))
        self.browse_logfiles_btn.clicked.connect(lambda: self.browse_folder("logfiles"))
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_file)

        btn_box.accepted.connect(self.save_and_close)
        btn_box.rejected.connect(self.reject)

    def browse_main_path(self):
        start_dir = self.get_last_used_dir_any()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle Hauptpfad", start_dir)
        if folder:
            self.path_edit.setText(folder)
            self.monitor_combo.setCurrentText(os.path.join(folder, "01_Monitor"))
            self.success_combo.setCurrentText(os.path.join(folder, "02_Succes"))
            self.fault_combo.setCurrentText(os.path.join(folder, "03_Fault"))
            self.logfiles_combo.setCurrentText(os.path.join(folder, "04_Logfiles"))

    def browse_folder(self, folder_type: str):
        start_dir = self.get_last_used_dir(folder_type)
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, f"Wähle {folder_type}-Pfad", start_dir)
        if folder:
            if folder_type == "monitor":
                self.monitor_combo.setCurrentText(folder)
            elif folder_type == "success":
                self.success_combo.setCurrentText(folder)
            elif folder_type == "fault":
                self.fault_combo.setCurrentText(folder)
            elif folder_type == "logfiles":
                self.logfiles_combo.setCurrentText(folder)
            update_recent_dirs(folder_type, folder)

    def browse_jsx_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Wähle JSX-Skript", "", "JSX Files (*.jsx);;Alle Dateien (*)")
        if file_path:
            self.additional_jsx_edit.setText(file_path)

    def save_and_close(self):
        self.hotfolder["name"] = self.name_edit.text()
        self.hotfolder["path"] = self.path_edit.text()
        self.hotfolder["monitor_dir"] = self.monitor_combo.currentText()
        self.hotfolder["success_dir"] = self.success_combo.currentText()
        self.hotfolder["fault_dir"] = self.fault_combo.currentText()
        self.hotfolder["logfiles_dir"] = self.logfiles_combo.currentText()

        req_layers = []
        for layer, cb in self.layer_checks.items():
            if cb.isChecked():
                req_layers.append(layer)
        self.hotfolder["required_layers"] = req_layers

        req_meta = []
        for meta, cb in self.meta_checks.items():
            if cb.isChecked():
                req_meta.append(meta)
        self.hotfolder["required_metadata"] = req_meta

        self.hotfolder["additional_jsx"] = self.additional_jsx_edit.text()

        debug_print("Hotfolder-Konfiguration gespeichert/aktualisiert.")
        self.accept()

    def get_last_used_dir(self, folder_type: str) -> str:
        if self.recent_dirs.get(folder_type):
            return self.recent_dirs[folder_type][0]
        return os.path.expanduser("~")

    def get_last_used_dir_any(self) -> str:
        for cat in ["monitor", "success", "fault", "logfiles"]:
            if self.recent_dirs.get(cat):
                return self.recent_dirs[cat][0]
        return os.path.expanduser("~")