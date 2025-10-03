#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import keyring
import smtplib
import platform
import json
from datetime import datetime
from typing import List, Callable, Any

try:
    import pync  # Für macOS-Notification
except ImportError:
    pync = None

try:
    import paramiko  # Für SFTP
except ImportError:
    paramiko = None

import ftplib  # Für (S)FTP (Plain FTP)

from utils.config_manager import (
    load_settings,
    load_smtp_settings,
    get_ftp_transfer_log_path,
    debug_print
)

class TransferError(Exception):
    """Eigene Exception für FTP-/SFTP-Fehler."""
    pass


def _is_transient_ftp_error(e: Exception) -> bool:
    """
    Erkennung temporärer Fehler, bei denen ein Reconnect + Retry sinnvoll ist.
    """
    msg = str(e).lower()
    return (
        isinstance(e, (ftplib.error_temp, ftplib.error_reply, OSError, ConnectionError))
        or "timeout" in msg
        or "timed out" in msg
        or "broken pipe" in msg
        or "connection reset" in msg
        or "not connected" in msg
        or "closed" in msg
    )


class FTPManager:
    """
    Kapselt alle FTP-/SFTP-Funktionen (Auto-Reconnect & Retry ergänzt):
      - Verbindung aufbauen (FTP oder SFTP)
      - Dateien hoch-/runterladen
      - Versionierung: mirror/suffix
      - Logging in ftptransfer_log.json (mit status)
      - E-Mail/Notification bei Fehler
      - Timestamp-Erhaltung optional
      - Remote-Verzeichnis erstellen
      - Remote Dateimanagement
      - list_directory() liefert Tupel (name, is_dir, size, mod_time_str[, owner])
    """

    def __init__(self):
        self.settings = load_settings()
        self.ftp_protocol = self.settings.get("ftp_protocol", "ftp")  # "ftp" | "sftp"
        self.host = self.settings.get("ftp_host", "")
        self.user = self.settings.get("ftp_user", "")
        self.password = None
        self.port = 21 if self.ftp_protocol == "ftp" else 22

        self.versioning_mode = self.settings.get("versioning_mode", "mirror")
        self.keep_timestamp = self.settings.get("keep_timestamp", False)

        smtp_conf = load_smtp_settings()
        self.smtp_enabled = smtp_conf.get("enabled", False)
        self.smtp_host = smtp_conf.get("host", "")
        self.smtp_port = smtp_conf.get("port", 587)
        self.smtp_user = smtp_conf.get("user", "")
        self.notify_email = smtp_conf.get("notify_email", "")

        self.conn = None

        # Retry-Parameter (per settings überschreibbar)
        self.max_retries = int(self.settings.get("ftp_max_retries", 3))
        self.retry_sleep_sec = float(self.settings.get("ftp_retry_sleep_sec", 2.0))

    # --- Passwortauflösung ---
    def _resolve_password(self):
        """Setzt self.password, falls noch leer: zuerst expliziter Wert, dann Keyring."""
        if self.password:
            return
        if not self.user:
            raise TransferError("Kein FTP-Benutzername definiert.")
        service_name = "PRisM-FTP"
        passwd = keyring.get_password(service_name, self.user)
        if passwd:
            self.password = passwd
        if not self.password:
            raise TransferError(f"Kein Passwort verfügbar (weder UI noch Keyring) für {self.user}")

    def connect(self):
        self._resolve_password()
        debug_print(f"Versuche {self.ftp_protocol.upper()}-Connect zu {self.host}:{self.port}, user={self.user}")

        if self.ftp_protocol == "ftp":
            self.conn = ftplib.FTP()
            self.conn.connect(self.host, self.port, timeout=30)
            self.conn.login(self.user, self.password)
            self.conn.set_pasv(True)
            if hasattr(self.conn, "sock") and self.conn.sock:
                self.conn.sock.settimeout(30)
            self.conn.encoding = "latin-1"
        elif self.ftp_protocol == "sftp":
            if paramiko is None:
                raise TransferError("paramiko ist nicht installiert, kann kein SFTP aufbauen.")
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(None, self.user, self.password)
            self.conn = paramiko.SFTPClient.from_transport(transport)
        else:
            raise TransferError("Unbekanntes Protokoll: " + self.ftp_protocol)

        debug_print(f"Verbindung zu {self.host} via {self.ftp_protocol} aufgebaut.")

    def disconnect(self):
        if self.conn:
            try:
                if self.ftp_protocol == "ftp":
                    try:
                        self.conn.voidcmd("NOOP")
                    except Exception:
                        pass
                    self.conn.quit()
                else:
                    try:
                        self.conn.get_channel().close()
                    except Exception:
                        pass
                    self.conn.close()
            except Exception:
                pass
            self.conn = None
            debug_print("Verbindung geschlossen.")

    # ---------- interner Retry-Wrapper ----------
    def _retry_op(self, label: str, fn: Callable[[], Any]) -> Any:
        """
        Führt fn() mit Auto-Reconnect + Retry aus, wenn transienter Fehler auftritt.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                return fn()
            except Exception as e:
                if not _is_transient_ftp_error(e) or attempt >= self.max_retries:
                    debug_print(f"[{label}] Fehler (final): {e}")
                    raise
                debug_print(f"[{label}] transienter Fehler: {e} — Versuch {attempt}/{self.max_retries}, Reconnect…")
                try:
                    self.disconnect()
                finally:
                    time.sleep(self.retry_sleep_sec)
                    self.connect()
                time.sleep(self.retry_sleep_sec)

    def ensure_remote_directory(self, remote_dir):
        def _impl():
            if self.ftp_protocol == "ftp":
                try:
                    self.conn.cwd(remote_dir)
                    return
                except ftplib.error_perm:
                    pass
                dirs = remote_dir.strip("/").split("/")
                cwd = ""
                for d in dirs:
                    cwd += "/" + d
                    try:
                        self.conn.cwd(cwd)
                    except ftplib.error_perm:
                        self.conn.mkd(cwd)
            else:
                try:
                    self.conn.chdir(remote_dir)
                    return
                except IOError:
                    pass
                dirs = remote_dir.strip("/").split("/")
                cwd = ""
                for d in dirs:
                    cwd += "/" + d
                    try:
                        self.conn.chdir(cwd)
                    except IOError:
                        self.conn.mkdir(cwd)
        return self._retry_op("ensure_remote_directory", _impl)

    def _upload_file_ftp(self, local_path, remote_path, progress_callback=None):
        file_size = os.path.getsize(local_path)
        uploaded = 0
        chunk_size = 8192

        def _impl():
            nonlocal uploaded
            with open(local_path, "rb") as f:
                def callback(data):
                    nonlocal uploaded
                    uploaded += len(data)
                    if progress_callback:
                        percent = int((uploaded / file_size) * 100) if file_size > 0 else 100
                        progress_callback(percent)
                self.conn.storbinary(f"STOR {remote_path}", f, blocksize=chunk_size, callback=callback)
            if self.keep_timestamp:
                modtime = time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(local_path)))
                try:
                    self.conn.sendcmd(f"MFMT {modtime} {remote_path}")
                except Exception:
                    pass

        self._retry_op(f"upload_file_ftp:{remote_path}", _impl)

    def _upload_file_sftp(self, local_path, remote_path):
        def _impl():
            sftp = self.conn
            sftp.put(local_path, remote_path)
            if self.keep_timestamp:
                atime = os.path.getatime(local_path)
                mtime = os.path.getmtime(local_path)
                sftp.utime(remote_path, (atime, mtime))
        self._retry_op(f"upload_file_sftp:{remote_path}", _impl)

    def upload_file(self, local_path, remote_dir, progress_callback=None):
        base_name = os.path.basename(local_path)
        remote_path = remote_dir.rstrip("/") + "/" + base_name

        # Versionierung prüfen (suffix)
        def _try_list_names() -> List[str]:
            try:
                existing_files = self.list_directory(remote_dir)
                return [x[0] for x in existing_files]
            except Exception as e:
                debug_print(f"[upload_file] Konnte Verzeichnis nicht listen (fahre fort): {e}")
                return []

        existing_names = _try_list_names()
        if base_name in existing_names:
            if self.versioning_mode == "mirror":
                pass
            elif self.versioning_mode == "suffix":
                ver = 2
                root, ext = os.path.splitext(base_name)
                new_name = f"{root}_v{ver}{ext}"
                while new_name in existing_names:
                    ver += 1
                    new_name = f"{root}_v{ver}{ext}"
                remote_path = remote_dir.rstrip("/") + "/" + new_name

        self.ensure_remote_directory(remote_dir)

        try:
            if self.ftp_protocol == "ftp":
                self._upload_file_ftp(local_path, remote_path, progress_callback)
            else:
                self._upload_file_sftp(local_path, remote_path)
            self.log_transfer(local_path, remote_path, "UPLOAD", status="SUCCESS")
        except Exception as e:
            debug_print(f"Upload fehlgeschlagen: {e}")
            self.log_transfer(local_path, remote_path, "UPLOAD", status="FAILED")
            raise

    def download_file(self, remote_path, local_dir):
        filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, filename)

        def _impl_ftp():
            if hasattr(self.conn, "sock") and self.conn.sock:
                old_timeout = self.conn.sock.gettimeout()
                self.conn.sock.settimeout(60)
            with open(local_path, "wb") as f:
                self.conn.retrbinary(f"RETR {remote_path}", f.write)
            if hasattr(self.conn, "sock") and self.conn.sock:
                self.conn.sock.settimeout(old_timeout)

        def _impl_sftp():
            sftp = self.conn
            sftp.get(remote_path, local_path)
            if self.keep_timestamp:
                attr = sftp.stat(remote_path)
                os.utime(local_path, (attr.st_atime, attr.st_mtime))

        try:
            if self.ftp_protocol == "ftp":
                self._retry_op(f"download_file_ftp:{remote_path}", _impl_ftp)
            else:
                self._retry_op(f"download_file_sftp:{remote_path}", _impl_sftp)
            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="SUCCESS")
        except Exception as e:
            debug_print(f"Download fehlgeschlagen: {e}")
            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="FAILED")
            raise

    def list_directory(self, remote_path):
        if self.ftp_protocol == "ftp":
            return self._listdir_ftp(remote_path)
        else:
            return self._listdir_sftp(remote_path)

    def _listdir_ftp(self, remote_path):
        """
        Liefert Liste aus Tupeln:
           (name, is_dir, size, mod_time_str, owner?)
        Owner kann leer sein, wenn Ausgabeformat das nicht hergibt.
        """
        items = []

        def _impl_list():
            try:
                self.conn.cwd(remote_path)
            except Exception:
                pass

            def parse_line(line: str):
                parts = line.split()
                if len(parts) < 9:
                    return
                is_dir = line.startswith("d") or parts[0].startswith("d")
                owner = ""
                try:
                    owner = parts[2]
                except Exception:
                    owner = ""
                try:
                    size = int(parts[4])
                except Exception:
                    size = 0
                mod_time_str = f"{parts[5]} {parts[6]} {parts[7]}"
                name = " ".join(parts[8:])
                items.append((name, is_dir, size, mod_time_str, owner))
            self.conn.retrlines(f"LIST {remote_path}", parse_line)

        self._retry_op(f"listdir_ftp:{remote_path}", _impl_list)
        return items

    def _listdir_sftp(self, remote_path):
        """
        Für SFTP: Owner kann ggf. als UID geliefert werden. Wir geben die UID als String aus.
        """
        filelist = []

        def _impl():
            sftp = self.conn
            for f in sftp.listdir_attr(remote_path):
                name = f.filename
                # Ordnererkennung robust:
                is_dir = False
                try:
                    sftp.listdir(remote_path.rstrip("/") + "/" + name)
                    is_dir = True
                except IOError:
                    is_dir = False
                size = getattr(f, "st_size", 0)
                mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(getattr(f, "st_mtime", 0)))
                owner = str(getattr(f, "st_uid", ""))  # UID als Fallback
                filelist.append((name, is_dir, size, mod_time, owner))

        self._retry_op(f"listdir_sftp:{remote_path}", _impl)
        return filelist

    def log_transfer(self, source, target, direction, status="SUCCESS"):
        logfile_path = get_ftp_transfer_log_path()
        entries = []
        if os.path.exists(logfile_path):
            try:
                with open(logfile_path, "r", encoding="utf-8") as lf:
                    entries = json.load(lf)
            except:
                entries = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_index = 0
        for e in entries:
            if "index" in e:
                try:
                    idx_val = int(e["index"])
                    if idx_val > last_index:
                        last_index = idx_val
                except:
                    pass
        new_index = last_index + 1
        idx_str = f"{new_index:07d}"
        new_entry = {
            "index": idx_str,
            "timestamp": now_str,
            "direction": direction,
            "source": source,
            "target": target,
            "status": status
        }
        entries.append(new_entry)
        os.makedirs(os.path.dirname(logfile_path), exist_ok=True)
        with open(logfile_path, "w", encoding="utf-8") as lf:
            json.dump(entries, lf, indent=2)

    def send_transfer_summary_email(self, results):
        from utils.config_manager import get_mail_transfer_info_path
        info_path = get_mail_transfer_info_path()
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            debug_print(f"Transfer summary written to {info_path}")
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von {info_path}: {e}")

        if self.smtp_enabled and self.notify_email:
            summary = "Transfer Summary:\n\n"
            for r in results:
                summary += f"{r['direction']} | {r['file']} -> {r.get('destination', '')}\n"
                if r["status"] == "FAILED":
                    summary += f"   Fehler: {r.get('error', 'Unbekannter Fehler')}\n"
            subject = "Transfer Summary Report"
            msg = f"From: {self.smtp_user}\r\nTo: {self.notify_email}\r\nSubject: {subject}\r\n\r\n{summary}"
            smtp_pass = keyring.get_password("PRisM-SMTP", self.smtp_user)
            if smtp_pass is None:
                debug_print("SMTP-Passwort nicht im Keyring, kann keine Transfer Summary Mail senden.")
                return
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(self.smtp_user, smtp_pass)
                    server.sendmail(self.smtp_user, [self.notify_email], msg)
                debug_print("Transfer summary email sent successfully.")
            except Exception as e:
                debug_print(f"Fehler beim Senden der Transfer summary Mail: {e}")

    def send_failure_notification(self, error_message):
        if platform.system() == "Darwin" and pync is not None:
            pync.notify(f"FTP-Transfer fehlgeschlagen: {error_message}", title="PRisM-RAC")
        if self.smtp_enabled and self.notify_email:
            smtp_pass = keyring.get_password("PRisM-SMTP", self.smtp_user)
            if smtp_pass is None:
                debug_print("SMTP-Passwort nicht im Keyring, kann keine E-Mail senden.")
                return
            subject = "FTP-Transfer fehlgeschlagen"
            body = f"Folgender Fehler ist aufgetreten:\n\n{error_message}"
            msg = f"From: {self.smtp_user}\r\nTo: {self.notify_email}\r\nSubject: {subject}\r\n\r\n{body}"
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(self.smtp_user, smtp_pass)
                    server.sendmail(self.smtp_user, [self.notify_email], msg)
            except Exception as e:
                debug_print(f"Fehler beim Senden der E-Mail: {e}")

    # --- Remote File Management (unverändert, aber mit Retry) ---
    def mkdir_remote(self, remote_path):
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.mkd(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.mkdir(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"mkdir_remote:{remote_path}", _impl)

    def rename_remote(self, old_path, new_path):
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.rename(old_path, new_path)
            elif self.ftp_protocol == "sftp":
                self.conn.rename(old_path, new_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"rename_remote:{old_path}->{new_path}", _impl)

    def delete_remote_file(self, remote_path):
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.delete(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.remove(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"delete_remote_file:{remote_path}", _impl)

    def delete_remote_directory(self, remote_path):
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.rmd(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.rmdir(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"delete_remote_dir:{remote_path}", _impl)

    def upload_folder(self, local_folder, remote_folder):
        for root, dirs, files in os.walk(local_folder):
            relative_sub = os.path.relpath(root, local_folder)
            if relative_sub == ".":
                remote_sub = remote_folder
            else:
                remote_sub = remote_folder.rstrip("/") + "/" + relative_sub
            for file in files:
                local_path = os.path.join(root, file)
                try:
                    self.upload_file(local_path, remote_sub)
                except Exception as e:
                    self.send_failure_notification(str(e))
                    raise


if __name__ == "__main__":
    mgr = FTPManager()
    try:
        mgr.connect()
    except Exception as e:
        mgr.send_failure_notification(str(e))
    finally:
        mgr.disconnect()