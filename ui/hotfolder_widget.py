#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtCore, QtGui, QtWidgets
from hotfolder_monitor import HotfolderMonitor, debug_print

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class HotfolderWidget(QtWidgets.QFrame):
    """
    Zeigt die Konfiguration und den Status eines einzelnen Hotfolders
    mit vier Überschriften untereinander:
      1) Ordner
      2) Bearbeitung
      3) Contentcheck
      4) Status

    - Spinner: 20×20 px
    - Bei inaktivem Hotfolder: Spinner komplett ausgeblendet
    - Bei aktivem Hotfolder ohne Verarbeitung: Spinner 30% Deckkraft
    - Bei Datei-Verarbeitung: Spinner 100% Deckkraft
    """

    def __init__(self, hotfolder_config: dict, parent=None):
        super().__init__(parent)
        self.hotfolder_config = hotfolder_config
        self.monitor = None
        self.active = False
        self.current_file = None
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

        # 1) Ordner
        ordner_group = QtWidgets.QGroupBox("Ordner")
        ordner_layout = QtWidgets.QVBoxLayout(ordner_group)

        monitor_path = self.hotfolder_config.get("monitor_dir", "01_Monitor")
        self.monitor_label = QtWidgets.QLabel(f"Monitor: {monitor_path}")
        ordner_layout.addWidget(self.monitor_label)

        success_path = self.hotfolder_config.get("success_dir", "02_Success")
        self.success_label = QtWidgets.QLabel(f"Success: {success_path}")
        ordner_layout.addWidget(self.success_label)

        fault_path = self.hotfolder_config.get("fault_dir", "03_Fault")
        self.fault_label = QtWidgets.QLabel(f"Fault: {fault_path}")
        ordner_layout.addWidget(self.fault_label)

        logfiles_path = self.hotfolder_config.get("logfiles_dir", "04_Logfiles")
        self.logfiles_label = QtWidgets.QLabel(f"Logfiles: {logfiles_path}")
        ordner_layout.addWidget(self.logfiles_label)

        main_layout.addWidget(ordner_group)

        # 2) Bearbeitung
        bearbeitung_group = QtWidgets.QGroupBox("Bearbeitung")
        bearbeitung_layout = QtWidgets.QVBoxLayout(bearbeitung_group)

        additional_jsx = self.hotfolder_config.get("additional_jsx", "")
        self.jsx_label = QtWidgets.QLabel(f"JSX-Script: {additional_jsx}")
        bearbeitung_layout.addWidget(self.jsx_label)

        main_layout.addWidget(bearbeitung_group)

        # 3) Contentcheck
        contentcheck_group = QtWidgets.QGroupBox("Contentcheck")
        contentcheck_layout = QtWidgets.QVBoxLayout(contentcheck_group)

        req_layers = ", ".join(self.hotfolder_config.get("required_layers", []))
        self.layers_label = QtWidgets.QLabel(f"Ebenen: {req_layers}")
        contentcheck_layout.addWidget(self.layers_label)

        req_meta = ", ".join(self.hotfolder_config.get("required_metadata", []))
        self.metadata_label = QtWidgets.QLabel(f"Metadaten: {req_meta}")
        contentcheck_layout.addWidget(self.metadata_label)

        main_layout.addWidget(contentcheck_group)

        # 4) Status
        status_group = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QHBoxLayout(status_group)

        # Label "Aktuell:" + Status (Aktiv/Inaktiv)
        status_layout.addWidget(QtWidgets.QLabel("Aktuell:"))
        self.status_label = QtWidgets.QLabel("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        status_layout.addWidget(self.status_label)

        # Spinner: 20×20 px
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
            # Hotfolder ist initial inaktiv -> spinner ausblenden
            self.spinner_label.setVisible(False)
        else:
            self.spinner_label.setText("Spinner?")

        status_layout.addWidget(self.spinner_label)

        # Buttons: Start/Stop, Edit
        self.start_stop_btn = QtWidgets.QPushButton("Start")
        self.start_stop_btn.clicked.connect(self.on_start_stop)
        status_layout.addWidget(self.start_stop_btn)

        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit)
        status_layout.addWidget(self.edit_btn)

        main_layout.addWidget(status_group)

    def on_start_stop(self):
        if not self.monitor or not self.monitor.active:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        debug_print(f"Starte Monitor für: {self.hotfolder_config.get('name','?')}")
        from hotfolder_monitor import HotfolderMonitor
        self.monitor = HotfolderMonitor(
            hf_config=self.hotfolder_config,
            on_status_update=self.on_status_update,
            on_file_processing=self.on_file_processing
        )
        self.monitor.start()
        self.start_stop_btn.setText("Stop")
        self.status_label.setText("Aktiv")
        self.status_label.setStyleSheet("color: green;")

        # Hotfolder aktiv -> Spinner anzeigen, aber noch keine Datei -> 30% Deckkraft
        if self.spinner_movie:
            self.spinner_label.setVisible(True)
            self.spinner_label.setStyleSheet("opacity: 0.3;")

    def stop_monitor(self):
        if self.monitor:
            debug_print(f"Stoppe Monitor für: {self.hotfolder_config.get('name','?')}")
            self.monitor.stop()
            self.monitor = None
        self.start_stop_btn.setText("Start")
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")

        # Hotfolder inaktiv -> Spinner komplett ausblenden
        if self.spinner_movie:
            self.spinner_label.setVisible(False)

    def on_status_update(self, status_text: str, is_active: bool):
        if is_active:
            self.status_label.setText("Aktiv")
            self.status_label.setStyleSheet("color: green;")
            # Spinner anzeigen, 30% Deckkraft (falls keine Datei)
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 0.3;")
        else:
            self.status_label.setText("Inaktiv")
            self.status_label.setStyleSheet("color: red;")
            # Spinner ausblenden
            if self.spinner_movie:
                self.spinner_label.setVisible(False)

    def on_file_processing(self, filename: str):
        if filename:
            # Datei wird verarbeitet -> Spinner 100% Deckkraft
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 1.0;")
            self.status_label.setText(f"Aktiv (Verarbeite: {filename})")
            self.status_label.setStyleSheet("color: green;")
        else:
            # Keine Datei -> Spinner 30% Deckkraft, falls Monitor aktiv
            if self.monitor and self.monitor.active:
                if self.spinner_movie:
                    self.spinner_label.setVisible(True)
                    self.spinner_label.setStyleSheet("opacity: 0.3;")
                self.status_label.setText("Aktiv")
                self.status_label.setStyleSheet("color: green;")
            else:
                # Falls Monitor gar nicht aktiv
                self.spinner_label.setVisible(False)
                self.status_label.setText("Inaktiv")
                self.status_label.setStyleSheet("color: red;")

    def on_edit(self):
        from ui.hotfolder_config import HotfolderConfigDialog
        dlg = HotfolderConfigDialog(self.hotfolder_config, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            debug_print("Hotfolder geändert, reload.")
            from config.config_manager import save_config, load_config
            save_config(load_config())  # Evtl. anpassen
            self.update_labels()

    def update_labels(self):
        # Titel
        self.title_label.setText(self.hotfolder_config.get("name", "Unbenannt"))

        # Ordner
        monitor_path = self.hotfolder_config.get("monitor_dir", "01_Monitor")
        self.monitor_label.setText(f"Monitor: {monitor_path}")

        success_path = self.hotfolder_config.get("success_dir", "02_Success")
        self.success_label.setText(f"Success: {success_path}")

        fault_path = self.hotfolder_config.get("fault_dir", "03_Fault")
        self.fault_label.setText(f"Fault: {fault_path}")

        logfiles_path = self.hotfolder_config.get("logfiles_dir", "04_Logfiles")
        self.logfiles_label.setText(f"Logfiles: {logfiles_path}")

        # Bearbeitung
        additional_jsx = self.hotfolder_config.get("additional_jsx", "")
        self.jsx_label.setText(f"JSX-Script: {additional_jsx}")

        # Contentcheck
        req_layers = ", ".join(self.hotfolder_config.get("required_layers", []))
        self.layers_label.setText(f"Ebenen: {req_layers}")

        req_meta = ", ".join(self.hotfolder_config.get("required_metadata", []))
        self.metadata_label.setText(f"Metadaten: {req_meta}")

        # Status zurücksetzen
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        self.start_stop_btn.setText("Start")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)  # bei inaktivem HF