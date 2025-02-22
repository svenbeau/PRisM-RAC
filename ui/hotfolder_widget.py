#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import save_settings, load_settings, debug_print
from ui.hotfolder_config import HotfolderConfigDialog
from hotfolder_monitor import HotfolderMonitor

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class HotfolderListWidget(QtWidgets.QWidget):
    """
    Zeigt alle Hotfolder in einer Liste (ScrollArea).
    Buttons oben: "Hotfolder hinzufügen" und "Hotfolder entfernen".
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Hotfolder hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Hotfolder entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.hf_container = QtWidgets.QWidget()
        self.hf_layout = QtWidgets.QVBoxLayout(self.hf_container)
        self.hf_layout.setContentsMargins(5, 5, 5, 5)
        self.hf_layout.setSpacing(10)

        self.scroll_area.setWidget(self.hf_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.add_btn.clicked.connect(self.add_hotfolder)
        self.del_btn.clicked.connect(self.delete_hotfolder)

        self.load_hotfolders()

    def load_hotfolders(self):
        debug_print("HotfolderListWidget.load_hotfolders() aufgerufen.")
        for i in reversed(range(self.hf_layout.count())):
            item = self.hf_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        hotfolders = self.settings.setdefault("hotfolders", [])
        debug_print(f"load_hotfolders: hotfolders={hotfolders}")
        for hf_data in hotfolders:
            widget = HotfolderWidget(hf_data, self.settings, parent=self.hf_container)
            self.hf_layout.addWidget(widget)

        self.hf_layout.addStretch()

    def add_hotfolder(self):
        import uuid
        new_id = str(uuid.uuid4())
        new_hf = {
            "id": new_id,
            "name": "Neuer Hotfolder",
            "path": "",
            "monitor_dir": "",
            "success_dir": "",
            "fault_dir": "",
            "logfiles_dir": "",
            "contentcheck_enabled": True,
            "required_layers": [],
            "required_metadata": [],
            "keyword_check_enabled": False,
            "keyword_check_word": "Rueckseite",
            "keyword_layers": [],
            "keyword_metadata": [],
            "jsx_folder": "",
            "additional_jsx": ""
        }
        self.settings.setdefault("hotfolders", []).append(new_hf)
        save_settings(self.settings)
        self.load_hotfolders()

    def delete_hotfolder(self):
        hotfolders = self.settings.setdefault("hotfolders", [])
        if not hotfolders:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Hotfolder vorhanden.")
            return
        idx, ok = QtWidgets.QInputDialog.getInt(self, "Hotfolder entfernen", "Index (1-basiert):", 1, 1, len(hotfolders))
        if ok:
            real_idx = idx - 1
            if 0 <= real_idx < len(hotfolders):
                del hotfolders[real_idx]
                save_settings(self.settings)
                self.load_hotfolders()

class HotfolderWidget(QtWidgets.QFrame):
    """
    Zeigt die Konfiguration (Ordner, Bearbeitung, Contentcheck) und den Status (Start/Stop, Spinner, Edit)
    für einen einzelnen Hotfolder an.
    """
    def __init__(self, hotfolder_config: dict, settings: dict, parent=None):
        super().__init__(parent)
        self.hotfolder_config = hotfolder_config
        self.settings = settings
        self.monitor = None
        self.setupUi()

    def setupUi(self):
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Titel
        self.title_label = QtWidgets.QLabel(self.hotfolder_config.get("name", "Unbenannt"))
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.title_label.setFont(font)
        main_layout.addWidget(self.title_label)

        # Ordner
        ordner_group = QtWidgets.QGroupBox("Ordner")
        ordner_layout = QtWidgets.QVBoxLayout(ordner_group)
        self.monitor_label = QtWidgets.QLabel(f"Monitor: {self.hotfolder_config.get('monitor_dir','')}")
        ordner_layout.addWidget(self.monitor_label)
        self.success_label = QtWidgets.QLabel(f"Success: {self.hotfolder_config.get('success_dir','')}")
        ordner_layout.addWidget(self.success_label)
        self.fault_label = QtWidgets.QLabel(f"Fault: {self.hotfolder_config.get('fault_dir','')}")
        ordner_layout.addWidget(self.fault_label)
        self.logfiles_label = QtWidgets.QLabel(f"Logfiles: {self.hotfolder_config.get('logfiles_dir','')}")
        ordner_layout.addWidget(self.logfiles_label)
        main_layout.addWidget(ordner_group)

        # Bearbeitung
        bearbeitung_group = QtWidgets.QGroupBox("Bearbeitung")
        bearbeitung_layout = QtWidgets.QVBoxLayout(bearbeitung_group)
        folder = self.hotfolder_config.get("jsx_folder", "")
        bearbeitung_layout.addWidget(QtWidgets.QLabel(f"JSX-Folder: {folder}"))
        script_choice = os.path.basename(self.hotfolder_config.get("additional_jsx", "")) or "(none)"
        self.jsx_label = QtWidgets.QLabel(f"JSX-Script: {script_choice}")
        bearbeitung_layout.addWidget(self.jsx_label)
        main_layout.addWidget(bearbeitung_group)

        # Contentcheck – dynamisch aktualisierbare Labels
        self.content_group = QtWidgets.QGroupBox("Contentcheck")
        self.content_layout = QtWidgets.QVBoxLayout(self.content_group)

        # Platzhalter-Labels für Standard-Contentcheck
        self.std_layers_label = QtWidgets.QLabel("")
        self.std_meta_label   = QtWidgets.QLabel("")
        self.content_layout.addWidget(self.std_layers_label)
        self.content_layout.addWidget(self.std_meta_label)

        # Platzhalter-Labels für Keyword-Contentcheck
        self.kw_layers_label = QtWidgets.QLabel("")
        self.kw_meta_label   = QtWidgets.QLabel("")
        self.content_layout.addWidget(self.kw_layers_label)
        self.content_layout.addWidget(self.kw_meta_label)

        main_layout.addWidget(self.content_group)

        # Status
        status_group = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QHBoxLayout(status_group)
        self.status_label = QtWidgets.QLabel("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        status_layout.addWidget(QtWidgets.QLabel("Aktuell:"))
        status_layout.addWidget(self.status_label)

        self.spinner_label = QtWidgets.QLabel()
        self.spinner_label.setFixedSize(20, 20)
        self.spinner_label.setScaledContents(True)
        spinner_path = os.path.join("assets", "spinner.gif")
        self.spinner_movie = None
        if os.path.exists(spinner_path):
            self.spinner_movie = QtGui.QMovie(spinner_path)
            self.spinner_movie.setScaledSize(QtCore.QSize(20, 20))
            self.spinner_label.setMovie(self.spinner_movie)
            self.spinner_movie.start()
            self.spinner_label.setVisible(False)
        else:
            self.spinner_label.setText("Spinner?")
        status_layout.addWidget(self.spinner_label)

        self.start_stop_btn = QtWidgets.QPushButton("Start")
        self.start_stop_btn.clicked.connect(self.on_start_stop)
        status_layout.addWidget(self.start_stop_btn)

        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit)
        status_layout.addWidget(self.edit_btn)

        main_layout.addWidget(status_group)

        # Einmalige Initialisierung der Labels
        self.update_labels()

    def on_start_stop(self):
        if not self.monitor or not self.monitor.active:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        debug_print(f"Starte Monitor für: {self.hotfolder_config.get('name','?')} (ID={self.hotfolder_config.get('id','??')})")
        self.monitor = HotfolderMonitor(
            hf_config=self.hotfolder_config,
            on_status_update=self.on_status_update,
            on_file_processing=self.on_file_processing
        )
        self.monitor.start()
        self.start_stop_btn.setText("Stop")
        self.status_label.setText("Aktiv")
        self.status_label.setStyleSheet("color: green;")
        if self.spinner_movie:
            self.spinner_label.setVisible(True)
            self.spinner_label.setStyleSheet("opacity: 0.3;")

    def stop_monitor(self):
        if self.monitor:
            debug_print(f"Stoppe Monitor für: {self.hotfolder_config.get('name','?')} (ID={self.hotfolder_config.get('id','??')})")
            self.monitor.stop()
            self.monitor = None
        self.start_stop_btn.setText("Start")
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)

    def on_status_update(self, status_text: str, is_active: bool):
        if is_active:
            self.status_label.setText("Aktiv")
            self.status_label.setStyleSheet("color: green;")
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 0.3;")
        else:
            self.status_label.setText("Inaktiv")
            self.status_label.setStyleSheet("color: red;")
            if self.spinner_movie:
                self.spinner_label.setVisible(False)

    def on_file_processing(self, filename: str):
        import os
        if filename:
            short_filename = os.path.basename(filename)
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 1.0;")
            self.status_label.setText(f"Aktiv (Verarbeite: {short_filename})")
            self.status_label.setStyleSheet("color: green;")
        else:
            if self.monitor and self.monitor.active:
                if self.spinner_movie:
                    self.spinner_label.setVisible(True)
                    self.spinner_label.setStyleSheet("opacity: 0.3;")
                self.status_label.setText("Aktiv")
                self.status_label.setStyleSheet("color: green;")
            else:
                if self.spinner_movie:
                    self.spinner_label.setVisible(False)
                self.status_label.setText("Inaktiv")
                self.status_label.setStyleSheet("color: red;")

    def on_edit(self):
        dlg = HotfolderConfigDialog(self.hotfolder_config, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            debug_print("Hotfolder geändert, reload.")
            save_settings(self.settings)
            self.settings = load_settings()
            self.update_labels()
            parent_widget = self.parent()
            if parent_widget and hasattr(parent_widget, "load_hotfolders"):
                debug_print("Rufe parent_widget.load_hotfolders() auf, um das gesamte UI zu aktualisieren.")
                parent_widget.load_hotfolders()
        else:
            debug_print("Hotfolder-Konfiguration Dialog abgebrochen.")

    def update_labels(self):
        debug_print("Aktualisiere HotfolderWidget-Labels.")
        self.title_label.setText(self.hotfolder_config.get("name", "Unbenannt"))
        debug_print("Name aktualisiert: " + self.hotfolder_config.get("name", "Unbenannt"))

        self.monitor_label.setText(f"Monitor: {self.hotfolder_config.get('monitor_dir','')}")
        self.success_label.setText(f"Success: {self.hotfolder_config.get('success_dir','')}")
        self.fault_label.setText(f"Fault: {self.hotfolder_config.get('fault_dir','')}")
        self.logfiles_label.setText(f"Logfiles: {self.hotfolder_config.get('logfiles_dir','')}")

        folder = self.hotfolder_config.get("jsx_folder", "")
        script_choice = os.path.basename(self.hotfolder_config.get("additional_jsx", "")) or "(none)"
        self.jsx_label.setText(f"JSX-Script: {script_choice}")

        # Standard Contentcheck – aktualisiere die Labels
        std_layers = ", ".join(self.hotfolder_config.get("required_layers", []))
        std_meta   = ", ".join(self.hotfolder_config.get("required_metadata", []))
        self.std_layers_label.setText(f"Standard Ebenen: {std_layers}")
        self.std_meta_label.setText(f"Standard Metadaten: {std_meta}")
        debug_print("Standard Contentcheck - Ebenen: " + std_layers)
        debug_print("Standard Contentcheck - Metadaten: " + std_meta)

        # Keyword Contentcheck – aktualisiere die Labels
        if self.hotfolder_config.get("keyword_check_enabled", False):
            kw = self.hotfolder_config.get("keyword_check_word", "Rueckseite")
            kw_layers = ", ".join(self.hotfolder_config.get("keyword_layers", []))
            kw_meta   = ", ".join(self.hotfolder_config.get("keyword_metadata", []))
            self.kw_layers_label.setText(f"Keyword '{kw}' Ebenen: {kw_layers}")
            self.kw_meta_label.setText(f"Keyword '{kw}' Metadaten: {kw_meta}")
            debug_print("Keyword Contentcheck - Keyword: " + kw)
            debug_print("Keyword Contentcheck - Ebenen: " + kw_layers)
            debug_print("Keyword Contentcheck - Metadaten: " + kw_meta)
        else:
            self.kw_layers_label.setText("")
            self.kw_meta_label.setText("")

        # Status zurücksetzen
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        self.start_stop_btn.setText("Start")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)