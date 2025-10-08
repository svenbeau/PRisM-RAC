#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print
from utils.transfer_plan_manager import update_transfer_plan as _update_transfer_plan  # Fallback, falls kein manager übergeben


class TransferPlanWidget(QtWidgets.QWidget):
    """
    Collapsible Widget zur Anzeige/Bearbeitung eines einzelnen Transfer-Plans.
    - manager ist OPTIONAL: wenn None, wird update_transfer_plan() direkt aufgerufen.
    - Header-Buttons: Jetzt ausführen / Bearbeiten / Löschen
    - Signale: runNowRequested(plan: dict), editRequested(plan: dict), deleteRequested(plan_id: str)
    """

    # Signale nach oben (für Schedule-Widget)
    runNowRequested = QtCore.Signal(dict)   # gibt komplettes plan_data-Dict
    editRequested = QtCore.Signal(dict)     # gibt komplettes plan_data-Dict
    deleteRequested = QtCore.Signal(str)    # gibt plan_id

    def __init__(self, plan_data, manager=None, parent=None):
        super().__init__(parent)
        self.plan_data = dict(plan_data or {})
        self.manager = manager  # optional
        self.is_collapsed = not self.plan_data.get("body_visible", True)
        self._build_ui()
        self._refresh_header_info()

    # ---------------- UI ----------------

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Header
        header = QtWidgets.QHBoxLayout()
        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        self.toggle_btn.setStyleSheet("font-weight: bold;")
        self.toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.clicked.connect(self.toggle_body)

        self.name_label = QtWidgets.QLabel(self.plan_data.get("name", "Neuer Transfer-Plan"))
        header.addWidget(self.toggle_btn)
        header.addWidget(self.name_label, 1)

        # Header: Aktions-Buttons
        self.btn_run_now = QtWidgets.QPushButton("Jetzt ausführen")
        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_delete = QtWidgets.QPushButton("Löschen")
        self.btn_run_now.clicked.connect(self._emit_run_now)
        self.btn_edit.clicked.connect(self._emit_edit)
        self.btn_delete.clicked.connect(self._emit_delete)
        header.addWidget(self.btn_run_now)
        header.addWidget(self.btn_edit)
        header.addWidget(self.btn_delete)

        main_layout.addLayout(header)

        # Body (Form)
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QFormLayout(self.body_widget)

        self.edit_name = QtWidgets.QLineEdit(self.plan_data.get("name", ""))
        body_layout.addRow("Plan-Name:", self.edit_name)

        # Quelle
        self.source_type_combo = QtWidgets.QComboBox()
        self.source_type_combo.addItems(["local", "ftp"])
        self.source_type_combo.setCurrentText(self.plan_data.get("source_type", "local"))
        body_layout.addRow("Quelle (Typ):", self.source_type_combo)

        self.edit_source_path = QtWidgets.QLineEdit(self.plan_data.get("source_path", ""))
        body_layout.addRow("Quelle (Pfad):", self.edit_source_path)

        # Ziel (vereinheitlicht: destination_path <-> target_path)
        self.edit_destination_path = QtWidgets.QLineEdit(self.plan_data.get("destination_path", self.plan_data.get("target_path", "")))
        body_layout.addRow("Ziel (Pfad):", self.edit_destination_path)

        # Versionierung (vereinheitlicht: version_mode <-> versioning_mode)
        self.version_mode_combo = QtWidgets.QComboBox()
        self.version_mode_combo.addItems(["mirror", "suffix"])
        self.version_mode_combo.setCurrentText(self.plan_data.get("version_mode", self.plan_data.get("versioning_mode", "mirror")))
        body_layout.addRow("Versionierung:", self.version_mode_combo)

        self.suffix_edit = QtWidgets.QLineEdit(self.plan_data.get("suffix_format", "_v{n}"))
        body_layout.addRow("Suffix-Format:", self.suffix_edit)

        # Zeitplan
        self.schedule_type_combo = QtWidgets.QComboBox()
        self.schedule_type_combo.addItems(["once", "daily", "weekly"])
        self.schedule_type_combo.setCurrentText(self.plan_data.get("schedule_type", "once"))
        body_layout.addRow("Zeitplan:", self.schedule_type_combo)

        self.schedule_time_edit = QtWidgets.QDateTimeEdit()
        self.schedule_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.schedule_time_edit.setCalendarPopup(True)
        from datetime import datetime, timedelta
        raw = self.plan_data.get("schedule_time", "")
        dt = None
        try:
            if raw:
                dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
        except Exception:
            dt = None
        if not dt:
            dt = datetime.now() + timedelta(minutes=10)
        self.schedule_time_edit.setDateTime(dt)
        body_layout.addRow("Zeitpunkt:", self.schedule_time_edit)

        # Speichern-Button (nur Plan-Daten updaten)
        self.save_btn = QtWidgets.QPushButton("Speichern")
        self.save_btn.clicked.connect(self.save_plan)
        body_layout.addRow(self.save_btn)

        main_layout.addWidget(self.body_widget)
        self.body_widget.setVisible(not self.is_collapsed)

    def _refresh_header_info(self):
        self.name_label.setText(self.plan_data.get("name", "Neuer Transfer-Plan"))

    # ---------------- Aktionen/Signale ----------------

    def _emit_run_now(self):
        debug_print(f"[TransferPlanWidget] runNowRequested id={self.plan_data.get('id')}")
        self.runNowRequested.emit(dict(self.plan_data))

    def _emit_edit(self):
        debug_print(f"[TransferPlanWidget] editRequested id={self.plan_data.get('id')}")
        self.editRequested.emit(dict(self.plan_data))

    def _emit_delete(self):
        debug_print(f"[TransferPlanWidget] deleteRequested id={self.plan_data.get('id')}")
        self.deleteRequested.emit(self.plan_data.get("id", ""))

    def toggle_body(self):
        self.is_collapsed = not self.is_collapsed
        self.body_widget.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        # body_visible persistieren
        self.plan_data["body_visible"] = (not self.is_collapsed)
        self._update_plan_persist({"body_visible": not self.is_collapsed})

    def save_plan(self):
        """
        Liest die UI-Felder aus, aktualisiert self.plan_data und persistiert.
        """
        debug_print(f"[TransferPlanWidget] save_plan() id={self.plan_data.get('id')}")
        self.plan_data["name"] = self.edit_name.text().strip()
        self.plan_data["source_type"] = self.source_type_combo.currentText()
        self.plan_data["source_path"] = self.edit_source_path.text().strip()

        # Ziel vereinheitlichen
        dest = self.edit_destination_path.text().strip()
        self.plan_data["destination_path"] = dest
        if dest:
            self.plan_data["target_path"] = dest  # für execute_transfer_plan()

        # Versionierung vereinheitlichen
        vm = self.version_mode_combo.currentText()
        self.plan_data["version_mode"] = vm
        self.plan_data["versioning_mode"] = vm  # für execute_transfer_plan()

        self.plan_data["suffix_format"] = self.suffix_edit.text().strip()
        self.plan_data["schedule_type"] = self.schedule_type_combo.currentText()
        self.plan_data["schedule_time"] = self.schedule_time_edit.dateTime().toString("yyyy-MM-dd HH:mm")

        self._update_plan_persist(self.plan_data)
        self._refresh_header_info()
        QtWidgets.QMessageBox.information(self, "Gespeichert", "Plan wurde aktualisiert.")

    def _update_plan_persist(self, data: dict):
        """
        Persistiert Änderungen: bevorzugt manager.update_plan, sonst direkter Fallback.
        """
        plan_id = self.plan_data.get("id")
        if hasattr(self.manager, "update_plan"):
            try:
                self.manager.update_plan(plan_id, data)
                return
            except Exception as e:
                debug_print(f"[TransferPlanWidget] manager.update_plan Fehler: {e}")
        # Fallback
        try:
            _update_transfer_plan(self.plan_data if "name" in data else {**self.plan_data, **data})
        except Exception as e:
            debug_print(f"[TransferPlanWidget] update_transfer_plan() Fallback-Fehler: {e}")