#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore, QtGui


class TransferPlanWidget(QtWidgets.QWidget):
    """
    Kompakte Darstellung eines Transferplans mit Edit-/Löschen-Buttons.
    Stellt die erwarteten Qt-Signale bereit:
        - editRequested(str plan_id)
        - deleteRequested(str plan_id)
    """
    editRequested = QtCore.Signal(str)
    deleteRequested = QtCore.Signal(str)

    def __init__(self, plan: dict, parent=None):
        super().__init__(parent)
        self.plan = plan or {}
        self.plan_id = self.plan.get("id", "")

        self._build_ui()
        self._fill_from_plan()

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Linke Spalte: Titel + Infozeilen
        left_box = QtWidgets.QVBoxLayout()
        left_box.setSpacing(2)

        self.title_lbl = QtWidgets.QLabel("")
        font = self.title_lbl.font()
        font.setBold(True)
        self.title_lbl.setFont(font)

        self.src_lbl = QtWidgets.QLabel("")
        self.dst_lbl = QtWidgets.QLabel("")
        self.sched_lbl = QtWidgets.QLabel("")
        self.opts_lbl = QtWidgets.QLabel("")

        for lbl in (self.src_lbl, self.dst_lbl, self.sched_lbl, self.opts_lbl):
            lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        left_box.addWidget(self.title_lbl)
        left_box.addWidget(self.src_lbl)
        left_box.addWidget(self.dst_lbl)
        left_box.addWidget(self.sched_lbl)
        left_box.addWidget(self.opts_lbl)
        left_box.addStretch()

        # Rechte Spalte: Buttons
        btn_box = QtWidgets.QVBoxLayout()
        btn_box.setSpacing(6)

        self.edit_btn = QtWidgets.QPushButton("Bearbeiten")
        self.del_btn = QtWidgets.QPushButton("Löschen")

        self.edit_btn.clicked.connect(lambda: self.editRequested.emit(self.plan_id))
        self.del_btn.clicked.connect(lambda: self.deleteRequested.emit(self.plan_id))

        btn_box.addWidget(self.edit_btn)
        btn_box.addWidget(self.del_btn)
        btn_box.addStretch()

        layout.addLayout(left_box, 1)
        layout.addLayout(btn_box, 0)

        # Rahmen/Style minimal
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), pal.color(QtGui.QPalette.AlternateBase))
        self.setPalette(pal)

    def _fill_from_plan(self):
        name = self.plan.get("name", "Unbenannter Plan")

        source_is_ftp = bool(self.plan.get("source_is_ftp", False))
        if source_is_ftp:
            src_server = self.plan.get("source_ftp_server", "")
            src_path = self.plan.get("source_remote_path", "")
            src_txt = f"Quelle: FTP [{src_server}] : {src_path or '—'}"
        else:
            src_txt = f"Quelle: {self.plan.get('source_path', '') or '—'}"

        use_ftp = bool(self.plan.get("use_ftp", False))
        if use_ftp:
            dst_server = self.plan.get("ftp_server", "")
            dst_path = self.plan.get("target_path", "")
            dst_txt = f"Ziel: FTP [{dst_server}] : {dst_path or '—'}"
        else:
            dst_txt = f"Ziel: {self.plan.get('target_path', '') or '—'}"

        schedule_type = self.plan.get("schedule_type", "once")
        schedule_time = self.plan.get("schedule_time", "")
        sched_txt = f"Zeitplan: {schedule_type}"
        if schedule_type == "once" and schedule_time:
            sched_txt += f" @ {schedule_time}"

        versioning = self.plan.get("versioning_mode", "mirror")
        verify = self.plan.get("verify_mode", "size_only")
        retry = self.plan.get("retry_count", 3)
        opts_txt = f"Modus: {versioning} • Verify: {verify} • Retries: {retry}"

        self.title_lbl.setText(name)
        self.src_lbl.setText(src_txt)
        self.dst_lbl.setText(dst_txt)
        self.sched_lbl.setText(sched_txt)
        self.opts_lbl.setText(opts_txt)

    # Falls das Widget nach einem Edit aktualisiert werden soll:
    def update_plan(self, new_plan: dict):
        self.plan = new_plan or {}
        self.plan_id = self.plan.get("id", self.plan_id)
        self._fill_from_plan()