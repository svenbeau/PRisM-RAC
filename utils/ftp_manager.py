#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import keyring
import platform
import json
from datetime import datetime
from typing import List
from pathlib import Path

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
    debug_print,
    get_mail_transfer_info_path,
)
from utils.mailer import Mailer


class TransferError(Exception):
    """Eigene Exception für FTP-/SFTP-Fehler."""
    pass


class FTPManager:
    """
    Kapselt alle FTP-/SFTP-Funktionen:
      - Verbindung aufbauen (FTP oder SFTP)
      - Dateien hoch-/runterladen
      - Versionierung: mirror/suffix
      - Logging in ftptransfer_log.json (mit status)
      - E-Mail/Notification bei Fehler (über utils.mailer.Mailer)
      - Timestamp-Erhaltung optional
      - Remote-Verzeichnis erstellen
      - Remote Dateimanagement
      - list_directory() liefert Tupel mit 4 oder 5 Feldern:
            (name, is_dir, size, mod_time_str[, owner])
        -> Owner ist optional und kann leer sein.
    """

    def __init__(self):
        self.settings = load_settings()
        self.ftp_protocol = self.settings.get("ftp_protocol", "ftp")  # "ftp" oder "sftp"
        self.host = self.settings.get("ftp_host", "")
        self.user = self.settings.get("ftp_user", "")
        self.password = None
        self.port = 21 if self.ftp_protocol == "ftp" else 22

        self.versioning_mode = self.settings.get("versioning_mode", "mirror")
        self.keep_timestamp = self.settings.get("keep_timestamp", False)

        # Verbindungshandle (ftplib.FTP oder paramiko.SFTPClient)
        self.conn = None

    # ------------------------------------------------------------------ #
    # Verbindungsmanagement
    # ------------------------------------------------------------------ #
    def _load_password_from_keyring(self):
        if not self.user:
            raise TransferError("Kein FTP-Benutzername definiert.")
        service_name = "PRisM-FTP"
        passwd = keyring.get_password(service_name, self.user)
        if passwd is None:
            raise TransferError(f"Kein Passwort im Keyring gefunden für {self.user}")
        self.password = passwd

    def connect(self):
        self._load_password_from_keyring()
        debug_print(f"Versuche {self.ftp_protocol.upper()}-Connect zu {self.host}:{self.port}, user={self.user}")

        if self.ftp_protocol == "ftp":
            self.conn = ftplib.FTP()
            self.conn.connect(self.host, self.port, timeout=30)
            self.conn.login(self.user, self.password)
            self.conn.set_pasv(True)
            if hasattr(self.conn, "sock") and self.conn.sock:
                self.conn.sock.settimeout(30)
            # Encoding hängt vom Server ab; latin-1 ist oft robust
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

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #
    def ensure_remote_directory(self, remote_dir: str) -> None:
        if self.ftp_protocol == "ftp":
            try:
                self.conn.cwd(remote_dir)
            except ftplib.error_perm:
                dirs = remote_dir.strip("/").split("/")
                cwd = ""
                for d in dirs:
                    cwd += "/" + d
                    try:
                        self.conn.cwd(cwd)
                    except ftplib.error_perm:
                        try:
                            self.conn.mkd(cwd)
                        except Exception as e:
                            debug_print(f"Fehler beim Erstellen des Ordners {cwd}: {e}")
        else:
            try:
                self.conn.chdir(remote_dir)
            except IOError:
                dirs = remote_dir.strip("/").split("/")
                cwd = ""
                for d in dirs:
                    cwd += "/" + d
                    try:
                        self.conn.chdir(cwd)
                    except IOError:
                        self.conn.mkdir(cwd)

    # ------------------------------------------------------------------ #
    # Upload / Download
    # ------------------------------------------------------------------ #
    def _upload_file_ftp(self, local_path: str, remote_path: str, progress_callback=None) -> None:
        file_size = os.path.getsize(local_path)
        uploaded = 0
        chunk_size = 8192
        with open(local_path, "rb") as f:
            def callback(data):
                nonlocal uploaded
                uploaded += len(data)
                if progress_callback:
                    percent = int((uploaded / file_size) * 100) if file_size else 100
                    progress_callback(percent)
            self.conn.storbinary(f"STOR {remote_path}", f, blocksize=chunk_size, callback=callback)
        if self.keep_timestamp:
            modtime = time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(local_path)))
            try:
                self.conn.sendcmd(f"MFMT {modtime} {remote_path}")
            except Exception:
                pass

    def _upload_file_sftp(self, local_path: str, remote_path: str) -> None:
        sftp = self.conn
        sftp.put(local_path, remote_path)
        if self.keep_timestamp:
            atime = os.path.getatime(local_path)
            mtime = os.path.getmtime(local_path)
            sftp.utime(remote_path, (atime, mtime))

    def upload_file(self, local_path: str, remote_dir: str, progress_callback=None) -> None:
        base_name = os.path.basename(local_path)
        remote_path = remote_dir.rstrip("/") + "/" + base_name
        try:
            existing_files = self.list_directory(remote_dir)
            existing_names = [x[0] for x in existing_files]
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
        except Exception:
            pass

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

    def download_file(self, remote_path: str, local_dir: str) -> None:
        filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, filename)
        try:
            if self.ftp_protocol == "ftp":
                if hasattr(self.conn, "sock") and self.conn.sock:
                    old_timeout = self.conn.sock.gettimeout()
                    self.conn.sock.settimeout(60)
                with open(local_path, "wb") as f:
                    self.conn.retrbinary(f"RETR {remote_path}", f.write)
                if hasattr(self.conn, "sock") and self.conn.sock:
                    self.conn.sock.settimeout(old_timeout)
            else:
                sftp = self.conn
                sftp.get(remote_path, local_path)
                if self.keep_timestamp:
                    attr = sftp.stat(remote_path)
                    os.utime(local_path, (attr.st_atime, attr.st_mtime))

            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="SUCCESS")
        except Exception as e:
            debug_print(f"Download fehlgeschlagen: {e}")
            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="FAILED")
            raise

    # ------------------------------------------------------------------ #
    # Listing
    # ------------------------------------------------------------------ #
    def list_directory(self, remote_path: str):
        if self.ftp_protocol == "ftp":
            return self._listdir_ftp(remote_path)
        else:
            return self._listdir_sftp(remote_path)

    def _listdir_ftp(self, remote_path: str):
        """
        Liefert Liste aus Tupeln:
           (name, is_dir, size, mod_time_str, owner?)
        Owner kann leer sein, wenn LIST-Ausgabe das nicht hergibt.
        """
        items = []

        def parse_line(line: str):
            # typische Unix-LIST-Zeile:
            # drwxr-xr-x  2 owner group      4096 Sep 24 12:34  dirname
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

        try:
            self.conn.retrlines(f"LIST {remote_path}", parse_line)
        except Exception as e:
            debug_print(f"LIST-Fehler auf '{remote_path}': {e}")
            raise
        return items

    def _listdir_sftp(self, remote_path: str):
        """
        Für SFTP: Owner ggf. als UID (String).
        """
        sftp = self.conn
        filelist = []
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
        return filelist

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    def log_transfer(self, source, target, direction, status="SUCCESS"):
        logfile_path = get_ftp_transfer_log_path()
        entries = []
        if os.path.exists(logfile_path):
            try:
                with open(logfile_path, "r", encoding="utf-8") as lf:
                    entries = json.load(lf)
            except Exception:
                entries = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_index = 0
        for e in entries:
            if "index" in e:
                try:
                    idx_val = int(e["index"])
                    if idx_val > last_index:
                        last_index = idx_val
                except Exception:
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

    # ------------------------------------------------------------------ #
    # E-Mail / Notifications (neu über utils.mailer.Mailer)
    # ------------------------------------------------------------------ #
    def send_transfer_summary_email(self, results: List[dict]) -> None:
        """
        Schreibt eine Info-Datei und sendet (falls SMTP aktiviert) eine kurze Zusammenfassung.
        """
        info_path = get_mail_transfer_info_path()
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            debug_print(f"Transfer summary written to {info_path}")
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von {info_path}: {e}")

        # SMTP prüfen
        cfg = load_smtp_settings() or {}
        if not cfg.get("enabled", False):
            debug_print("SMTP deaktiviert – keine Transfer-Summary-E-Mail.")
            return
        if not cfg.get("notify_email"):
            debug_print("Kein notify_email konfiguriert – keine Transfer-Summary-E-Mail.")
            return

        summary = "Transfer Summary:\n\n"
        for r in results:
            summary += f"{r.get('direction','')} | {r.get('file','')} -> {r.get('destination','')}\n"
            if r.get("status") == "FAILED":
                summary += f"   Fehler: {r.get('error', 'Unbekannter Fehler')}\n"

        subject = "Transfer Summary Report"

        try:
            mailer = Mailer()
            # Empfänger leer lassen → Mailer nutzt notify_email; JSON als Attachment beilegen
            mailer.send_mail(subject=subject, body=summary, attachments=[info_path])
            debug_print("Transfer summary email sent successfully (über Mailer).")
        except Exception as e:
            debug_print(f"Fehler beim Senden der Transfer summary Mail: {e}")

    def send_failure_notification(self, error_message: str) -> None:
        """
        Zeigt unter macOS eine System-Notification und sendet (falls SMTP aktiviert) eine Fehler-E-Mail.
        """
        if platform.system() == "Darwin" and pync is not None:
            try:
                pync.notify(f"FTP-Transfer fehlgeschlagen: {error_message}", title="PRisM-RAC")
            except Exception:
                pass

        cfg = load_smtp_settings() or {}
        if not cfg.get("enabled", False):
            debug_print("SMTP deaktiviert – keine Fehler-E-Mail.")
            return
        if not cfg.get("notify_email"):
            debug_print("Kein notify_email konfiguriert – keine Fehler-E-Mail.")
            return

        subject = "FTP-Transfer fehlgeschlagen"
        body = f"Folgender Fehler ist aufgetreten:\n\n{error_message}"

        try:
            mailer = Mailer()
            mailer.send_mail(subject=subject, body=body)  # Empfänger -> notify_email
            debug_print("Fehler-E-Mail gesendet (über Mailer).")
        except Exception as e:
            debug_print(f"Fehler beim Senden der Fehler-E-Mail: {e}")

    # ------------------------------------------------------------------ #
    # Remote File Management
    # ------------------------------------------------------------------ #
    def mkdir_remote(self, remote_path):
        if self.ftp_protocol == "ftp":
            try:
                self.conn.mkd(remote_path)
            except ftplib.error_perm as e:
                raise TransferError(f"Fehler beim Erstellen des Ordners {remote_path}: {e}")
        elif self.ftp_protocol == "sftp":
            try:
                self.conn.mkdir(remote_path)
            except Exception as e:
                raise TransferError(f"Fehler beim Erstellen des Ordners {remote_path}: {e}")
        else:
            raise TransferError("Unbekanntes Protokoll")

    def rename_remote(self, old_path, new_path):
        if self.ftp_protocol == "ftp":
            try:
                self.conn.rename(old_path, new_path)
            except ftplib.error_perm as e:
                raise TransferError(f"Fehler beim Umbenennen von {old_path} zu {new_path}: {e}")
        elif self.ftp_protocol == "sftp":
            try:
                self.conn.rename(old_path, new_path)
            except Exception as e:
                raise TransferError(f"Fehler beim Umbenennen von {old_path} zu {new_path}: {e}")
        else:
            raise TransferError("Unbekanntes Protokoll")

    def delete_remote_file(self, remote_path):
        if self.ftp_protocol == "ftp":
            try:
                self.conn.delete(remote_path)
            except ftplib.error_perm as e:
                raise TransferError(f"Fehler beim Löschen der Datei {remote_path}: {e}")
        elif self.ftp_protocol == "sftp":
            try:
                self.conn.remove(remote_path)
            except Exception as e:
                raise TransferError(f"Fehler beim Löschen der Datei {remote_path}: {e}")
        else:
            raise TransferError("Unbekanntes Protokoll")

    def delete_remote_directory(self, remote_path):
        if self.ftp_protocol == "ftp":
            try:
                self.conn.rmd(remote_path)
            except ftplib.error_perm as e:
                raise TransferError(f"Fehler beim Löschen des Ordners {remote_path}: {e}")
        elif self.ftp_protocol == "sftp":
            try:
                self.conn.rmdir(remote_path)
            except Exception as e:
                raise TransferError(f"Fehler beim Löschen des Ordners {remote_path}: {e}")
        else:
            raise TransferError("Unbekanntes Protokoll")

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