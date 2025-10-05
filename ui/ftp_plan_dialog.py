#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print, load_ftp_servers

class TransferPlanDialog(QtWidgets.QDialog):
    """
    Dialog zur Konfiguration eines Transferplans.

    WICHTIG: Abwärtskompatible Signatur
        __init__(plan_data, manager=None, parent=None)
    -> Dein TransferPlanWidget kann den Dialog weiterhin mit nur (plan_data, parent=self) öffnen.
    -> Ein optionaler manager wird ignoriert, wenn nicht benötigt.

    Unterstützte Felder (wie in deinen Logs/JSON):
      - name
      - source_is_ftp, source_ftp_server, source_remote_path, source_path, source_remote_archive
      - use_ftp, ftp_server, target_path
      - versioning_mode ("mirror" | "suffix"), suffix_format
      - retry_count, verify_mode ("size_only" | "md5")
      - schedule_type ("once" | "daily" | "weekly"), schedule_time ("yyyy-MM-dd HH:mm")
      - move_after
      - auto_delete_after_move_enabled, auto_delete_after_move_hours
    """

    def __init__(self, plan_data, manager=None, parent=None):
        super().__init__(parent)
        # plan_data wird in-place aktualisiert (Verhalten wie bisher)
        self.plan_data = plan_data if isinstance(plan_data, dict) else {}
        self._manager = manager  # bewusst optional/ungenutzt für Abwärtskompatibilität

        self.setWindowTitle("Transferplan konfigurieren")
        self.resize(600, 460)

        self._build_ui()
        self._load_ftp_servers()
        self._load_plan_into_widgets()

    # ---------------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        main_layout.addLayout(form_layout)

        # --- Planname ---
        self.name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Plan Name:", self.name_edit)

        # ========== QUELLE ==========
        self.src_is_ftp_check = QtWidgets.QCheckBox("Quelle ist FTP/SFTP")
        self.src_is_ftp_check.stateChanged.connect(self._on_src_ftp_toggled)
        form_layout.addRow("", self.src_is_ftp_check)

        self.src_ftp_combo = QtWidgets.QComboBox()
        form_layout.addRow("Quell-Server:", self.src_ftp_combo)

        self.src_remote_edit = QtWidgets.QLineEdit()
        self.src_remote_edit.setPlaceholderText("Remote-Pfad, z. B. /incoming/jobs")
        form_layout.addRow("Quell-Remote-Pfad:", self.src_remote_edit)

        # Quellordner (lokal)
        self.source_btn = QtWidgets.QPushButton("Ordner wählen")
        self.source_btn.clicked.connect(self._pick_source_folder)
        self.source_label = QtWidgets.QLabel("(none)")
        src_hbox = QtWidgets.QHBoxLayout()
        src_hbox.addWidget(self.source_label, 1)
        src_hbox.addWidget(self.source_btn)
        form_layout.addRow("Quellordner lokal:", src_hbox)

        # Optionales Remote-Archiv (wenn Quelle FTP/SFTP ist)
        self.src_move_after_remote_edit = QtWidgets.QLineEdit()
        self.src_move_after_remote_edit.setPlaceholderText("Optional: Remote-Archivpfad auf Quell-Server")
        form_layout.addRow("Quelle: Remote-Archiv:", self.src_move_after_remote_edit)

        # ========== ZIEL ==========
        self.ftp_check = QtWidgets.QCheckBox("Ziel über FTP/SFTP übertragen")
        self.ftp_check.stateChanged.connect(self._on_dst_ftp_toggled)
        form_layout.addRow("", self.ftp_check)

        self.ftp_combo = QtWidgets.QComboBox()
        form_layout.addRow("Ziel-Server:", self.ftp_combo)

        # Zielordner (lokal oder Remote-Pfad-String)
        self.target_edit = QtWidgets.QLineEdit()
        self.target_btn = QtWidgets.QPushButton("Ordner wählen")
        self.target_btn.clicked.connect(self._pick_target_folder)
        target_hbox = QtWidgets.QHBoxLayout()
        target_hbox.addWidget(self.target_edit, 1)
        target_hbox.addWidget(self.target_btn)
        form_layout.addRow("Zielordner (lokal od. Remote-Pfad):", target_hbox)

        # ========== VERSIONIERUNG ==========
        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.addItems(["mirror", "suffix"])
        form_layout.addRow("Versionierung:", self.version_combo)

        self.suffix_edit = QtWidgets.QLineEdit("_v{n}")
        form_layout.addRow("Suffix (bei 'suffix'):", self.suffix_edit)

        # ========== ROBUSTHEIT ==========
        self.retry_spin = QtWidgets.QSpinBox()
        self.retry_spin.setRange(1, 20)
        self.retry_spin.setValue(5)
        form_layout.addRow("Wiederholungen bei Fehlern:", self.retry_spin)

        self.verify_combo = QtWidgets.QComboBox()
        # Index 0: size_only, Index 1: md5
        self.verify_combo.addItems(["size_only", "md5 (langsamer)"])
        form_layout.addRow("Integritätsprüfung:", self.verify_combo)

        # ========== ZEITPLAN ==========
        self.schedule_combo = QtWidgets.QComboBox()
        self.schedule_combo.addItems(["once", "daily", "weekly"])
        form_layout.addRow("Zeitplan:", self.schedule_combo)

        self.datetime_edit = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setCalendarPopup(True)
        form_layout.addRow("Geplanter Zeitpunkt:", self.datetime_edit)

        # ========== MOVE-AFTER (lokal) ==========
        self.move_btn = QtWidgets.QPushButton("Ordner wählen")
        self.move_btn.clicked.connect(self._pick_move_after_folder)
        self.move_label = QtWidgets.QLabel("(none)")
        mv_hbox = QtWidgets.QHBoxLayout()
        mv_hbox.addWidget(self.move_label, 1)
        mv_hbox.addWidget(self.move_btn)
        form_layout.addRow("Nach Transfer verschieben (lokal):", mv_hbox)

        # Auto-Delete im lokalen Move-Ordner
        self.auto_delete_move_checkbox = QtWidgets.QCheckBox("Auto-Delete aktivieren")
        self.auto_delete_move_hours_spin = QtWidgets.QSpinBox()
        self.auto_delete_move_hours_spin.setRange(1, 24 * 30)
        self.auto_delete_move_hours_spin.setValue(48)
        mv_delete_hbox = QtWidgets.QHBoxLayout()
        mv_delete_hbox.addWidget(self.auto_delete_move_checkbox)
        mv_delete_hbox.addWidget(QtWidgets.QLabel("Stunden:"))
        mv_delete_hbox.addWidget(self.auto_delete_move_hours_spin)
        form_layout.addRow("Dateien löschen in:", mv_delete_hbox)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(self.ok_btn)
        main_layout.addLayout(btn_layout)

    # ---------------------------------------------------------------------
    # Daten laden
    # ---------------------------------------------------------------------
    def _load_ftp_servers(self):
        servers = load_ftp_servers()
        # Ziel-Server
        self.ftp_combo.clear()
        self.ftp_combo.addItem("(none)")
        # Quell-Server
        self.src_ftp_combo.clear()
        self.src_ftp_combo.addItem("(none)")
        for srv in servers:
            name = srv.get("name", "Unnamed")
            self.ftp_combo.addItem(name)
            self.src_ftp_combo.addItem(name)
        debug_print(f"TransferPlanDialog: load_ftp_servers => {servers}")

    def _load_plan_into_widgets(self):
        """Befüllt die Widgets aus self.plan_data."""
        pd = self.plan_data or {}

        # Planname
        self.name_edit.setText(pd.get("name", "Neuer Transfer-Plan"))

        # Quelle
        self.src_is_ftp_check.setChecked(pd.get("source_is_ftp", False))
        src_server = pd.get("source_ftp_server", "")
        idx_src = self.src_ftp_combo.findText(src_server) if src_server else 0
        self.src_ftp_combo.setCurrentIndex(idx_src if idx_src >= 0 else 0)
        self.src_remote_edit.setText(pd.get("source_remote_path", ""))

        src_local = pd.get("source_path", "")
        self.source_label.setText(src_local or "(none)")

        self.src_move_after_remote_edit.setText(pd.get("source_remote_archive", ""))

        # Ziel
        use_ftp = pd.get("use_ftp", False)
        self.ftp_check.setChecked(use_ftp)
        ftp_name = pd.get("ftp_server", "")
        if ftp_name:
            idx = self.ftp_combo.findText(ftp_name)
            self.ftp_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.ftp_combo.setCurrentIndex(0)

        self.target_edit.setText(pd.get("target_path", ""))

        # Versionierung
        version_mode = pd.get("versioning_mode", "mirror")
        self.version_combo.setCurrentText(version_mode)
        self.suffix_edit.setText(pd.get("suffix_format", "_v{n}"))

        # Robustheit
        self.retry_spin.setValue(pd.get("retry_count", 5))
        self.verify_combo.setCurrentText(pd.get("verify_mode", "size_only") if pd.get("verify_mode") else "size_only")

        # Zeitplan
        schedule_type = pd.get("schedule_type", "once")
        self.schedule_combo.setCurrentText(schedule_type)

        dt_str = pd.get("schedule_time", "")
        if dt_str:
            dt = QtCore.QDateTime.fromString(dt_str, "yyyy-MM-dd HH:mm")
            if dt.isValid():
                self.datetime_edit.setDateTime(dt)

        # Move-After lokal
        move_after = pd.get("move_after", "")
        self.move_label.setText(move_after or "(none)")

        self.auto_delete_move_checkbox.setChecked(pd.get("auto_delete_after_move_enabled", False))
        self.auto_delete_move_hours_spin.setValue(pd.get("auto_delete_after_move_hours", 48))

        # Initiale Enable/Disable-States
        self._on_src_ftp_toggled()
        self._on_dst_ftp_toggled()

    # ---------------------------------------------------------------------
    # Aktionen
    # ---------------------------------------------------------------------
    def _on_ok(self):
        debug_print("TransferPlanDialog.on_ok() aufgerufen.")
        pd = self.plan_data

        # Planname
        pd["name"] = self.name_edit.text().strip()

        # Quelle
        pd["source_is_ftp"] = self.src_is_ftp_check.isChecked()
        if pd["source_is_ftp"]:
            chosen_server = self.src_ftp_combo.currentText()
            pd["source_ftp_server"] = "" if chosen_server == "(none)" else chosen_server
            pd["source_remote_path"] = self.src_remote_edit.text().strip()
        else:
            pd["source_ftp_server"] = ""
            pd["source_remote_path"] = ""

        src_str = self.source_label.text()
        pd["source_path"] = "" if src_str == "(none)" else src_str

        pd["source_remote_archive"] = self.src_move_after_remote_edit.text().strip()

        # Ziel
        pd["use_ftp"] = self.ftp_check.isChecked()
        if pd["use_ftp"]:
            chosen_server = self.ftp_combo.currentText()
            pd["ftp_server"] = "" if chosen_server == "(none)" else chosen_server
        else:
            pd["ftp_server"] = ""

        pd["target_path"] = self.target_edit.text().strip()

        # Versionierung
        pd["versioning_mode"] = self.version_combo.currentText()
        pd["suffix_format"] = self.suffix_edit.text().strip()

        # Robustheit
        pd["retry_count"] = self.retry_spin.value()
        pd["verify_mode"] = "size_only" if self.verify_combo.currentIndex() == 0 else "md5"

        # Zeitplan
        pd["schedule_type"] = self.schedule_combo.currentText()
        dt_obj = self.datetime_edit.dateTime()
        pd["schedule_time"] = dt_obj.toString("yyyy-MM-dd HH:mm")

        # Move-After / Auto-Delete
        mv_str = self.move_label.text()
        pd["move_after"] = "" if mv_str == "(none)" else mv_str
        pd["auto_delete_after_move_enabled"] = self.auto_delete_move_checkbox.isChecked()
        pd["auto_delete_after_move_hours"] = self.auto_delete_move_hours_spin.value()

        debug_print(f"TransferPlanDialog => final plan_data: {pd}")
        self.accept()

    # --- Picker ---
    def _pick_source_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Quellordner wählen")
        if folder:
            self.source_label.setText(folder)

    def _pick_target_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if folder:
            self.target_edit.setText(folder)

    def _pick_move_after_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Nach Transfer verschieben nach…")
        if folder:
            self.move_label.setText(folder)

    # --- Toggles ---
    def _on_src_ftp_toggled(self):
        checked = self.src_is_ftp_check.isChecked()
        self.src_ftp_combo.setEnabled(checked)
        self.src_remote_edit.setEnabled(checked)
        self.src_move_after_remote_edit.setEnabled(checked)
        # Lokale Quelle deaktivieren, wenn FTP-Quelle aktiv
        self.source_btn.setEnabled(not checked)

    def _on_dst_ftp_toggled(self):
        checked = self.ftp_check.isChecked()
        self.ftp_combo.setEnabled(checked)
        # Lokale Zielauswahl bleibt erlaubt (lokaler Pfad ODER Remote-String)