#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Dict, List

from PySide6 import QtWidgets, QtCore

from utils.transfer_plan_manager import (
    load_transfer_plans,
    add_transfer_plan,
    remove_transfer_plan,
    update_transfer_plan,
)
from utils.config_manager import debug_print

from ui.ftp_plan_widget import TransferPlanWidget
from ui.ftp_plan_dialog import TransferPlanDialog
from ui.transfer_queue_dialog import TransferQueueDialog  # vorhandener Dialog mit Datei-Warteschlange/Progress


class FtpScheduleWidget(QtWidgets.QWidget):
    """
    Verwaltung der Transferpläne + eingebauter Scheduler.
    - „Jetzt ausführen“ und Scheduler-Trigger öffnen je Plan ein TransferQueueDialog-Fenster,
      befüllen die Dateiliste und starten den Transfer asynchron.
    - Unten: kleines Log für Scheduler-Ereignisse.
    """

    planTriggered = QtCore.Signal(dict)  # optionaler Hook nach außen

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick_interval_ms = 15_000
        self._tolerance = timedelta(seconds=90)
        self._open_transfers: List[TransferQueueDialog] = []  # Referenzen halten, damit Dialoge nicht vom GC gekillt werden

        self._build_ui()
        self.load_plans()

        # Scheduler starten
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self._tick_interval_ms)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()
        debug_print("[SCHEDULER] gestartet (15s Tick, 90s Toleranz)")

    # ---------------- UI ----------------

    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(5, 5, 5, 5)
        main.setSpacing(5)

        # Button-Leiste
        row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transferplan hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Transferplan entfernen")
        row.addWidget(self.add_btn)
        row.addWidget(self.del_btn)
        row.addStretch(1)
        main.addLayout(row)

        # Scroll für Plan-Widgets
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QtWidgets.QWidget()
        self.inner_layout = QtWidgets.QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(5, 5, 5, 5)
        self.inner_layout.setSpacing(10)
        self.scroll.setWidget(self.inner)
        main.addWidget(self.scroll, 1)

        # Kleines Log nur für Scheduler-Meldungen
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(90)
        main.addWidget(self.log_edit, 0)

        # Aktionen
        self.add_btn.clicked.connect(self.add_plan)
        self.del_btn.clicked.connect(self.remove_any_plan)

    def _append_log(self, msg: str):
        self.log_edit.appendPlainText(msg)
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    # ---------------- Plans laden / UI befüllen ----------------

    def load_plans(self):
        # vorhandene löschen
        while self.inner_layout.count():
            item = self.inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        plans = load_transfer_plans()
        for plan in plans:
            w = TransferPlanWidget(plan, manager=None, parent=self.inner)
            w.editRequested.connect(self.edit_plan)
            w.deleteRequested.connect(self.delete_plan_by_id)
            w.runNowRequested.connect(self._on_run_now)  # öffnet TransferQueueDialog und startet
            self.inner_layout.addWidget(w)

        self.inner_layout.addStretch(1)
        debug_print(f"[SCHEDULER] Pläne geladen: {len(plans)}")

    # ---------------- CRUD ----------------

    def add_plan(self):
        dlg = TransferPlanDialog({"id": self._gen_id()}, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_plan = dlg.plan_data
            new_plan.setdefault("last_run", "")
            new_plan.setdefault("completed_once_at", "")
            self._normalize_schedule(new_plan)
            add_transfer_plan(new_plan)
            self.load_plans()

    def edit_plan(self, plan: dict):
        dlg = TransferPlanDialog(plan, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            updated = dlg.plan_data
            updated.setdefault("last_run", plan.get("last_run", ""))
            updated.setdefault("completed_once_at", plan.get("completed_once_at", ""))
            self._normalize_schedule(updated)
            update_transfer_plan(updated)
            self.load_plans()

    def delete_plan_by_id(self, plan_id: str):
        reply = QtWidgets.QMessageBox.question(
            self, "Löschen", "Transferplan wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            remove_transfer_plan(plan_id)
            self.load_plans()

    def remove_any_plan(self):
        plans = load_transfer_plans()
        if not plans:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Transferpläne vorhanden.")
            return
        self.delete_plan_by_id(plans[0].get("id", ""))

    # ---------------- Ad-hoc: Jetzt ausführen -> TransferQueueDialog ----------------

    def _on_run_now(self, plan: dict):
        """
        Öffnet den vorhandenen TransferQueueDialog für diesen Plan und startet den Transfer.
        Mehrere Pläne können parallel laufen: pro Plan ein Dialogfenster.
        """
        self._append_log(f"[UI] Starte 'Jetzt ausführen' → {plan.get('name')}")
        self._open_transfer_dialog(plan, bring_to_front=True)

    def _open_transfer_dialog(self, plan: dict, bring_to_front: bool = False):
        dlg = TransferQueueDialog(plan, parent=self)
        # Referenz halten, bis der Dialog/Worker fertig ist
        self._open_transfers.append(dlg)
        def _cleanup():
            try:
                self._open_transfers.remove(dlg)
            except ValueError:
                pass
        dlg.finished.connect(_cleanup)

        dlg.show()
        if bring_to_front:
            dlg.raise_()
            dlg.activateWindow()
        # WICHTIG: Dateiliste sammeln + Worker starten
        dlg.start_transfer()

    # ---------------- Scheduler ----------------

    @QtCore.Slot()
    def _on_timer_tick(self):
        try:
            plans = load_transfer_plans()
        except Exception as e:
            debug_print(f"[SCHEDULER] Fehler beim Laden der Pläne: {e}")
            return

        now = datetime.now()
        any_triggered = False

        for plan in plans:
            if self._is_due(plan, now):
                self._append_log(f"[SCHEDULER] Trigger: {plan.get('name')} ({plan.get('id')})")
                any_triggered = True
                # Stempel setzen und persistieren
                plan["last_run"] = now.strftime("%Y-%m-%d %H:%M")
                if plan.get("schedule_type", "once") == "once":
                    plan["completed_once_at"] = plan["last_run"]
                try:
                    update_transfer_plan(plan)
                except Exception as e:
                    debug_print(f"[SCHEDULER] update_transfer_plan() Fehler: {e}")

                # Dialog öffnen & starten (nicht modal, kann im Hintergrund laufen)
                self._open_transfer_dialog(plan, bring_to_front=False)
                # Optional zusätzlich nach außen signalisieren:
                self.planTriggered.emit(plan)

        if any_triggered:
            self.load_plans()

    def _is_due(self, plan: Dict, now: datetime) -> bool:
        stype = plan.get("schedule_type", "once")
        raw = plan.get("schedule_time", "")
        try:
            sched_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M") if raw else None
        except ValueError:
            debug_print(f"[SCHEDULER] Ungültiges schedule_time: {raw} ({plan.get('name')})")
            return False

        if stype == "once":
            if plan.get("completed_once_at"):
                return False
            return self._in_window(sched_dt, now, self._tolerance)

        last_run = None
        if plan.get("last_run"):
            try:
                last_run = datetime.strptime(plan["last_run"], "%Y-%m-%d %H:%M")
            except ValueError:
                last_run = None

        target_hour = sched_dt.hour
        target_min = sched_dt.minute

        if stype == "daily":
            today_target = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            if not self._in_window(today_target, now, self._tolerance):
                return False
            if last_run and last_run.date() == now.date():
                return False
            return True

        if stype == "weekly":
            target_weekday = sched_dt.isoweekday()
            if now.isoweekday() != target_weekday:
                return False
            weekly_target = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            if not self._in_window(weekly_target, now, self._tolerance):
                return False
            if last_run:
                ly, lw, _ = last_run.isocalendar()
                ny, nw, _ = now.isocalendar()
                if (ly, lw) == (ny, nw):
                    return False
            return True

        return False

    @staticmethod
    def _in_window(target: datetime, now: datetime, tol: timedelta) -> bool:
        if target is None:
            return False
        delta = now - target
        if abs(delta) <= tol:
            return True
        if delta.total_seconds() > 0 and delta <= tol:
            return True
        return False

    # ---------------- Utils ----------------

    @staticmethod
    def _gen_id() -> str:
        import uuid
        return str(uuid.uuid4())

    @staticmethod
    def _normalize_schedule(p: dict):
        """
        Harmonisierungen:
        - 'destination_path' → 'target_path'
        - 'version_mode' ↔ 'versioning_mode'
        """
        dest = (p.get("destination_path") or "").strip()
        if dest and not p.get("target_path"):
            p["target_path"] = dest

        vm = p.get("version_mode") or p.get("versioning_mode") or "mirror"
        p["version_mode"] = vm
        p["versioning_mode"] = vm