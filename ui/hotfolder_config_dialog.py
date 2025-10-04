#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, QPoint, QSettings
from PySide6.QtWidgets import QApplication

from utils.config_manager import get_recent_dirs, update_recent_dirs
from utils.hotfolder_config_manager import HotfolderConfigManager, debug_print

print(">>> NEUE HOTFOLDERCONFIGDIALOG UI WIRD GELADEN <<<")

class HotfolderConfigDialog(QtWidgets.QDialog):
    """
    Dialog zum Bearbeiten eines einzelnen Hotfolders.
    Jetzt mit ScrollArea, damit die OK/Abbrechen-Buttons auf kleineren Screens
    immer erreichbar bleiben. Merkt sich außerdem Größe/Position per QSettings.
    """
    def __init__(self, hotfolder_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hotfolder Konfiguration")
        self.resize(1200, 800)  # Wunsch-Startgröße

        # QSettings: Geometrie zwischen Sessions merken
        self.settings = QSettings("PRisM-CC", "HotfolderConfigDialog")
        geom = self.settings.value("geom")
        if geom is not None:
            try:
                self.restoreGeometry(geom)
            except Exception as e:
                debug_print(f"[HotfolderConfigDialog] restoreGeometry failed: {e}")

        self.hotfolder = hotfolder_data
        debug_print("HotfolderConfigDialog init: " + str(self.hotfolder))

        self.manager = HotfolderConfigManager()

        self.init_ui()
        self.update_fields_from_hotfolder()

    # ---------- Hilfetexte ----------
    def _keyword_help_text(self) -> str:
        return (
            "Keyword-Logik:\n"
            "• ANY (ODER): Trennzeichen ; , | — mindestens eines muss vorkommen\n"
            "• ALL (UND):  Trennzeichen & + — alle müssen vorkommen\n"
            "• NOT: !Token bedeutet Ausschluss (darf NICHT vorkommen)\n"
            "• AUTO: entscheidet zwischen ANY/ALL anhand der verwendeten Trenner\n"
            "\n"
            "Beispiele:  A;B  |  A,B  |  A|B   (ODER)\n"
            "            A&B  |  A+B            (UND)\n"
            "            !B                     (NICHT)"
        )

    def _show_keyword_tooltip(self):
        # Tooltip an der Unterkante des Keyword-Feldes einblenden
        pt = self.keyword_edit.mapToGlobal(QPoint(0, self.keyword_edit.height()))
        QtWidgets.QToolTip.showText(pt, self._keyword_help_text(), self.keyword_edit)

    def _show_keyword_help_dialog(self):
        # Nicht-modaler Info-Dialog mit gleicher Info
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle("Keyword-Logik – Hilfe")
        msg.setText(self._keyword_help_text())
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.setModal(False)
        msg.show()

    # ---------- UI ----------
    def init_ui(self):
        # ÄUSSERE Struktur: ScrollArea + feste Button-Leiste unten
        outer_layout = QtWidgets.QVBoxLayout(self)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)

        # ------- Hauptformular (im Scrollbereich) -------
        form_layout = QtWidgets.QFormLayout()

        # ID
        self.id_label = QtWidgets.QLabel()
        form_layout.addRow("ID:", self.id_label)

        # Name
        self.name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Name:", self.name_edit)

        # Hauptpfad (LineEdit + Browse)
        self.path_edit = QtWidgets.QLineEdit()
        self.browse_main_btn = QtWidgets.QPushButton("Browse")
        main_path_layout = QtWidgets.QHBoxLayout()
        main_path_layout.addWidget(self.path_edit)
        main_path_layout.addWidget(self.browse_main_btn)
        form_layout.addRow("Hauptpfad:", main_path_layout)

        # 01_Monitor (Dropdown mit Recent-Folders)
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

        # 02_Success (Dropdown mit Recent-Folders)
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

        # NEU: Automatisches Löschen für 02_Success
        self.auto_delete_success_checkbox = QtWidgets.QCheckBox("Auto-Delete aktivieren")
        self.auto_delete_success_spin = QtWidgets.QSpinBox()
        self.auto_delete_success_spin.setRange(1, 24*30)  # 30 Tage
        self.auto_delete_success_spin.setValue(24)
        success_delete_layout = QtWidgets.QHBoxLayout()
        success_delete_layout.addWidget(self.auto_delete_success_checkbox)
        success_delete_layout.addWidget(QtWidgets.QLabel("Stunden:"))
        success_delete_layout.addWidget(self.auto_delete_success_spin)
        form_layout.addRow("Automatisches Löschen 02_Success:", success_delete_layout)
        print(">>> Auto-Delete 02_Success UI-Elemente erstellt")

        # 03_Fault (Dropdown mit Recent-Folders)
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

        # NEU: Automatisches Löschen für 03_Fault
        self.auto_delete_fault_checkbox = QtWidgets.QCheckBox("Auto-Delete aktivieren")
        self.auto_delete_fault_spin = QtWidgets.QSpinBox()
        self.auto_delete_fault_spin.setRange(1, 24*30)
        self.auto_delete_fault_spin.setValue(72)
        fault_delete_layout = QtWidgets.QHBoxLayout()
        fault_delete_layout.addWidget(self.auto_delete_fault_checkbox)
        fault_delete_layout.addWidget(QtWidgets.QLabel("Stunden:"))
        fault_delete_layout.addWidget(self.auto_delete_fault_spin)
        form_layout.addRow("Automatisches Löschen 03_Fault:", fault_delete_layout)
        print(">>> Auto-Delete 03_Fault UI-Elemente erstellt")

        # 04_Logfiles (Dropdown mit Recent-Folders)
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

        # Standard-Contentcheck
        self.standard_contentcheck_group = QtWidgets.QGroupBox("Standard-Contentcheck")
        self.standard_contentcheck_group.setCheckable(True)
        std_layout = QtWidgets.QHBoxLayout(self.standard_contentcheck_group)
        self.layer_checks = {}
        layer_group = QtWidgets.QGroupBox("Erforderliche Ebenen")
        layer_layout = QtWidgets.QVBoxLayout()
        for layer in ["Freisteller", "Messwerte", "Korrektur", "Freisteller_Wand", "Bildausschnitt"]:
            cb = QtWidgets.QCheckBox(layer)
            layer_layout.addWidget(cb)
            self.layer_checks[layer] = cb
        layer_group.setLayout(layer_layout)
        std_layout.addWidget(layer_group)
        self.meta_checks = {}
        meta_group = QtWidgets.QGroupBox("Erforderliche Metadaten")
        meta_layout = QtWidgets.QVBoxLayout()
        for meta in ["author", "description", "keywords", "headline"]:
            cb = QtWidgets.QCheckBox(meta)
            meta_layout.addWidget(cb)
            self.meta_checks[meta] = cb
        meta_group.setLayout(meta_layout)
        std_layout.addWidget(meta_group)

        # alles ins Scroll-Formular schieben
        scroll_layout.addLayout(form_layout)
        scroll_layout.addWidget(self.standard_contentcheck_group)

        # Keyword-basierter Contentcheck
        self.keyword_check_group = QtWidgets.QGroupBox("Keyword-basierter Contentcheck")
        self.keyword_check_group.setCheckable(True)
        kw_vlayout = QtWidgets.QVBoxLayout(self.keyword_check_group)

        # Top-Zeile: Keyword + Logik + Info
        kw_hlayout_top = QtWidgets.QHBoxLayout()
        self.kw_label = QtWidgets.QLabel("Keyword:")
        kw_hlayout_top.addWidget(self.kw_label)
        self.keyword_edit = QtWidgets.QLineEdit()

        placeholder = (
            'Beispiele: "Rueckseite;Back" (ODER) · "Rueckseite&Signatur" (UND) · '
            '"!Preview" (Ausschluss). Logik via Dropdown "Keyword-Logik".'
        )
        self.keyword_edit.setPlaceholderText(placeholder)
        hint = self._keyword_help_text()
        self.kw_label.setToolTip(hint)
        self.keyword_edit.setToolTip(hint)

        kw_hlayout_top.addWidget(self.keyword_edit)

        self.kw_logic_label = QtWidgets.QLabel("Keyword-Logik:")
        self.kw_logic = QtWidgets.QComboBox()
        self.kw_logic.addItems(["AUTO", "ANY", "ALL"])
        self.kw_logic.setToolTip("AUTO = per Trenner entscheiden (siehe Hilfe)")
        kw_hlayout_top.addWidget(self.kw_logic_label)
        kw_hlayout_top.addWidget(self.kw_logic)

        # Info-Button (ℹ️)
        self.kw_info_btn = QtWidgets.QToolButton()
        self.kw_info_btn.setAutoRaise(True)
        self.kw_info_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))
        self.kw_info_btn.setToolTip("Hilfe zur Keyword-Logik anzeigen")
        self.kw_info_btn.clicked.connect(self._show_keyword_help_dialog)
        kw_hlayout_top.addWidget(self.kw_info_btn)

        kw_vlayout.addLayout(kw_hlayout_top)

        # Untere Zeile: Checkbox-Gruppen
        kw_hlayout_bottom = QtWidgets.QHBoxLayout()
        self.keyword_layer_checks = {}
        kw_layer_group = QtWidgets.QGroupBox("Erforderliche Ebenen (Keyword)")
        kw_layer_layout = QtWidgets.QVBoxLayout()
        for layer in ["Freisteller", "Messwerte", "Korrektur", "Freisteller_Wand", "Bildausschnitt"]:
            cb = QtWidgets.QCheckBox(layer)
            kw_layer_layout.addWidget(cb)
            self.keyword_layer_checks[layer] = cb
        kw_layer_group.setLayout(kw_layer_layout)
        kw_hlayout_bottom.addWidget(kw_layer_group)

        self.keyword_meta_checks = {}
        kw_meta_group = QtWidgets.QGroupBox("Erforderliche Metadaten (Keyword)")
        kw_meta_layout = QtWidgets.QVBoxLayout()
        for meta in ["author", "description", "keywords", "headline"]:
            cb = QtWidgets.QCheckBox(meta)
            kw_meta_layout.addWidget(cb)
            self.keyword_meta_checks[meta] = cb
        kw_meta_group.setLayout(kw_meta_layout)
        kw_hlayout_bottom.addWidget(kw_meta_group)

        kw_vlayout.addLayout(kw_hlayout_bottom)

        # Keyword-Gruppe in den Scrollbereich
        scroll_layout.addWidget(self.keyword_check_group)

        # JSX Folder
        jsx_folder_layout = QtWidgets.QHBoxLayout()
        self.jsx_folder_edit = QtWidgets.QLineEdit()
        self.browse_jsx_folder_btn = QtWidgets.QPushButton("Browse Folder")
        jsx_folder_layout.addWidget(QtWidgets.QLabel("JSX Folder:"))
        jsx_folder_layout.addWidget(self.jsx_folder_edit)
        jsx_folder_layout.addWidget(self.browse_jsx_folder_btn)
        scroll_layout.addLayout(jsx_folder_layout)

        # JSX Combo
        jsx_combo_layout = QtWidgets.QHBoxLayout()
        self.jsx_combo = QtWidgets.QComboBox()
        self.jsx_combo.setEditable(True)
        jsx_combo_layout.addWidget(QtWidgets.QLabel("JSX-Script Auswahl:"))
        jsx_combo_layout.addWidget(self.jsx_combo)
        scroll_layout.addLayout(jsx_combo_layout)

        # Zusätzliches JSX
        add_jsx_layout = QtWidgets.QHBoxLayout()
        self.additional_jsx_edit = QtWidgets.QLineEdit()
        self.jsx_browse_btn = QtWidgets.QPushButton("JSX durchsuchen")
        add_jsx_layout.addWidget(QtWidgets.QLabel("Zusätzliches JSX:"))
        add_jsx_layout.addWidget(self.additional_jsx_edit)
        add_jsx_layout.addWidget(self.jsx_browse_btn)
        scroll_layout.addLayout(add_jsx_layout)

        # ScrollArea fertig einhängen
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        # Buttons unten FIX
        btn_save_load_layout = QtWidgets.QHBoxLayout()
        self.btn_save_config = QtWidgets.QPushButton("Konfiguration speichern")
        self.btn_load_config = QtWidgets.QPushButton("Konfiguration laden")
        btn_save_load_layout.addWidget(self.btn_save_config)
        btn_save_load_layout.addWidget(self.btn_load_config)
        btn_save_load_layout.addStretch()
        outer_layout.addLayout(btn_save_load_layout)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        outer_layout.addWidget(btn_box)

        # Signals
        btn_box.accepted.connect(self.save_and_close)
        btn_box.rejected.connect(self.reject)
        self.browse_main_btn.clicked.connect(self.browse_main_path)
        self.browse_monitor_btn.clicked.connect(lambda: self.browse_folder(self.monitor_combo))
        self.browse_success_btn.clicked.connect(lambda: self.browse_folder(self.success_combo))
        self.browse_fault_btn.clicked.connect(lambda: self.browse_folder(self.fault_combo))
        self.browse_logfiles_btn.clicked.connect(lambda: self.browse_folder(self.logfiles_combo))
        self.browse_jsx_folder_btn.clicked.connect(self.browse_jsx_folder)
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_file)
        self.btn_save_config.clicked.connect(self.save_configuration_to_file)
        self.btn_load_config.clicked.connect(self.load_configuration_from_file)

        # Tooltip automatisch zeigen, wenn die Gruppe aktiviert wird
        self.keyword_check_group.toggled.connect(self.on_keyword_group_toggled)

    def on_keyword_group_toggled(self, enabled: bool):
        # Controls sind nur informativ; Tooltip nur zeigen, wenn aktiv (=nicht disabled)
        if enabled:
            # kurze Verzögerung, damit Layout fertig ist und Position stimmt
            QtCore.QTimer.singleShot(150, self._show_keyword_tooltip)

    def update_fields_from_hotfolder(self):
        self.id_label.setText(self.hotfolder.get("id", "NO-ID"))
        self.name_edit.setText(self.hotfolder.get("name", "Neuer Hotfolder"))
        self.path_edit.setText(self.hotfolder.get("path", ""))
        self.monitor_combo.setCurrentText(self.hotfolder.get("monitor_dir", ""))
        self.success_combo.setCurrentText(self.hotfolder.get("success_dir", ""))
        # Auto-Delete 02_Success
        self.auto_delete_success_checkbox.setChecked(self.hotfolder.get("auto_delete_success_enabled", False))
        self.auto_delete_success_spin.setValue(self.hotfolder.get("auto_delete_success_hours", 24))
        self.fault_combo.setCurrentText(self.hotfolder.get("fault_dir", ""))
        # Auto-Delete 03_Fault
        self.auto_delete_fault_checkbox.setChecked(self.hotfolder.get("auto_delete_fault_enabled", False))
        self.auto_delete_fault_spin.setValue(self.hotfolder.get("auto_delete_fault_hours", 72))
        self.logfiles_combo.setCurrentText(self.hotfolder.get("logfiles_dir", ""))

        self.standard_contentcheck_group.setChecked(self.hotfolder.get("contentcheck_enabled", True))
        required_layers = self.hotfolder.get("required_layers", [])
        for layer, cb in self.layer_checks.items():
            cb.setChecked(layer in required_layers)
        required_metadata = self.hotfolder.get("required_metadata", [])
        for meta, cb in self.meta_checks.items():
            cb.setChecked(meta in required_metadata)

        self.keyword_check_group.setChecked(self.hotfolder.get("keyword_check_enabled", False))
        self.keyword_edit.setText(self.hotfolder.get("keyword_check_word", ""))
        # Keyword-Logik (Default AUTO)
        self.kw_logic.setCurrentText(self.hotfolder.get("keyword_logic", "AUTO"))
        kw_layers = self.hotfolder.get("keyword_layers", [])
        for layer, cb in self.keyword_layer_checks.items():
            cb.setChecked(layer in kw_layers)
        kw_meta = self.hotfolder.get("keyword_metadata", [])
        for meta, cb in self.keyword_meta_checks.items():
            cb.setChecked(meta in kw_meta)

        self.jsx_folder_edit.setText(self.hotfolder.get("jsx_folder", ""))
        self.populate_jsx_combo()
        self.additional_jsx_edit.setText(self.hotfolder.get("additional_jsx", ""))

    def populate_jsx_combo(self):
        self.jsx_combo.clear()
        folder = self.hotfolder.get("jsx_folder", "")
        if folder and os.path.isdir(folder):
            for filename in os.listdir(folder):
                if filename.lower().endswith(".jsx"):
                    self.jsx_combo.addItem(filename)
        selected_jsx_path = self.hotfolder.get("selected_jsx", "")
        if selected_jsx_path:
            base_script = os.path.basename(selected_jsx_path)
            idx = self.jsx_combo.findText(base_script)
            if idx >= 0:
                self.jsx_combo.setCurrentIndex(idx)

    def browse_main_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle Hauptpfad", os.path.expanduser("~"))
        if folder:
            self.path_edit.setText(folder)
            self.monitor_combo.setCurrentText(os.path.join(folder, "01_Monitor"))
            self.success_combo.setCurrentText(os.path.join(folder, "02_Success"))
            self.fault_combo.setCurrentText(os.path.join(folder, "03_Fault"))
            self.logfiles_combo.setCurrentText(os.path.join(folder, "04_Logfiles"))

    def browse_folder(self, combo_widget):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner wählen", os.path.expanduser("~"))
        if folder:
            combo_widget.setCurrentText(folder)
            # Update recent folders
            if combo_widget == self.monitor_combo:
                update_recent_dirs("monitor", folder)
            elif combo_widget == self.success_combo:
                update_recent_dirs("success", folder)
            elif combo_widget == self.fault_combo:
                update_recent_dirs("fault", folder)
            elif combo_widget == self.logfiles_combo:
                update_recent_dirs("logfiles", folder)

    def browse_jsx_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wähle JSX Folder", os.path.expanduser("~"))
        if folder:
            self.jsx_folder_edit.setText(folder)
            self.hotfolder["jsx_folder"] = folder
            self.populate_jsx_combo()

    def browse_jsx_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Wähle JSX-Skript", os.path.expanduser("~"),
            "JSX Files (*.jsx);;Alle Dateien (*)"
        )
        if file_path:
            self.additional_jsx_edit.setText(file_path)

    # --- Settings sichern ---
    def _save_geometry(self):
        try:
            self.settings.setValue("geom", self.saveGeometry())
        except Exception as e:
            debug_print(f"[HotfolderConfigDialog] saveGeometry failed: {e}")

    # --- Werte AUS UI -> hotfolder dict ---
    def update_hotfolder_from_fields(self):
        self.hotfolder["id"] = self.id_label.text()
        self.hotfolder["name"] = self.name_edit.text()
        self.hotfolder["path"] = self.path_edit.text()

        self.hotfolder["monitor_dir"] = self.monitor_combo.currentText()
        self.hotfolder["success_dir"] = self.success_combo.currentText()
        self.hotfolder["fault_dir"] = self.fault_combo.currentText()
        self.hotfolder["logfiles_dir"] = self.logfiles_combo.currentText()

        self.hotfolder["auto_delete_success_enabled"] = self.auto_delete_success_checkbox.isChecked()
        self.hotfolder["auto_delete_success_hours"] = self.auto_delete_success_spin.value()
        self.hotfolder["auto_delete_fault_enabled"] = self.auto_delete_fault_checkbox.isChecked()
        self.hotfolder["auto_delete_fault_hours"] = self.auto_delete_fault_spin.value()

        self.hotfolder["contentcheck_enabled"] = self.standard_contentcheck_group.isChecked()
        self.hotfolder["required_layers"] = [layer for layer, cb in self.layer_checks.items() if cb.isChecked()]
        self.hotfolder["required_metadata"] = [meta for meta, cb in self.meta_checks.items() if cb.isChecked()]

        self.hotfolder["keyword_check_enabled"] = self.keyword_check_group.isChecked()
        self.hotfolder["keyword_check_word"] = self.keyword_edit.text()
        self.hotfolder["keyword_logic"] = self.kw_logic.currentText()  # speichere Logik
        self.hotfolder["keyword_layers"] = [layer for layer, cb in self.keyword_layer_checks.items() if cb.isChecked()]
        self.hotfolder["keyword_metadata"] = [meta for meta, cb in self.keyword_meta_checks.items() if cb.isChecked()]

        self.hotfolder["jsx_folder"] = self.jsx_folder_edit.text()
        selected_script = self.jsx_combo.currentText().strip()
        if selected_script and selected_script != "(none)":
            self.hotfolder["selected_jsx"] = os.path.join(self.hotfolder["jsx_folder"], selected_script)
        else:
            self.hotfolder["selected_jsx"] = ""
        self.hotfolder["additional_jsx"] = self.additional_jsx_edit.text().strip()

    def save_and_close(self):
        self.update_hotfolder_from_fields()
        if not self.hotfolder.get("id"):
            new_id = self.manager.generate_hotfolder_id()
            self.hotfolder["id"] = new_id
        existing = self.manager.get_hotfolder_by_id(self.hotfolder["id"])
        if existing:
            debug_print(f"Update Hotfolder mit ID {self.hotfolder['id']}")
            self.manager.update_hotfolder(self.hotfolder["id"], self.hotfolder)
        else:
            debug_print("Neuer Hotfolder, füge hinzu...")
            self.manager.add_hotfolder(self.hotfolder)
        # Geometrie sichern vor dem Schließen
        self._save_geometry()
        self.accept()

    def reject(self):
        # Auch beim Abbrechen Geometrie sichern
        self._save_geometry()
        super().reject()

    def save_configuration_to_file(self):
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
                    json.dump(self.hotfolder, f, indent=4, ensure_ascii=False)
                QtWidgets.QMessageBox.information(self, "Erfolg", "Konfiguration erfolgreich gespeichert.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {e}")

    def load_configuration_from_file(self):
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
        "required_layers": ["Freisteller", "Messwerte"],
        "required_metadata": ["author", "description"],
        "keyword_check_enabled": True,
        "keyword_check_word": "Rueckseite",
        "keyword_logic": "AUTO",
        "keyword_layers": ["Freisteller"],
        "keyword_metadata": ["author", "description"],
        "jsx_folder": "",
        "selected_jsx": "",
        "additional_jsx": "",
        # Auto-Delete
        "auto_delete_success_enabled": False,
        "auto_delete_success_hours": 24,
        "auto_delete_fault_enabled": False,
        "auto_delete_fault_hours": 72,
        "body_visible": True
    }
    dlg = HotfolderConfigDialog(test_config)
    if dlg.exec():
        print("Gespeichert:")
        print(dlg.hotfolder)
    else:
        print("Abgebrochen")