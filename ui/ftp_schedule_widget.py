#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PySide6 import QtWidgets, QtCore

from utils.transfer_plan_manager import (
    load_transfer_plans,
    add_transfer_plan,
    remove_transfer_plan,
    update_transfer_plan,
)
from utils.config_manager import debug_print  # für Logs
from ui.ftp_plan_widget import FtpPlanWidget
from ui.ftp_plan_dialog import FtpPlanDialog


class FtpScheduleWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Transferpläne.
    Zusätzlich ist hier jetzt ein kleiner Scheduler eingebaut:
      - Ein QTimer prüft periodisch (alle 15 s), ob Pläne fällig sind.
      - Fällige Pläne lösen das Signal `planTriggered` mit dem Plan-Dict aus.
      - Der Aufrufer (z. B. Haupt-Widget) kann dieses Signal an einen Worker binden.
    """

    # ==> Hook: hier kann der Aufrufer seinen Worker anbinden
    planTriggered = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plans_cache: List[Dict] = []
        self._last_reload_mtime: Optional[float] = None

        self.init_ui()
        self.load_plans()

        # --- Scheduler: alle 15 Sekunden prüfen ---
        self._tick_interval_ms = 15_000
        self._tolerance = timedelta(seconds=90)  # Fenstertoleranz
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self._tick_interval_ms)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()
        debug_print("[SCHEDULER] gestartet (15s Tick, 90s Toleranz)")

    # ---------------- UI ----------------

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transferplan hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Transferplan entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(10)
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.add_btn.clicked.connect(self.add_plan)
        self.del_btn.clicked.connect(self.remove_plan)

    def load_plans(self):
        """UI auffrischen + Cache aktualisieren."""
        # Alte Widgets entfernen
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._plans_cache = load_transfer_plans()
        for plan in self._plans_cache:
            widget = FtpPlanWidget(plan, parent=self.container_widget)
            widget.editRequested.connect(self.edit_plan)
            widget.deleteRequested.connect(self.delete_plan)
            self.container_layout.addWidget(widget)
        self.container_layout.addStretch()
        debug_print(f"[SCHEDULER] Pläne geladen: {len(self._plans_cache)}")

    # ---------------- CRUD ----------------

    def add_plan(self):
        dlg = FtpPlanDialog(parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_plan = dlg.get_plan()
            # Standardfelder für Scheduler, wenn nicht vorhanden
            new_plan.setdefault("last_run", "")
            new_plan.setdefault("completed_once_at", "")
            add_transfer_plan(new_plan)
            self.load_plans()

    def edit_plan(self, plan):
        dlg = FtpPlanDialog(plan, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            updated_plan = dlg.get_plan()
            # vorhandene Scheduler-Felder erhalten, falls UI sie nicht setzt
            updated_plan.setdefault("last_run", plan.get("last_run", ""))
            updated_plan.setdefault("completed_once_at", plan.get("completed_once_at", ""))
            update_transfer_plan(updated_plan)
            self.load_plans()

    def delete_plan(self, plan_id):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Löschen",
            "Transferplan wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            remove_transfer_plan(plan_id)
            self.load_plans()

    def remove_plan(self):
        # Beispielweise: Entferne den ersten Plan (oder implementiere eine Auswahl)
        plans = load_transfer_plans()
        if not plans:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Transferpläne vorhanden.")
            return
        plan_id = plans[0].get("id")
        self.delete_plan(plan_id)

    # ---------------- Scheduler ----------------

    @QtCore.Slot()
    def _on_timer_tick(self):
        """Periodischer Tick: Pläne neu laden (leicht), Fälligkeit prüfen, fällige auslösen."""
        try:
            # Immer frisch laden (Datei ist klein) – vermeidet In-Memory-Drift nach UI-Änderungen
            plans = load_transfer_plans()
        except Exception as e:
            debug_print(f"[SCHEDULER] Fehler beim Laden der Pläne: {e}")
            return

        now = datetime.now()
        any_triggered = False

        for plan in plans:
            if self._is_due(plan, now):
                debug_print(f"[SCHEDULER] Trigger: {plan.get('name')} ({plan.get('id')})")
                any_triggered = True

                # Markiere Start (last_run), für „once“ zusätzlich completed_once_at
                plan["last_run"] = now.strftime("%Y-%m-%d %H:%M")
                if plan.get("schedule_type", "once") == "once":
                    plan["completed_once_at"] = plan["last_run"]

                # Persistieren
                try:
                    update_transfer_plan(plan)
                except Exception as e:
                    debug_print(f"[SCHEDULER] update_transfer_plan() Fehler: {e}")

                # Ausführen signalisieren (Worker/Engine anbinden)
                self.planTriggered.emit(plan)

        if any_triggered:
            # UI auffrischen, damit Zeitstempel sichtbar werden
            self.load_plans()

    def _is_due(self, plan: Dict, now: datetime) -> bool:
        """
        Prüft, ob ein Plan fällig ist.
        Regeln:
          - schedule_time ist lokaler Zeitpunkt "YYYY-MM-DD HH:mm".
          - Fenster: |now - schedule_time(heute/entspr. Intervall)| <= tolerance.
          - „once“: nur wenn noch kein completed_once_at gesetzt ist.
          - „daily/weekly“: wenn seit last_run kein Lauf im entsprechenden Intervall stattfand
                            und wir im Toleranzfenster um die geplante Uhrzeit sind.
        """
        schedule_type = plan.get("schedule_type", "once")
        verify_str = plan.get("verify_mode", "size_only")  # nur falls du das loggen willst
        retry_count = int(plan.get("retry_count", 5))      # dito

        # 1) schedule_time parsen
        sched_raw = plan.get("schedule_time", "")
        try:
            sched_dt = datetime.strptime(sched_raw, "%Y-%m-%d %H:%M") if sched_raw else None
        except ValueError:
            # Falls Format nicht stimmt, nicht laufen lassen
            debug_print(f"[SCHEDULER] Ungültiges schedule_time: {sched_raw} für Plan {plan.get('name')}")
            return False

        # 2) „once“: war schon?
        if schedule_type == "once":
            if plan.get("completed_once_at"):
                return False
            # fällig sobald schedule_time <= now (mit Toleranzfenster nach vorne UND hinten)
            return self._in_window(sched_dt, now, self._tolerance)

        # 3) „daily“ / „weekly“
        last_run_str = plan.get("last_run", "")
        last_run_dt = None
        if last_run_str:
            try:
                last_run_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M")
            except ValueError:
                last_run_dt = None

        # Ziel-uhrzeit aus sched_dt (nur Uhrzeit relevant)
        target_hour = sched_dt.hour
        target_min = sched_dt.minute

        if schedule_type == "daily":
            # Heute um target_hour:target_min ist der Target-Zeitpunkt
            today_target = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            if not self._in_window(today_target, now, self._tolerance):
                return False
            # Wenn heute schon gelaufen, nicht nochmal
            if last_run_dt and last_run_dt.date() == now.date():
                return False
            return True

        if schedule_type == "weekly":
            # In derselben Kalenderwoche, am Wochentag von sched_dt, um target Uhrzeit
            # Wir verwenden isocalendar(): (year, week, weekday 1..7)
            target_weekday = sched_dt.isoweekday()
            now_weekday = now.isoweekday()
            if target_weekday != now_weekday:
                return False
            weekly_target = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            if not self._in_window(weekly_target, now, self._tolerance):
                return False
            if last_run_dt:
                last_year, last_week, _ = last_run_dt.isocalendar()
                now_year, now_week, _ = now.isocalendar()
                if (last_year, last_week) == (now_year, now_week):
                    return False
            return True

        # Unbekannter Typ -> nicht laufen
        return False

    @staticmethod
    def _in_window(target: datetime, now: datetime, tol: timedelta) -> bool:
        """True, wenn now im +-tol-Fenster um target liegt ODER target <= now (Failsafe für knappe Ticks)."""
        if target is None:
            return False
        delta = now - target
        # Fenstercheck
        if abs(delta) <= tol:
            return True
        # Failsafe: falls Timer knapp nach target tickt
        if delta.total_seconds() > 0 and delta <= tol:
            return True
        return False