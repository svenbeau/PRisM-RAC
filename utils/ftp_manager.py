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
    debug_print
)

class TransferError(Exception):
    """Eigene Exception für FTP-/SFTP-Fehler."""
    pass

class FTPManager:
    """
    Kapselt alle FTP-/SFTP-Funktionen:
      - Verbindung aufbauen (FTP oder SFTP)
      - Dateien hoch-/runterladen
      - Versionierungsoption ("mirror" = überschreiben, "suffix" = neue Version)
      - Logging in ftptransfer_log.json (JSON) (jetzt mit "status"=SUCCESS/FAILED)
      - E-Mail/Notification bei Fehler
      - ggf. Timestamp-Erhaltung
      - Remote-Verzeichnis erstellen (ensure_remote_directory)
      - Methoden zum Erstellen, Umbenennen, Löschen von Remote-Dateien/Ordnern
    """

    def __init__(self):
        # 1) FTP-Einstellungen => aus settings.json
        self.settings = load_settings()
        self.ftp_protocol = self.settings.get("ftp_protocol", "ftp")  # "ftp" oder "sftp"
        self.host = self.settings.get("ftp_host", "")
        self.user = self.settings.get("ftp_user", "")
        self.password = None
        self.port = 21
        if self.ftp_protocol == "sftp":
            self.port = 22

        self.versioning_mode = self.settings.get("versioning_mode", "mirror")
        self.keep_timestamp = self.settings.get("keep_timestamp", False)

        # 2) SMTP-Einstellungen => aus smtp_settings.json
        smtp_conf = load_smtp_settings()
        self.smtp_enabled = smtp_conf.get("enabled", False)
        self.smtp_host = smtp_conf.get("host", "")
        self.smtp_port = smtp_conf.get("port", 587)
        self.smtp_user = smtp_conf.get("user", "")
        self.notify_email = smtp_conf.get("notify_email", "")

    def _load_password_from_keyring(self):
        if not self.user:
            raise TransferError("Kein FTP-Benutzername definiert.")
        service_name = "PRisM-FTP"
        passwd = keyring.get_password(service_name, self.user)
        if passwd is None:
            raise TransferError(f"Kein Passwort im Keyring gefunden für {self.user}")
        self.password = passwd

    def connect(self):
        """Baut je nach Protocol (FTP oder SFTP) eine Verbindung auf."""
        self._load_password_from_keyring()
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
            self.conn = paramiko.Transport((self.host, self.port))
            self.conn.connect(None, self.user, self.password)
            sftp = paramiko.SFTPClient.from_transport(self.conn)
            self.conn = sftp
        else:
            raise TransferError("Unbekanntes Protokoll: " + self.ftp_protocol)

        debug_print(f"Verbindung zu {self.host} via {self.ftp_protocol} aufgebaut.")

    def disconnect(self):
        if hasattr(self, "conn") and self.conn:
            try:
                if self.ftp_protocol == "ftp":
                    self.conn.quit()
                else:
                    self.conn.close()
            except Exception:
                pass
            debug_print("Verbindung geschlossen.")

    def ensure_remote_directory(self, remote_dir):
        """Stellt sicher, dass das Remote-Verzeichnis existiert (rekursiv)."""
        if self.ftp_protocol == "ftp":
            import ftplib
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

    # Neuer Callback-Upload für FTP (optional)
    def _upload_file_ftp(self, local_path, remote_path, progress_callback=None):
        file_size = os.path.getsize(local_path)
        uploaded = 0
        chunk_size = 8192
        with open(local_path, "rb") as f:
            def callback(data):
                nonlocal uploaded
                uploaded += len(data)
                if progress_callback:
                    percent = int((uploaded / file_size) * 100)
                    progress_callback(percent)
            self.conn.storbinary(f"STOR {remote_path}", f, blocksize=chunk_size, callback=callback)
        if self.keep_timestamp:
            modtime = time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(local_path)))
            try:
                self.conn.sendcmd(f"MFMT {modtime} {remote_path}")
            except Exception:
                pass

    def _upload_file_sftp(self, local_path, remote_path):
        sftp = self.conn
        sftp.put(local_path, remote_path)
        if self.keep_timestamp:
            atime = os.path.getatime(local_path)
            mtime = os.path.getmtime(local_path)
            sftp.utime(remote_path, (atime, mtime))

    def upload_file(self, local_path, remote_dir, progress_callback=None):
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

        # Neu: Wir erfassen success/fail => log_transfer(..., status="...")
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

    def list_directory(self, remote_path):
        if self.ftp_protocol == "ftp":
            return self._listdir_ftp(remote_path)
        else:
            return self._listdir_sftp(remote_path)

    def _listdir_ftp(self, remote_path):
        items = []
        def parse_line(line):
            parts = line.split()
            if len(parts) < 9:
                return
            name = " ".join(parts[8:])
            size = int(parts[4])
            is_dir = line.startswith("d")
            mod_time_str = f"{parts[5]} {parts[6]} {parts[7]}"
            items.append((name, is_dir, size, mod_time_str))
        self.conn.retrlines(f"LIST {remote_path}", parse_line)
        return items

    def _listdir_sftp(self, remote_path):
        sftp = self.conn
        filelist = []
        for f in sftp.listdir_attr(remote_path):
            name = f.filename
            is_dir = False
            try:
                sftp.listdir(remote_path + "/" + name)
                is_dir = True
            except IOError:
                pass
            size = f.st_size
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.st_mtime))
            filelist.append((name, is_dir, size, mod_time))
        return filelist

    def log_transfer(self, source, target, direction, status="SUCCESS"):
        """
        Schreibt in ftptransfer_log.json
        mit den Feldern: index, timestamp, direction, source, target, status
        """
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
        """
        'results' ist eine Liste von Dictionaries mit den Transfer-Ergebnissen.
        """
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

    # --- Neue Methoden für Remote File Management ---
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