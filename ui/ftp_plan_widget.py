#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore, QtGui
from utils.config_manager import debug_print
from utils.transfer_plan_manager import update_transfer_plan as _update_transfer_plan
from ui.ftp_plan_dialog import TransferPlanDialog

class FtpPlanWidget(QtWidgets.QWidget):
    """
    Nur-Anzeige-Variante eines Transferplans:
    - Zeigt Plan-Parameter (Quelle, Ziel, FTP/Lokal etc.)
    - Buttons: Bearbeiten (öffnet Dialog), Jetzt ausführen
    - Klappbereich (Details) mittels Toggle-Pfeil
    - Persistiert body_visible (Anzeige/Verstecken der Details)
    """

    runNowRequested = QtCore.Signal(dict)
    editRequested = QtCore.Signal(dict)
    deleteRequested = QtCore.Signal(str)  # optional, falls Löschfunktion benötigt wird

    def __init__(self, plan_data: dict, manager=None, parent=None):
        super().__init__(parent)
        self.plan = dict(plan_data or {})
        self.manager = manager
        # body_visible steuert, ob Details angezeigt werden:
        self.is_collapsed = not self.plan.get("body_visible", True)
        self._build_ui()
        self._refresh_display()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Header: Toggle + Name + Buttons
        h = QtWidgets.QHBoxLayout()
        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        self.toggle_btn.clicked.connect(self._on_toggle)
        h.addWidget(self.toggle_btn)

        self.name_label = QtWidgets.QLabel(self.plan.get("name", "Neuer Transfer-Plan"))
        font = self.name_label.font()
        font.setBold(True)
        self.name_label.setFont(font)
        h.addWidget(self.name_label, stretch=1)

        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        h.addWidget(self.btn_edit)

        self.btn_run = QtWidgets.QPushButton("Jetzt ausführen")
        self.btn_run.clicked.connect(self._on_run_clicked)
        h.addWidget(self.btn_run)

        layout.addLayout(h)

        # Details-Widget (Form, Anzeige, nicht editierbar)
        self.details = QtWidgets.QWidget()
        det_layout = QtWidgets.QFormLayout(self.details)
        det_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        det_layout.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Labels zur Anzeige
        self.lbl_source = QtWidgets.QLabel()
        self.lbl_target = QtWidgets.QLabel()
        self.lbl_type = QtWidgets.QLabel()
        self.lbl_version = QtWidgets.QLabel()
        self.lbl_schedule = QtWidgets.QLabel()
        self.lbl_moveafter = QtWidgets.QLabel()

        det_layout.addRow("Quelle:", self.lbl_source)
        det_layout.addRow("Ziel:", self.lbl_target)
        det_layout.addRow("Lokal / FTP:", self.lbl_type)
        det_layout.addRow("Versionierung:", self.lbl_version)
        det_layout.addRow("Zeitplan:", self.lbl_schedule)
        det_layout.addRow("Nach Transfer verschieben:", self.lbl_moveafter)

        layout.addWidget(self.details)
        self.details.setVisible(not self.is_collapsed)

    def _on_toggle(self):
        # Umschalten
        self.is_collapsed = not self.is_collapsed
        self.details.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        # Persist body_visible
        self.plan["body_visible"] = not self.is_collapsed
        self._persist({"body_visible": self.plan["body_visible"]})

    def _on_edit_clicked(self):
        dlg = TransferPlanDialog(self.plan, parent=self)
        result = dlg.exec()
        if result == QtWidgets.QDialog.Accepted:
            # Dialog ändert self.plan
            self.plan = dlg.plan_data
            # Emit editRequested in case jemand reagieren will
            self.editRequested.emit(dict(self.plan))
            # Aktualisieren Anzeige
            self._refresh_display()

    def _on_run_clicked(self):
        self.runNowRequested.emit(dict(self.plan))

    def _refresh_display(self):
        # Überschrift neu setzen
        self.name_label.setText(self.plan.get("name", "Neuer Transfer-Plan"))

        src = self.plan.get("source_path", "") or "—"
        tgt = self.plan.get("target_path", "") or self.plan.get("destination_path", "") or "—"
        use_ftp = bool(self.plan.get("use_ftp", False))
        ftp_name = self.plan.get("ftp_server", "")

        self.lbl_source.setText(src)
        self.lbl_target.setText(tgt)
        if use_ftp:
            typ = f"FTP{f' ({ftp_name})' if ftp_name else ''}"
        else:
            typ = "Lokal (kein FTP)"
        self.lbl_type.setText(typ)

        ver_mode = self.plan.get("versioning_mode", self.plan.get("version_mode", "mirror"))
        suffix = self.plan.get("suffix_format", "")
        if ver_mode.lower() == "suffix":
            self.lbl_version.setText(f"suffix (Suffix={suffix})")
        else:
            self.lbl_version.setText(f"mirror (Suffix={suffix})")

        sched_type = self.plan.get("schedule_type", "once")
        sched_time = self.plan.get("schedule_time", "")
        if sched_type == "once":
            self.lbl_schedule.setText(f"once @ {sched_time}" if sched_time else "once")
        elif sched_type == "daily":
            self.lbl_schedule.setText(f"daily @ {sched_time}" if sched_time else "daily")
        else:  # weekly
            self.lbl_schedule.setText(f"weekly @ {sched_time}" if sched_time else "weekly")

        move_after = self.plan.get("move_after", "")
        self.lbl_moveafter.setText(move_after or "—")

    def _persist(self, changes: dict):
        try:
            plan_id = self.plan.get("id")
            if self.manager and hasattr(self.manager, "update_plan") and plan_id:
                # Nutze Manager
                merged = {**self.plan, **changes}
                self.manager.update_plan(plan_id, merged)
            else:
                merged = {**self.plan, **changes}
                _update_transfer_plan(merged)
        except Exception as e:
            debug_print(f"[FtpPlanWidget] persist error: {e}")

    # optional: wenn jemand löschen will
    def request_delete(self):
        pid = self.plan.get("id", "")
        if pid:
            self.deleteRequested.emit(pid)