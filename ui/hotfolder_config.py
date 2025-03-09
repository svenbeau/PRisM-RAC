#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import json

# Hier importieren wir PySide6, damit QtWidgets/QtCore bekannt sind
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt, Signal
# Wenn du z. B. Icons verwendest:
# from PySide6.QtGui import QIcon

# Falls du im __main__-Testlauf QApp brauchst:
from PySide6.QtWidgets import QApplication

from utils.config_manager import (
    load_settings,
    save_settings,
    get_recent_dirs,
    update_recent_dirs
)

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class HotfolderConfigDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten eines einzelnen Hotfolders (per Referenz).
    Identifikation erfolgt über 'id' statt über den Namen.
    Die Änderungen werden nur einmal gespeichert – kein doppeltes Überschreiben.
    """
    def __init__(self, hotfolder_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hotfolder Konfiguration")
        self.resize(700, 600)

        # Direkte Referenz; Änderungen wirken direkt im übergebenen Dictionary
        self.hotfolder = hotfolder_data
        debug_print("HotfolderConfigDialog init: " + str(self.hotfolder))

        self.current_config = load_settings()
        # recent_paths wird nun verwendet – falls keine Einträge vorhanden sind, liefern wir einen Fallback
        self.recent_dirs = self.current_config.setdefault("recent_paths", {
            "monitor": [os.path.expanduser("~")],
            "success": [os.path.expanduser("~")],
            "fault": [os.path.expanduser("~")],
            "logfiles": [os.path.expanduser("~")]
        })
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # (A) Formulardaten
        form_layout = QtWidgets.QFormLayout()

        # ID (nur zur Information)
        self.id_label = QtWidgets.QLabel(self.hotfolder.get("id", "NO-ID"))
        form_layout.addRow("ID:", self.id_label)

        # Name
        self.name_edit = QtWidgets.QLineEdit(self.hotfolder.get("name", "Neuer Hotfolder"))
        form_layout.addRow("Name:", self.name_edit)

        # Hauptpfad
        self.path_edit = QtWidgets.QLineEdit(self.hotfolder.get("path", ""))
        self.browse_main_btn = QtWidgets.QPushButton("Browse")
        main_path_layout = QtWidgets.QHBoxLayout()
        main_path_layout.addWidget(self.path_edit)
        main_path_layout.addWidget(self.browse_main_btn)
        form_layout.addRow("Hauptpfad:", main_path_layout)

        # 01_Monitor
        self.monitor_combo = QtWidgets.QComboBox()
        self.monitor_combo.setEditable(True)
        for d in get_recent_dirs("monitor"):
            self.monitor_combo.addItem(d)
        monitor_dir = self.hotfolder.get("monitor_dir", "")
        if monitor_dir and monitor_dir not in get_recent_dirs("monitor"):
            self.monitor_combo.insertItem(0, monitor_dir)
        self.monitor_combo.setCurrentText(monitor_dir)
        self.browse_monitor_btn = QtWidgets.QPushButton("Browse")
        monitor_layout = QtWidgets.QHBoxLayout()
        monitor_layout.addWidget(self.monitor_combo)
        monitor_layout.addWidget(self.browse_monitor_btn)
        form_layout.addRow("01_Monitor:", monitor_layout)

        # 02_Success
        self.success_combo = QtWidgets.QComboBox()
        self.success_combo.setEditable(True)
        for d in get_recent_dirs("success"):
            self.success_combo.addItem(d)
        success_dir = self.hotfolder.get("success_dir", "")
        if success_dir and success_dir not in get_recent_dirs("success"):
            self.success_combo.insertItem(0, success_dir)
        self.success_combo.setCurrentText(success_dir)
        self.browse_success_btn = QtWidgets.QPushButton("Browse")
        success_layout = QtWidgets.QHBoxLayout()
        success_layout.addWidget(self.success_combo)
        success_layout.addWidget(self.browse_success_btn)
        form_layout.addRow("02_Success:", success_layout)

        # 03_Fault
        self.fault_combo = QtWidgets.QComboBox()
        self.fault_combo.setEditable(True)
        for d in get_recent_dirs("fault"):
            self.fault_combo.addItem(d)
        fault_dir = self.hotfolder.get("fault_dir", "")
        if fault_dir and fault_dir not in get_recent_dirs("fault"):
            self.fault_combo.insertItem(0, fault_dir)
        self.fault_combo.setCurrentText(fault_dir)
        self.browse_fault_btn = QtWidgets.QPushButton("Browse")
        fault_layout = QtWidgets.QHBoxLayout()
        fault_layout.addWidget(self.fault_combo)
        fault_layout.addWidget(self.browse_fault_btn)
        form_layout.addRow("03_Fault:", fault_layout)

        # 04_Logfiles
        self.logfiles_combo = QtWidgets.QComboBox()
        self.logfiles_combo.setEditable(True)
        for d in get_recent_dirs("logfiles"):
            self.logfiles_combo.addItem(d)
        logfiles_dir = self.hotfolder.get("logfiles_dir", "")
        if logfiles_dir and logfiles_dir not in get_recent_dirs("logfiles"):
            self.logfiles_combo.insertItem(0, logfiles_dir)
        self.logfiles_combo.setCurrentText(logfiles_dir)
        self.browse_logfiles_btn = QtWidgets.QPushButton("Browse")
        logfiles_layout = QtWidgets.QHBoxLayout()
        logfiles_layout.addWidget(self.logfiles_combo)
        logfiles_layout.addWidget(self.browse_logfiles_btn)
        form_layout.addRow("04_Logfiles:", logfiles_layout)

        main_layout.addLayout(form_layout)

        # (B) Standard-Contentcheck
        self.standard_contentcheck_group = QtWidgets.QGroupBox("Standard-Contentcheck")
        self.standard_contentcheck_group.setCheckable(True)
        self.standard_contentcheck_group.setChecked(self.hotfolder.get("contentcheck_enabled", True))
        std_layout = QtWidgets.QHBoxLayout(self.standard_contentcheck_group)

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
        std_layout.addWidget(layer_group)

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
        std_layout.addWidget(meta_group)

        main_layout.addWidget(self.standard_contentcheck_group)

        # (C) Keyword-basierter Contentcheck
        self.keyword_check_group = QtWidgets.QGroupBox("Keyword-basierter Contentcheck")
        self.keyword_check_group.setCheckable(True)
        self.keyword_check_group.setChecked(self.hotfolder.get("keyword_check_enabled", False))
        keyword_vlayout = QtWidgets.QVBoxLayout(self.keyword_check_group)

        keyword_hlayout = QtWidgets.QHBoxLayout()
        keyword_hlayout.addWidget(QtWidgets.QLabel("Keyword:"))
        self.keyword_edit = QtWidgets.QLineEdit(self.hotfolder.get("keyword_check_word", ""))
        keyword_hlayout.addWidget(self.keyword_edit)
        keyword_vlayout.addLayout(keyword_hlayout)

        kw_hlayout = QtWidgets.QHBoxLayout()

        self.keyword_layer_checks = {}
        keyword_layer_group = QtWidgets.QGroupBox("Erforderliche Ebenen (Keyword)")
        kw_layer_layout = QtWidgets.QVBoxLayout()
        kw_layers_cfg = self.hotfolder.get("keyword_layers", [])
        for layer in ["Freisteller", "Messwerte", "Korrektur", "Freisteller_Wand", "Bildausschnitt"]:
            cb = QtWidgets.QCheckBox(layer)
            if layer in kw_layers_cfg:
                cb.setChecked(True)
            kw_layer_layout.addWidget(cb)
            self.keyword_layer_checks[layer] = cb
        keyword_layer_group.setLayout(kw_layer_layout)
        kw_hlayout.addWidget(keyword_layer_group)

        self.keyword_meta_checks = {}
        keyword_meta_group = QtWidgets.QGroupBox("Erforderliche Metadaten (Keyword)")
        kw_meta_layout = QtWidgets.QVBoxLayout()
        kw_meta_cfg = self.hotfolder.get("keyword_metadata", [])
        for meta in ["author", "description", "keywords", "headline"]:
            cb = QtWidgets.QCheckBox(meta)
            if meta in kw_meta_cfg:
                cb.setChecked(True)
            kw_meta_layout.addWidget(cb)
            self.keyword_meta_checks[meta] = cb
        keyword_meta_group.setLayout(kw_meta_layout)
        kw_hlayout.addWidget(keyword_meta_group)

        keyword_vlayout.addLayout(kw_hlayout)
        main_layout.addWidget(self.keyword_check_group)

        # (D) JSX Folder + Dropdown
        self.jsx_folder_edit = QtWidgets.QLineEdit(self.hotfolder.get("jsx_folder", ""))
        self.browse_jsx_folder_btn = QtWidgets.QPushButton("Browse Folder")
        jsx_folder_layout = QtWidgets.QHBoxLayout()
        jsx_folder_layout.addWidget(QtWidgets.QLabel("JSX Folder:"))
        jsx_folder_layout.addWidget(self.jsx_folder_edit)
        jsx_folder_layout.addWidget(self.browse_jsx_folder_btn)
        main_layout.addLayout(jsx_folder_layout)

        # ComboBox-Skript -> "selected_jsx"
        self.jsx_combo = QtWidgets.QComboBox()
        self.jsx_combo.setEditable(True)
        self.populate_jsx_combo()  # Füllt die ComboBox mit .jsx-Dateien
        jsx_combo_layout = QtWidgets.QHBoxLayout()
        jsx_combo_layout.addWidget(QtWidgets.QLabel("JSX-Script Auswahl:"))
        jsx_combo_layout.addWidget(self.jsx_combo)
        main_layout.addLayout(jsx_combo_layout)

        # (E) Zusätzliches JSX (manuelles Skript) -> "additional_jsx"
        self.additional_jsx_edit = QtWidgets.QLineEdit(self.hotfolder.get("additional_jsx", ""))
        self.jsx_browse_btn = QtWidgets.QPushButton("JSX durchsuchen")
        add_jsx_layout = QtWidgets.QHBoxLayout()
        add_jsx_layout.addWidget(QtWidgets.QLabel("Zusätzliches JSX:"))
        add_jsx_layout.addWidget(self.additional_jsx_edit)
        add_jsx_layout.addWidget(self.jsx_browse_btn)
        main_layout.addLayout(add_jsx_layout)

        # *** NEUE BUTTONS FÜR SPEICHERN/LADEN ***
        btn_save_load_layout = QtWidgets.QHBoxLayout()
        self.btn_save_config = QtWidgets.QPushButton("Konfiguration speichern")
        self.btn_load_config = QtWidgets.QPushButton("Konfiguration laden")
        btn_save_load_layout.addWidget(self.btn_save_config)
        btn_save_load_layout.addWidget(self.btn_load_config)
        btn_save_load_layout.addStretch()
        main_layout.addLayout(btn_save_load_layout)

        # (F) OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        main_layout.addWidget(btn_box)

        # Signals
        self.browse_main_btn.clicked.connect(self.browse_main_path)
        self.browse_monitor_btn.clicked.connect(lambda: self.browse_folder("monitor"))
        self.browse_success_btn.clicked.connect(lambda: self.browse_folder("success"))
        self.browse_fault_btn.clicked.connect(lambda: self.browse_folder("fault"))
        self.browse_logfiles_btn.clicked.connect(lambda: self.browse_folder("logfiles"))
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_file)
        self.browse_jsx_folder_btn.clicked.connect(self.browse_jsx_folder)

        btn_box.accepted.connect(self.save_and_close)
        btn_box.rejected.connect(self.reject)

        self.btn_save_config.clicked.connect(self.save_configuration_to_file)
        self.btn_load_config.clicked.connect(self.load_configuration_from_file)

    def populate_jsx_combo(self):
        self.jsx_combo.clear()
        folder = self.hotfolder.get("jsx_folder", "")
        if folder and os.path.isdir(folder):
            for filename in os.listdir(folder):
                if filename.lower().endswith(".jsx"):
                    self.jsx_combo.addItem(filename)
        # Falls in "selected_jsx" bereits ein Skript hinterlegt ist, wähle es aus
        selected_jsx_path = self.hotfolder.get("selected_jsx", "")
        if selected_jsx_path:
            base_script = os.path.basename(selected_jsx_path)
            idx = self.jsx_combo.findText(base_script)
            if idx >= 0:
                self.jsx_combo.setCurrentIndex(idx)

    def browse_main_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle Hauptpfad", self.get_last_used_dir_any())
        if folder:
            self.path_edit.setText(folder)
            self.monitor_combo.setCurrentText(os.path.join(folder, "01_Monitor"))
            self.success_combo.setCurrentText(os.path.join(folder, "02_Success"))
            self.fault_combo.setCurrentText(os.path.join(folder, "03_Fault"))
            self.logfiles_combo.setCurrentText(os.path.join(folder, "04_Logfiles"))

    def browse_folder(self, folder_type: str):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, f"Wähle {folder_type}-Pfad", self.get_last_used_dir(folder_type))
        if folder:
            if folder_type == "monitor":
                self.monitor_combo.setCurrentText(folder)
            elif folder_type == "success":
                self.success_combo.setCurrentText(folder)
            elif folder_type == "fault":
                self.fault_combo.setCurrentText(folder)
            elif folder_type == "logfiles":
                self.logfiles_combo.setCurrentText(folder)
            update_recent_dirs(self.recent_dirs, folder)

    def browse_jsx_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Wähle JSX-Skript", "",
            "JSX Files (*.jsx);;Alle Dateien (*)"
        )
        if file_path:
            self.additional_jsx_edit.setText(file_path)

    def browse_jsx_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle JSX Folder", os.path.expanduser("~"))
        if folder:
            self.jsx_folder_edit.setText(folder)
            self.hotfolder["jsx_folder"] = folder
            self.populate_jsx_combo()

    def save_and_close(self):
        debug_print("Vor save_and_close - Hotfolder war: " + str(self.hotfolder))
        # 1) Basisdaten
        self.hotfolder["name"] = self.name_edit.text()
        self.hotfolder["path"] = self.path_edit.text()
        self.hotfolder["monitor_dir"] = self.monitor_combo.currentText()
        self.hotfolder["success_dir"] = self.success_combo.currentText()
        self.hotfolder["fault_dir"] = self.fault_combo.currentText()
        self.hotfolder["logfiles_dir"] = self.logfiles_combo.currentText()

        # 2) Standard-Contentcheck
        self.hotfolder["contentcheck_enabled"] = self.standard_contentcheck_group.isChecked()
        self.hotfolder["required_layers"] = [layer for layer, cb in self.layer_checks.items() if cb.isChecked()]
        self.hotfolder["required_metadata"] = [meta for meta, cb in self.meta_checks.items() if cb.isChecked()]

        # 3) Keyword-Contentcheck
        self.hotfolder["keyword_check_enabled"] = self.keyword_check_group.isChecked()
        self.hotfolder["keyword_check_word"] = self.keyword_edit.text()
        self.hotfolder["keyword_layers"] = [layer for layer, cb in self.keyword_layer_checks.items() if cb.isChecked()]
        self.hotfolder["keyword_metadata"] = [meta for meta, cb in self.keyword_meta_checks.items() if cb.isChecked()]

        # 4) JSX
        self.hotfolder["jsx_folder"] = self.jsx_folder_edit.text()
        selected_script = self.jsx_combo.currentText().strip()
        if selected_script and selected_script != "(none)":
            self.hotfolder["selected_jsx"] = os.path.join(self.hotfolder["jsx_folder"], selected_script)
        else:
            self.hotfolder["selected_jsx"] = ""
        manual_script = self.additional_jsx_edit.text().strip()
        self.hotfolder["additional_jsx"] = manual_script

        debug_print("In save_and_close - Hotfolder neu: " + str(self.hotfolder))
        # 5) Sicherstellen, dass der Hotfolder eine ID besitzt
        if not self.hotfolder.get("id"):
            new_id = str(uuid.uuid4())
            self.hotfolder["id"] = new_id
            debug_print("Keine ID vorhanden. Neue ID: " + new_id)

        # 6) In globale settings.json übernehmen
        settings_data = load_settings()
        hotfolders_list = settings_data.setdefault("hotfolders", [])
        current_id = self.hotfolder["id"]
        found_idx = -1
        for i, hf in enumerate(hotfolders_list):
            if hf.get("id") == current_id:
                found_idx = i
                break
        if found_idx >= 0:
            debug_print(f"Ersetze alten Eintrag an Index {found_idx} durch: {self.hotfolder}")
            hotfolders_list[found_idx] = self.hotfolder
        else:
            debug_print("Kein Hotfolder mit dieser ID gefunden; hänge neuen an.")
            hotfolders_list.append(self.hotfolder)
        save_settings(settings_data)
        debug_print("Hotfolder-Konfiguration gespeichert/aktualisiert.")
        self.accept()

    def get_last_used_dir(self, folder_type: str) -> str:
        return self.recent_dirs.get(folder_type, [os.path.expanduser("~")])[0]

    def get_last_used_dir_any(self) -> str:
        for cat in ["monitor", "success", "fault", "logfiles"]:
            if self.recent_dirs.get(cat):
                return self.recent_dirs[cat][0]
        return os.path.expanduser("~")

    def save_configuration_to_file(self):
        """
        Exportiert die aktuelle Hotfolder-Konfiguration als JSON in eine Datei.
        """
        self.update_hotfolder_from_fields()
        options = QtWidgets.QFileDialog.Options()
        default_name = "HF_Settings_" + self.hotfolder.get("name", "").strip() + ".json"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Konfiguration speichern", default_name, "JSON Files (*.json)", options=options
        )
        if filename:
            if not filename.lower().endswith(".json"):
                filename += ".json"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.hotfolder, f, indent=4)
                QtWidgets.QMessageBox.information(self, "Erfolg", "Konfiguration erfolgreich gespeichert.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {e}")

    def load_configuration_from_file(self):
        """
        Lädt eine Hotfolder-Konfiguration aus einer JSON-Datei und aktualisiert die Felder.
        """
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Konfiguration laden", "", "JSON Files (*.json)", options=options
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.hotfolder.update(config)
                self.update_fields_from_hotfolder()
                QtWidgets.QMessageBox.information(self, "Erfolg", "Konfiguration erfolgreich geladen.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Laden: {e}")

    def update_hotfolder_from_fields(self):
        """
        Schreibt sämtliche Felder in self.hotfolder (bevor wir extern speichern).
        """
        self.hotfolder["name"] = self.name_edit.text()
        self.hotfolder["path"] = self.path_edit.text()
        self.hotfolder["monitor_dir"] = self.monitor_combo.currentText()
        self.hotfolder["success_dir"] = self.success_combo.currentText()
        self.hotfolder["fault_dir"] = self.fault_combo.currentText()
        self.hotfolder["logfiles_dir"] = self.logfiles_combo.currentText()
        self.hotfolder["contentcheck_enabled"] = self.standard_contentcheck_group.isChecked()
        self.hotfolder["required_layers"] = [layer for layer, cb in self.layer_checks.items() if cb.isChecked()]
        self.hotfolder["required_metadata"] = [meta for meta, cb in self.meta_checks.items() if cb.isChecked()]
        self.hotfolder["keyword_check_enabled"] = self.keyword_check_group.isChecked()
        self.hotfolder["keyword_check_word"] = self.keyword_edit.text()
        self.hotfolder["keyword_layers"] = [layer for layer, cb in self.keyword_layer_checks.items() if cb.isChecked()]
        self.hotfolder["keyword_metadata"] = [meta for meta, cb in self.keyword_meta_checks.items() if cb.isChecked()]
        self.hotfolder["jsx_folder"] = self.jsx_folder_edit.text()
        selected_script = self.jsx_combo.currentText().strip()
        if selected_script and selected_script != "(none)":
            self.hotfolder["selected_jsx"] = os.path.join(self.hotfolder["jsx_folder"], selected_script)
        else:
            self.hotfolder["selected_jsx"] = ""
        self.hotfolder["additional_jsx"] = self.additional_jsx_edit.text().strip()

    def update_fields_from_hotfolder(self):
        """
        Aktualisiert die Dialog-Felder anhand der in self.hotfolder gespeicherten Daten.
        """
        self.id_label.setText(self.hotfolder.get("id", "NO-ID"))
        self.name_edit.setText(self.hotfolder.get("name", "Neuer Hotfolder"))
        self.path_edit.setText(self.hotfolder.get("path", ""))
        self.monitor_combo.setCurrentText(self.hotfolder.get("monitor_dir", ""))
        self.success_combo.setCurrentText(self.hotfolder.get("success_dir", ""))
        self.fault_combo.setCurrentText(self.hotfolder.get("fault_dir", ""))
        self.logfiles_combo.setCurrentText(self.hotfolder.get("logfiles_dir", ""))
        self.standard_contentcheck_group.setChecked(self.hotfolder.get("contentcheck_enabled", True))
        for layer, cb in self.layer_checks.items():
            cb.setChecked(layer in self.hotfolder.get("required_layers", []))
        for meta, cb in self.meta_checks.items():
            cb.setChecked(meta in self.hotfolder.get("required_metadata", []))
        self.keyword_check_group.setChecked(self.hotfolder.get("keyword_check_enabled", False))
        self.keyword_edit.setText(self.hotfolder.get("keyword_check_word", ""))
        for layer, cb in self.keyword_layer_checks.items():
            cb.setChecked(layer in self.hotfolder.get("keyword_layers", []))
        for meta, cb in self.keyword_meta_checks.items():
            cb.setChecked(meta in self.hotfolder.get("keyword_metadata", []))
        self.jsx_folder_edit.setText(self.hotfolder.get("jsx_folder", ""))
        self.populate_jsx_combo()
        self.additional_jsx_edit.setText(self.hotfolder.get("additional_jsx", ""))

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    test_config = {
        "id": "1234",
        "name": "TestHotfolder",
        "monitor_dir": "/Pfad/Monitor",
        "success_dir": "/Pfad/Success",
        "fault_dir": "/Pfad/Fault",
        "logfiles_dir": "/Pfad/Logfiles",
        "contentcheck_enabled": True,
        "required_layers": [],
        "required_metadata": [],
        "keyword_check_enabled": False,
        "keyword_check_word": "",
        "keyword_layers": [],
        "keyword_metadata": [],
        "jsx_folder": "",
        "selected_jsx": "",
        "additional_jsx": ""
    }
    dlg = HotfolderConfigDialog(test_config)
    if dlg.exec():
        print("Gespeichert:")
        print(dlg.hotfolder)
    else:
        print("Abgebrochen")