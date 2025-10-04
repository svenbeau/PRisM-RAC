#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import shutil
import time
from dataclasses import dataclass
from typing import List

from PySide6 import QtCore


@dataclass
class _FeederRow:
    file_path: str
    target_subdir: str = ""
    rename_to: str = ""


class ListFeederWorker(QtCore.QThread):
    """
    Arbeiter-Thread für das Einspeisen einer CSV-Liste in den Monitor-Ordner.
    Bevorzugt Links (Hardlink/Symlink), fällt – falls erlaubt – auf Kopieren zurück.
    In der aktuellen UI-Konfiguration wird NICHT verschoben und Copy-Fallback ist erlaubt.
    """

    # bestehend
    progress = QtCore.Signal(int, int)     # processed, total
    log = QtCore.Signal(str)
    error = QtCore.Signal(str)
    finished_ok = QtCore.Signal()
    cancelled = QtCore.Signal()

    # NEU: Warteschlangen-Signale
    item_started = QtCore.Signal(str, int, int)      # src, idx(1-based), total
    item_result = QtCore.Signal(bool, str, int)      # ok, dst, idx(1-based)

    def __init__(
        self,
        csv_path: str,
        monitor_dir: str,
        move_files: bool = False,
        interval_seconds: float = 0.5,
        ensure_unique_names: bool = True,
        links_only: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.csv_path = csv_path
        self.monitor_dir = monitor_dir
        self.move_files = bool(move_files)
        self.interval_seconds = float(interval_seconds or 0.0)
        self.ensure_unique_names = bool(ensure_unique_names)
        self.links_only = bool(links_only)

        self._cancel = False
        self._fail_count = 0

    # ------------- Lebenszyklus -------------

    def cancel(self):
        self._cancel = True

    @property
    def fail_count(self) -> int:
        return int(self._fail_count)

    def run(self):
        try:
            rows = self._read_csv(self.csv_path)
        except Exception as e:
            self.error.emit(f"CSV konnte nicht gelesen werden: {e}")
            return

        total = len(rows)
        self.progress.emit(0, total)
        self.log.emit(f"Einträge geladen: {total}")

        csv_dir = os.path.dirname(os.path.abspath(self.csv_path))

        processed = 0
        for idx, r in enumerate(rows, start=1):
            if self._cancel:
                self.cancelled.emit()
                return

            # Quelle auflösen (relativ zur CSV zulassen)
            src = r.file_path
            if not os.path.isabs(src):
                src = os.path.normpath(os.path.join(csv_dir, src))

            # Start-Info an UI
            self.item_started.emit(src, idx, total)

            if not os.path.exists(src):
                self.log.emit(f"[SKIP {idx}] Quelle nicht gefunden: {src}")
                self.item_result.emit(False, "", idx)
                self._fail_count += 1
                self.progress.emit(processed, total)
                continue

            # Zielbasis: Monitor[/target_subdir]
            target_dir = self.monitor_dir
            if r.target_subdir:
                target_dir = os.path.join(target_dir, r.target_subdir)

            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                self.log.emit(f"[SKIP {idx}] Zielordner kann nicht erstellt werden: {target_dir} – {e}")
                self.item_result.emit(False, "", idx)
                self._fail_count += 1
                self.progress.emit(processed, total)
                continue

            # Zielname
            base_name = r.rename_to.strip() or os.path.basename(src)
            dst = os.path.join(target_dir, base_name)

            # Eindeutige Namen bei Kollision
            if self.ensure_unique_names:
                dst = self._make_unique(dst)

            try:
                self._place_file(src, dst)
                self.log.emit(f"[OK {idx}] → {dst}")
                processed += 1
                self.item_result.emit(True, dst, idx)
                self.progress.emit(processed, total)
            except Exception as e:
                self.log.emit(f"[FAIL {idx}] {os.path.basename(src)} → {dst}: {e}")
                self._fail_count += 1
                self.item_result.emit(False, dst, idx)
                self.progress.emit(processed, total)

            # kleine Pause zwischen Jobs (mit Abbruchfenster)
            if self.interval_seconds > 0:
                for _ in range(int(self.interval_seconds * 10)):
                    if self._cancel:
                        self.cancelled.emit()
                        return
                    time.sleep(0.1)

        self.finished_ok.emit()

    # ------------- Helpers -------------

    def _read_csv(self, path: str) -> List[_FeederRow]:
        """
        CSV robust einlesen:
        - UTF-8 mit BOM (utf-8-sig)
        - Delimiter-Autodetect (Sniffer) mit Fallback auf ; , \t
        - Header normalisieren (strip + lower)
        - akzeptierte Spalten: file_path [pflicht], target_subdir, rename_to
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=",;\t")
            except Exception:
                class _Fallback(csv.Dialect):
                    delimiter = ";"
                    quotechar = '"'
                    doublequote = True
                    skipinitialspace = True
                    lineterminator = "\n"
                    quoting = csv.QUOTE_MINIMAL
                dialect = _Fallback()

            reader = csv.reader(f, dialect)
            try:
                raw_header = next(reader)
            except StopIteration:
                raise ValueError("CSV ist leer.")

            header = [h.strip().lower() for h in raw_header]
            col_idx = {name: i for i, name in enumerate(header)}

            if "file_path" not in col_idx:
                if "filepath" in col_idx:
                    col_idx["file_path"] = col_idx["filepath"]
                else:
                    raise ValueError("CSV benötigt mindestens die Spalte 'file_path'.")

            tgt_idx = col_idx.get("target_subdir")
            ren_idx = col_idx.get("rename_to")

            rows: List[_FeederRow] = []
            for row in reader:
                if not any((c.strip() if i < len(row) else "") for i, c in enumerate(row or [])):
                    continue
                try:
                    fp = row[col_idx["file_path"]].strip()
                except Exception:
                    continue
                if not fp:
                    continue
                tgt = (row[tgt_idx].strip() if tgt_idx is not None and tgt_idx < len(row) else "")
                ren = (row[ren_idx].strip() if ren_idx is not None and ren_idx < len(row) else "")
                rows.append(_FeederRow(file_path=fp, target_subdir=tgt, rename_to=ren))

            return rows

    def _make_unique(self, dst: str) -> str:
        if not os.path.exists(dst):
            return dst
        base, ext = os.path.splitext(dst)
        n = 1
        while True:
            cand = f"{base}__{n}{ext}"
            if not os.path.exists(cand):
                return cand
            n += 1

    def _place_file(self, src: str, dst: str):
        if self.move_files:
            shutil.move(src, dst)
            return

        # 1) Hardlink
        try:
            os.link(src, dst)
            return
        except Exception:
            pass

        # 2) Symlink
        try:
            rel = os.path.relpath(src, os.path.dirname(dst))
            os.symlink(rel, dst)
            return
        except Exception:
            pass

        # 3) Kopieren (wenn Links nicht möglich)
        if self.links_only:
            raise RuntimeError("Link nicht möglich und 'links_only' ist aktiv.")
        shutil.copy2(src, dst)