#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore, QtGui
from utils.config_manager import debug_print
from utils.transfer_plan_manager import update_transfer_plan as _update_transfer_plan


class TransferPlanWidget(QtWidgets.QWidget):
    """
    Anzeige-Widget für einen Transfer-Plan im Karten-Look:
      - Dunkler Header mit Titel + Toggle (▸/▾)
      - Subheader (hellgrau) mit "Quelle -> Ziel" und Buttons rechts
      - Ausklappbarer Details-Block (helles Feld) mit Labels
    Interaktion:
      - 'Bearbeiten' -> emit editRequested(plan: dict)
      - 'Jetzt ausführen' -> emit runNowRequested(plan: dict)
      - body_visible wird persistiert.
    """

    runNowRequested = QtCore.Signal(dict)
    editRequested = QtCore.Signal(dict)
    deleteRequested = QtCore.Signal(str)

    def __init__(self, plan_data: dict, manager=None, parent=None):
        super().__init__(parent)
        self.plan = dict(plan_data or {})
        self.manager = manager
        self._collapsed = not self.plan.get("body_visible", True)
        self._build_ui()
        self._fill()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 6, 12, 0)
        root.setSpacing(6)

        # ===== Karte (Container) =====
        self.card = QtWidgets.QFrame(objectName="card")
        card_l = QtWidgets.QVBoxLayout(self.card)
        card_l.setContentsMargins(0, 0, 0, 0)
        card_l.setSpacing(0)

        # ----- Header (dunkel) -----
        header = QtWidgets.QWidget(objectName="header")
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(14, 8, 10, 8)
        hl.setSpacing(10)

        self.toggle_btn = QtWidgets.QToolButton(objectName="toggle")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(not self._collapsed)
        self._apply_toggle_glyph()
        self.toggle_btn.clicked.connect(self._on_toggle)
        hl.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignLeft)

        self.title_lbl = QtWidgets.QLabel(self.plan.get("name", ""))
        tfont = self.title_lbl.font()
        tfont.setBold(True)
        self.title_lbl.setFont(tfont)
        self.title_lbl.setObjectName("title")
        hl.addWidget(self.title_lbl, 1, QtCore.Qt.AlignVCenter)

        # (kleiner Platzhalter rechts, falls später Menü/Icons gewünscht)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        hl.addWidget(spacer)

        card_l.addWidget(header)

        # ----- Subheader (hellgrau: Quelle -> Ziel + Buttons) -----
        sub = QtWidgets.QWidget(objectName="subheader")
        sl = QtWidgets.QHBoxLayout(sub)
        sl.setContentsMargins(14, 8, 14, 8)
        sl.setSpacing(8)

        self.path_summary = QtWidgets.QLabel("")
        pfont = self.path_summary.font()
        pfont.setWeight(QtGui.QFont.DemiBold)
        self.path_summary.setFont(pfont)
        sl.addWidget(self.path_summary, 1)

        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(dict(self.plan)))
        sl.addWidget(self.btn_edit, 0)

        self.btn_run = QtWidgets.QPushButton("Jetzt ausführen")
        self.btn_run.clicked.connect(lambda: self.runNowRequested.emit(dict(self.plan)))
        sl.addWidget(self.btn_run, 0)

        card_l.addWidget(sub)

        # ----- Details (helles Feld) -----
        self.details = QtWidgets.QFrame(objectName="details")
        dl = QtWidgets.QVBoxLayout(self.details)
        dl.setContentsMargins(12, 10, 12, 12)
        dl.setSpacing(8)

        title_det = QtWidgets.QLabel("Details")
        dfont = title_det.font()
        dfont.setWeight(QtGui.QFont.DemiBold)
        title_det.setFont(dfont)
        dl.addWidget(title_det, 0, QtCore.Qt.AlignLeft)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)

        self.v_source = QtWidgets.QLabel("—")
        self.v_target = QtWidgets.QLabel("—")
        self.v_type = QtWidgets.QLabel("—")
        self.v_version = QtWidgets.QLabel("—")
        self.v_schedule = QtWidgets.QLabel("—")
        self.v_move = QtWidgets.QLabel("—")

        form.addRow(self._bold("Quellordner:"), self.v_source)
        form.addRow(self._bold("Zielordner:"), self.v_target)
        form.addRow(self._bold("Lokal/FTP:"), self.v_type)
        form.addRow(self._bold("Versionierung:"), self.v_version)
        form.addRow(self._bold("Zeitplan:"), self.v_schedule)
        form.addRow(self._bold("Nach Transfer verschieben:"), self.v_move)

        dl.addLayout(form)
        card_l.addWidget(self.details)
        self.details.setVisible(not self._collapsed)

        root.addWidget(self.card)

        # ----- Styles (nahe am Screenshot) -----
        self.setStyleSheet("""
            QFrame#card { border: none; }
            QWidget#header {
                background: #222; border-top-left-radius: 6px; border-top-right-radius: 6px;
            }
            QLabel#title { color: #fff; }
            QToolButton#toggle {
                color: #fff; border: 1px solid rgba(255,255,255,0.25);
                border-radius: 4px; padding: 0px 6px; font-weight: 700;
            }
            QWidget#subheader {
                background: #cfcfcf; /* hellgrau Balken */
                border-left: 1px solid #c6c6c6;
                border-right: 1px solid #c6c6c6;
            }
            QFrame#details {
                background: #eeeeee;
                border: 1px solid #d9d9d9;
                border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;
                border-top: none;
            }
        """)

    def _bold(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        return lbl

    def _apply_toggle_glyph(self):
        # ▾ offen, ▸ zu
        self.toggle_btn.setText("▾" if self.toggle_btn.isChecked() else "▸")

    # ---------------- Daten -> UI ----------------
    def _fill(self):
        self.title_lbl.setText(self.plan.get("name", "Neuer Transfer-Plan"))

        src = self.plan.get("source_path") or "—"
        tgt = self.plan.get("target_path") or self.plan.get("destination_path") or "—"
        self.path_summary.setText(f"{src} -> {tgt}")

        use_ftp = bool(self.plan.get("use_ftp", False))
        ftp_name = self.plan.get("ftp_server", "")
        typ = "Lokal (kein FTP)" if not use_ftp else f"FTP{f' ({ftp_name})' if ftp_name else ''}"

        vm = (self.plan.get("versioning_mode")
              or self.plan.get("version_mode")
              or "mirror")
        suffix = self.plan.get("suffix_format", "_v{n}")
        ver_txt = f"suffix (Suffix={suffix})" if vm.lower() == "suffix" else f"mirror (Suffix={suffix})"

        st = self.plan.get("schedule_type", "once")
        stime = self.plan.get("schedule_time", "")
        if st == "weekly":
            sched_txt = f"weekly @ {stime}" if stime else "weekly"
        elif st == "daily":
            sched_txt = f"daily @ {stime}" if stime else "daily"
        else:
            sched_txt = f"once @ {stime}" if stime else "once"

        move_after = self.plan.get("move_after", "") or "—"

        self.v_source.setText(src)
        self.v_target.setText(tgt)
        self.v_type.setText(typ)
        self.v_version.setText(ver_txt)
        self.v_schedule.setText(sched_txt)
        self.v_move.setText(move_after)

    # ---------------- Events ----------------
    def _on_toggle(self):
        expanded = self.toggle_btn.isChecked()
        self._apply_toggle_glyph()
        self.details.setVisible(expanded)
        self._collapsed = not expanded
        # persist body_visible
        try:
            self.plan["body_visible"] = expanded
            self._persist({"body_visible": expanded})
        except Exception as e:
            debug_print(f"[TransferPlanWidget] persist body_visible error: {e}")

    # ---------------- API ----------------
    def set_plan(self, plan: dict):
        self.plan = dict(plan or {})
        # body_visible beachten
        self._collapsed = not self.plan.get("body_visible", True)
        self.toggle_btn.setChecked(not self._collapsed)
        self._apply_toggle_glyph()
        self.details.setVisible(not self._collapsed)
        self._fill()

    # ---------------- Persistenz ----------------
    def _persist(self, changes: dict):
        """
        Bevorzugt manager.update_plan(id, data); ansonsten direkter Fallback in die JSON.
        """
        payload = {**self.plan, **changes}
        plan_id = self.plan.get("id")
        try:
            if self.manager and hasattr(self.manager, "update_plan") and plan_id:
                self.manager.update_plan(plan_id, payload)
            else:
                _update_transfer_plan(payload)
            self.plan.update(changes)
        except Exception as e:
            debug_print(f"[TransferPlanWidget] persist error: {e}")