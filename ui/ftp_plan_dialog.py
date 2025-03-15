#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print
from utils.transfer_plan_manager import TransferPlanManager

class TransferPlanDialog(QtWidgets.QDialog):
    """
    Entspricht dem ScriptRecipeDialog. Öffnet ein kleines Fenster,
    um die Felder eines TransferPlans zu bearbeiten.
    """

    def __init__(self, plan_data, manager: TransferPlanManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Transfer-Plan")
        self.resize(500, 400)
        self.plan_data = plan_data
        self.manager = manager

        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()
        layout.addLayout(form_layout)

        # Name
        self.name_edit = QtWidgets.QLineEdit(self.plan_data.get("name",""))
        form_layout.addRow("Name:", self.name_edit)

        # Source
        self.source_edit = QtWidgets.QLineEdit(self.plan_data.get("source_path",""))
        form_layout.addRow("Quelle:", self.source_edit)

        # Target
        self.target_edit = QtWidgets.QLineEdit(self.plan_data.get("target_path",""))
        form_layout.addRow("Ziel:", self.target_edit)

        # FTP
        self.ftp_check = QtWidgets.QCheckBox("FTP verwenden?")
        self.ftp_check.setChecked(self.plan_data.get("use_ftp",False))
        form_layout.addRow(self.ftp_check)

        self.ftp_server_edit = QtWidgets.QLineEdit(self.plan_data.get("ftp_server_name",""))
        form_layout.addRow("FTP-Server Name:", self.ftp_server_edit)

        # Version
        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.addItems(["mirror", "suffix"])
        self.version_combo.setCurrentText(self.plan_data.get("versioning_mode","mirror"))
        form_layout.addRow("Versionierung:", self.version_combo)

        self.suffix_edit = QtWidgets.QLineEdit(self.plan_data.get("suffix_format","_v{n}"))
        form_layout.addRow("Suffix-Format:", self.suffix_edit)

        # Zeitplan
        self.schedule_combo = QtWidgets.QComboBox()
        self.schedule_combo.addItems(["manual", "interval", "cron"])
        self.schedule_combo.setCurrentText(self.plan_data.get("schedule_type","manual"))
        form_layout.addRow("Zeitplan:", self.schedule_combo)

        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 100000)
        self.interval_spin.setValue(self.plan_data.get("interval_minutes",60))
        form_layout.addRow("Intervall (Min):", self.interval_spin)

        # Move after done
        self.move_check = QtWidgets.QCheckBox("Nach Abschluss verschieben?")
        self.move_check.setChecked(self.plan_data.get("move_after_done",False))
        form_layout.addRow(self.move_check)

        self.move_path_edit = QtWidgets.QLineEdit(self.plan_data.get("move_path",""))
        form_layout.addRow("Zielordner (verschieben):", self.move_path_edit)

        # Button-Layout
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.addStretch()

        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_dialog)
        btn_layout.addWidget(self.ok_btn)

    def accept_dialog(self):
        # Felder übernehmen
        self.plan_data["name"] = self.name_edit.text().strip()
        self.plan_data["source_path"] = self.source_edit.text().strip()
        self.plan_data["target_path"] = self.target_edit.text().strip()
        self.plan_data["use_ftp"] = self.ftp_check.isChecked()
        self.plan_data["ftp_server_name"] = self.ftp_server_edit.text().strip()
        self.plan_data["versioning_mode"] = self.version_combo.currentText()
        self.plan_data["suffix_format"] = self.suffix_edit.text().strip()
        self.plan_data["schedule_type"] = self.schedule_combo.currentText()
        self.plan_data["interval_minutes"] = self.interval_spin.value()
        self.plan_data["move_after_done"] = self.move_check.isChecked()
        self.plan_data["move_path"] = self.move_path_edit.text().strip()

        # Falls kein ID vorhanden, generieren wir eins
        if not self.plan_data.get("id"):
            self.plan_data["id"] = str(uuid.uuid4())

        # Plan in Manager speichern
        plan_id = self.plan_data["id"]
        self.manager.update_plan(plan_id, self.plan_data)

        self.accept()