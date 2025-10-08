#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import shutil
import hashlib
import tempfile
from datetime import datetime, timezone

from PySide6 import QtCore, QtWidgets

from utils.config_manager import debug_print, get_ftp_transfer_log_path
from utils.ftp_manager import FTPManager
from utils.transfer_reporter import send_transfer_report  # nutzt SMTP-Settings


class TransferQueuePanel(QtWidgets.QWidget):
    """
    Eingebettete Variante der Transfer-Queue (wie dein Dialog), zur Anzeige unten im Tab.
    Public API:
        - set_plan(plan_dict)     -> Plan setzen + Dateiliste sammeln + Tabelle füllen (ruft collect_files)
        - start_transfer()        -> Worker starten
        - is_busy() -> bool       -> ob gerade ein Transfer läuft
        - cancel()                -> Abbruch anfordern
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan_data = {}
        self.worker_thread = None
        self.worker = None
        self.file_list = []
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(6)

        header = QtWidgets.QHBoxLayout()
        self.lbl_title = QtWidgets.QLabel("Transfer-Queue")
        f = self.lbl_title.font(); f.setBold(True); self.lbl_title.setFont(f)
        header.addWidget(self.lbl_title)
        header.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_cancel.setEnabled(False)
        header.addWidget(self.btn_cancel)
        main.addLayout(header)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Quelle", "Ziel", "Status", "Fortschritt (%)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        main.addWidget(self.table, 1)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setMinimumHeight(90)
        main.addWidget(self.log, 0)

    # ---------------- Public API ----------------
    def is_busy(self) -> bool:
        return self.worker is not None

    def set_plan(self, plan_data: dict):
        self.plan_data = dict(plan_data or {})
        self._append_log(f"[Queue] Plan übernommen: {self.plan_data.get('name', '(ohne)')}")
        self.file_list = self._collect_files()
        self._populate_table()

    def start_transfer(self):
        if not self.plan_data:
            QtWidgets.QMessageBox.warning(self, "Hinweis", "Kein Plan gesetzt.")
            return
        if not self.file_list:
            self._append_log("[Queue] Keine Dateien zu übertragen.")
            return

        self.btn_cancel.setEnabled(True)
        self.worker_thread = QtCore.QThread()
        self.worker = _TransferQueueWorker(self.plan_data, self.file_list)
        self.worker.moveToThread(self.worker_thread)
        self.worker.progress.connect(self._on_progress)
        self.worker.log_line.connect(self._append_log)
        self.worker.finished.connect(self._on_finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()
        self._append_log("[Queue] Transfer gestartet.")

    def cancel(self):
        if self.worker:
            self._append_log("[Queue] Abbruch angefordert …")
            self.worker.request_abort()

    # ---------------- intern: UI Hooks ----------------
    def _on_progress(self, key, status, percent):
        # key == erste Spalte (Quelle)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == key:
                self.table.item(row, 2).setText(status)
                bar = self.table.cellWidget(row, 3)
                if bar:
                    bar.setValue(percent)
                break

    def _on_finished(self):
        self._append_log("[Queue] Transfer beendet.")
        self.btn_cancel.setEnabled(False)
        try:
            self.worker_thread.quit()
            self.worker_thread.wait()
        except Exception:
            pass
        self.worker_thread = None
        self.worker = None

    def _append_log(self, msg: str):
        self.log.appendPlainText(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------------- Dateien sammeln & Tabelle füllen ----------------
    def _collect_files(self):
        pd = self.plan_data
        if pd.get("source_is_ftp", False):
            return self._collect_files_from_ftp_source()
        else:
            return self._collect_files_from_local_source()

    def _collect_files_from_local_source(self):
        source_path = self.plan_data.get("source_path", "")
        if not source_path or not os.path.exists(source_path):
            debug_print(f"Quelle fehlt/existiert nicht: {source_path}")
            return []
        file_list = []
        move_after = self.plan_data.get("move_after", "")
        abs_move_after = os.path.abspath(move_after) if move_after else None
        for root, dirs, files in os.walk(source_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if abs_move_after:
                dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) != abs_move_after]
            for f in files:
                if f.startswith('.'):
                    continue
                full_path = os.path.join(root, f)
                rel = os.path.relpath(full_path, source_path)
                dest_hint = self._build_target_hint(rel)
                file_list.append({
                    "mode": "local_src",
                    "src_path": full_path,
                    "rel": rel,
                    "dest_hint": dest_hint
                })
        debug_print(f"Zu übertragende lokale Dateien: {len(file_list)}")
        return file_list

    def _collect_files_from_ftp_source(self):
        server_name = self.plan_data.get("source_ftp_server", "")
        remote_root = self.plan_data.get("source_remote_path", "").rstrip("/")
        if not server_name or not remote_root:
            return []
        ftp = FTPManager()
        try:
            ftp.connect(server_name=server_name)
            rel_files = ftp.list_files_recursive(remote_root)
        except Exception as e:
            debug_print(f"FTP-Quelle connect/list fail: {e}")
            rel_files = []
        finally:
            try: ftp.disconnect()
            except Exception: pass

        file_list = []
        for rel in rel_files:
            remote_path = f"{remote_root}/{rel}".replace("//", "/")
            dest_hint = self._build_target_hint(rel)
            file_list.append({
                "mode": "ftp_src",
                "src_server": server_name,
                "src_remote": remote_path,
                "rel": rel,
                "dest_hint": dest_hint
            })
        debug_print(f"Zu übertragende Remote-Dateien (Quelle FTP): {len(file_list)}")
        return file_list

    def _build_target_hint(self, rel):
        target = self.plan_data.get("target_path", "")
        if self.plan_data.get("use_ftp", False):
            remote_sub = target.rstrip("/") + "/" + os.path.dirname(rel).replace("\\", "/")
            return remote_sub
        else:
            return os.path.join(target, os.path.dirname(rel))

    def _populate_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, entry in enumerate(self.file_list):
            src_txt = entry["src_path"] if entry["mode"] == "local_src" else f"{entry['src_server']}:{entry['src_remote']}"
            tgt_txt = entry.get("dest_hint", "")
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(src_txt))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(tgt_txt))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem("Wartet"))
            bar = QtWidgets.QProgressBar(); bar.setValue(0)
            self.table.setCellWidget(row, 3, bar)


# ====================== Worker (aus deinem Dialog übernommen) ======================
class _TransferQueueWorker(QtCore.QObject):
    progress = QtCore.Signal(str, str, int)  # key (Quelle), status, percent
    finished = QtCore.Signal()
    log_line = QtCore.Signal(str)

    def __init__(self, plan_data, file_list):
        super().__init__()
        self.plan_data = plan_data
        self.file_list = file_list
        self._abort = False
        self.results = []
        self.verify_mode = self.plan_data.get("verify_mode", "size_only")
        self.dst_ftp = None
        self._move_after_records = []

    def request_abort(self):
        self._abort = True

    # --- run ---
    def run(self):
        self.log_line.emit("TransferQueueWorker: run() gestartet.")
        retry_count = self.plan_data.get("retry_count", 5)

        if self.plan_data.get("use_ftp", False):
            if not self._ensure_dst_ftp_connected():
                for entry in self.file_list:
                    self._emit_progress(entry, "FTP-Connect-Error", 0)
                    self._add_result(entry, "FAILED", "Ziel-FTP nicht erreichbar")
                self._finalize(); return

        for entry in self.file_list:
            if self._abort:
                self._emit_progress(entry, "Abgebrochen", 0)
                self._add_result(entry, "ABORTED", "Vom Benutzer abgebrochen")
                continue

            attempts, success, last_err = 0, False, ""
            while attempts < retry_count and not success and not self._abort:
                attempts += 1
                try:
                    self._transfer_one_with_verify(entry)
                    self._emit_progress(entry, "SUCCESS", 100)
                    self._add_result(entry, "SUCCESS", "")
                    success = True
                except Exception as e:
                    last_err = str(e)
                    self.log_line.emit(f"Transfer Fehlversuch ({attempts}/{retry_count}): {self._key(entry)} -> {last_err}")
                    time.sleep(min(2.0, 0.5 * attempts))
                    if self.plan_data.get("use_ftp", False):
                        self._ensure_dst_ftp_connected()
                    if attempts >= retry_count:
                        self._emit_progress(entry, "FAILED", 0)
                        self._add_result(entry, "FAILED", last_err)

        if self.dst_ftp:
            try: self.dst_ftp.disconnect()
            except Exception: pass

        try: self._cleanup_local_move_after()
        except Exception as e: self.log_line.emit(f"Auto-Delete Fehler: {e}")

        try: self._persist_logs()
        except Exception as e: self.log_line.emit(f"Persistentes Logging fehlgeschlagen: {e}")

        try: self._send_report_mail()
        except Exception as e: self.log_line.emit(f"Report-Mail fehlgeschlagen: {e}")

        self._finalize()

    # --- copy helpers / verify (identisch zu Dialog, leicht gekürzt) ---
    def _transfer_one_with_verify(self, entry):
        rel = entry["rel"]
        if entry["mode"] == "local_src":
            src_path = entry["src_path"]
            if self.plan_data.get("use_ftp", False):
                remote_dir = self.plan_data.get("target_path", "").rstrip("/") + "/" + os.path.dirname(rel).replace("\\", "/")
                remote_path = remote_dir.rstrip("/") + "/" + os.path.basename(src_path)
                self._copy_local_to_ftp_with_retries(src_path, remote_dir)
                self._verify_local_vs_remote(src_path, remote_path)
                self._move_source_after_success_local(src_path)
            else:
                dest_dir = os.path.join(self.plan_data.get("target_path", ""), os.path.dirname(rel))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(src_path))
                self._copy_file_with_progress(src_path, dest_path, entry)
                self._verify_local_vs_local(src_path, dest_path)
                self._move_source_after_success_local(src_path)
        else:
            server = entry["src_server"]; remote_src_path = entry["src_remote"]
            tmp_dir = tempfile.mkdtemp(prefix="transfer_tmp_")
            tmp_local = self._download_from_ftp_with_retries(server, remote_src_path, tmp_dir)
            if self.plan_data.get("use_ftp", False):
                remote_dir = self.plan_data.get("target_path", "").rstrip("/") + "/" + os.path.dirname(entry["rel"]).replace("\\", "/")
                remote_dst_path = remote_dir.rstrip("/") + "/" + os.path.basename(tmp_local)
                self._copy_local_to_ftp_with_retries(tmp_local, remote_dir)
                self._verify_local_vs_remote(tmp_local, remote_dst_path)
            else:
                dest_dir = os.path.join(self.plan_data.get("target_path", ""), os.path.dirname(entry["rel"]))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(tmp_local))
                self._copy_file_with_progress(tmp_local, dest_path, entry)
                self._verify_local_vs_local(tmp_local, dest_path)
            self._move_source_after_success_remote(server, remote_src_path)
            try:
                os.remove(tmp_local); os.rmdir(tmp_dir)
            except Exception: pass

    def _ensure_dst_ftp_connected(self) -> bool:
        if self.dst_ftp is None:
            self.dst_ftp = FTPManager()
        try:
            if self.dst_ftp.is_connected():
                return True
        except Exception:
            pass
        try:
            self.dst_ftp.connect(server_name=self.plan_data.get("ftp_server", ""))
            return True
        except Exception:
            return False

    def _copy_local_to_ftp_with_retries(self, local_file, remote_dir):
        attempts = 0; retry_count = self.plan_data.get("retry_count", 5)
        while attempts < retry_count and not self._abort:
            attempts += 1
            try:
                if not self._ensure_dst_ftp_connected():
                    raise RuntimeError("Ziel-FTP nicht verbunden")
                self.dst_ftp.upload_file(local_file, remote_dir)
                return
            except Exception:
                if attempts >= retry_count:
                    raise
                time.sleep(min(2.0, 0.5 * attempts))
                self._ensure_dst_ftp_connected()

    def _download_from_ftp_with_retries(self, server_name, remote_path, local_dir):
        attempts = 0; retry_count = self.plan_data.get("retry_count", 5); last_local = None
        while attempts < retry_count and not self._abort:
            attempts += 1
            ftp = FTPManager()
            try:
                ftp.connect(server_name=server_name)
                local_path = ftp.download_file(remote_path, local_dir)
                self.progress.emit(remote_path, "Download", 50)
                last_local = local_path
                return local_path
            except Exception:
                if attempts >= retry_count: raise
                time.sleep(min(2.0, 0.5 * attempts))
            finally:
                try: ftp.disconnect()
                except Exception: pass
        return last_local

    def _copy_file_with_progress(self, src, dest, entry):
        total_size = max(1, os.path.getsize(src)); copied = 0; buf = 1024 * 256
        with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
            while True:
                if self._abort: raise RuntimeError("Transfer abgebrochen")
                chunk = fsrc.read(buf)
                if not chunk: break
                fdst.write(chunk); copied += len(chunk)
                percent = int((copied / total_size) * 100)
                self.progress.emit(self._key(entry), "In Progress", percent)
                time.sleep(0.002)

    # verify
    def _verify_local_vs_local(self, a, b):
        if self.plan_data.get("verify_mode","size_only") == "md5":
            if self._md5(a) != self._md5(b): raise RuntimeError("Verify md5 fehlgeschlagen (lokal)")
        else:
            if os.path.getsize(a) != os.path.getsize(b): raise RuntimeError("Verify size fehlgeschlagen (lokal)")

    def _verify_local_vs_remote(self, src_local, dst_remote):
        if self.plan_data.get("verify_mode","size_only") == "md5":
            r = self._remote_md5_or_redl(dst_remote); l = self._md5(src_local)
            if r != l: raise RuntimeError("Verify md5 fehlgeschlagen (remote)")
        else:
            r = self._remote_size_or_redl(dst_remote); l = os.path.getsize(src_local)
            if r != l: raise RuntimeError("Verify size fehlgeschlagen (remote)")

    def _remote_size_or_redl(self, remote_path) -> int:
        try:
            s = self.dst_ftp.get_size(remote_path);
            if s is not None: return int(s)
            st = self.dst_ftp.stat(remote_path)
            if isinstance(st, dict) and st.get("size") is not None: return int(st["size"])
        except Exception: pass
        tmp = tempfile.mkdtemp(prefix="verify_tmp_")
        try:
            local = self.dst_ftp.download_file(remote_path, tmp)
            return os.path.getsize(local)
        finally:
            try: os.remove(local)
            except Exception: pass
            try: os.rmdir(tmp)
            except Exception: pass

    def _remote_md5_or_redl(self, remote_path) -> str:
        try: return str(self.dst_ftp.md5(remote_path))
        except Exception: pass
        tmp = tempfile.mkdtemp(prefix="verify_tmp_")
        try:
            local = self.dst_ftp.download_file(remote_path, tmp)
            return self._md5(local)
        finally:
            try: os.remove(local)
            except Exception: pass
            try: os.rmdir(tmp)
            except Exception: pass

    @staticmethod
    def _md5(p: str) -> str:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    # move-after & logging / mail (identisch zum Dialog, leicht gekürzt)
    def _move_source_after_success_local(self, local_file):
        move_after = self.plan_data.get("move_after", "")
        if not move_after: return
        src_root = self.plan_data.get("source_path", "")
        rel = os.path.relpath(local_file, src_root) if src_root and os.path.exists(src_root) else os.path.basename(local_file)
        target_dir = os.path.join(move_after, os.path.dirname(rel)); os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, os.path.basename(local_file))
        if os.path.exists(target_file):
            base, ext = os.path.splitext(target_file)
            target_file = f"{base}_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        shutil.move(local_file, target_file)
        self._register_move_after(target_file)

    def _register_move_after(self, dest_path: str):
        self._move_after_records.append({
            "path": os.path.abspath(dest_path),
            "processed_at": datetime.now(timezone.utc).isoformat()
        })

    def _move_source_after_success_remote(self, server_name, remote_path):
        archive = self.plan_data.get("source_remote_archive", "").rstrip("/")
        if not archive: return
        ftp = FTPManager(); ftp.connect(server_name=server_name)
        try:
            dest_remote = f"{archive}/{os.path.basename(remote_path)}"
            ftp.move_remote(remote_path, dest_remote)
        except Exception:
            debug_print("Remote-Archiv übersprungen.")
        finally:
            try: ftp.disconnect()
            except Exception: pass

    def _persist_logs(self):
        log_json = get_ftp_transfer_log_path()
        try:
            data = []
            if os.path.exists(log_json):
                with open(log_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list): data = []
        except Exception: data = []

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plan_name = self.plan_data.get("name", "")
        entry = {
            "time": now,
            "plan": plan_name,
            "source_is_ftp": self.plan_data.get("source_is_ftp", False),
            "source": self.plan_data.get("source_remote_path", "") if self.plan_data.get("source_is_ftp", False) else self.plan_data.get("source_path", ""),
            "target_is_ftp": self.plan_data.get("use_ftp", False),
            "target": self.plan_data.get("target_path", ""),
            "verify_mode": self.verify_mode,
            "results": self.results,
            "move_after_records": self._move_after_records,
        }
        with open(log_json, "w", encoding="utf-8") as f:
            data.append(entry); json.dump(data, f, indent=2, ensure_ascii=False)

    def _send_report_mail(self):
        total = len(self.results)
        ok = sum(1 for r in self.results if r["status"] == "SUCCESS")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        aborted = sum(1 for r in self.results if r["status"] == "ABORTED")
        lines = [
            f"Transfer-Report ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            f"Plan: {self.plan_data.get('name','(ohne)')}",
            f"Quelle: {'FTP ' + self.plan_data.get('source_ftp_server','') + ' ' + self.plan_data.get('source_remote_path','') if self.plan_data.get('source_is_ftp', False) else self.plan_data.get('source_path','')}",
            f"Ziel:   {'FTP ' + self.plan_data.get('ftp_server','') + ' ' + self.plan_data.get('target_path','') if self.plan_data.get('use_ftp', False) else self.plan_data.get('target_path','')}",
            f"Verify: {self.verify_mode}",
            "",
            f"Gesamt: {total} | Erfolgreich: {ok} | Fehlgeschlagen: {failed} | Abgebrochen: {aborted}",
        ]
        send_transfer_report(self.plan_data, "\n".join(lines), summary={"ok": ok, "failed": failed, "aborted": aborted})

    def _finalize(self):
        self.finished.emit()

    # utils
    def _key(self, entry) -> str:
        return entry["src_path"] if entry["mode"] == "local_src" else entry["src_server"] + ":" + entry["src_remote"]
    def _emit_progress(self, entry, status, percent):
        self.progress.emit(self._key(entry), status, percent)
    def _add_result(self, entry, status, message):
        dst = entry.get("dest_hint", "")
        self.results.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "src": self._key(entry), "dst": dst, "status": status, "message": message
        })