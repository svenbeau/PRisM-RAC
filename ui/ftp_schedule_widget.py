#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Dict

from PySide6 import QtWidgets, QtCore

from utils.transfer_plan_manager import (
    load_transfer_plans, add_transfer_plan, remove_transfer_plan, update_transfer_plan,
)
from utils.config_manager import debug_print

# ⬇️ Korrigiert: Karten-Widget & Dialog-Namen
from ui.ftp_plan_widget import FtpPlanWidget
from ui.ftp_plan_dialog import FtpPlanDialog
from ui.transfer_queue_panel import TransferQueuePanel   # Panel unten im Widget

class FtpScheduleWidget(QtWidgets.QWidget):
    planTriggered = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick_interval_ms = 15_000
        self._tolerance = timedelta(seconds=90)
        self._build_ui()
        self.load_plans()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self._tick_interval_ms)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()
        debug_print("[SCHEDULER] gestartet (15s Tick, 90s Toleranz)")

    # UI
    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(5, 5, 5, 5)
        main.setSpacing(5)

        row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transferplan hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Transferplan entfernen")
        row.addWidget(self.add_btn); row.addWidget(self.del_btn); row.addStretch(1)
        main.addLayout(row)

        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.inner = QtWidgets.QWidget()
        self.inner_layout = QtWidgets.QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(5, 5, 5, 5); self.inner_layout.setSpacing(10)
        self.scroll.setWidget(self.inner)
        main.addWidget(self.scroll, 1)

        # ==== Eingebaute Queue unten ====
        self.queue_panel = TransferQueuePanel(parent=self)
        self.queue_panel.setVisible(True)
        main.addWidget(self.queue_panel, 0)

        self.add_btn.clicked.connect(self.add_plan)
        self.del_btn.clicked.connect(self.remove_any_plan)

    # Plans
    def load_plans(self):
        while self.inner_layout.count():
            item = self.inner_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        plans = load_transfer_plans()
        for plan in plans:
            w = FtpPlanWidget(plan, manager=None, parent=self.inner)
            w.editRequested.connect(self.edit_plan)
            w.deleteRequested.connect(self.delete_plan_by_id)
            w.runNowRequested.connect(self._on_run_now)    # -> unten im Panel
            self.inner_layout.addWidget(w)
        self.inner_layout.addStretch(1)
        debug_print(f"[SCHEDULER] Pläne geladen: {len(plans)}")

    def add_plan(self):
        dlg = FtpPlanDialog({"id": self._gen_id()}, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            p = dlg.plan_data; p.setdefault("last_run",""); p.setdefault("completed_once_at","")
            self._normalize_schedule(p); add_transfer_plan(p); self.load_plans()

    def edit_plan(self, plan: dict):
        dlg = FtpPlanDialog(plan, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            upd = dlg.plan_data
            upd.setdefault("last_run", plan.get("last_run",""))
            upd.setdefault("completed_once_at", plan.get("completed_once_at",""))
            self._normalize_schedule(upd); update_transfer_plan(upd); self.load_plans()

    def delete_plan_by_id(self, plan_id: str):
        if QtWidgets.QMessageBox.question(self, "Löschen", "Transferplan wirklich löschen?",
                                          QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            remove_transfer_plan(plan_id); self.load_plans()

    def remove_any_plan(self):
        plans = load_transfer_plans()
        if not plans:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Transferpläne vorhanden."); return
        self.delete_plan_by_id(plans[0].get("id",""))

    # ==== Start unten im Panel ====
    def _on_run_now(self, plan: dict):
        self._start_in_panel(plan, bring_to_front=True)

    def _start_in_panel(self, plan: dict, bring_to_front: bool):
        # Falls gerade ein anderer Transfer läuft, Nachfrage:
        if self.queue_panel.is_busy():
            if QtWidgets.QMessageBox.question(
                self, "Laufender Transfer", "Ein Transfer läuft bereits. Trotzdem neuen starten?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            ) != QtWidgets.QMessageBox.Yes:
                return
        self.queue_panel.set_plan(plan)
        if bring_to_front:
            self.scroll.ensureWidgetVisible(self.queue_panel)
        self.queue_panel.start_transfer()

    # Scheduler
    @QtCore.Slot()
    def _on_timer_tick(self):
        try:
            plans = load_transfer_plans()
        except Exception as e:
            debug_print(f"[SCHEDULER] Fehler beim Laden der Pläne: {e}")
            return

        now = datetime.now()
        for plan in plans:
            if self._is_due(plan, now):
                debug_print(f"[SCHEDULER] Trigger: {plan.get('name')} ({plan.get('id')})")
                plan["last_run"] = now.strftime("%Y-%m-%d %H:%M")
                if plan.get("schedule_type","once") == "once":
                    plan["completed_once_at"] = plan["last_run"]
                try: update_transfer_plan(plan)
                except Exception as e: debug_print(f"[SCHEDULER] update_transfer_plan Fehler: {e}")
                self._start_in_panel(plan, bring_to_front=False)
                self.planTriggered.emit(plan)
        # (optional) self.load_plans() – nur nötig, wenn Zeitstempel im UI sichtbar sein sollen

    def _is_due(self, plan: Dict, now: datetime) -> bool:
        stype = plan.get("schedule_type","once")
        raw = plan.get("schedule_time","")
        try: sched_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M") if raw else None
        except ValueError: return False

        if stype == "once":
            if plan.get("completed_once_at"): return False
            return self._in_window(sched_dt, now, self._tolerance)

        last_run = None
        if plan.get("last_run"):
            try: last_run = datetime.strptime(plan["last_run"], "%Y-%m-%d %H:%M")
            except ValueError: pass

        h, m = sched_dt.hour, sched_dt.minute
        if stype == "daily":
            tgt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if not self._in_window(tgt, now, self._tolerance): return False
            if last_run and last_run.date() == now.date(): return False
            return True
        if stype == "weekly":
            if now.isoweekday() != sched_dt.isoweekday(): return False
            tgt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if not self._in_window(tgt, now, self._tolerance): return False
            if last_run:
                ly, lw, _ = last_run.isocalendar(); ny, nw, _ = now.isocalendar()
                if (ly, lw) == (ny, nw): return False
            return True
        return False

    @staticmethod
    def _in_window(target: datetime, now: datetime, tol: timedelta) -> bool:
        if target is None: return False
        d = now - target
        return abs(d) <= tol or (d.total_seconds() > 0 and d <= tol)

    @staticmethod
    def _gen_id() -> str:
        import uuid; return str(uuid.uuid4())

    @staticmethod
    def _normalize_schedule(p: dict):
        dest = (p.get("destination_path") or "").strip()
        if dest and not p.get("target_path"): p["target_path"] = dest
        vm = p.get("version_mode") or p.get("versioning_mode") or "mirror"
        p["version_mode"] = vm; p["versioning_mode"] = vm