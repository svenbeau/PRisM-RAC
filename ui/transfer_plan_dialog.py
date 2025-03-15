#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print, load_ftp_servers

class TransferPlanDialog(QtWidgets.QDialog):
    def __init__(self, plan_data, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.setWindowTitle("Transferplan konfigurieren")
        self.resize(450, 250)  # Breiteres Default-Fenster

        self.init_ui()
        self.load_plan_data()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        # Plan Name
        self.name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Plan Name:", self.name_edit)

        # Quellordner (lokaler Pfad)
        self.source_btn = QtWidgets.QPushButton("Ordner wählen")
        self.source_btn.clicked.connect(self.pick_source_folder)
        self.source_label = QtWidgets.QLabel("(none)")
        src_hbox = QtWidgets.QHBoxLayout()
        src_hbox.addWidget(self.source_label, 1)
        src_hbox.addWidget(self.source_btn)
        form_layout.addRow("Quellordner:", src_hbox)

        # Checkbox: Über FTP übertragen?
        self.ftp_check = QtWidgets.QCheckBox("Über FTP übertragen")
        self.ftp_check.stateChanged.connect(self.on_ftp_toggled)
        form_layout.addRow("", self.ftp_check)

        # FTP-Server: Combobox (wenn ftp_check aktiv)
        self.ftp_combo = QtWidgets.QComboBox()
        form_layout.addRow("FTP-Server Name:", self.ftp_combo)

        # Zielordner (lokaler Pfad oder Remote-Pfad)
        self.target_btn = QtWidgets.QPushButton("Ordner wählen")
        self.target_btn.clicked.connect(self.pick_target_folder)
        self.target_label = QtWidgets.QLabel("(none)")
        tgt_hbox = QtWidgets.QHBoxLayout()
        tgt_hbox.addWidget(self.target_label, 1)
        tgt_hbox.addWidget(self.target_btn)
        form_layout.addRow("Zielordner:", tgt_hbox)

        # Versionierung
        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.addItems(["mirror", "suffix"])
        form_layout.addRow("Versionierung:", self.version_combo)

        # Suffix (bei suffix)
        self.suffix_edit = QtWidgets.QLineEdit("_v{n}")
        form_layout.addRow("Suffix (bei 'suffix'):", self.suffix_edit)

        # Zeitplan
        self.schedule_combo = QtWidgets.QComboBox()
        self.schedule_combo.addItems(["once", "daily", "weekly"])
        form_layout.addRow("Zeitplan:", self.schedule_combo)

        # Geplanter Zeitpunkt (Datum+Uhrzeit)
        self.datetime_edit = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        form_layout.addRow("Geplanter Zeitpunkt:", self.datetime_edit)

        # Nach Transfer verschieben
        self.move_btn = QtWidgets.QPushButton("Ordner wählen")
        self.move_btn.clicked.connect(self.pick_move_after_folder)
        self.move_label = QtWidgets.QLabel("(none)")
        mv_hbox = QtWidgets.QHBoxLayout()
        mv_hbox.addWidget(self.move_label, 1)
        mv_hbox.addWidget(self.move_btn)
        form_layout.addRow("Nach Transfer verschieben nach:", mv_hbox)

        main_layout.addLayout(form_layout)

        # Buttons OK / Cancel
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(self.ok_btn)

        main_layout.addLayout(btn_layout)

        # FTP-Serverliste laden
        self.load_ftp_servers()

    def load_ftp_servers(self):
        """
        Lädt die Liste der FTP-Server aus ftp_servers.json und befüllt self.ftp_combo.
        """
        servers = load_ftp_servers()
        self.ftp_combo.clear()
        self.ftp_combo.addItem("(none)")  # Index 0 = none
        for srv in servers:
            self.ftp_combo.addItem(srv.get("name", "Unnamed"))
        debug_print(f"TransferPlanDialog: load_ftp_servers => {servers}")

    def load_plan_data(self):
        """
        Befüllt die Felder aus self.plan_data.
        """
        self.name_edit.setText(self.plan_data.get("name", "Neuer Transfer-Plan"))
        src = self.plan_data.get("source_path", "")
        self.source_label.setText(src or "(none)")
        tgt = self.plan_data.get("target_path", "")
        self.target_label.setText(tgt or "(none)")

        use_ftp = self.plan_data.get("use_ftp", False)
        self.ftp_check.setChecked(use_ftp)

        # ftp_server in ComboBox
        ftp_name = self.plan_data.get("ftp_server", "")
        if ftp_name:
            idx = self.ftp_combo.findText(ftp_name)
            if idx >= 0:
                self.ftp_combo.setCurrentIndex(idx)
            else:
                self.ftp_combo.setCurrentIndex(0)  # (none)
        else:
            self.ftp_combo.setCurrentIndex(0)

        version_mode = self.plan_data.get("versioning_mode", "mirror")
        self.version_combo.setCurrentText(version_mode)
        self.suffix_edit.setText(self.plan_data.get("suffix_format", "_v{n}"))

        schedule_type = self.plan_data.get("schedule_type", "once")
        self.schedule_combo.setCurrentText(schedule_type)

        # Zeitstempel
        dt_str = self.plan_data.get("schedule_time", "")
        if dt_str:
            # parse
            dt = QtCore.QDateTime.fromString(dt_str, "yyyy-MM-dd HH:mm")
            if dt.isValid():
                self.datetime_edit.setDateTime(dt)
            else:
                # fallback auf jetzt
                pass

        move_after = self.plan_data.get("move_after", "")
        self.move_label.setText(move_after or "(none)")

        # Check initial ftp state
        self.on_ftp_toggled()

    def on_ok(self):
        """
        Übernimmt die Werte ins self.plan_data und schließt mit Accept.
        """
        debug_print("TransferPlanDialog.on_ok() aufgerufen.")
        self.plan_data["name"] = self.name_edit.text().strip()
        self.plan_data["source_path"] = self.source_label.text()
        if self.plan_data["source_path"] == "(none)":
            self.plan_data["source_path"] = ""

        self.plan_data["target_path"] = self.target_label.text()
        if self.plan_data["target_path"] == "(none)":
            self.plan_data["target_path"] = ""

        self.plan_data["use_ftp"] = self.ftp_check.isChecked()

        # ftp_server
        if self.ftp_check.isChecked():
            ftp_chosen = self.ftp_combo.currentText()
            if ftp_chosen == "(none)":
                # user has not selected a server
                self.plan_data["ftp_server"] = ""
            else:
                self.plan_data["ftp_server"] = ftp_chosen
        else:
            self.plan_data["ftp_server"] = ""

        self.plan_data["versioning_mode"] = self.version_combo.currentText()
        self.plan_data["suffix_format"] = self.suffix_edit.text().strip()
        self.plan_data["schedule_type"] = self.schedule_combo.currentText()

        # Zeitstempel
        dt_obj = self.datetime_edit.dateTime()
        dt_str = dt_obj.toString("yyyy-MM-dd HH:mm")
        self.plan_data["schedule_time"] = dt_str

        move_after_str = self.move_label.text()
        if move_after_str == "(none)":
            move_after_str = ""
        self.plan_data["move_after"] = move_after_str

        debug_print(f"TransferPlanDialog => final plan_data: {self.plan_data}")
        self.accept()

    def pick_source_folder(self):
        """
        Wählt einen Ordner als Quellpfad.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Quellordner wählen")
        if folder:
            self.source_label.setText(folder)

    def pick_target_folder(self):
        """
        Wählt einen Ordner als Zielpfad (wenn kein FTP).
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if folder:
            self.target_label.setText(folder)

    def pick_move_after_folder(self):
        """
        Wählt einen Ordner, in den Dateien nach Transfer verschoben werden sollen.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Nach Transfer verschieben nach...")
        if folder:
            self.move_label.setText(folder)

    def on_ftp_toggled(self):
        """
        Wird aufgerufen, wenn die Checkbox "Über FTP übertragen" an- oder abgewählt wird.
        Deaktiviert/aktiviert das FTP-Combo-Feld entsprechend.
        """
        checked = self.ftp_check.isChecked()
        self.ftp_combo.setEnabled(checked)
        # Wenn abgewählt, könnte man auch target_label disablen, etc.
        # Aber das ist optional je nach gewünschter Logik.
        if not checked:
            # Falls du z.B. den Combo-Index zurücksetzen willst:
            self.ftp_combo.setCurrentIndex(0)