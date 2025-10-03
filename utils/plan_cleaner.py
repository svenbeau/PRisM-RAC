#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import stat
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, Tuple

from PySide6 import QtCore

# leichte Koppelung für Pläne
from utils.transfer_plan_config_manager import TransferPlanConfigManager


class CleanerConfig(QtCore.QObject):
    """
    Konfiguration für den PlanCleaner.
    """
    def __init__(
        self,
        interval_ms: int = 10 * 60 * 1000,   # alle 10 Minuten
        remove_empty_dirs: bool = True,
        follow_symlinks: bool = False,
        dry_run: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.remove_empty_dirs = remove_empty_dirs
        self.follow_symlinks = follow_symlinks
        self.dry_run = dry_run


class PlanCleaner(QtCore.QThread):
    """
    Periodischer Cleaner, der auf Basis der Transfer-Pläne Dateien im jeweiligen
    'move_after'-Ordner löscht, sobald diese älter als 'auto_delete_after_move_hours' sind.

    Eigenschaften:
    - Läuft in eigenem Thread (blockiert UI nicht).
    - Führt beim Start sofort einen Scan aus (damit nach App-Neustart aufgeräumt wird).
    - Löscht ausschließlich innerhalb der 'move_after'-Ordner aktivierter Pläne.
    - Optionales Aufräumen leerer Unterordner.
    - Dry-Run möglich (nur Logging, keine Löschung).
    """

    sig_log = QtCore.Signal(str)
    sig_deleted = QtCore.Signal(str)
    sig_error = QtCore.Signal(str)

    def __init__(
        self,
        config_manager: TransferPlanConfigManager,
        config: Optional[CleanerConfig] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.cm = config_manager
        self.cfg = config or CleanerConfig()
        self._stop_requested = False

    # ------------- Lifecycle -------------

    def stop(self, wait: bool = True):
        """
        Thread freundlich stoppen.
        """
        self._stop_requested = True
        self.requestInterruption()
        if wait:
            self.wait(3_000)

    def run(self):
        """
        Thread-Loop: sofort scannen, dann periodisch.
        """
        try:
            # Initialscan direkt beim Start (persistentes Verhalten über Neustarts)
            self._scan_all_plans()

            # Periodischer Loop
            interval_s = max(1, int(self.cfg.interval_ms / 1000))
            while not self.isInterruptionRequested() and not self._stop_requested:
                for _ in range(interval_s):
                    if self.isInterruptionRequested() or self._stop_requested:
                        break
                    time.sleep(1)
                if self.isInterruptionRequested() or self._stop_requested:
                    break
                self._scan_all_plans()
        except Exception as e:
            self._emit_error(f"[Cleaner] Unerwarteter Fehler im Thread: {e}\n{traceback.format_exc()}")

    # ------------- Kernlogik -------------

    def _scan_all_plans(self):
        """
        Lädt alle Pläne und wendet die Auto-Delete-Logik auf aktivierte an.
        """
        try:
            plans = self.cm.load_plans()
        except Exception as e:
            self._emit_error(f"[Cleaner] Konnte Pläne nicht laden: {e}")
            return

        # Iteriere über alle Pläne
        for plan in plans:
            if not plan.get("auto_delete_after_move_enabled"):
                continue

            hours = plan.get("auto_delete_after_move_hours", 0)
            if not isinstance(hours, (int, float)) or hours <= 0:
                continue

            move_after = (plan.get("move_after") or "").strip()
            if not move_after:
                continue

            # Sicherheitschecks
            safe, reason = self._is_safe_delete_root(move_after)
            if not safe:
                self._emit_log(f"[Cleaner] Überspringe Plan '{plan.get('name','?')}', unsicherer Zielordner: {reason}")
                continue

            cutoff = datetime.now() - timedelta(hours=float(hours))
            self._emit_log(f"[Cleaner] Prüfe '{move_after}' (>{hours}h) – Plan: {plan.get('name','?')}")

            try:
                deleted_files, deleted_dirs = self._clean_folder(
                    move_after,
                    cutoff=cutoff,
                    remove_empty_dirs=self.cfg.remove_empty_dirs,
                    follow_symlinks=self.cfg.follow_symlinks,
                    dry_run=self.cfg.dry_run,
                )
                if deleted_files or deleted_dirs:
                    self._emit_log(
                        f"[Cleaner] '{move_after}': gelöscht Dateien={deleted_files}, leere Ordner={deleted_dirs} "
                        f"{'(DRY-RUN)' if self.cfg.dry_run else ''}"
                    )
            except Exception as e:
                self._emit_error(f"[Cleaner] Fehler beim Säubern von '{move_after}': {e}")

    def _clean_folder(
        self,
        root: str,
        *,
        cutoff: datetime,
        remove_empty_dirs: bool,
        follow_symlinks: bool,
        dry_run: bool,
    ) -> Tuple[int, int]:
        """
        Löscht Dateien in 'root', deren mtime < cutoff.
        Optional werden leere Ordner nach dem Durchlauf entfernt.

        Returns: (count_deleted_files, count_removed_dirs)
        """
        if not os.path.isdir(root):
            return (0, 0)

        deleted_files = 0
        removed_dirs = 0

        # Walk bottom-up, damit wir leere Ordner einfacher erkennen können
        for dirpath, dirnames, filenames in os.walk(root, topdown=False, followlinks=follow_symlinks):
            # Dateien prüfen
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.lstat(fpath) if not follow_symlinks else os.stat(fpath)
                    # ignorieren, wenn es ein Symlink ist und wir Symlinks nicht folgen
                    if not follow_symlinks and stat.S_ISLNK(st.st_mode):
                        continue

                    mtime = datetime.fromtimestamp(st.st_mtime)
                    if mtime <= cutoff:
                        if dry_run:
                            self._emit_log(f"[Cleaner] (DRY) Lösche: {fpath}")
                        else:
                            try:
                                os.remove(fpath)
                                deleted_files += 1
                                self.sig_deleted.emit(fpath)
                            except Exception as e_del:
                                self._emit_error(f"[Cleaner] Datei konnte nicht gelöscht werden: {fpath} → {e_del}")
                except FileNotFoundError:
                    # Datei wurde parallel entfernt – egal
                    continue
                except Exception as e_stat:
                    self._emit_error(f"[Cleaner] Stat-Fehler bei '{fpath}': {e_stat}")

            # Leere Ordner ggf. entfernen (nur innerhalb von root)
            if remove_empty_dirs:
                try:
                    # Ist Ordner (noch) leer?
                    if not os.listdir(dirpath):
                        rel = os.path.relpath(dirpath, root)
                        if rel == ".":
                            # Root selbst nicht löschen
                            continue
                        if dry_run:
                            self._emit_log(f"[Cleaner] (DRY) Entferne leeren Ordner: {dirpath}")
                        else:
                            try:
                                os.rmdir(dirpath)
                                removed_dirs += 1
                            except OSError:
                                # Ordner doch nicht leer oder keine Rechte → ignorieren
                                pass
                except FileNotFoundError:
                    continue
                except Exception as e_dir:
                    self._emit_error(f"[Cleaner] Fehler beim Ordnercheck '{dirpath}': {e_dir}")

        return (deleted_files, removed_dirs)

    # ------------- Safety -------------

    def _is_safe_delete_root(self, path: str) -> Tuple[bool, str]:
        """
        Grobe Sicherheit: Wir erlauben keine gefährlichen Wurzeln (/, /Users, /Volumes, etc.).
        Zusätzlich prüfen wir, ob der Pfad existiert und ein Verzeichnis ist.
        """
        norm = os.path.abspath(path)

        if not os.path.exists(norm):
            return False, "Pfad existiert nicht"
        if not os.path.isdir(norm):
            return False, "Pfad ist kein Verzeichnis"

        # Sehr grobe Schutzliste
        forbidden = {"/", "/Users", "/Volumes", "/System", "/Applications", "/Library", "/bin", "/etc", "/usr"}
        if norm in forbidden:
            return False, f"'{norm}' ist gesperrt"

        # Sicherstellen, dass der Ordner tief genug ist (z. B. mindestens 2 Ebenen)
        parts = [p for p in norm.split(os.sep) if p]
        if len(parts) < 2:
            return False, "Pfad ist zu kurz/unspezifisch"

        return True, "ok"

    # ------------- Logging -------------

    def _emit_log(self, msg: str):
        self.sig_log.emit(msg)

    def _emit_error(self, msg: str):
        self.sig_error.emit(msg)
        self.sig_log.emit(msg)