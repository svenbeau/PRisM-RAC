#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from PySide6 import QtWidgets, QtCore

from utils.transfer_plan_manager import (
    load_transfer_plans,
    add_transfer_plan,
    update_transfer_plan,
    remove_transfer_plan,
)
from utils.config_manager import debug_print
from ui.ftp_plan_widget import TransferPlanWidget
from ui.ftp_plan_dialog import TransferPlanDialog  # Dialog, der plan_data liefert


class FtpScheduleWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Transferpläne:
      – Oben Buttons (Hinzufügen/Löschen)
      – Darunter ScrollArea mit einem TransferPlanWidget pro Plan
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plans = []
        self._build_ui()
        self.load_plans()

    # ---------------- UI ----------------
    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(5, 5, 5, 5)
        main.setSpacing(6)

        # Buttonzeile
        btn_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transferplan hinzufügen")
        self.add_btn.clicked.connect(self.add_plan)
        self.del_btn = QtWidgets.QPushButton("Transferplan entfernen")
        self.del_btn.clicked.connect(self.delete_selected_plan)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        main.addLayout(btn_row)

        # Scrollbare Liste
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QtWidgets.QWidget()
        self.vbox = QtWidgets.QVBoxLayout(self.container)
        self.vbox.setContentsMargins(4, 4, 4, 4)
        self.vbox.setSpacing(8)
        self.vbox.addStretch()
        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll, 1)

        # Für "Auswahl": wir merken uns das zuletzt geklickte Widget
        self._selected_plan_id = None

    # -------------- Daten laden --------------
    def load_plans(self):
        self._plans = load_transfer_plans() or []
        # Container leeren (bis auf Stretch am Ende)
        for i in reversed(range(self.vbox.count() - 1)):  # -1 wegen Stretch
            item = self.vbox.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        # Widgets neu aufbauen
        for plan in self._plans:
            w = TransferPlanWidget(plan, self)
            # erwartete Signals verdrahten
            w.editRequested.connect(self.edit_plan)
            w.deleteRequested.connect(self.delete_plan_by_id)
            # Klick auf den gesamten Widgetbereich als Auswahl interpretieren
            w.mousePressEvent = self._mk_select_handler(plan.get("id"))
            self.vbox.insertWidget(self.vbox.count() - 1, w)  # vor Stretch

    def _mk_select_handler(self, plan_id):
        def handler(event):
            self._selected_plan_id = plan_id
            event.accept()
        return handler

    # -------------- Helpers --------------
    def _normalize_schedule(self, p: dict):
        """
        Stelle sicher, dass die minimal nötigen Felder vorhanden sind.
        (Defensive Defaults, falls ältere Dialoge/Builds etwas nicht liefern.)
        """
        p.setdefault("id", str(uuid.uuid4()))
        p.setdefault("name", "Neuer Transfer-Plan")
        p.setdefault("schedule_type", "once")
        p.setdefault("schedule_time", "")
        p.setdefault("versioning_mode", "mirror")
        p.setdefault("verify_mode", "size_only")
        p.setdefault("retry_count", 3)
        p.setdefault("use_ftp", False)
        p.setdefault("ftp_server", "")
        p.setdefault("target_path", "")
        p.setdefault("source_is_ftp", False)
        p.setdefault("source_ftp_server", "")
        p.setdefault("source_remote_path", "")
        p.setdefault("source_path", "")
        p.setdefault("move_after", "")
        p.setdefault("auto_delete_after_move_enabled", False)
        p.setdefault("auto_delete_after_move_hours", 48)

    def _find_plan_index(self, plan_id: str) -> int:
        for idx, p in enumerate(self._plans):
            if p.get("id") == plan_id:
                return idx
        return -1

    # -------------- Aktionen --------------
    def add_plan(self):
        dlg = TransferPlanDialog(self)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        p = dlg.get_plan_data()
        debug_print(f"[FtpScheduleWidget] add_plan => plan_data: {p}")
        self._normalize_schedule(p)
        add_transfer_plan(p)
        self.load_plans()

    def edit_plan(self, plan_id: str):
        idx = self._find_plan_index(plan_id)
        if idx < 0:
            return
        current = self._plans[idx]
        dlg = TransferPlanDialog(self, initial_plan=current)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        new_p = dlg.get_plan_data()
        self._normalize_schedule(new_p)
        update_transfer_plan(new_p)
        self.load_plans()

    def delete_plan_by_id(self, plan_id: str):
        idx = self._find_plan_index(plan_id)
        if idx < 0:
            return
        name = self._plans[idx].get("name", "Transfer-Plan")
        if QtWidgets.QMessageBox.question(
            self,
            "Plan löschen?",
            f"Soll der Plan „{name}“ wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) != QtWidgets.QMessageBox.Yes:
            return
        remove_transfer_plan(plan_id)
        self.load_plans()

    def delete_selected_plan(self):
        if not self._selected_plan_id:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte zuerst einen Plan in der Liste auswählen.")
            return
        self.delete_plan_by_id(self._selected_plan_id)