#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import shutil
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

from PySide6 import QtCore

# Kompatibel zu deinem Projekt
try:
    from utils.config_manager import debug_print
except Exception:
    def debug_print(msg: str):  # Fallback, falls außerhalb des Projekts gestartet
        print(f"[DEBUG] {msg}")


@dataclass
class _CsvRow:
    src: str
    target_subdir: str
    rename_to: str


class ListFeederWorker(QtCore.QThread):
    """
    Liest eine CSV und speist die dort gelisteten Dateien in den Monitor-Ordner ein.
    Diese Version arbeitet **Copy-only**:
      - Keine Hardlinks
      - Keine Symlinks
      - Immer echte Kopien (shutil.copy2)
    Konflikte werden (optional) durch eindeutige Namen vermieden.
    """

    # Bestehende Signale (vom Dialog bereits verdrahtet)
    progress = QtCore.Signal(int, int)           # processed, total
    log = QtCore.Signal(str)                     # text
    error = QtCore.Signal(str)                   # fatal error -> Dialog zeigt MessageBox
    finished_ok = QtCore.Signal()                # Ende ohne Abbruch
    cancelled = QtCore.Signal()                  # Benutzerabbruch

    # Vom Dialog genutzt
    item_started = QtCore.Signal(str, int, int)  # src, idx, total
    item_result = QtCore.Signal(bool, str, int)  # ok, dst, idx

    def __init__(
        self,
        *,
        csv_path: str,
        monitor_dir: str,
        move_files: bool = False,                 # wird in dieser Copy-only-Version ignoriert (immer Kopie)
        interval_seconds: float = 0.5,
        ensure_unique_names: bool = True,
        links_only: bool = False,                 # wird ignoriert (keine Links in dieser Version)
        parent=None
    ):
        super().__init__(parent)
        self.csv_path = csv_path
        self.monitor_dir = monitor_dir
        self.interval_seconds = max(0.0, float(interval_seconds))
        self.ensure_unique_names = bool(ensure_unique_names)

        self._abort = False
        self._rows: List[_CsvRow] = []

    # ---------- öffentlich ----------

    def cancel(self):
        self._abort = True

    # ---------- Thread ----------

    def run(self):
        try:
            # 1) CSV einlesen
            ok, msg = self._load_csv()
            if not ok:
                self._emit_error(msg)
                return

            total = len(self._rows)
            self.log.emit(f"CSV gelesen: {total} Einträge")
            if total == 0:
                self.finished_ok.emit()
                return

            # 2) pro Eintrag kopieren
            processed = 0
            for idx, row in enumerate(self._rows, start=1):
                if self._abort:
                    self.cancelled.emit()
                    return

                self.item_started.emit(row.src, idx, total)
                ok, dst, emsg = self._copy_one(row)
                if ok:
                    self.log.emit(f"✓ {os.path.basename(row.src)} → {dst}")
                else:
                    self.log.emit(f"✗ {os.path.basename(row.src)} – {emsg}")

                self.item_result.emit(ok, dst, idx)

                processed += 1
                self.progress.emit(processed, total)

                # kurze Pause, damit der HF seriell arbeiten kann
                self._sleep_seconds(self.interval_seconds)

            self.finished_ok.emit()

        except Exception as e:
            self._emit_error(f"Unerwarteter Fehler im Worker: {e}")

    # ---------- CSV ----------

    @staticmethod
    def _clean(s: str) -> str:
        """Header/Strings robust normalisieren (BOM, NBSP, Quotes, Whitespace)."""
        if s is None:
            return ""
        return (
            str(s)
            .replace("\ufeff", "")     # BOM
            .replace("\xa0", " ")      # NBSP -> space
            .strip()
            .strip('"')
            .strip("'")
        )

    def _detect_delimiter_and_skip(self, f) -> Tuple[str, bool]:
        """
        Erkennt den Delimiter (berücksichtigt `sep=;`-Zeile).
        Gibt (delimiter, skip_first_line) zurück.
        """
        pos0 = f.tell()
        first = f.readline()
        first_clean = (first or "").strip().lower()
        if first_clean.startswith("sep=") and len(first_clean) >= 5:
            delim = first_clean.split("=", 1)[1][:1]
            debug_print(f"[ListFeederWorker] CSV 'sep=' erkannt → Delimiter='{delim}'")
            return delim or ";", True

        # Kein sep=; -> sniffen auf Basis eines Samples
        sample = first + f.read(4096)
        f.seek(pos0, 0)

        # Manuelle Heuristik: zähle Zeichen
        counts = {
            ",": sample.count(","),
            ";": sample.count(";"),
            "\t": sample.count("\t"),
            "|": sample.count("|"),
        }
        # Favorisiere das häufigste von den gängigen Kandidaten
        delim = max(counts, key=counts.get)
        # Wenn alles 0 ist, default auf Komma
        if counts[delim] == 0:
            delim = ","

        debug_print(f"[ListFeederWorker] CSV Delimiter erkannt → '{delim}' (Heuristik {counts})")
        return delim, False

    def _load_csv(self) -> Tuple[bool, str]:
        if not self.csv_path or not os.path.exists(self.csv_path):
            return False, "CSV konnte nicht gelesen werden: Datei existiert nicht."

        rows: List[_CsvRow] = []
        base_dir = os.path.dirname(os.path.abspath(self.csv_path))

        try:
            with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
                delimiter, skip_first = self._detect_delimiter_and_skip(f)
                if skip_first:
                    _ = f.readline()  # sep=...-Zeile überspringen

                reader = csv.DictReader(f, delimiter=delimiter)
                raw_headers = reader.fieldnames or []
                headers = [self._clean(h) for h in raw_headers]
                headers_lower = [h.lower() for h in headers]
                debug_print(f"[ListFeederWorker] CSV-Spalten: {headers} (Delimiter='{delimiter}')")

                # Pflichtfeld prüfen (case-insensitiv)
                if "file_path" not in headers_lower:
                    self.log.emit(f"[DEBUG] Header erkannt: {headers}")
                    return False, "CSV benötigt mindestens die Spalte 'file_path'."

                # Mapping: lowercase -> Originalheader
                lower_to_orig = {h.lower(): h for h in headers}

                def get_val(row: dict, key: str) -> str:
                    # tolerant: case-insensitiv & robust clean
                    if key in row:
                        return self._clean(row.get(key, ""))
                    lk = key.lower()
                    orig = lower_to_orig.get(lk)
                    if orig is not None and orig in row:
                        return self._clean(row.get(orig, ""))
                    return ""

                for rec in reader:
                    raw_path = get_val(rec, "file_path")
                    if not raw_path:
                        continue

                    # relative Pfade relativ zur CSV
                    src = os.path.abspath(os.path.join(base_dir, raw_path)) \
                        if not os.path.isabs(raw_path) else os.path.abspath(raw_path)

                    target_subdir = get_val(rec, "target_subdir")
                    rename_to = get_val(rec, "rename_to")

                    rows.append(_CsvRow(src=src,
                                        target_subdir=target_subdir,
                                        rename_to=rename_to))

        except Exception as e:
            return False, f"CSV konnte nicht gelesen werden: {e}"

        # Validierung
        kept: List[_CsvRow] = []
        bad = 0
        for r in rows:
            if not os.path.exists(r.src) or not os.path.isfile(r.src):
                bad += 1
                self.log.emit(f"[WARN] Quelle nicht gefunden/keine Datei: {r.src}")
                continue
            kept.append(r)

        self._rows = kept
        if bad > 0:
            self.log.emit(f"[INFO] {bad} Eintrag/Einträge wegen fehlender Quelle übersprungen.")
        return True, ""

    # ---------- Kopierlogik (Copy-only) ----------

    def _copy_one(self, row: _CsvRow) -> Tuple[bool, str, str]:
        """
        Kopiert row.src nach monitor_dir[/target_subdir]/(rename_to|basename).
        Liefert (ok, dst_path, msg).
        """
        try:
            # Zielverzeichnis
            dst_dir = self.monitor_dir
            if row.target_subdir:
                row_dir = row.target_subdir.replace("\\", "/").strip("/").strip()
                if row_dir:
                    dst_dir = os.path.join(dst_dir, row_dir)

            os.makedirs(dst_dir, exist_ok=True)

            # Zielname
            if row.rename_to:
                base, ext = os.path.splitext(row.rename_to)
                if not ext:
                    _, src_ext = os.path.splitext(row.src)
                    dst_name = base + src_ext
                else:
                    dst_name = row.rename_to
            else:
                dst_name = os.path.basename(row.src)

            dst_path = os.path.join(dst_dir, dst_name)

            if self.ensure_unique_names and os.path.exists(dst_path):
                dst_path = self._unique_path(dst_path)

            # echte Kopie inkl. Metadaten/Zeitstempel
            self._copy_file(row.src, dst_path)

            return True, dst_path, ""

        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _copy_file(src: str, dst: str) -> None:
        # copy2: erhält mtime/atime, Permissions soweit möglich
        shutil.copy2(src, dst)
        # Optional: mtime auf "jetzt" setzen (derzeit deaktiviert)
        # os.utime(dst, None)

    @staticmethod
    def _unique_path(path: str) -> str:
        """
        Hängt __1, __2, … an, bis ein freier Name gefunden ist.
        """
        base, ext = os.path.splitext(path)
        i = 1
        candidate = f"{base}__{i}{ext}"
        while os.path.exists(candidate):
            i += 1
            candidate = f"{base}__{i}{ext}"
        return candidate

    # ---------- Utils ----------

    @staticmethod
    def _sleep_seconds(sec: float):
        # fein granular, damit Abbruch zeitnah greift
        end = time.time() + max(0.0, sec)
        while time.time() < end:
            time.sleep(min(0.05, end - time.time()))

    def _emit_error(self, msg: str):
        """
        Einheitliche Fehlerausgabe:
        - schreibt in Debug-Log
        - emittiert error-Signal (Dialog zeigt MessageBox)
        """
        try:
            debug_print(f"[ListFeederWorker] ERROR: {msg}")
        except Exception:
            pass
        try:
            self.error.emit(str(msg))
        except Exception:
            pass