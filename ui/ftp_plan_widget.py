#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore, QtGui
from utils.config_manager import debug_print
from utils.transfer_plan_manager import update_transfer_plan as _update_transfer_plan


class FtpPlanWidget(QtWidgets.QWidget):
    """
    Karten-Widget für einen einzelnen Transfer-Plan (Optik wie im Screenshot):
      - Dunkler Header mit Titel
      - Subheader: "Quelle -> Ziel"
      - Buttons rechts: Bearbeiten / Jetzt ausführen
      - Ausklappbare "Details"-Sektion im hellen Bereich
      - Kopf-Menü (⋮) mit 'Löschen…'
    Signale:
      - runNowRequested(dict)
      - editRequested(dict)
      - deleteRequested(str)
    Persistenz:
      - optionaler 'manager' mit update_plan(id, data); sonst Fallback _update_transfer_plan(...)
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

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setObjectName("planCard")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(16, 8, 16, 0)
        outer.setSpacing(6)

        # ===== Header (dunkel) =====
        header = QtWidgets.QWidget(objectName="header")
        header_l = QtWidgets.QHBoxLayout(header)
        header_l.setContentsMargins(12, 6, 8, 6)
        header_l.setSpacing(10)

        self.title_lbl = QtWidgets.QLabel(self.plan.get("name", ""))
        self.title_lbl.setObjectName("title")
        header_l.addWidget(self.title_lbl, 1)

        # Menü (⋮) rechts
        self.menu_btn = QtWidgets.QToolButton()
        self.menu_btn.setObjectName("menuBtn")
        self.menu_btn.setText("⋮")
        self.menu_btn.setToolTip("Aktionen")
        self.menu_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(self.menu_btn)
        act_delete = menu.addAction("Löschen…")
        act_delete.triggered.connect(self._emit_delete)
        self.menu_btn.setMenu(menu)
        header_l.addWidget(self.menu_btn, 0, QtCore.Qt.AlignRight)

        # Auf-/Zuklapp-Pfeil (Text, damit garantiert kein fremdes Icon kommt)
        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(not self.is_collapsed)
        self._apply_toggle_glyph()
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        header_l.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignRight)

        outer.addWidget(header)

        # ===== Subheader (hell) =====
        sub = QtWidgets.QWidget(objectName="subheader")
        sub_l = QtWidgets.QHBoxLayout(sub)
        sub_l.setContentsMargins(12, 6, 12, 6)
        sub_l.setSpacing(8)

        self.path_summary = QtWidgets.QLabel("")
        f = self.path_summary.font()
        f.setWeight(QtGui.QFont.DemiBold)
        self.path_summary.setFont(f)
        sub_l.addWidget(self.path_summary, 1)

        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_run = QtWidgets.QPushButton("Jetzt ausführen")
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(dict(self.plan)))
        self.btn_run.clicked.connect(lambda: self.runNowRequested.emit(dict(self.plan)))
        sub_l.addWidget(self.btn_edit, 0)
        sub_l.addWidget(self.btn_run, 0)

        outer.addWidget(sub)

        # ===== Details (helles Feld) =====
        self.details_wrap = QtWidgets.QWidget(objectName="detailsWrap")
        det_l = QtWidgets.QFormLayout(self.details_wrap)
        det_l.setContentsMargins(12, 8, 12, 12)
        det_l.setSpacing(10)
        det_l.setLabelAlignment(QtCore.Qt.AlignLeft)
        det_l.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # „Details“-Titel wie im Screenshot
        self.details_title = QtWidgets.QLabel("Details")
        df = self.details_title.font(); df.setWeight(QtGui.QFont.DemiBold)
        self.details_title.setFont(df)
        det_l.addRow(self.details_title)

        # Zeilen
        self.row_source = QtWidgets.QLabel("—")
        self.row_target = QtWidgets.QLabel("—")
        self.row_target_type = QtWidgets.QLabel("—")
        self.row_version = QtWidgets.QLabel("—")
        self.row_schedule = QtWidgets.QLabel("—")
        self.row_moveafter = QtWidgets.QLabel("—")

        det_l.addRow(self._bold("Quellordner:"), self.row_source)
        det_l.addRow(self._bold("Zielordner:"), self.row_target)
        det_l.addRow(self._bold("Lokal/FTP:"), self.row_target_type)
        det_l.addRow(self._bold("Versionierung:"), self.row_version)
        det_l.addRow(self._bold("Zeitplan:"), self.row_schedule)
        det_l.addRow(self._bold("Nach Transfer verschieben:"), self.row_moveafter)

        outer.addWidget(self.details_wrap)
        self.details_wrap.setVisible(not self.is_collapsed)

        # ===== Styles (an Screenshot angelehnt) =====
        self.setStyleSheet("""
            QWidget#header {
                background: #222; border-radius: 6px;
            }
            QLabel#title {
                color: #fff; font-weight: 700;
            }
            QWidget#subheader {
                background: #dcdcdc; border-radius: 4px; 
            }
            QWidget#detailsWrap {
                background: #eee; border: 1px solid #ddd; border-radius: 6px;
            }
            QToolButton#toggleBtn {
                color: #fff; font-weight: 700; border: 1px solid rgba(255,255,255,0.25);
                border-radius: 4px; padding: 2px 6px;
            }
            QToolButton#menuBtn {
                color: #fff; border: 1px solid rgba(255,255,255,0.25);
                border-radius: 4px; padding: 2px 6px; font-weight: 700;
            }
        """)

    def _bold(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        return lbl

    def _apply_toggle_glyph(self):
        # ▾ = offen, ▸ = zu
        self.toggle_btn.setText("▾" if self.toggle_btn.isChecked() else "▸")

    # ---------------- State/UI ----------------
    def _refresh(self):
        self.title_lbl.setText(self.plan.get("name", "Neuer Transfer-Plan"))

        src = self.plan.get("source_path", "") or "—"
        tgt = (self.plan.get("target_path") or self.plan.get("destination_path") or "") or "—"
        self.path_summary.setText(f"{src} -> {tgt}")

        use_ftp = bool(self.plan.get("use_ftp", False))
        ftp_name = self.plan.get("ftp_server", "")
        ver_mode = self.plan.get("versioning_mode", self.plan.get("version_mode", "mirror"))
        suffix = self.plan.get("suffix_format", "_v{n}")
        sched_type = self.plan.get("schedule_type", "once")
        sched_time = self.plan.get("schedule_time", "")

        self.row_source.setText(src)
        self.row_target.setText(tgt)
        self.row_target_type.setText("Lokal (kein FTP)" if not use_ftp else f"FTP{f' ({ftp_name})' if ftp_name else ''}")
        if (ver_mode or "").lower() == "suffix":
            self.row_version.setText(f"suffix (Suffix={suffix})")
        else:
            self.row_version.setText(f"mirror (Suffix={suffix})")
        if sched_type == "weekly":
            self.row_schedule.setText(f"weekly @ {sched_time}" if sched_time else "weekly")
        elif sched_type == "daily":
            self.row_schedule.setText(f"daily @ {sched_time}" if sched_time else "daily")
        else:
            self.row_schedule.setText(f"once @ {sched_time}" if sched_time else "once")

        move_after = self.plan.get("move_after", "") or "—"
        self.row_moveafter.setText(move_after)

    # ---------------- Aktionen ----------------
    def _on_toggle_clicked(self):
        expanded = self.toggle_btn.isChecked()
        self._apply_toggle_glyph()
        self.details_wrap.setVisible(expanded)
        self.is_collapsed = not expanded
        # body_visible persistieren
        self.plan["body_visible"] = expanded
        self._persist({"body_visible": expanded})

    def _emit_delete(self):
        pid = self.plan.get("id", "")
        if not pid:
            return
        self.deleteRequested.emit(pid)

    # ---------------- API ----------------
    def set_plan(self, plan: dict):
        self.plan = dict(plan or {})
        self._refresh()

    # ---------------- Persistenz ----------------
    def _persist(self, changes: dict):
        """manager.update_plan bevorzugen; sonst Fallback direkt in Datei."""
        try:
            plan_id = self.plan.get("id")
            if hasattr(self.manager, "update_plan") and plan_id:
                # Manager bekommt MERGED-Stand
                payload = {**self.plan, **changes}
                self.manager.update_plan(plan_id, payload)
                self.plan.update(changes)
            else:
                payload = {**self.plan, **changes}
                _update_transfer_plan(payload)
                self.plan.update(changes)
        except Exception as e:
            debug_print(f"[FtpPlanWidget] persist error: {e}")