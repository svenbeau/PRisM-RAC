#!/usr/bin/env python3
# transfer_queue_dialog.py
# -*- coding: utf-8 -*-

import os
import io
import csv
import time
import json
import shutil
import hashlib
import tempfile
import posixpath
from datetime import datetime, timezone
from PySide6 import QtCore, QtWidgets, QtGui

from utils.config_manager import debug_print, get_ftp_transfer_log_path, load_ftp_servers
from utils.ftp_manager import FTPManager
from utils.transfer_reporter import send_transfer_report  # nutzt SMTP-Settings


class TransferQueueDialog(QtWidgets.QDialog):
    """
    Zeigt eine Liste aller zu übertragenden Dateien mit Fortschrittsanzeige.
    Der Transfer wird asynchron in einem Worker-Thread ausgeführt.
    """
    def __init__(self, plan_data, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.setWindowTitle("Transfer Queue")
        self.resize(900, 600)

        self.worker_thread = None
        self.worker = None
        self.file_list = []
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Tabelle
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Quelle", "Ziel", "Status", "Fortschritt (%)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self.on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.file_list = self.collect_files()
        self.populate_table()

    # -------------------------- Sammlung der Quelldateien --------------------------
    def collect_files(self):
        pd = self.plan_data
        if pd.get("source_is_ftp", False):
            return self._collect_files_from_ftp_source()
        else:
            return self._collect_files_from_local_source()

    def _collect_files_from_local_source(self):
        source_path = self.plan_data.get("source_path", "")
        if not source_path:
            debug_print("Quelle nicht gesetzt.")
            return []
        if not os.path.exists(source_path):
            debug_print(f"Quelle existiert nicht: {source_path}")
            return []
        file_list = []
        move_after = self.plan_data.get("move_after", "")
        abs_move_after = os.path.abspath(move_after) if move_after else None
        for root, dirs, files in os.walk(source_path):
            # versteckte Ordner/Dateien raus
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

    # ---- FTP-Quelle: Lookup + connect() ----
    def _collect_files_from_ftp_source(self):
        server_name = self.plan_data.get("source_ftp_server", "")
        remote_root = (self.plan_data.get("source_remote_path", "") or "").rstrip("/")
        if not server_name or not remote_root:
            debug_print("FTP-Quelle unvollständig konfiguriert (Server/Remote-Pfad).")
            return []
        ftp = FTPManager()
        try:
            if not self._apply_server_by_name(ftp, server_name):
                debug_print(f"FTP-Quelle: Server '{server_name}' nicht gefunden.")
                return []
            ftp.connect()
        except Exception as e:
            debug_print(f"FTP-Quelle connect fail: {e}")
            return []

        file_list = []
        try:
            rel_files = ftp.list_files_recursive(remote_root)  # z.B. ["subA/file1.tif", "file2.psd"]
            for rel in rel_files:
                # Remotepfade immer POSIX
                rel_posix = rel.replace("\\", "/")
                remote_path = f"{remote_root}/{rel_posix}".replace("//", "/")
                dest_hint = self._build_target_hint(rel_posix)
                file_list.append({
                    "mode": "ftp_src",
                    "src_server": server_name,
                    "src_remote": remote_path,
                    "rel": rel_posix,
                    "dest_hint": dest_hint
                })
        finally:
            try:
                ftp.disconnect()
            except Exception:
                pass
        debug_print(f"Zu übertragende Remote-Dateien (Quelle FTP): {len(file_list)}")
        return file_list

    def _build_target_hint(self, rel):
        """
        Nur zur Anzeige in der Tabelle; Zielverzeichnisse werden später beim Transfer
        sauber gebaut (lokal: os.path, remote: posixpath).
        """
        target = self.plan_data.get("target_path", "") or ""
        if self.plan_data.get("use_ftp", False):
            # Remote-Hinweis (POSIX)
            base = "/" + target.lstrip("/")
            sub = rel.rsplit("/", 1)[0] if "/" in rel else ""
            hint = (base.rstrip("/") + ("/" + sub if sub else "")).replace("//", "/")
            return hint
        else:
            # Lokal
            sub = os.path.dirname(rel)
            return os.path.join(target, sub)

    def populate_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, entry in enumerate(self.file_list):
            src_txt = entry["src_path"] if entry["mode"] == "local_src" else f"{entry['src_server']}:{entry['src_remote']}"
            tgt_txt = entry.get("dest_hint", "")
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(src_txt))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(tgt_txt))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem("Wartet"))
            bar = QtWidgets.QProgressBar()
            bar.setValue(0)
            self.table.setCellWidget(row, 3, bar)

    # -------------------------- Ablauf --------------------------
    def start_transfer(self):
        self.worker_thread = QtCore.QThread()
        self.worker = TransferQueueWorker(self.plan_data, self.file_list)
        self.worker.moveToThread(self.worker_thread)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def on_progress(self, key, status, percent):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == key:
                self.table.item(row, 2).setText(status)
                bar = self.table.cellWidget(row, 3)
                if bar:
                    bar.setValue(percent)
                break

    def on_worker_finished(self):
        debug_print("TransferQueueDialog: Worker finished.")
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None

    def on_cancel(self):
        if self.worker:
            self.worker.request_abort()
        else:
            self.close()


class TransferQueueWorker(QtCore.QObject):
    """
    Führt den Transfer aus (lokal↔lokal / lokal↔FTP / FTP↔lokal / FTP↔FTP).
    Robust:
      - Reconnect, Retry
      - Verify (size/md5) mit sauberem Remote-Handling
      - Persistente Logs + Report
    """
    progress = QtCore.Signal(str, str, int)  # key (Quellen-String), status, percent
    finished = QtCore.Signal()

    def __init__(self, plan_data, file_list):
        super().__init__()
        self.plan_data = plan_data
        self.file_list = file_list
        self._abort = False
        self.results = []  # {time, src, dst, status, message}
        self.verify_mode = self.plan_data.get("verify_mode", "size_only")
        self.dst_ftp = None  # FTPManager für Ziel (optional)

        # Merkliste aller nach move_after verschobenen Dateien + Zeit
        self._move_after_records = []  # [{path, processed_at_iso}]

    def request_abort(self):
        self._abort = True

    # -------------------------- Helper: Server-Lookup --------------------------
    def _apply_server_by_name(self, ftp: FTPManager, server_name: str) -> bool:
        """Konfiguriert ftp anhand eines gespeicherten Servernamens. Rückgabe: True wenn gefunden."""
        servers = load_ftp_servers() or []
        srv = next((s for s in servers if s.get("name") == server_name), None)
        if not srv:
            return False
        proto = (srv.get("protocol") or "ftp").lower()
        ftp.ftp_protocol = proto
        ftp.host = srv.get("host", "")
        ftp.user = srv.get("user", "")
        ftp.port = int(srv.get("port", 21 if proto == "ftp" else 22))
        # optionale Flags aus Plan übernehmen, falls vorhanden
        ftp.keep_timestamp = self.plan_data.get("keep_timestamp", False)
        ftp.versioning_mode = self.plan_data.get("versioning_mode", "mirror")
        return True

    # -------------------------- small guards --------------------------
    @staticmethod
    def _ensure_local_path(p: str, label: str = "path") -> str:
        if not isinstance(p, (str, os.PathLike)):
            raise ValueError(f"{label} is invalid (got {type(p).__name__})")
        p = os.fspath(p)
        if not os.path.exists(p):
            raise FileNotFoundError(f"{label} does not exist: {p}")
        return p

    @staticmethod
    def _ensure_remote_path(p: str, label: str = "remote_path") -> str:
        if not isinstance(p, str):
            raise ValueError(f"{label} is invalid (got {type(p).__name__})")
        if not p:
            raise ValueError(f"{label} is empty")
        # nur für Logging/Sanity
        return p

    # -------------------------- core run --------------------------
    def run(self):
        debug_print("TransferQueueWorker: run() gestartet.")
        retry_count = int(self.plan_data.get("retry_count", 5) or 5)

        # Ziel-FTP vorbereiten (falls nötig)
        if self.plan_data.get("use_ftp", False):
            if not self._ensure_dst_ftp_connected():
                for entry in self.file_list:
                    self._emit_progress(entry, "FTP-Connect-Error", 0)
                    self._add_result(entry, "FAILED", "Ziel-FTP nicht erreichbar")
                self._finalize()
                return

        for entry in self.file_list:
            if self._abort:
                self._emit_progress(entry, "Abgebrochen", 0)
                self._add_result(entry, "ABORTED", "Vom Benutzer abgebrochen")
                continue

            attempts = 0
            success = False
            last_err = ""
            while attempts < retry_count and not success and not self._abort:
                attempts += 1
                try:
                    self._transfer_one_with_verify(entry)
                    self._emit_progress(entry, "SUCCESS", 100)
                    self._add_result(entry, "SUCCESS", "")
                    success = True
                except Exception as e:
                    last_err = str(e)
                    debug_print(f"Transfer Fehlversuch ({attempts}/{retry_count}): {self._key(entry)} -> {last_err}")
                    time.sleep(min(2.0, 0.5 * attempts))
                    if self.plan_data.get("use_ftp", False):
                        self._ensure_dst_ftp_connected()
                    if attempts >= retry_count:
                        self._emit_progress(entry, "FAILED", 0)
                        self._add_result(entry, "FAILED", last_err)

        # Ziel-FTP trennen
        if self.dst_ftp:
            try:
                self.dst_ftp.disconnect()
            except Exception:
                pass

        # Cleanup / Logs / Mail
        try:
            self._cleanup_local_move_after()
        except Exception as e:
            debug_print(f"Auto-Delete Fehler: {e}")

        try:
            self._persist_logs()
        except Exception as e:
            debug_print(f"Persistentes Logging fehlgeschlagen: {e}")

        try:
            self._send_report_mail()
        except Exception as e:
            debug_print(f"Report-Mail fehlgeschlagen: {e}")

        self._finalize()

    # -------------------------- single transfer (with verify) --------------------------
    def _transfer_one_with_verify(self, entry):
        rel = entry["rel"]

        if entry["mode"] == "local_src":
            src_path = self._ensure_local_path(entry["src_path"], "local_path")
            if self.plan_data.get("use_ftp", False):
                # lokal -> FTP (Remote-Pfade per POSIX!)
                base_remote = "/" + (self.plan_data.get("target_path", "") or "").lstrip("/")
                sub_remote = rel.rsplit("/", 1)[0] if "/" in rel else ""
                remote_dir = (base_remote.rstrip("/") + ("/" + sub_remote if sub_remote else "")) or "/"
                remote_dir = remote_dir.replace("//", "/")
                final_name = os.path.basename(src_path)
                remote_path = posixpath.join(remote_dir, final_name)

                # Debug: zeigen, was wir hochladen/prüfen
                debug_print(f"Upload -> remote_dir={remote_dir}, remote_path={remote_path}")

                self._copy_local_to_ftp_with_retries(src_path, remote_dir, entry)
                # Verify
                self._verify_local_vs_remote(src_path, remote_path, entry)
                # Nach Erfolg: lokale Quelle verschieben
                self._move_source_after_success_local(src_path)
            else:
                # lokal -> lokal
                dest_dir = os.path.join(self.plan_data.get("target_path", "") or "", os.path.dirname(rel))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(src_path))
                self._copy_file_with_progress(src_path, dest_path, entry)
                self._verify_local_vs_local(src_path, dest_path, entry)
                self._move_source_after_success_local(src_path)

        else:  # ftp_src
            server = entry["src_server"]
            remote_src_path = self._ensure_remote_path(entry["src_remote"], "remote_src_path")
            # Download → temp dir
            tmp_dir = tempfile.mkdtemp(prefix="transfer_tmp_")
            tmp_local = self._download_from_ftp_with_retries(server, remote_src_path, tmp_dir, entry)
            tmp_local = self._ensure_local_path(tmp_local, "tmp_local_download")

            if self.plan_data.get("use_ftp", False):
                # FTP-Quelle -> FTP-Ziel (via tmp)
                base_remote = "/" + (self.plan_data.get("target_path", "") or "").lstrip("/")
                sub_remote = entry["rel"].rsplit("/", 1)[0] if "/" in entry["rel"] else ""
                remote_dir = (base_remote.rstrip("/") + ("/" + sub_remote if sub_remote else "")) or "/"
                remote_dir = remote_dir.replace("//", "/")
                remote_dst_path = posixpath.join(remote_dir, os.path.basename(tmp_local))
                self._copy_local_to_ftp_with_retries(tmp_local, remote_dir, entry)
                self._verify_local_vs_remote(tmp_local, remote_dst_path, entry)
            else:
                # FTP-Quelle -> lokales Ziel
                dest_dir = os.path.join(self.plan_data.get("target_path", "") or "", os.path.dirname(entry["rel"]))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(tmp_local))
                self._copy_file_with_progress(tmp_local, dest_path, entry)
                self._verify_local_vs_local(tmp_local, dest_path, entry)

            # Quelle auf Remote archivieren (falls konfiguriert)
            self._move_source_after_success_remote(server, remote_src_path)

            # Temp entfernen
            try:
                os.remove(tmp_local)
                os.rmdir(tmp_dir)
            except Exception:
                pass

    # -------------------------- transfer helpers w/ reconnect --------------------------
    def _ensure_dst_ftp_connected(self) -> bool:
        if self.dst_ftp is None:
            self.dst_ftp = FTPManager()
        try:
            if self.dst_ftp.is_connected():
                return True
        except Exception:
            pass
        # Reconnect: per Servernamen aus Plan konfigurieren
        try:
            server_name = self.plan_data.get("ftp_server", "")
            if not self._apply_server_by_name(self.dst_ftp, server_name):
                debug_print(f"Reconnect: FTP-Server '{server_name}' nicht gefunden.")
                return False
            self.dst_ftp.connect()   # <— ohne Argumente
            return True
        except Exception as e:
            debug_print(f"Reconnect Ziel-FTP fehlgeschlagen: {e}")
            return False

    def _copy_local_to_ftp_with_retries(self, local_file, remote_dir, entry):
        local_file = self._ensure_local_path(local_file, "local_file_upload")
        # remote_dir ist POSIX-Pfad; basic sanity
        self._ensure_remote_path(remote_dir, "remote_dir_upload")

        attempts = 0
        retry_count = int(self.plan_data.get("retry_count", 5) or 5)
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

    def _download_from_ftp_with_retries(self, server_name, remote_path, local_dir, entry):
        self._ensure_remote_path(remote_path, "remote_path_download")
        attempts = 0
        retry_count = int(self.plan_data.get("retry_count", 5) or 5)
        last_local = None
        while attempts < retry_count and not self._abort:
            attempts += 1
            ftp = FTPManager()
            try:
                if not self._apply_server_by_name(ftp, server_name):
                    raise RuntimeError(f"FTP-Server '{server_name}' nicht gefunden.")
                ftp.connect()
                local_path = ftp.download_file(remote_path, local_dir)
                # mini-progress
                self.progress.emit(self._key(entry), "Download", 50)
                last_local = local_path
                return local_path
            except Exception:
                if attempts >= retry_count:
                    raise
                time.sleep(min(2.0, 0.5 * attempts))
            finally:
                try:
                    ftp.disconnect()
                except Exception:
                    pass
        return last_local

    def _copy_file_with_progress(self, src, dest, entry):
        src = self._ensure_local_path(src, "copy_src")
        total_size = max(1, os.path.getsize(src))
        copied = 0
        bufsize = 1024 * 256  # 256KB
        with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
            while True:
                if self._abort:
                    raise RuntimeError("Transfer abgebrochen")
                chunk = fsrc.read(bufsize)
                if not chunk:
                    break
                fdst.write(chunk)
                copied += len(chunk)
                percent = int((copied / total_size) * 100)
                self.progress.emit(self._key(entry), "In Progress", percent)
                time.sleep(0.002)

    # -------------------------- verification --------------------------
    def _verify_local_vs_local(self, src_local, dst_local, entry):
        src_local = self._ensure_local_path(src_local, "verify_src_local")
        dst_local = self._ensure_local_path(dst_local, "verify_dst_local")
        if self.verify_mode == "md5":
            s = self._md5_local(src_local)
            d = self._md5_local(dst_local)
            if s != d:
                raise RuntimeError("Verifikation (md5) fehlgeschlagen (lokal↔lokal)")
        else:
            if os.path.getsize(src_local) != os.path.getsize(dst_local):
                raise RuntimeError("Verifikation (size) fehlgeschlagen (lokal↔lokal)")

    def _verify_local_vs_remote(self, src_local, dst_remote_path, entry):
        src_local = self._ensure_local_path(src_local, "verify_src_local")
        dst_remote_path = self._ensure_remote_path(dst_remote_path, "verify_remote_path")

        if self.verify_mode == "md5":
            try:
                r_md5 = self._remote_md5_or_redownload(dst_remote_path)
                l_md5 = self._md5_local(src_local)
                if r_md5 != l_md5:
                    raise RuntimeError("Verifikation (md5) fehlgeschlagen (lokal↔remote)")
            except Exception as e:
                raise RuntimeError(str(e))
        else:
            try:
                r_size = self._remote_size_or_redownload(dst_remote_path)
                l_size = os.path.getsize(src_local)
                if r_size != l_size:
                    raise RuntimeError(f"Verifikation (size) fehlgeschlagen (lokal↔remote) "
                                       f"[remote={r_size}, local={l_size}]")
            except Exception as e:
                raise RuntimeError(str(e))

    def _remote_size_or_redownload(self, remote_path) -> int:
        remote_path = self._ensure_remote_path(remote_path, "remote_path_size")
        try:
            s = self.dst_ftp.get_size(remote_path)
            if s is not None:
                return int(s)
            st = self.dst_ftp.stat(remote_path)
            if isinstance(st, dict) and st.get("size") is not None:
                return int(st["size"])
        except Exception as e:
            # wichtig fürs Debugging
            debug_print(f"_remote_size_or_redownload: primary failed for '{remote_path}': {e}")

        # Fallback: redownload temp und size bestimmen
        tmp_dir = tempfile.mkdtemp(prefix="verify_tmp_")
        tmp_local = None
        try:
            tmp_local = self.dst_ftp.download_file(remote_path, tmp_dir)
            tmp_local = self._ensure_local_path(tmp_local, "verify_tmp_local")
            return os.path.getsize(tmp_local)
        finally:
            try:
                if tmp_local and os.path.exists(tmp_local):
                    os.remove(tmp_local)
            except Exception:
                pass
            try:
                os.rmdir(tmp_dir)
            except Exception:
                pass

    def _remote_md5_or_redownload(self, remote_path) -> str:
        remote_path = self._ensure_remote_path(remote_path, "remote_path_md5")
        try:
            return str(self.dst_ftp.md5(remote_path))
        except NotImplementedError:
            pass
        except Exception as e:
            debug_print(f"_remote_md5_or_redownload: md5 remote failed for '{remote_path}': {e}")
        tmp_dir = tempfile.mkdtemp(prefix="verify_tmp_")
        tmp_local = None
        try:
            tmp_local = self.dst_ftp.download_file(remote_path, tmp_dir)
            tmp_local = self._ensure_local_path(tmp_local, "verify_tmp_local")
            return self._md5_local(tmp_local)
        finally:
            try:
                if tmp_local and os.path.exists(tmp_local):
                    os.remove(tmp_local)
            except Exception:
                pass
            try:
                os.rmdir(tmp_dir)
            except Exception:
                pass

    @staticmethod
    def _md5_local(path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    # -------------------------- move after --------------------------
    def _move_source_after_success_local(self, local_file):
        """
        Verschiebt die verarbeitete Quelldatei in den konfigurierten 'move_after'-Ordner.
        """
        move_after = self.plan_data.get("move_after", "")
        if not move_after:
            return
        src_root = self.plan_data.get("source_path", "")
        rel = os.path.relpath(local_file, src_root) if src_root and os.path.exists(src_root) else os.path.basename(local_file)
        target_dir = os.path.join(move_after, os.path.dirname(rel))
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, os.path.basename(local_file))
        if os.path.exists(target_file):
            base, ext = os.path.splitext(target_file)
            target_file = f"{base}_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        shutil.move(local_file, target_file)
        debug_print(f"Moved source to: {target_file}")

        # Registrierung für Log-basiertes Aging
        self._register_move_after(target_file)

    def _register_move_after(self, dest_path: str):
        try:
            self._move_after_records.append({
                "path": os.path.abspath(dest_path),
                "processed_at": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass

    def _move_source_after_success_remote(self, server_name, remote_path):
        archive = (self.plan_data.get("source_remote_archive", "") or "").rstrip("/")
        if not archive:
            return
        ftp = FTPManager()
        if not self._apply_server_by_name(ftp, server_name):
            debug_print(f"Remote-Archiv: Server '{server_name}' nicht gefunden.")
            return
        ftp.connect()
        try:
            dest_remote = f"{archive}/{posixpath.basename(remote_path)}".replace("//", "/")
            ftp.move_remote(remote_path, dest_remote)
        except Exception:
            debug_print("FTP move/rename nicht verfügbar; Remote-Archiv übersprungen.")
        finally:
            try:
                ftp.disconnect()
            except Exception:
                pass

    # -------------------------- cleanup/logs/report --------------------------
    def _cleanup_local_move_after(self):
        if not self.plan_data.get("auto_delete_after_move_enabled", False):
            return
        hours = int(self.plan_data.get("auto_delete_after_move_hours", 48) or 48)
        move_after = self.plan_data.get("move_after", "")
        if not move_after or not os.path.isdir(move_after):
            return

        cutoff_ts = time.time() - (hours * 3600)

        # 1) Log laden und Map path->processed_at bauen (letzter Eintrag gewinnt)
        log_json = get_ftp_transfer_log_path()
        path_to_processed_ts = {}
        try:
            if os.path.exists(log_json):
                with open(log_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for run in data if isinstance(data, list) else []:
                    recs = run.get("move_after_records", [])
                    for rec in recs:
                        p = rec.get("path", "")
                        t = rec.get("processed_at", "")
                        if not p or not t:
                            continue
                        try:
                            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                            ts = dt.timestamp()
                        except Exception:
                            continue
                        try:
                            ap = os.path.abspath(p)
                            if ap.startswith(os.path.abspath(move_after) + os.sep) or ap == os.path.abspath(move_after):
                                prev = path_to_processed_ts.get(ap)
                                if prev is None or ts > prev:
                                    path_to_processed_ts[ap] = ts
                        except Exception:
                            pass
        except Exception as e:
            debug_print(f"Log-basiertes Aging: Konnte Log nicht auswerten: {e}")

        # 2) Durchlaufe move_after und entscheide anhand processed_at oder mtime
        deleted = 0
        checked = 0
        for root, dirs, files in os.walk(move_after):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    checked += 1
                    ts = path_to_processed_ts.get(os.path.abspath(fpath))
                    if ts is None:
                        ts = os.path.getmtime(fpath)
                    if ts < cutoff_ts:
                        os.remove(fpath)
                        deleted += 1
                except Exception as e:
                    debug_print(f"Auto-Delete konnte {fpath} nicht löschen: {e}")
        debug_print(f"Auto-Delete move_after: geprüft={checked}, gelöscht={deleted}, Grenze={hours}h (log-basiert, Fallback mtime)")

    def _persist_logs(self):
        log_json = get_ftp_transfer_log_path()
        log_csv = os.path.splitext(log_json)[0] + ".csv"

        # Bestehendes JSON laden
        try:
            if os.path.exists(log_json):
                with open(log_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    data = []
            else:
                data = []
        except Exception:
            data = []

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
        data.append(entry)

        with open(log_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # CSV (nur Ergebnisse)
        header = ["time", "plan", "src", "dst", "status", "message"]
        new_rows = []
        for r in self.results:
            new_rows.append([r["time"], plan_name, r.get("src", ""), r.get("dst", ""), r.get("status", ""), r.get("message", "")])

        write_header = not os.path.exists(log_csv)
        with open(log_csv, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f, dialect="excel")
            if write_header:
                w.writerow(header)
            w.writerows(new_rows)

        debug_print(f"Persistente Logs aktualisiert: {log_json}, {log_csv}")

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
            f"Gesamt: {total}",
            f"Erfolgreich: {ok}",
            f"Fehlgeschlagen: {failed}",
            f"Abgebrochen: {aborted}",
            "",
            "Dateiliste:",
        ]
        for r in self.results:
            lines.append(f"- {r['status']}: {r.get('src','')} -> {r.get('dst','')} {('('+r['message']+')') if r.get('message') else ''}")
        report_text = "\n".join(lines)

        send_transfer_report(self.plan_data, report_text, summary={"ok": ok, "failed": failed, "aborted": aborted})

    def _finalize(self):
        self.finished.emit()

    # -------------------------- utils --------------------------
    def _key(self, entry) -> str:
        return entry["src_path"] if entry["mode"] == "local_src" else f"{entry['src_server']}:{entry['src_remote']}"

    def _emit_progress(self, entry, status, percent):
        self.progress.emit(self._key(entry), status, percent)

    def _add_result(self, entry, status, message):
        dst = entry.get("dest_hint", "")
        self.results.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "src": self._key(entry),
            "dst": dst,
            "status": status,
            "message": message
        })