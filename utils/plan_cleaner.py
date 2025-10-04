#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from PySide6 import QtCore

from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager


@dataclass
class CleanerConfig:
    interval_ms: int = 10 * 60 * 1000  # Standard: alle 10 Minuten
    remove_empty_dirs: bool = True
    follow_symlinks: bool = False
    dry_run: bool = False


class PlanCleaner(QtCore.QObject):
    """
    Ein einfacher Cleaner, der auf Basis der Transfer-Pläne "move_after"-Ordner
    nach Dateien durchsucht, die älter als N Stunden sind (auto_delete_after_move_hours),
    und diese löscht. Läuft in eigenem Thread mit QTimer.
    """

    sig_log = QtCore.Signal(str)
    sig_error = QtCore.Signal(str)
    sig_deleted = QtCore.Signal(str)

    def __init__(
        self,
        config_manager: Optional[TransferPlanConfigManager] = None,
        config: CleanerConfig = CleanerConfig(),
        parent=None
    ):
        super().__init__(parent)
        self.cm = config_manager or TransferPlanConfigManager()
        self.cfg = config

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.cfg.interval_ms)
        self._timer.timeout.connect(self._on_tick)

        self._thread = QtCore.QThread(self)
        self.moveToThread(self._thread)
        self._thread.started.connect(self._timer.start, QtCore.Qt.QueuedConnection)

    # ------------- Public API -------------

    @QtCore.Slot()
    def start(self):
        if self._thread.isRunning():
            return
        self._thread.start()
        self._log("[Cleaner] gestartet.")

    @QtCore.Slot(bool)
    def stop(self, wait: bool = False):
        """
        Thread-sicherer Stopp: Timer im eigenen Thread stoppen und Thread beenden.
        """
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(
                self,
                "_stop_internal",
                QtCore.Qt.BlockingQueuedConnection if wait else QtCore.Qt.QueuedConnection
            )
            if wait and self._thread.isRunning():
                self._thread.wait(3000)
            return

        self._stop_internal()
        if wait and self._thread.isRunning():
            self._thread.wait(3000)

    # ------------- Internals -------------

    @QtCore.Slot()
    def _stop_internal(self):
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass
        self._log("[Cleaner] gestoppt.")
        self._thread.quit()

    @QtCore.Slot()
    def _on_tick(self):
        try:
            plans = self.cm.load_plans()
        except Exception as e:
            self._err(f"[Cleaner] Konnte Pläne nicht laden: {e}")
            return

        now = datetime.now()
        for plan in plans:
            try:
                if not plan.get("auto_delete_after_move_enabled"):
                    continue
                hours = int(plan.get("auto_delete_after_move_hours", 0) or 0)
                if hours <= 0:
                    continue
                base = plan.get("move_after") or ""
                if not base or not os.path.isdir(base):
                    continue

                cutoff = now - timedelta(hours=hours)
                self._log(f"[Cleaner] Prüfe '{base}' (>{hours}h) – Plan: {plan.get('name','?')}")

                for root, dirs, files in os.walk(base, followlinks=self.cfg.follow_symlinks):
                    # Dateien prüfen
                    for fn in files:
                        fp = os.path.join(root, fn)
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                        except Exception:
                            continue
                        if mtime <= cutoff:
                            if self.cfg.dry_run:
                                self._log(f"[Cleaner] (dry-run) Lösche: {fp}")
                            else:
                                try:
                                    os.remove(fp)
                                    self.sig_deleted.emit(fp)
                                except Exception as e:
                                    self._err(f"[Cleaner] Löschen fehlgeschlagen: {fp}: {e}")

                    # Leere Ordner optional entfernen
                    if self.cfg.remove_empty_dirs:
                        try:
                            if not os.listdir(root):
                                if not self.cfg.dry_run:
                                    os.rmdir(root)
                                    self._log(f"[Cleaner] Leeren Ordner entfernt: {root}")
                        except Exception:
                            pass
            except Exception as e:
                self._err(f"[Cleaner] Fehler in Plan {plan.get('name')}: {e}")

    # ------------- Helpers -------------

    def _log(self, msg: str):
        debug_print(msg)
        self.sig_log.emit(msg)

    def _err(self, msg: str):
        debug_print(msg)
        self.sig_error.emit(msg)