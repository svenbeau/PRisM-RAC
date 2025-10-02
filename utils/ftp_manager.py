#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import keyring
import smtplib
import platform
import json
import socket
from datetime import datetime
from typing import List
from pathlib import Path

import ftplib
try:
    import paramiko
except ImportError:
    paramiko = None

from utils.helpers import debug_print


class TransferError(Exception):
    pass


class FTPManager:
    def __init__(self, server_config):
        self.server_config = server_config
        self.conn = None
        self.ftp_protocol = server_config.get("protocol", "ftp")
        self.host = server_config.get("host", "")
        self.port = int(server_config.get("port", 21))
        self.user = server_config.get("user", "")
        self.password = server_config.get("password", "")
        self.keep_timestamp = server_config.get("keep_timestamp", True)
        self.versioning_mode = server_config.get("versioning_mode", "overwrite")

        # SMTP Settings
        self.smtp_enabled = server_config.get("smtp_enabled", False)
        self.smtp_host = server_config.get("smtp_host", "")
        self.smtp_port = int(server_config.get("smtp_port", 587))
        self.smtp_user = server_config.get("smtp_user", "")
        self.smtp_pass = server_config.get("smtp_pass", "")
        self.notify_email = server_config.get("notify_email", "")

    # -------------------------
    # Connection Management
    # -------------------------

    def _ensure_connected(self):
        """Check if connection is alive, else reconnect."""
        if not self.conn:
            self.connect()
            return
        try:
            self.conn.voidcmd("NOOP")
        except Exception:
            try:
                self.disconnect()
            finally:
                self.connect()

    def _with_retry(self, func, *args, **kwargs):
        """Retry wrapper for FTP ops (1 reconnect)."""
        tries = 2
        last_exc = None
        for i in range(tries):
            try:
                self._ensure_connected()
                return func(*args, **kwargs)
            except (ftplib.error_temp, OSError, TimeoutError, socket.timeout) as e:
                last_exc = e
                debug_print(f"[FTPManager] transienter Fehler ({e}) -> Reconnect + Retry …")
                self.disconnect()
                self.connect()
        if last_exc:
            raise last_exc

    def connect(self):
        self._load_password_from_keyring()
        debug_print(f"Versuche {self.ftp_protocol.upper()}-Connect zu {self.host}:{self.port}, user={self.user}")

        if self.ftp_protocol == "ftp":
            self.conn = ftplib.FTP()
            self.conn.connect(self.host, self.port, timeout=30)
            self.conn.login(self.user, self.password)
            self.conn.set_pasv(True)
            try:
                self.conn.sendcmd("TYPE I")
            except Exception:
                pass
            if hasattr(self.conn, "sock") and self.conn.sock:
                self.conn.sock.settimeout(60)
                try:
                    self.conn.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except Exception:
                    pass
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
                self.conn.quit()
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
            self.conn = None

    # -------------------------
    # SMTP
    # -------------------------

    def send_transfer_summary_email(self, results):
        if not (self.smtp_enabled and self.smtp_host and self.notify_email and self.smtp_user):
            return
        try:
            msg = "\n".join([f"{r['action']}: {r['file']} [{r['status']}]" for r in results])
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_user, self.notify_email, msg)
            server.quit()
        except Exception as e:
            debug_print(f"Fehler beim Senden der E-Mail: {e}")

    def send_failure_notification(self, error_message):
        if not (self.smtp_enabled and self.smtp_host and self.notify_email and self.smtp_user):
            return
        try:
            msg = f"Transfer Error:\n{error_message}"
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_user, self.notify_email, msg)
            server.quit()
        except Exception as e:
            debug_print(f"Fehler beim Senden der Fehler-E-Mail: {e}")

    # -------------------------
    # Directory Handling
    # -------------------------

    def ensure_remote_directory(self, remote_dir):
        if self.ftp_protocol == "ftp":
            return self._with_retry(self._ensure_remote_dir_ftp, remote_dir)
        else:
            return self._ensure_remote_dir_sftp(remote_dir)

    def _ensure_remote_dir_ftp(self, remote_dir):
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
                try:
                    self.conn.mkd(cwd)
                except Exception as e:
                    debug_print(f"Fehler beim Erstellen des Ordners {cwd}: {e}")

    def _ensure_remote_dir_sftp(self, remote_dir):
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

    def list_directory(self, remote_path):
        if self.ftp_protocol == "ftp":
            return self._with_retry(self._listdir_ftp, remote_path)
        else:
            return self._listdir_sftp(remote_path)

    def _listdir_ftp(self, remote_path):
        result = []

        def callback(line):
            parts = line.split(maxsplit=8)
            if len(parts) < 9:
                return
            name = parts[-1]
            size = int(parts[4]) if parts[4].isdigit() else 0
            kind = "Dir" if parts[0].startswith("d") else "File"
            result.append((name, size, kind))

        self.conn.retrlines(f"LIST {remote_path}", callback)
        return result

    def _listdir_sftp(self, remote_path):
        result = []
        for f in self.conn.listdir_attr(remote_path):
            kind = "Dir" if str(f.longname).startswith("d") else "File"
            result.append((f.filename, f.st_size, kind))
        return result

    # -------------------------
    # File Transfer
    # -------------------------

    def get_remote_size(self, remote_path) -> int:
        """Return size of file on remote, -1 if not available."""
        if self.ftp_protocol != "ftp":
            try:
                return getattr(self.conn.stat(remote_path), "st_size", -1)
            except Exception:
                return -1
        try:
            self._ensure_connected()
            resp = self.conn.sendcmd(f"SIZE {remote_path}")
            return int(resp.split()[1])
        except Exception:
            return -1

    def _upload_file_ftp(self, local_path, remote_final_path, progress_callback=None):
        """Upload with resume, .part temp, verify + rename."""
        self._ensure_connected()

        remote_dir = os.path.dirname(remote_final_path).rstrip("/")
        base_name = os.path.basename(remote_final_path)
        temp_name = f".{base_name}.part"
        remote_temp_path = f"{remote_dir}/{temp_name}"

        file_size = os.path.getsize(local_path)
        chunk_size = 64 * 1024
        uploaded = 0

        offset = 0
        try:
            resp = self.conn.sendcmd(f"SIZE {remote_temp_path}")
            offset = int(resp.split()[1])
            if offset < 0 or offset > file_size:
                offset = 0
        except Exception:
            offset = 0

        with open(local_path, "rb") as f:
            if offset:
                f.seek(offset)
                uploaded = offset

            def callback(data):
                nonlocal uploaded
                uploaded += len(data)
                if progress_callback:
                    percent = int((uploaded / file_size) * 100)
                    progress_callback(percent)

            if offset:
                self.conn.storbinary(f"STOR {remote_temp_path}", f, blocksize=chunk_size, callback=callback, rest=offset)
            else:
                self.conn.storbinary(f"STOR {remote_temp_path}", f, blocksize=chunk_size, callback=callback)

        remote_size = self.get_remote_size(remote_temp_path)
        if remote_size != file_size:
            raise ftplib.error_temp(f"incomplete upload ({remote_size}/{file_size} bytes)")

        if self.keep_timestamp:
            modtime = time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(local_path)))
            try:
                self.conn.sendcmd(f"MFMT {modtime} {remote_temp_path}")
            except Exception:
                pass

        try:
            self.conn.rename(remote_temp_path, remote_final_path)
        except Exception:
            try:
                self.conn.delete(remote_final_path)
            except Exception:
                pass
            self.conn.rename(remote_temp_path, remote_final_path)

    def _upload_file_sftp(self, local_path, remote_final_path):
        self.ensure_remote_directory(os.path.dirname(remote_final_path))
        self.conn.put(local_path, remote_final_path)

    def upload_file(self, local_path, remote_dir, progress_callback=None):
        base_name = os.path.basename(local_path)
        remote_final = remote_dir.rstrip("/") + "/" + base_name

        try:
            entries = self.list_directory(remote_dir)
            existing_names = [x[0] for x in entries]
            if base_name in existing_names and self.versioning_mode == "suffix":
                ver = 2
                root, ext = os.path.splitext(base_name)
                new_name = f"{root}_v{ver}{ext}"
                while new_name in existing_names:
                    ver += 1
                    new_name = f"{root}_v{ver}{ext}"
                remote_final = remote_dir.rstrip("/") + "/" + new_name
        except Exception:
            pass

        self.ensure_remote_directory(remote_dir)

        try:
            if self.ftp_protocol == "ftp":
                self._with_retry(self._upload_file_ftp, local_path, remote_final, progress_callback)
            else:
                self._upload_file_sftp(local_path, remote_final)
            self.log_transfer(local_path, remote_final, "UPLOAD", status="SUCCESS")
        except Exception as e:
            debug_print(f"Upload fehlgeschlagen: {e}")
            self.log_transfer(local_path, remote_final, "UPLOAD", status="FAILED")
            raise

    def download_file(self, remote_file, local_path):
        if self.ftp_protocol == "ftp":
            with open(local_path, "wb") as f:
                self.conn.retrbinary(f"RETR {remote_file}", f.write)
        else:
            self.conn.get(remote_file, local_path)

    # -------------------------
    # Logging
    # -------------------------

    def log_transfer(self, local_path, remote_path, action, status="SUCCESS"):
        debug_print(f"[{action}] {local_path} → {remote_path} [{status}]")

    def _load_password_from_keyring(self):
        if not self.password:
            try:
                pwd = keyring.get_password("PRiSM-CC", self.user + "@" + self.host)
                if pwd:
                    self.password = pwd
            except Exception:
                pass