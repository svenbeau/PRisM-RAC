#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PlanCleaner – Log-basiertes Aufräumen der Hotfolder-Ausgänge (Success / Fault).

NEU (Option 3):
- Löscht Dateien in 02_Success / 03_Fault NICHT mehr nach mtime,
  sondern anhand des "letzten Verarbeitungszeitpunkts" aus dem globalen Log
  (utils.log_manager -> global_log.json).
- Sehr sprechende Debug-Logs: zeigt Cutoff, gefundenen Log-Timestamp, Safety-Fenster usw.
- Sicherheitsfenster (safety_window_minutes): schützt frische Dateien, auch wenn Log alt ist.
- Schutz der "letzten N" Dateien (protect_last_n) pro Ordner – optional.
- hf_gate_mode:
    - "always"           -> immer aufräumen
    - "never"            -> niemals Success/Fault anfassen
    - "watcher_running"  -> nur, wenn der Hotfolder-Watcher aktiv ist (derzeit konservativ als 'True' behandelt,
                            s.u. _is_hotfolder_active()).

Voraussetzungen:
- utils.log_manager muss 'get_global_log_path' oder 'get_global_log_dir' bereitstellen;
  wir versuchen mehrere Fallbacks, um den Logpfad zu finden.
- Hotfolder-Configs liefern:
    - success_dir, fault_dir
    - auto_delete_success_enabled + auto_delete_success_hours (Cutoff)
    - auto_delete_fault_enabled  + auto_delete_fault_hours
"""

import os
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

from PySide6 import QtCore

# ---- Imports aus deinem Projekt ----
from utils.config_manager import debug_print
try:
    # bevorzugte Quelle
    from utils.log_manager import get_global_log_path as _get_global_log_path
except Exception:
    _get_global_log_path = None

try:
    # Hotfolder-Configs einlesen
    from utils.hotfolder_config_manager import HotfolderConfigManager
except Exception:
    HotfolderConfigManager = None  # zur Not brechen wir den Tick sauber ab


# =========================
#   Konfiguration
# =========================

@dataclass
class CleanerConfig:
    interval_ms: int = 10 * 60 * 1000      # alle 10 Minuten
    remove_empty_dirs: bool = True
    follow_symlinks: bool = False
    dry_run: bool = False
    # Gate für Hotfolder-Cleanup
    hf_gate_mode: str = "always"           # "always" | "never" | "watcher_running"
    # Wann erster Lauf?
    run_immediately: bool = False

    # --- NEU: Log-basierte Parameter ---
    use_log_age_for_hf: bool = True        # wenn False -> kein HF-Cleanup
    safety_window_minutes: int = 5         # schützt frische Dateien zusätzlich (mtime)
    protect_last_n: int = 0                # pro Ordner NIE löschen (z.B. 5 schützt die 5 jüngsten Log-Items)
    # Falls kein Log-Eintrag auffindbar:
    delete_without_log_entry: bool = False # False = nie löschen, wenn keine Logspur existiert


# =========================
#   PlanCleaner
# =========================

class PlanCleaner(QtCore.QThread):
    """
    Thread, der periodisch Success/Fault mit Hilfe des globalen Logs aufräumt.
    """
    sig_log = QtCore.Signal(str)
    sig_error = QtCore.Signal(str)
    sig_deleted = QtCore.Signal(str)

    def __init__(self, config: CleanerConfig, config_manager=None, parent=None):
        super().__init__(parent)
        self.config = config
        # 'config_manager' wird in der aktuellen App mit TransferPlanConfigManager befüllt;
        # für HF-Cleanup brauchen wir HotfolderConfigManager separat.
        self.plan_config_manager = config_manager
        self._stop = False

    # ---------- Lebenszyklus ----------

    def stop(self):
        self._stop = True

    def run(self):
        # optional: erster Lauf verzögert
        if not self.config.run_immediately:
            self._sleep_ms(self.config.interval_ms)

        while not self._stop:
            try:
                self._tick()
            except Exception as e:
                self._emit_error(f"[Cleaner] Unhandled exception im Tick: {e}")
            self._sleep_ms(self.config.interval_ms)

    # ---------- Ein Tick ----------

    def _tick(self):
        # Nur HF-Cleanup in dieser Datei (Option 3).
        if not self.config.use_log_age_for_hf:
            self._emit_log("[Cleaner] HF-Cleanup (logbasiert) ist deaktiviert (use_log_age_for_hf=False).")
            return

        if self.config.hf_gate_mode == "never":
            self._emit_log("[Cleaner] HF-Cleanup: Gate=never → übersprungen.")
            return

        # Hotfolder-Configs laden
        if HotfolderConfigManager is None:
            self._emit_error("[Cleaner] HotfolderConfigManager nicht verfügbar – HF-Cleanup übersprungen.")
            return

        hf_manager = HotfolderConfigManager()
        hotfolders = hf_manager.get_hotfolders() or []
        if not hotfolders:
            self._emit_log("[Cleaner] Keine Hotfolder gefunden – HF-Cleanup übersprungen.")
            return

        # Globales Log einlesen → Map: name -> letzter timestamp
        log_path = self._resolve_global_log_path()
        last_ts_map = self._build_last_processed_map(log_path)

        # Lauf pro Hotfolder
        for hf in hotfolders:
            # Gate "watcher_running": derzeit konservativ als "True"
            if self.config.hf_gate_mode == "watcher_running" and not self._is_hotfolder_active(hf):
                self._emit_log(f"[Cleaner] HF '{hf.get('name','?')}' nicht aktiv (Gate=watcher_running) → übersprungen.")
                continue

            self._clean_single_hotfolder(hf, last_ts_map)

    # ---------- HF-Cleanup (ein Hotfolder) ----------

    def _clean_single_hotfolder(self, hf: dict, last_ts_map: Dict[str, float]):
        name = hf.get("name", "(ohne)")
        now = time.time()

        # Success
        if hf.get("auto_delete_success_enabled", False):
            hours = int(hf.get("auto_delete_success_hours", 24) or 24)
            success_dir = hf.get("success_dir", "")
            if success_dir and os.path.isdir(success_dir):
                self._emit_log(f"[Cleaner] [LOG-DELETE] Success prüfen: {success_dir} (>{hours}h seit VERARBEITET)")
                self._delete_by_log_age(
                    base_dir=success_dir,
                    cutoff_hours=hours,
                    last_ts_map=last_ts_map,
                    now_ts=now,
                    label="Success"
                )

        # Fault
        if hf.get("auto_delete_fault_enabled", False):
            hours = int(hf.get("auto_delete_fault_hours", 72) or 72)
            fault_dir = hf.get("fault_dir", "")
            if fault_dir and os.path.isdir(fault_dir):
                self._emit_log(f"[Cleaner] [LOG-DELETE] Fault prüfen:   {fault_dir} (>{hours}h seit VERARBEITET)")
                self._delete_by_log_age(
                    base_dir=fault_dir,
                    cutoff_hours=hours,
                    last_ts_map=last_ts_map,
                    now_ts=now,
                    label="Fault"
                )

    # ---------- Kern: Löschen nach Log-Alter ----------

    def _delete_by_log_age(self,
                           base_dir: str,
                           cutoff_hours: int,
                           last_ts_map: Dict[str, float],
                           now_ts: float,
                           label: str):
        checked = 0
        deleted = 0

        # optional: "schütze letzte N" – wir bestimmen "jüngst verarbeitet" über Log-Zeit
        protect_set = set()
        if self.config.protect_last_n > 0:
            protect_set = self._pick_last_n_processed(base_dir, last_ts_map, self.config.protect_last_n)
            if protect_set:
                self._emit_log(f"[Cleaner]   Schutz: {len(protect_set)} jüngste Dateien im Ordner (per Log) werden nicht gelöscht.")

        safety_cutoff = now_ts - (self.config.safety_window_minutes * 60)
        log_cutoff = now_ts - (cutoff_hours * 3600)

        for root, _, files in os.walk(base_dir):
            for fname in files:
                # .hidden überspringen
                if fname.startswith("."):
                    continue
                fpath = os.path.join(root, fname)
                checked += 1

                # Safety: mtime noch sehr frisch? -> überspringen
                try:
                    mtime = os.path.getmtime(fpath)
                except Exception:
                    mtime = 0.0
                if mtime > safety_cutoff:
                    self._emit_log(f"[Cleaner]   (skip) {label}: {fpath} – innerhalb Safety-Window ({self.config.safety_window_minutes} min).")
                    continue

                # Schutz letzter N
                key = fname  # Basename als Schlüssel im Log
                if key in protect_set:
                    self._emit_log(f"[Cleaner]   (keep) {label}: {fpath} – unter den letzten {self.config.protect_last_n} (per Log).")
                    continue

                # Wann zuletzt verarbeitet?
                last_ts = last_ts_map.get(key)
                if last_ts is None:
                    # Keine Logspur → nur löschen, wenn explizit erlaubt
                    if not self.config.delete_without_log_entry:
                        self._emit_log(f"[Cleaner]   (skip) {label}: {fpath} – keine Logspur gefunden.")
                        continue
                    # Optional: mtime-basierter Fallback? (standard: NEIN)
                    # Hier bewusst: aus Gründen der Nachvollziehbarkeit NICHT löschen.
                    self._emit_log(f"[Cleaner]   (skip) {label}: {fpath} – delete_without_log_entry=False.")
                    continue

                # Ist Log-Zeit älter als Cutoff?
                if last_ts <= log_cutoff:
                    # Löschen
                    if self.config.dry_run:
                        self._emit_log(f"[Cleaner]   (dry-run) delete {label}: {fpath} – last={self._fmt(last_ts)}, cutoff={self._fmt(log_cutoff)}")
                    else:
                        try:
                            os.remove(fpath)
                            deleted += 1
                            self._emit_deleted(fpath)
                            self._emit_log(f"[Cleaner]   Removed {label}: {fpath} – last={self._fmt(last_ts)} (> {cutoff_hours}h)")
                        except Exception as e:
                            self._emit_error(f"[Cleaner]   Konnte {label} nicht löschen: {fpath} – {e}")
                else:
                    self._emit_log(f"[Cleaner]   (keep) {label}: {fpath} – last={self._fmt(last_ts)} <= cutoff={self._fmt(log_cutoff)}")

        self._emit_log(f"[Cleaner]   Checked={checked}, Deleted={deleted} in {base_dir} (>{cutoff_hours}h seit VERARBEITET)")

        # Option: leere Ordner entfernen
        if self.config.remove_empty_dirs and not self.config.dry_run:
            self._remove_empty_dirs(base_dir)

    # ---------- Hilfen: „letzte N“ bestimmen ----------

    def _pick_last_n_processed(self, base_dir: str, last_ts_map: Dict[str, float], n: int) -> set:
        """
        Liefert die Menge der basenames der N jüngsten (laut Log) Dateien, die aktuell in base_dir liegen.
        """
        items: List[Tuple[str, float]] = []  # (basename, last_ts)
        for root, _, files in os.walk(base_dir):
            for fname in files:
                if fname.startswith("."):
                    continue
                ts = last_ts_map.get(fname)
                if ts is not None:
                    items.append((fname, ts))
        # sortiert nach "zuletzt verarbeitet" absteigend
        items.sort(key=lambda x: x[1], reverse=True)
        keep = {fname for (fname, _) in items[:max(0, n)]}
        return keep

    # ---------- Hilfen: globales Log laden ----------

    def _resolve_global_log_path(self) -> Optional[str]:
        """
        Versuche den globalen Logpfad aufzulösen. Bevorzugt utils.log_manager.get_global_log_path().
        Fallback: ~/Library/Application Support/PRisM-CC/logs/global_log.json (macOS).
        """
        try:
            if callable(_get_global_log_path):
                p = _get_global_log_path()
                if p and os.path.exists(p):
                    return p
        except Exception:
            pass

        # Fallback (macOS Standard in deinem Projekt)
        fallback = os.path.expanduser("~/Library/Application Support/PRisM-CC/logs/global_log.json")
        return fallback if os.path.exists(fallback) else None

    def _build_last_processed_map(self, log_path: Optional[str]) -> Dict[str, float]:
        """
        Liest global_log.json und baut eine Map:
            basename -> letzter timestamp (epoch seconds)
        Wir benutzen 'filename' und 'timestamp' aus deinen Logeinträgen.
        """
        result: Dict[str, float] = {}
        if not log_path:
            self._emit_log("[Cleaner] Kein global_log.json gefunden – es werden keine Dateien aufgrund fehlender Logspur gelöscht.")
            return result

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self._emit_error(f"[Cleaner] Konnte Log nicht lesen: {log_path} – {e}")
            return result

        if not isinstance(data, list):
            self._emit_error(f"[Cleaner] Unerwartetes Logformat (keine Liste): {log_path}")
            return result

        count = 0
        for entry in data:
            # Erwartetes Format aus add_log_entry(...):
            # { "timestamp": ISO-String, "filename": "foo.tif", ... }
            ts_iso = entry.get("timestamp")
            fname = entry.get("filename")
            if not ts_iso or not fname:
                continue
            try:
                # ISO‐Zeit in epoch
                dt = datetime.fromisoformat(ts_iso)
                ts = dt.timestamp()
            except Exception:
                # toleranter Parser (z.B. wenn 'Z' drin wäre)
                try:
                    dt = datetime.strptime(ts_iso.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    ts = dt.timestamp()
                except Exception:
                    continue
            base = os.path.basename(str(fname))
            # nur "letzter" Timestamp
            prev = result.get(base)
            if prev is None or ts > prev:
                result[base] = ts
                count += 1

        self._emit_log(f"[Cleaner] Log geladen ({count} Einträge in Index) aus: {log_path}")
        return result

    # ---------- Utils ----------

    def _remove_empty_dirs(self, base_dir: str):
        # von unten nach oben
        for root, dirs, files in os.walk(base_dir, topdown=False):
            # symlinks ignorieren, wenn follow_symlinks=False
            try:
                if not self.config.follow_symlinks and os.path.islink(root):
                    continue
            except Exception:
                pass
            try:
                # ist leer?
                if not os.listdir(root):
                    os.rmdir(root)
                    self._emit_log(f"[Cleaner] Leeren Ordner entfernt: {root}")
            except Exception:
                # ggf. Rechteprobleme: ignorieren
                pass

    @staticmethod
    def _fmt(ts: float) -> str:
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts)

    def _sleep_ms(self, ms: int):
        waited = 0
        step = 200
        while not self._stop and waited < ms:
            QtCore.QThread.msleep(min(step, ms - waited))
            waited += step

    def _is_hotfolder_active(self, hf: dict) -> bool:
        """
        Gate 'watcher_running': ohne direkten Zugriff auf deinen HotfolderMonitor
        entscheiden wir konservativ. Wenn du später eine aktive Watcher-Abfrage
        übergibst, koppel sie hier ein.
        """
        # TODO: Später per Callback/Provider implementieren.
        return True

    # ---------- Signal-Helfer ----------

    def _emit_log(self, msg: str):
        try:
            self.sig_log.emit(msg)
        except Exception:
            pass
        debug_print(msg)

    def _emit_error(self, msg: str):
        try:
            self.sig_error.emit(msg)
        except Exception:
            pass
        debug_print(msg)

    def _emit_deleted(self, path: str):
        try:
            self.sig_deleted.emit(path)
        except Exception:
            pass
        # zusätzlicher Debug erfolgt in _emit_log beim Löschvorgang