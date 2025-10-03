#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import shutil
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any, List, Tuple

import keyring
from PySide6 import QtCore

from utils.config_manager import (
    debug_print,
    load_ftp_servers,
)
from utils.transfer_plan_config_manager import TransferPlanConfigManager
from utils.ftp_manager import FTPManager


@dataclass
class SchedulerConfig:
    """Einstellungen für das Plan-Scanning."""
    scan_interval_ms: int = 30_000          # alle 30s nachsehen
    once_guard_window_s: int = 90            # Toleranzfenster für 'once'-Trigger
    retry_count: int = 2                     # zusätzliche Verbindungs-/Upload-Versuche
    retry_backoff_s: int = 5                 # Pause zwischen Versuchen
    connect_timeout_s: int = 20              # Verbindungs-Timeout (falls FTPManager das unterstützt)


class PlanScheduler(QtCore.QObject):
    """
    Entkoppelter Scheduler:
      - Läuft zyklisch über QTimer in einem eigenen QThread
      - Triggert Pläne anhand schedule_type / schedule_time
      - Führt die Transfers selbstständig aus (FTP/SFTP), inkl. Guarding & Retry
      - Aktualisiert Plan-Felder: last_run, completed_once_at
    """

    # Signale für UI/Logs
    sig_log = QtCore.Signal(str)
    sig_plan_started = QtCore.Signal(str, str)          # plan_id, plan_name
    sig_plan_finished = QtCore.Signal(str, bool, str)   # plan_id, success, message

    def __init__(
        self,
        config_manager: Optional[TransferPlanConfigManager] = None,
        precheck: Optional[Callable[[Dict[str, Any]], bool]] = None,
        config: SchedulerConfig = SchedulerConfig(),
        parent: Optional[QtCore.QObject] = None
    ):
        super().__init__(parent)
        self.cm = config_manager or TransferPlanConfigManager()
        self.cfg = config
        self.precheck = precheck  # z. B. VPN-Check; soll True zurückgeben, sonst überspringen

        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.cfg.scan_interval_ms)
        self._timer.timeout.connect(self._on_tick)

        self._thread = QtCore.QThread()
        self._timer.moveToThread(self._thread)
        self.moveToThread(self._thread)
        self._thread.started.connect(self._timer.start)

        # Reentrancy/Parallel-Schutz
        self._running_ids: set[str] = set()

    # ------------ Public API ------------

    @QtCore.Slot()
    def start(self):
        if not self._thread.isRunning():
            self._thread.start()
            self._emit_log(f"[{self._now_hms()}] Scheduler gestartet.")

    @QtCore.Slot()
    def stop(self):
        """Kontext-sensitiver Stopp (ohne auf sich selbst zu warten)."""
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass

        # Wenn wir im Worker-Thread sind: nicht auf uns selbst warten
        if QtCore.QThread.currentThread() is self._thread:
            try:
                self._thread.quit()
            except Exception:
                pass
            # kein wait() hier!
            self._emit_log(f"[{self._now_hms()}] Scheduler gestoppt.")
            return

        # Wir sind NICHT im Worker-Thread -> sicher warten
        try:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)
        finally:
            self._emit_log(f"[{self._now_hms()}] Scheduler gestoppt.")

    # ------------ Internals ------------

    @QtCore.Slot()
    def _on_tick(self):
        try:
            plans = self.cm.load_plans()
        except Exception as e:
            self._emit_log(f"[{self._now_hms()}] [Scheduler] Konnte Pläne nicht laden: {e}")
            return

        now = datetime.now()
        for plan in plans:
            try:
                if self._should_trigger(plan, now):
                    pid = plan.get("id", "<unknown>")
                    if pid in self._running_ids:
                        continue
                    self._running_ids.add(pid)
                    self._emit_log(f"[{self._now_hms()}] [Scheduler] Trigger für Plan '{plan.get('name','?')}' ({plan.get('schedule_type')})")

                    ok, msg = self._run_plan(plan)
                    plan["last_run"] = datetime.now().isoformat(timespec="seconds")
                    if ok and plan.get("schedule_type") == "once":
                        plan["completed_once_at"] = plan["last_run"]
                    try:
                        self.cm.update_plan(plan["id"], plan)
                    finally:
                        pass

                    self.sig_plan_finished.emit(plan.get("id", ""), ok, msg or "")
                    self._running_ids.discard(pid)
            except Exception as e:
                self._running_ids.discard(plan.get("id", ""))
                self._emit_log(f"[{self._now_hms()}] [Scheduler] Fehler beim Ausführen: {e}")
                traceback.print_exc()

    # --- Trigger-Logik ---

    def _should_trigger(self, plan: Dict[str, Any], now: datetime) -> bool:
        stype = plan.get("schedule_type", "once")
        stime_str = plan.get("schedule_time", "")
        if not stime_str:
            return False

        try:
            sched_dt = datetime.strptime(stime_str, "%Y-%m-%d %H:%M")
        except Exception:
            try:
                hm = datetime.strptime(stime_str[-5:], "%H:%M")
                sched_dt = now.replace(hour=hm.hour, minute=hm.minute, second=0, microsecond=0)
            except Exception:
                return False

        last_run_iso = plan.get("last_run", "")
        if last_run_iso:
            try:
                last = datetime.fromisoformat(last_run_iso)
                if (now - last) < timedelta(seconds=self.cfg.once_guard_window_s):
                    return False
            except Exception:
                pass

        if stype == "once":
            if plan.get("completed_once_at"):
                return False
            window_start = sched_dt
            window_end = sched_dt + timedelta(seconds=self.cfg.once_guard_window_s)
            return window_start <= now <= window_end or (now >= window_end and not plan.get("completed_once_at"))

        if stype == "daily":
            today_sched = now.replace(hour=sched_dt.hour, minute=sched_dt.minute, second=0, microsecond=0)
            if abs((now - today_sched).total_seconds()) <= self.cfg.once_guard_window_s:
                if last_run_iso and last_run_iso[:10] == now.strftime("%Y-%m-%d"):
                    return False
                return True
            return False

        if stype == "weekly":
            if now.weekday() == sched_dt.weekday():
                weekly_sched = now.replace(hour=sched_dt.hour, minute=sched_dt.minute, second=0, microsecond=0)
                if abs((now - weekly_sched).total_seconds()) <= self.cfg.once_guard_window_s:
                    if last_run_iso and last_run_iso[:10] == now.strftime("%Y-%m-%d"):
                        return False
                    return True
            return False

        return False

    # --- Ausführung eines Plans ---

    def _run_plan(self, plan: Dict[str, Any]) -> Tuple[bool, str]:
        plan_name = plan.get("name", "Unbenannt")
        plan_id = plan.get("id", "")
        self.sig_plan_started.emit(plan_id, plan_name)

        if self.precheck:
            try:
                if not self.precheck(plan):
                    self._emit_log(f"[{self._now_hms()}] [Scheduler] Precheck fehlgeschlagen – Ausführung übersprungen.")
                    return False, "Precheck failed"
            except Exception as e:
                self._emit_log(f"[{self._now_hms()}] [Scheduler] Precheck-Fehler: {e}")

        use_ftp = bool(plan.get("use_ftp", False))
        if not use_ftp:
            return self._run_local_copy(plan)

        ftp = FTPManager()
        server_name = plan.get("ftp_server", "")
        srv = next((s for s in load_ftp_servers() if s.get("name") == server_name), None)
        if not srv:
            return False, f"FTP-Server '{server_name}' nicht gefunden."

        protocol = (srv.get("protocol") or "ftp").lower()
        host = srv.get("host", "")
        port = int(srv.get("port", 21))
        if protocol == "sftp":
            port = 22
        user = srv.get("user", "")
        # Passwort ggf. via keyring (FTPManager kann es intern ziehen, hier behalten wir das Pattern)
        _ = keyring.get_password("PRisM-FTP", user) or ""

        ftp.ftp_protocol = protocol
        ftp.host = host
        ftp.port = port
        ftp.user = user

        try:
            ftp.connect()
            self._emit_log(f"[{self._now_hms()}] [Scheduler] Verbunden zu {user}@{host}:{port} ({protocol})")
        except Exception as e:
            return False, str(e)

        try:
            ok, msg = self._upload_folder_with_retry(ftp, plan)
        finally:
            try:
                ftp.disconnect()
                self._emit_log(f"[{self._now_hms()}] Verbindung geschlossen.")
            except Exception:
                pass

        return ok, msg

    # --- Upload/Download Helfer ---

    def _upload_folder_with_retry(self, ftp: FTPManager, plan: Dict[str, Any]) -> Tuple[bool, str]:
        src = plan.get("source_path") or ""
        tgt = plan.get("target_path") or "/"
        versioning = plan.get("versioning_mode", "mirror")

        if not src or not os.path.isdir(src):
            return False, "Ungültiger lokaler Plan."

        try:
            ftp.mkdir_remote(tgt)
        except Exception as e:
            self._emit_log(f"[mkdir_remote:{tgt}] Fehler (final): {e}")

        files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if os.path.isfile(os.path.join(src, f))]
        if not files:
            self._emit_log(f"[{self._now_hms()}] [Scheduler] Keine Dateien im Quellordner.")
            return True, "Keine Dateien zu übertragen."

        try:
            existing = {e[0] for e in ftp.list_directory(tgt)}
        except Exception:
            existing = set()

        for local_path in files:
            base = os.path.basename(local_path)
            remote_dir = tgt
            remote_name = base

            if versioning == "suffix" and base in existing:
                root, ext = os.path.splitext(base)
                v = 2
                candidate = f"{root}_v{v}{ext}"
                while candidate in existing:
                    v += 1
                    candidate = f"{root}_v{v}{ext}"
                remote_name = candidate

            remote_path = (tgt.rstrip("/") + "/" + remote_name).replace("//", "/")
            self._emit_log(f"[{self._now_hms()}] [Scheduler] ↑ {local_path} → {remote_path}")

            success = False
            last_err = ""
            for attempt in range(self.cfg.retry_count + 1):
                try:
                    ftp.upload_file(local_path, remote_dir)
                    success = True
                    break
                except Exception as e:
                    last_err = str(e)
                    if attempt < self.cfg.retry_count:
                        time.sleep(self.cfg.retry_backoff_s)

            if not success:
                return False, f"Upload fehlgeschlagen für {local_path}: {last_err}"

            existing.add(remote_name)

        self._post_process_source(plan, files)
        return True, "Upload abgeschlossen."

    def _post_process_source(self, plan: Dict[str, Any], uploaded_files: List[str]):
        move_after = plan.get("move_after", "")
        if move_after:
            os.makedirs(move_after, exist_ok=True)
            for p in uploaded_files:
                try:
                    target = os.path.join(move_after, os.path.basename(p))
                    if os.path.exists(target):
                        root, ext = os.path.splitext(target)
                        v = 2
                        cand = f"{root}_v{v}{ext}"
                        while os.path.exists(cand):
                            v += 1
                            cand = f"{root}_v{v}{ext}"
                        target = cand
                    shutil.move(p, target)
                except Exception as e:
                    self._emit_log(f"[{self._now_hms()}] [Scheduler] Move-Fehler '{p}': {e}")

        # Auto-Delete nach X Stunden übernimmt der PlanCleaner.

    def _run_local_copy(self, plan: Dict[str, Any]) -> Tuple[bool, str]:
        src = plan.get("source_path") or ""
        tgt = plan.get("target_path") or ""
        if not os.path.isdir(src) or not tgt:
            return False, "Ungültiger lokaler Plan."
        os.makedirs(tgt, exist_ok=True)
        files = [f for f in sorted(os.listdir(src)) if os.path.isfile(os.path.join(src, f))]
        for name in files:
            sp = os.path.join(src, name)
            dp = os.path.join(tgt, name)
            try:
                shutil.copy2(sp, dp)
            except Exception as e:
                return False, f"Kopierfehler {name}: {e}"
        self._post_process_source(plan, [os.path.join(src, f) for f in files])
        return True, "Lokaler Transfer abgeschlossen."

    # --- Helpers ---

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _emit_log(self, text: str):
        debug_print(text)
        self.sig_log.emit(text)