#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore, QtGui
from utils.config_manager import debug_print
from utils.transfer_plan_manager import update_transfer_plan as _update_transfer_plan

class FtpPlanWidget(QtWidgets.QWidget):
    """
    Karten-Widget für einen einzelnen Transfer-Plan (wie im Screenshot):
      - einklappbarer Bereich „Details“
      - Zeilen: Quelle, Ziel, Zieltyp, Versionierung, Zeitplan, Move-After
      - Buttons rechts: Bearbeiten, Jetzt ausführen
      - Signale: runNowRequested(plan: dict), editRequested(plan: dict), deleteRequested(plan_id: str)

    'manager' ist optional. Wenn keiner übergeben wird, persistieren wir direkt via _update_transfer_plan().
    """

    runNowRequested = QtCore.Signal(dict)
    editRequested = QtCore.Signal(dict)
    deleteRequested = QtCore.Signal(str)

    def __init__(self, plan_data: dict, manager=None, parent=None):
        super().__init__(parent)
        self.plan = dict(plan_data or {})
        self.manager = manager
        self.is_collapsed = not self.plan.get("body_visible", True)
        self._build_ui()
        self._refresh()

    # ---------- UI ----------
    def _build_ui(self):
        self.setObjectName("planCard")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(4)

        # Header (dunkel)
        header = QtWidgets.QWidget()
        header.setObjectName("header")
        header_l = QtWidgets.QHBoxLayout(header)
        header_l.setContentsMargins(10, 6, 10, 6)
        header_l.setSpacing(8)

        self.title_lbl = QtWidgets.QLabel(self.plan.get("name", ""))
        self.title_lbl.setStyleSheet("font-weight: 700; color: white;")
        header_l.addWidget(self.title_lbl, 1)

        # Collapse-Button (rechts)
        self.collapse_btn = QtWidgets.QToolButton()
        self.collapse_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setChecked(not self.is_collapsed)
        self.collapse_btn.toggled.connect(self._toggle_details)
        header_l.addWidget(self.collapse_btn, 0, QtCore.Qt.AlignRight)

        outer.addWidget(header)

        # Subheader (hellgrau) – Ziel-Pfad als fette Zeile
        sub = QtWidgets.QWidget()
        sub_l = QtWidgets.QHBoxLayout(sub)
        sub_l.setContentsMargins(10, 6, 10, 6)
        sub_l.setSpacing(8)
        self.path_summary = QtWidgets.QLabel("")
        self.path_summary.setStyleSheet("font-weight: 600;")
        sub_l.addWidget(self.path_summary, 1)

        # Buttons rechts
        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_run = QtWidgets.QPushButton("Jetzt ausführen")
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(dict(self.plan)))
        self.btn_run.clicked.connect(lambda: self.runNowRequested.emit(dict(self.plan)))
        sub_l.addWidget(self.btn_edit)
        sub_l.addWidget(self.btn_run)

        outer.addWidget(sub)

        # Details-Box (hell) – Formartige Anzeige
        self.details = QtWidgets.QGroupBox("Details")
        det_l = QtWidgets.QFormLayout(self.details)
        det_l.setLabelAlignment(QtCore.Qt.AlignLeft)
        det_l.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        det_l.setContentsMargins(12, 8, 12, 8)

        self.row_source = QtWidgets.QLabel("")
        self.row_target = QtWidgets.QLabel("")
        self.row_target_type = QtWidgets.QLabel("")
        self.row_version = QtWidgets.QLabel("")
        self.row_schedule = QtWidgets.QLabel("")
        self.row_moveafter = QtWidgets.QLabel("")

        det_l.addRow(self._bold("Quellordner:"), self.row_source)
        det_l.addRow(self._bold("Zielordner:"), self.row_target)
        det_l.addRow(self._bold("Lokal/FTP:"), self.row_target_type)
        det_l.addRow(self._bold("Versionierung:"), self.row_version)
        det_l.addRow(self._bold("Zeitplan:"), self.row_schedule)
        det_l.addRow(self._bold("Nach Transfer verschieben:"), self.row_moveafter)

        outer.addWidget(self.details)

        # Styles
        self.setStyleSheet("""
            QWidget#header { background:#2b2b2b; border-radius:4px; }
            QWidget#planCard { }
            QGroupBox { font-weight:600; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding:2px 6px; }
        """)
        self.details.setVisible(not self.is_collapsed)

    def _bold(self, text):
        lbl = QtWidgets.QLabel(text)
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        return lbl

    # ---------- State/UI aktualisieren ----------
    def _refresh(self):
        self.title_lbl.setText(self.plan.get("name", ""))
        src = self.plan.get("source_path", "")
        tgt = self.plan.get("target_path", self.plan.get("destination_path", ""))
        use_ftp = self.plan.get("use_ftp", False)
        ftp_name = self.plan.get("ftp_server", "")
        ver_mode = self.plan.get("versioning_mode", self.plan.get("version_mode", "mirror"))
        suffix = self.plan.get("suffix_format", "_v")
        sched_type = self.plan.get("schedule_type", "once")
        sched_time = self.plan.get("schedule_time", "")
        move_after = self.plan.get("move_after", "")

        self.path_summary.setText(f"{src} -> {tgt}")
        self.row_source.setText(src or "—")
        self.row_target.setText(tgt or "—")
        self.row_target_type.setText("FTP" + (f" ({ftp_name})" if use_ftp and ftp_name else "") if use_ftp else "Lokal (kein FTP)")
        if ver_mode == "suffix":
            self.row_version.setText(f"suffix (Suffix={suffix})")
        else:
            self.row_version.setText(f"mirror (Suffix={suffix})")
        if sched_type == "once":
            self.row_schedule.setText(f"once @ {sched_time}" if sched_time else "once")
        elif sched_type == "daily":
            self.row_schedule.setText(f"daily @ {sched_time}" if sched_time else "daily")
        else:
            self.row_schedule.setText(f"weekly @ {sched_time}" if sched_time else "weekly")
        self.row_moveafter.setText(move_after or "—")

    # ---------- Aktionen ----------
    def _toggle_details(self, checked: bool):
        self.details.setVisible(checked)
        self.is_collapsed = not checked
        self.plan["body_visible"] = checked
        self._persist({"body_visible": checked})

    # Öffentliche Helfer (falls UI-Änderungen nötig)
    def set_plan(self, plan: dict):
        self.plan = dict(plan or {})
        self._refresh()

    # ---------- Persistenz ----------
    def _persist(self, changes: dict):
        """manager.update_plan bevorzugen; sonst Fallback direkt in Datei."""
        try:
            plan_id = self.plan.get("id")
            if hasattr(self.manager, "update_plan") and plan_id:
                self.manager.update_plan(plan_id, {**self.plan, **changes})
            else:
                _update_transfer_plan({**self.plan, **changes})
            self.plan.update(changes)
        except Exception as e:
            debug_print(f"[FtpPlanWidget] persist error: {e}")