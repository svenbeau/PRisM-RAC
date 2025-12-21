#!/usr/bin/env python3
# plan_scheduler.py
# -*- coding: utf-8 -*-

import os
import time
import json
import shutil
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Dict, Any, List, Tuple

import keyring
from PySide6 import QtCore

from utils.config_manager import (
    debug_print,
    load_ftp_servers,
    load_settings,                # NEU: SMTP/Notify lesen
    get_mail_transfer_info_path,  # NEU: Status-Datei schreiben
)
from utils.transfer_plan_config_manager import TransferPlanConfigManager
from utils.ftp_manager import FTPManager
from utils.mailer import send_transfer_summary_email  # NEU: Mailversand


@dataclass
class SchedulerConfig:
    """Einstellungen für das Plan-Scanning."""
    scan_interval_ms: int = 30_000          # alle 30s nachsehen
    once_guard_window_s: int = 90            # Toleranzfenster für 'once'-Trigger
    retry_count: int = 2                     # zusätzliche Verbindungs-/Upload-Versuche
    retry_backoff_s: int = 5                 # Pause zwischen Versuchen
    connect_timeout_s: int = 20              # Verbindungs-Timeout (wenn FTPManager das unterstützt)


class PlanScheduler(QtCore.QObject):
    """
    Entkoppelter Scheduler:
      - Läuft zyklisch über QTimer in einem eigenen QThread
      - Triggert Pläne anhand schedule_type / schedule_time
      - Führt die Transfers selbstständig aus (FTP/SFTP), inkl. Guarding & Retry
      - Aktualisiert Plan-Felder: last_run, completed_once_at
      - NEU: versendet Mail + schreibt mail_transfer_info.json
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
        parent=None
    ):
        super().__init__(parent)
        self.cm = config_manager or TransferPlanConfigManager()
        self.cfg = config
        self.precheck = precheck  # z.B. VPN-Check

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.cfg.scan_interval_ms)
        self._timer.timeout.connect(self._on_tick)

        self._thread = QtCore.QThread(self)
        self.moveToThread(self._thread)

        # Start des Timers, sobald der Thread läuft
        self._thread.started.connect(self._timer.start, QtCore.Qt.QueuedConnection)

        # Reentrancy/Parallel-Schutz
        self._running_ids: set[str] = set()

    # ------------ Public API ------------

    @QtCore.Slot()
    def start(self):
        """Startet den Scheduler-Thread (nur wenn nicht bereits laufend)."""
        if self._thread.isRunning():
            return
        self._thread.start()
        self._emit_log(f"[{self._now_hms()}] Scheduler gestartet.")

    @QtCore.Slot(bool)
    def stop(self, wait: bool = False):
        """
        Stoppt den Timer im **eigenen** Thread und fährt danach den Thread herunter.
        Kann aus jedem Thread aufgerufen werden.
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

    # ------------ Internals ------------

    @QtCore.Slot()
    def _stop_internal(self):
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass
        self._emit_log(f"[{self._now_hms()}] Scheduler gestoppt.")
        self._thread.quit()

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

                    ok, msg, results = self._run_plan(plan)

                    # Status-Felder aktualisieren
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

        # Zeit parsen
        try:
            sched_dt = datetime.strptime(stime_str, "%Y-%m-%d %H:%M")
        except Exception:
            try:
                hm = datetime.strptime(stime_str[-5:], "%H:%M")
                sched_dt = now.replace(hour=hm.hour, minute=hm.minute, second=0, microsecond=0)
            except Exception:
                return False

        # Doppelstart-Guard
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
        elif stype == "daily":
            today_sched = now.replace(hour=sched_dt.hour, minute=sched_dt.minute, second=0, microsecond=0)
            if abs((now - today_sched).total_seconds()) <= self.cfg.once_guard_window_s:
                if last_run_iso and last_run_iso[:10] == now.strftime("%Y-%m-%d"):
                    return False
                return True
            return False
        elif stype == "weekly":
            if now.weekday() == sched_dt.weekday():
                weekly_sched = now.replace(hour=sched_dt.hour, minute=sched_dt.minute, second=0, microsecond=0)
                if abs((now - weekly_sched).total_seconds()) <= self.cfg.once_guard_window_s:
                    if last_run_iso and last_run_iso[:10] == now.strftime("%Y-%m-%d"):
                        return False
                    return True
            return False
        else:
            return False

    # --- Ausführung eines Plans ---

    def _run_plan(self, plan: Dict[str, Any]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Führt den Plan aus und gibt (ok, msg, results) zurück.
        results: Liste von Dicts mit keys:
            file, direction ("UPLOAD"/"DOWNLOAD"), destination, status ("SUCCESS"/"FAILED"), error (optional)
        """
        plan_name = plan.get("name", "Unbenannt")
        plan_id = plan.get("id", "")
        self.sig_plan_started.emit(plan_id, plan_name)

        if self.precheck:
            try:
                if not self.precheck(plan):
                    self._emit_log(f"[{self._now_hms()}] [Scheduler] Precheck fehlgeschlagen – Ausführung übersprungen.")
                    # auch in diesem Fall Mailstatus schreiben (SKIPPED), damit du es siehst
                    self._write_mail_status(plan, [], "SKIPPED_PRECHECK", "Precheck failed")
                    return False, "Precheck failed", []
            except Exception as e:
                self._emit_log(f"[{self._now_hms()}] [Scheduler] Precheck-Fehler: {e}")

        use_ftp = bool(plan.get("use_ftp", False))
        if not use_ftp:
            ok, msg, res = self._run_local_copy(plan)
            self._send_and_record_mail(plan, ok, msg, res)
            return ok, msg, res

        # FTP/SFTP
        ftp = FTPManager()
        server_name = plan.get("ftp_server", "")
        srv = None
        for s in load_ftp_servers():
            if s.get("name") == server_name:
                srv = s
                break
        if not srv:
            msg = f"FTP-Server '{server_name}' nicht gefunden."
            self._send_and_record_mail(plan, False, msg, [])
            return False, msg, []

        protocol = srv.get("protocol", "ftp")
        host = srv.get("host", "")
        port = int(srv.get("port", 21))
        if (protocol or "ftp").lower() == "sftp":
            port = 22
        user = srv.get("user", "")
        # Passwort aus keyring (FTPManager greift intern darauf zu)
        _ = keyring.get_password("PRisM-FTP", user) or ""

        ftp.ftp_protocol = protocol
        ftp.host = host
        ftp.port = port
        ftp.user = user

        try:
            ftp.connect()
            self._emit_log(f"[{self._now_hms()}] [Scheduler] Verbunden zu {user}@{host}:{port} ({protocol})")
        except Exception as e:
            msg = str(e)
            self._send_and_record_mail(plan, False, msg, [])
            return False, msg, []

        try:
            ok, msg, results = self._upload_folder_with_retry(ftp, plan)
        finally:
            try:
                ftp.disconnect()
                self._emit_log(f"[{self._now_hms()}] Verbindung geschlossen.")
            except Exception:
                pass

        self._send_and_record_mail(plan, ok, msg, results)
        return ok, msg, results

    # --- Upload/Download Helfer ---

    def _upload_folder_with_retry(self, ftp: FTPManager, plan: Dict[str, Any]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        src = plan.get("source_path") or ""
        tgt = plan.get("target_path") or "/"
        verify_mode = plan.get("verify_mode", "size_only")
        versioning = plan.get("versioning_mode", "mirror")

        if not src or not os.path.isdir(src):
            return False, f"Quellordner existiert nicht: {src}", []

        # Zielordner vorbereiten
        try:
            ftp.mkdir_remote(tgt)
        except Exception as e:
            self._emit_log(f"[mkdir_remote:{tgt}] Fehler (final): {e}")

        # Sammle Quelldateien (flach)
        files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if os.path.isfile(os.path.join(src, f))]
        if not files:
            self._emit_log(f"[{self._now_hms()}] [Scheduler] Keine Dateien im Quellordner.")
            # trotzdem Ergebnisse/Mail mit leerer Liste
            return True, "Keine Dateien zu übertragen.", []

        # Bereits existierende Namen ermitteln (für Suffix-Modus)
        try:
            existing = {e[0] for e in ftp.list_directory(tgt)}
        except Exception:
            existing = set()

        results: List[Dict[str, Any]] = []

        for local_path in files:
            base = os.path.basename(local_path)
            remote_dir = tgt
            remote_name = base

            # Versionierung (Suffix)
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

            if success:
                results.append({
                    "file": local_path,
                    "direction": "UPLOAD",
                    "destination": remote_path,
                    "status": "SUCCESS",
                })
            else:
                results.append({
                    "file": local_path,
                    "direction": "UPLOAD",
                    "destination": remote_path,
                    "status": "FAILED",
                    "error": last_err,
                })
                # bei Fehler abbrechen und Ergebnis zurück
                return False, f"Upload fehlgeschlagen für {local_path}: {last_err}", results

            existing.add(remote_name)

        # Nachbearbeitung: Dateien verschieben/löschen
        self._post_process_source(plan, files)

        return True, "Upload abgeschlossen.", results

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

    def _run_local_copy(self, plan: Dict[str, Any]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Lokaler Kopiermodus."""
        src = plan.get("source_path") or ""
        tgt = plan.get("target_path") or ""
        if not os.path.isdir(src) or not tgt:
            return False, "Ungültiger lokaler Plan.", []

        os.makedirs(tgt, exist_ok=True)
        names = [f for f in sorted(os.listdir(src)) if os.path.isfile(os.path.join(src, f))]
        results: List[Dict[str, Any]] = []

        for name in names:
            sp = os.path.join(src, name)
            dp = os.path.join(tgt, name)
            try:
                shutil.copy2(sp, dp)
                results.append({
                    "file": sp,
                    "direction": "COPY",
                    "destination": dp,
                    "status": "SUCCESS",
                })
            except Exception as e:
                results.append({
                    "file": sp,
                    "direction": "COPY",
                    "destination": dp,
                    "status": "FAILED",
                    "error": str(e),
                })
                return False, f"Kopierfehler {name}: {e}", results

        self._post_process_source(plan, [os.path.join(src, f) for f in names])
        return True, "Lokaler Transfer abgeschlossen.", results

    # --- Mail & Statusfile ---

    def _send_and_record_mail(self, plan: Dict[str, Any], ok: bool, msg: str, results: List[Dict[str, Any]]):
        """
        Versendet die Mail (falls konfiguriert) und schreibt mail_transfer_info.json
        in das neue Schema, das das MailStatusWidget darstellen kann.
        """
        settings = {}
        try:
            settings = load_settings() or {}
        except Exception:
            settings = {}

        smtp = (settings.get("smtp") or {})
        notify = (settings.get("notify_email") or "").strip()

        enabled = bool(smtp.get("enabled")) if "enabled" in smtp else True
        host = str(smtp.get("host") or "")
        port = int(smtp.get("port") or 0)
        user = str(smtp.get("user") or "")
        mode = str(smtp.get("mode") or "SSL").upper()

        attempted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        mail_result = "SKIPPED_NO_NOTIFY" if not notify else "SKIPPED_DISABLED" if not enabled else "SENT"
        mail_error = ""

        # nur senden, wenn alles nötige da ist
        if enabled and notify and host:
            try:
                subject = f"PRiSM Transfer {'OK' if ok else 'FAIL'} – {plan.get('name','')}"
                body = (msg or "").strip() or ("Transfer erfolgreich." if ok else "Transfer fehlgeschlagen.")
                sent = send_transfer_summary_email(
                    notify_email=notify,
                    subject=subject,
                    body=body,
                    results=results,
                    plan=plan,
                    settings=settings,
                )
                if not sent:
                    mail_result = "ERROR_SEND"
                    mail_error = "send_transfer_summary_email() returned False"
            except Exception as e:
                mail_result = "ERROR_SEND"
                mail_error = str(e)
                self._emit_log(f"[{self._now_hms()}] Fehler beim Versenden des Transfer-Reports: {e}")
        else:
            if not enabled:
                mail_result = "SKIPPED_DISABLED"
            elif not host:
                mail_result = "ERROR_CONFIG"
                mail_error = "SMTP host fehlt"
            elif not notify:
                mail_result = "SKIPPED_NO_NOTIFY"

        # Statusdatei schreiben (neues Schema)
        try:
            status_payload = {
                "mail": {
                    "enabled": enabled,
                    "host": host,
                    "port": port,
                    "user_present": bool(user),
                    "notify_email_present": bool(notify),
                    "mode": mode,
                    "attempted_at_utc": attempted_at,
                    "result": mail_result,
                    "error": mail_error,
                },
                "results": results or [],
            }
            path = get_mail_transfer_info_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(status_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._emit_log(f"[{self._now_hms()}] Konnte mail_transfer_info.json nicht schreiben: {e}")

    # --- Helpers ---

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _emit_log(self, text: str):
        debug_print(text)
        self.sig_log.emit(text)