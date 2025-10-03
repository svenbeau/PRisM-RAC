#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from PySide6 import QtCore

from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager


@dataclass
class CleanerConfig:
    interval_ms: int = 10 * 60 * 1000  # alle 10 Minuten
    remove_empty_dirs: bool = True
    follow_symlinks: bool = False
    dry_run: bool = False


class PlanCleaner(QtCore.QObject):
    """
    Räumt die in Transfer-Plänen definierten 'move_after'-Ordner gemäß
    'auto_delete_after_move_enabled' / 'auto_delete_after_move_hours' auf.
    Läuft zyklisch in einem QThread mit QTimer.
    """

    sig_log = QtCore.Signal(str)
    sig_error = QtCore.Signal(str)
    sig_deleted = QtCore.Signal(str)

    def __init__(
        self,
        config_manager: Optional[TransferPlanConfigManager] = None,
        config: CleanerConfig = CleanerConfig(),
        parent: Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        self.cm = config_manager or TransferPlanConfigManager()
        self.cfg = config

        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.cfg.interval_ms)
        self._timer.timeout.connect(self._tick)

        self._thread = QtCore.QThread()
        self._timer.moveToThread(self._thread)
        self.moveToThread(self._thread)
        self._thread.started.connect(self._timer.start)

    @QtCore.Slot()
    def start(self):
        if not self._thread.isRunning():
            self._thread.start()
            self._emit_log("[Cleaner] gestartet.")

    @QtCore.Slot()
    def stop(self):
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass

        if QtCore.QThread.currentThread() is self._thread:
            try:
                self._thread.quit()
            except Exception:
                pass
            self._emit_log("[Cleaner] gestoppt.")
            return

        try:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)
        finally:
            self._emit_log("[Cleaner] gestoppt.")

    # -------- intern --------

    @QtCore.Slot()
    def _tick(self):
        try:
            plans = self.cm.load_plans()
        except Exception as e:
            self._emit_err(f"[Cleaner] Konnte Pläne nicht laden: {e}")
            return

        now = datetime.now()
        for p in plans:
            try:
                if not p.get("auto_delete_after_move_enabled"):
                    continue
                hours = int(p.get("auto_delete_after_move_hours", 0) or 0)
                if hours <= 0:
                    continue
                base = (p.get("move_after") or "").strip()
                if not base or not os.path.isdir(base):
                    continue

                cutoff = now - timedelta(hours=hours)
                self._emit_log(f"[Cleaner] Prüfe '{base}' (>{hours}h) – Plan: {p.get('name','?')}")
                self._cleanup_folder(base, cutoff)
            except Exception as e:
                self._emit_err(f"[Cleaner] Fehler bei Plan '{p.get('name','?')}': {e}")

    def _cleanup_folder(self, folder: str, cutoff_dt: datetime):
        # Dateien & Ordner
        try:
            for entry in os.scandir(folder):
                path = entry.path
                try:
                    stat = entry.stat(follow_symlinks=self.cfg.follow_symlinks)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if mtime <= cutoff_dt:
                        if entry.is_file(follow_symlinks=self.cfg.follow_symlinks):
                            if not self.cfg.dry_run:
                                os.remove(path)
                            self.sig_deleted.emit(path)
                        elif entry.is_dir(follow_symlinks=self.cfg.follow_symlinks):
                            # rekursiv aufräumen
                            self._cleanup_folder(path, cutoff_dt)
                            if self.cfg.remove_empty_dirs:
                                if not self.cfg.dry_run:
                                    try:
                                        os.rmdir(path)
                                        self.sig_deleted.emit(path)
                                    except OSError:
                                        pass  # nicht leer -> bleibt
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass

    # -------- Helpers --------
    def _emit_log(self, msg: str):
        debug_print(msg)
        self.sig_log.emit(msg)

    def _emit_err(self, msg: str):
        debug_print(msg)
        self.sig_error.emit(msg)