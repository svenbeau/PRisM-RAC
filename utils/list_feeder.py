#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import time
import shutil
from dataclasses import dataclass
from typing import List, Optional

from PySide6 import QtCore

@dataclass
class FeedItem:
    file_path: str
    target_subdir: Optional[str] = None
    rename_to: Optional[str] = None

class ListFeederWorker(QtCore.QThread):
    """
    Liest eine CSV und speist die Dateien in den Monitor-Ordner ein.

    Strategie (wenn move_files=False):
      1) Hardlink (os.link) falls Quelle & Ziel auf demselben Volume
      2) Symlink (os.symlink) andernfalls
      3) Copy (shutil.copy2) als Fallback ODER Fehler, wenn links_only=True

    Damit entsteht minimaler Traffic. Der bestehende Hotfolder-Workflow bleibt unangetastet.
    """
    progress = QtCore.Signal(int, int)       # processed, total
    log = QtCore.Signal(str)                 # log text lines
    error = QtCore.Signal(str)               # error message
    finished_ok = QtCore.Signal()            # completed without fatal error
    cancelled = QtCore.Signal()              # user cancelled

    def __init__(self,
                 csv_path: str,
                 monitor_dir: str,
                 move_files: bool = False,
                 interval_seconds: float = 0.5,
                 ensure_unique_names: bool = True,
                 links_only: bool = False,
                 parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.monitor_dir = monitor_dir
        self.move_files = move_files
        self.interval_seconds = max(0.0, float(interval_seconds))
        self.ensure_unique_names = ensure_unique_names
        self.links_only = links_only
        self._cancel = False
        self._items: List[FeedItem] = []

    def cancel(self):
        self._cancel = True

    # ---- intern ----

    def _read_csv(self) -> List[FeedItem]:
        items: List[FeedItem] = []
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV nicht gefunden: {self.csv_path}")

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "file_path" not in reader.fieldnames:
                raise ValueError("CSV benötigt mindestens die Spalte 'file_path'.")

            for row in reader:
                file_path = (row.get("file_path") or "").strip()
                if not file_path:
                    continue
                target_subdir = (row.get("target_subdir") or "").strip() or None
                rename_to = (row.get("rename_to") or "").strip() or None
                items.append(FeedItem(file_path=file_path,
                                      target_subdir=target_subdir,
                                      rename_to=rename_to))
        return items

    def _ensure_dir(self, path: str):
        os.makedirs(path, exist_ok=True)

    def _unique_name(self, dst_path: str) -> str:
        if not self.ensure_unique_names or not os.path.exists(dst_path):
            return dst_path
        base_dir = os.path.dirname(dst_path)
        stem, ext = os.path.splitext(os.path.basename(dst_path))
        i = 1
        while True:
            cand = os.path.join(base_dir, f"{stem}__{i}{ext}")
            if not os.path.exists(cand):
                return cand
            i += 1

    def _emit(self, text: str):
        self.log.emit(text)

    def _same_device(self, a: str, b: str) -> bool:
        try:
            return os.stat(a).st_dev == os.stat(b).st_dev
        except Exception:
            return False

    def _link_first_transfer(self, src: str, dst: str) -> str:
        """
        Versucht Hardlink -> Symlink -> Copy (falls erlaubt).
        Rückgabe: 'hardlink' | 'symlink' | 'copy'
        Wirft Exception, wenn links_only=True und Copy nötig wäre.
        """
        # Hardlink
        try:
            if self._same_device(src, os.path.dirname(dst)):
                if os.path.exists(dst):
                    os.remove(dst)
                os.link(src, dst)
                return "hardlink"
        except Exception:
            pass

        # Symlink
        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.symlink(src, dst)
            return "symlink"
        except Exception:
            pass

        # Copy-Fallback
        if self.links_only:
            raise RuntimeError("Verlinken nicht möglich (Hard/Sym). 'Nur verlinken' aktiv – Copy-Fallback unterdrückt.")
        shutil.copy2(src, dst)
        return "copy"

    # ---- QThread.run ----

    def run(self):
        try:
            self._items = self._read_csv()
        except Exception as e:
            self.error.emit(f"CSV konnte nicht gelesen werden: {e}")
            return

        total = len(self._items)
        processed = 0
        self._emit(f"Starte Einspeisung: {total} Einträge aus {self.csv_path}")

        for item in self._items:
            if self._cancel:
                self._emit("Abbruch durch Benutzer.")
                self.cancelled.emit()
                return

            src = item.file_path
            if not os.path.isabs(src):
                csv_dir = os.path.dirname(os.path.abspath(self.csv_path))
                src = os.path.abspath(os.path.join(csv_dir, src))

            if not os.path.exists(src):
                self._emit(f"Übersprungen (nicht gefunden): {src}")
                processed += 1
                self.progress.emit(processed, total)
                continue

            # Zielordner bestimmen
            target_dir = self.monitor_dir
            if item.target_subdir:
                target_dir = os.path.join(self.monitor_dir, item.target_subdir)
            try:
                self._ensure_dir(target_dir)
            except Exception as e:
                self._emit(f"Fehler beim Erstellen von {target_dir}: {e}")
                processed += 1
                self.progress.emit(processed, total)
                continue

            # Zieldateiname
            dst_name = item.rename_to if item.rename_to else os.path.basename(src)
            dst_path = os.path.join(target_dir, dst_name)
            dst_path = self._unique_name(dst_path)

            # Transfer
            try:
                if self.move_files:
                    # Move: rename auf gleichem Volume; sonst shutil.move (kopiert)
                    if self._same_device(src, target_dir):
                        os.rename(src, dst_path)
                        self._emit(f"Verschoben (rename, gleiches Volume): {src} → {dst_path}")
                    else:
                        shutil.move(src, dst_path)
                        self._emit(f"Verschoben (move, anderes Volume): {src} → {dst_path}")
                else:
                    method = self._link_first_transfer(src, dst_path)
                    if method == "hardlink":
                        self._emit(f"Hardlink: {src} ⇒ {dst_path}")
                    elif method == "symlink":
                        self._emit(f"Symlink:  {src} ⇒ {dst_path}")
                    else:
                        self._emit(f"Kopiert:  {src} → {dst_path}")
            except Exception as e:
                self._emit(f"Fehler bei Transfer {src} → {dst_path}: {e}")
                processed += 1
                self.progress.emit(processed, total)
                continue

            processed += 1
            self.progress.emit(processed, total)

            # Pause, damit der Hotfolder-Watcher sauber triggert
            if self.interval_seconds > 0:
                slept = 0.0
                while slept < self.interval_seconds:
                    if self._cancel:
                        self._emit("Abbruch durch Benutzer.")
                        self.cancelled.emit()
                        return
                    time.sleep(min(0.1, self.interval_seconds - slept))
                    slept += 0.1

        self._emit("Einspeisung abgeschlossen.")
        self.finished_ok.emit()