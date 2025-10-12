#!/usr/bin/env python3
# ftp_manager.py
# -*- coding: utf-8 -*-

import os
import sys
import time
import keyring
import smtplib
import platform
import json
import ftplib
import posixpath
import tempfile
from datetime import datetime, timezone  # timezone für UTC-ISO
from typing import List, Callable, Any, Optional, Dict

try:
    import pync  # Für macOS-Notification
except ImportError:
    pync = None

try:
    import paramiko  # Für SFTP
except ImportError:
    paramiko = None

# Local TZ (Europe/Berlin) für menschenlesbare ISO-Stempel
try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo("Europe/Berlin")
except Exception:
    _LOCAL_TZ = None

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
      - get_size/stat für Verifikation
      - move_remote Convenience
      - list_files_recursive für Quell-FTP-Scans
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

    # ---------- Hilfen ----------
    @staticmethod
    def _normalize_posix(p: str) -> str:
        if not isinstance(p, str):
            p = str(p)
        p = p.replace("\\", "/")
        # Doppelslashes (außer am Anfang) vermeiden
        if len(p) > 1:
            while "//" in p[1:]:
                p = p[0] + p[1:].replace("//", "/")
        return p

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

    # ---- Verbindung prüfen (für Worker) ----
    def is_connected(self) -> bool:
        """
        Liefert True, wenn eine Verbindung-Instanz vorhanden ist. (Leichtgewichtig,
        bewusst ohne NOOP-Command, um Hänger zu vermeiden.)
        """
        try:
            return self.conn is not None
        except Exception:
            return False

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
        remote_dir = self._normalize_posix(remote_dir)
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
                    if not d:
                        continue
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
                    if not d:
                        continue
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
        remote_path = self._normalize_posix(remote_path)

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
                    # nicht jeder Server unterstützt MFMT
                    self.conn.sendcmd(f"MFMT {modtime} {remote_path}")
                except Exception:
                    pass

        self._retry_op(f"upload_file_ftp:{remote_path}", _impl)

    def _upload_file_sftp(self, local_path, remote_path):
        remote_path = self._normalize_posix(remote_path)
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
        remote_dir = self._normalize_posix(remote_dir)
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
            return remote_path
        except Exception as e:
            debug_print(f"Upload fehlgeschlagen: {e}")
            self.log_transfer(local_path, remote_path, "UPLOAD", status="FAILED")
            raise

    def download_file(self, remote_path, local_dir):
        remote_path = self._normalize_posix(remote_path)
        filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, filename)

        def _impl_ftp(path_to_get: str):
            if hasattr(self.conn, "sock") and self.conn.sock:
                old_timeout = self.conn.sock.gettimeout()
                self.conn.sock.settimeout(60)
            try:
                with open(local_path, "wb") as f:
                    self.conn.retrbinary(f"RETR {path_to_get}", f.write)
            finally:
                if hasattr(self.conn, "sock") and self.conn.sock:
                    self.conn.sock.settimeout(old_timeout)

        def _impl_sftp(path_to_get: str):
            sftp = self.conn
            sftp.get(path_to_get, local_path)
            if self.keep_timestamp:
                attr = sftp.stat(path_to_get)
                os.utime(local_path, (attr.st_atime, attr.st_mtime))

        try:
            if self.ftp_protocol == "ftp":
                try:
                    self._retry_op(f"download_file_ftp:{remote_path}", lambda: _impl_ftp(remote_path))
                except Exception:
                    # Alternative: ohne führenden Slash versuchen
                    alt = remote_path.lstrip("/")
                    if alt != remote_path:
                        self._retry_op(f"download_file_ftp:{alt}", lambda: _impl_ftp(alt))
                    else:
                        raise
            else:
                try:
                    self._retry_op(f"download_file_sftp:{remote_path}", lambda: _impl_sftp(remote_path))
                except Exception:
                    alt = remote_path.lstrip("/")
                    if alt != remote_path:
                        self._retry_op(f"download_file_sftp:{alt}", lambda: _impl_sftp(alt))
                    else:
                        raise

            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="SUCCESS")
        except Exception as e:
            debug_print(f"Download fehlgeschlagen: {e}")
            self.log_transfer(remote_path, local_path, "DOWNLOAD", status="FAILED")
            raise

        return local_path

    def list_directory(self, remote_path):
        remote_path = self._normalize_posix(remote_path)
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

        def _impl_list(path_to_list: str):
            try:
                self.conn.cwd(path_to_list)
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

            self.conn.retrlines(f"LIST {path_to_list}", parse_line)

        try:
            self._retry_op(f"listdir_ftp:{remote_path}", lambda: _impl_list(remote_path))
        except Exception:
            # Alternative ohne führenden Slash
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                self._retry_op(f"listdir_ftp:{alt}", lambda: _impl_list(alt))
            else:
                raise
        return items

    def _listdir_sftp(self, remote_path):
        """
        Für SFTP: Owner kann ggf. als UID geliefert werden. Wir geben die UID als String aus.
        """
        filelist = []

        def _impl(path_to_list: str):
            sftp = self.conn
            for f in sftp.listdir_attr(path_to_list):
                name = f.filename
                # Ordnererkennung robust:
                is_dir = False
                try:
                    sftp.listdir(path_to_list.rstrip("/") + "/" + name)
                    is_dir = True
                except IOError:
                    is_dir = False
                size = getattr(f, "st_size", 0)
                mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(getattr(f, "st_mtime", 0)))
                owner = str(getattr(f, "st_uid", ""))  # UID als Fallback
                filelist.append((name, is_dir, size, mod_time, owner))

        try:
            self._retry_op(f"listdir_sftp:{remote_path}", lambda: _impl(path_to_list=remote_path))
        except Exception:
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                self._retry_op(f"listdir_sftp:{alt}", lambda: _impl(path_to_list=alt))
            else:
                raise
        return filelist

    # ---------------- get_size / stat / md5 ----------------
    def get_size(self, remote_path: str) -> Optional[int]:
        """
        Liefert Dateigröße in Bytes oder None. Testet ggf. alternative Pfadvariante ohne führenden Slash.
        """
        remote_path = self._normalize_posix(remote_path)

        def _ftp_try(path_to_check: str) -> Optional[int]:
            try:
                size = self._retry_op(f"ftp_size:{path_to_check}", lambda: self.conn.size(path_to_check))
                if size is not None:
                    return int(size)
            except Exception:
                # Fallback: stat() probieren
                info = self.stat(path_to_check)
                if info and info.get("size") is not None:
                    return int(info["size"])
            return None

        def _sftp_try(path_to_check: str) -> Optional[int]:
            try:
                st = self._retry_op(f"sftp_stat:{path_to_check}", lambda: self.conn.stat(path_to_check))
                return int(st.st_size)
            except Exception:
                return None

        if self.ftp_protocol == "ftp":
            s = _ftp_try(remote_path)
            if s is not None:
                return s
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                return _ftp_try(alt)
            return None
        else:
            s = _sftp_try(remote_path)
            if s is not None:
                return s
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                return _sftp_try(alt)
            return None

    def stat(self, remote_path: str) -> Optional[Dict]:
        """
        Liefert ein Dict mit Feldern (sofern verfügbar):
          {"size": int, "mtime": int|None, "mode": int|None}
        oder None.
        """
        remote_path = self._normalize_posix(remote_path)

        def _ftp_mlst(path_to_check: str) -> Optional[Dict]:
            try:
                # MLST liefert eine Zeile mit Facts; via sendcmd abrufen
                # Beispiel: '250-Listing ...\n type=file;size=123;modify=20250109101530;perm=adfr; /path/file\n250 End.'
                resp = self._retry_op(f"ftp_mlst:{path_to_check}", lambda: self.conn.sendcmd(f"MLST {path_to_check}"))
                facts_line = ""
                for line in resp.splitlines():
                    line = line.strip()
                    if ";" in line and "type=" in line:
                        facts_line = line
                        break
                facts = {}
                if facts_line:
                    # bis zum ersten Leerzeichen sind Facts
                    facts_part = facts_line.split(" ", 1)[0]
                    for kv in facts_part.split(";"):
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            facts[k.strip().lower()] = v.strip()
                out = {}
                if "size" in facts and facts["size"].isdigit():
                    out["size"] = int(facts["size"])
                else:
                    # ohne MLST size -> None
                    pass
                # mtime aus "modify" (YYYYMMDDhhmmss) -> nicht trivial ohne TZ; wir liefern None
                out["mtime"] = None
                out["mode"] = None
                return out if out else None
            except Exception:
                return None

        def _sftp_stat(path_to_check: str) -> Optional[Dict]:
            try:
                st = self._retry_op(f"sftp_stat:{path_to_check}", lambda: self.conn.stat(path_to_check))
                return {
                    "size": int(getattr(st, "st_size", 0)),
                    "mtime": int(getattr(st, "st_mtime", 0)) if hasattr(st, "st_mtime") else None,
                    "mode": int(getattr(st, "st_mode", 0)) if hasattr(st, "st_mode") else None,
                }
            except Exception:
                return None

        if self.ftp_protocol == "ftp":
            info = _ftp_mlst(remote_path)
            if info:
                return info
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                return _ftp_mlst(alt)
            return None
        else:
            info = _sftp_stat(remote_path)
            if info:
                return info
            alt = remote_path.lstrip("/")
            if alt != remote_path:
                return _sftp_stat(alt)
            return None

    def md5(self, remote_path: str) -> str:
        """
        Optional: MD5 vom Server anfragen. Viele FTP/SFTP-Server unterstützen das nicht.
        Wir werfen bewusst NotImplementedError, damit der Aufrufer fallbacked.
        """
        raise NotImplementedError("Remote-MD5 wird vom Server/Protokoll nicht unterstützt.")

    # --- Remote File Management (unverändert, plus move_remote) ---
    def mkdir_remote(self, remote_path):
        remote_path = self._normalize_posix(remote_path)
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.mkd(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.mkdir(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"mkdir_remote:{remote_path}", _impl)

    def rename_remote(self, old_path, new_path):
        old_path = self._normalize_posix(old_path)
        new_path = self._normalize_posix(new_path)
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.rename(old_path, new_path)
            elif self.ftp_protocol == "sftp":
                self.conn.rename(old_path, new_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"rename_remote:{old_path}->{new_path}", _impl)

    def move_remote(self, src_remote: str, dst_remote: str):
        """
        Bequemer Move mit Fallback (copy+delete), inkl. Zielverzeichnis-Erstellung.
        """
        src_remote = self._normalize_posix(src_remote)
        dst_remote = self._normalize_posix(dst_remote)
        dst_dir = posixpath.dirname(dst_remote)
        self.ensure_remote_directory(dst_dir)

        try:
            self.rename_remote(src_remote, dst_remote)
            return
        except Exception:
            pass

        # Fallback: RETR -> STOR -> DELETE
        if self.ftp_protocol == "ftp":
            def _impl_copy():
                tmp = tempfile.TemporaryFile()
                self.conn.retrbinary(f"RETR {src_remote}", tmp.write)
                tmp.seek(0)
                self.conn.storbinary(f"STOR {dst_remote}", tmp)
                tmp.close()
                try:
                    self.conn.delete(src_remote)
                except Exception:
                    pass
            self._retry_op(f"move_remote_fallback_ftp:{src_remote}->{dst_remote}", _impl_copy)
        else:
            def _impl_copy():
                f_in = self.conn.open(src_remote, "rb")
                try:
                    self.conn.putfo(f_in, dst_remote)
                finally:
                    try:
                        f_in.close()
                    except Exception:
                        pass
                try:
                    self.conn.remove(src_remote)
                except Exception:
                    pass
            self._retry_op(f"move_remote_fallback_sftp:{src_remote}->{dst_remote}", _impl_copy)

    def delete_remote_file(self, remote_path):
        remote_path = self._normalize_posix(remote_path)
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.delete(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.remove(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"delete_remote_file:{remote_path}", _impl)

    def delete_remote_directory(self, remote_path):
        remote_path = self._normalize_posix(remote_path)
        def _impl():
            if self.ftp_protocol == "ftp":
                self.conn.rmdir(remote_path)
            elif self.ftp_protocol == "sftp":
                self.conn.rmdir(remote_path)
            else:
                raise TransferError("Unbekanntes Protokoll")
        self._retry_op(f"delete_remote_dir:{remote_path}", _impl)

    def upload_folder(self, local_folder, remote_folder):
        remote_folder = self._normalize_posix(remote_folder)
        for root, dirs, files in os.walk(local_folder):
            relative_sub = os.path.relpath(root, local_folder)
            if relative_sub == ".":
                remote_sub = remote_folder
            else:
                remote_sub = remote_folder.rstrip("/") + "/" + self._normalize_posix(relative_sub)
            for file in files:
                local_path = os.path.join(root, file)
                try:
                    self.upload_file(local_path, remote_sub)
                except Exception as e:
                    self.send_failure_notification(str(e))
                    raise

    # ---------------- Rekursives Listing für FTP-Quelle ----------------
    def list_files_recursive(self, remote_root: str) -> List[str]:
        """
        Liefert alle Dateien unter remote_root als relative POSIX-Pfade.
        """
        remote_root = self._normalize_posix(remote_root).rstrip("/")
        files: List[str] = []

        if self.ftp_protocol == "ftp":
            def _walk(dir_path: str, rel_prefix: str):
                entries = self._listdir_ftp(dir_path)
                for name, is_dir, size, _, _ in entries:
                    if name in (".", ".."):
                        continue
                    child_abs = dir_path.rstrip("/") + "/" + name
                    child_rel = (rel_prefix + "/" + name) if rel_prefix else name
                    if is_dir:
                        _walk(child_abs, child_rel)
                    else:
                        files.append(child_rel)

            try:
                _walk(remote_root, "")
            except Exception as e:
                debug_print(f"[list_files_recursive FTP] Fehler: {e}")
                raise
        else:
            def _walk_sftp(dir_path: str, rel_prefix: str):
                try:
                    for attr in self.conn.listdir_attr(dir_path):
                        name = attr.filename
                        if name in (".", ".."):
                            continue
                        child_abs = dir_path.rstrip("/") + "/" + name
                        child_rel = (rel_prefix + "/" + name) if rel_prefix else name
                        # Verzeichnis?
                        is_dir = False
                        try:
                            # robust: Verzeichnis?
                            self.conn.listdir(child_abs)
                            is_dir = True
                        except IOError:
                            is_dir = False
                        if is_dir:
                            _walk_sftp(child_abs, child_rel)
                        else:
                            files.append(child_rel)
                except Exception as e:
                    debug_print(f"[list_files_recursive SFTP] Fehler: {e}")
                    raise

            _walk_sftp(remote_root, "")

        debug_print(f"[list_files_recursive] {len(files)} Dateien unter {remote_root}")
        return files

    # ------------- Zeit-Helfer -------------
    def _now_utc_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _now_local_iso(self) -> Optional[str]:
        if _LOCAL_TZ is None:
            return None
        return datetime.now(_LOCAL_TZ).isoformat()

    # ---------------- Logging/Benachrichtigung ----------------
    def log_transfer(self, source, target, direction, status="SUCCESS"):
        logfile_path = get_ftp_transfer_log_path()
        entries = []
        if os.path.exists(logfile_path):
            try:
                with open(logfile_path, "r", encoding="utf-8") as lf:
                    entries = json.load(lf)
            except:
                entries = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # legacy beibehalten
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
            "timestamp": now_str,                       # legacy
            "event_time_utc": self._now_utc_iso(),     # neu
            "event_time_local": self._now_local_iso(), # neu
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
        Schreibt immer eine Status-Datei mit Ergebnissen + Mail-Metadaten.
        Sendet E-Mail nur, wenn SMTP aktiviert und notify_email vorhanden.
        Nutzt automatisch SSL bei Port 465, sonst (sofern nicht Port 25) STARTTLS.
        """
        from utils.config_manager import get_mail_transfer_info_path
        info_path = get_mail_transfer_info_path()

        # Basisinformationen für Statusausgabe
        mail_meta = {
            "attempted_at_utc": self._now_utc_iso(),
            "enabled": bool(self.smtp_enabled),
            "host": self.smtp_host,
            "port": self.smtp_port,
            "user_present": bool(self.smtp_user),
            "notify_email_present": bool(self.notify_email),
            "mode": "unknown",
            "result": "SKIPPED",
            "error": ""
        }

        # Statusdatei vorab schreiben (mit Roh-Results)
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({"results": results, "mail": mail_meta}, f, indent=2)
            debug_print(f"Transfer summary written to {info_path}")
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von {info_path}: {e}")

        # Voraussetzungen prüfen
        if not self.smtp_enabled:
            mail_meta["result"] = "SKIPPED_DISABLED"
        elif not self.notify_email:
            mail_meta["result"] = "SKIPPED_NO_NOTIFY_EMAIL"
        else:
            smtp_pass = None
            if self.smtp_user:
                smtp_pass = keyring.get_password("PRisM-SMTP", self.smtp_user)
                if smtp_pass is None:
                    debug_print("SMTP-Passwort nicht im Keyring, kann keine Transfer Summary Mail senden.")
                    mail_meta["result"] = "ERROR_NO_PASSWORD"
                    mail_meta["error"] = "Keychain: PRisM-SMTP Passwort fehlt"
            # Sendeversuch nur, wenn kein Fehler bis hier
            if mail_meta["result"] in ("SKIPPED_DISABLED", "SKIPPED_NO_NOTIFY_EMAIL"):
                pass
            else:
                try:
                    # Transportmodus bestimmen
                    use_ssl = (int(self.smtp_port) == 465)
                    mail_meta["mode"] = "SSL" if use_ssl else ("PLAIN" if int(self.smtp_port) == 25 else "STARTTLS")

                    subject = "Transfer Summary Report"
                    summary = "Transfer Summary:\n\n"
                    for r in results:
                        summary += f"{r['direction']} | {r['file']} -> {r.get('destination', '')}\n"
                        if r["status"] == "FAILED":
                            summary += f"   Fehler: {r.get('error', 'Unbekannter Fehler')}\n"
                    msg = f"From: {self.smtp_user}\r\nTo: {self.notify_email}\r\nSubject: {subject}\r\n\r\n{summary}"

                    if use_ssl:
                        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15) as server:
                            if self.smtp_user:
                                server.login(self.smtp_user, smtp_pass or "")
                            server.sendmail(self.smtp_user or self.notify_email, [self.notify_email], msg)
                    else:
                        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                            server.ehlo()
                            if int(self.smtp_port) != 25:
                                server.starttls()
                                server.ehlo()
                            if self.smtp_user:
                                server.login(self.smtp_user, smtp_pass or "")
                            server.sendmail(self.smtp_user or self.notify_email, [self.notify_email], msg)

                    mail_meta["result"] = "SENT"
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    debug_print(f"Fehler beim Senden der Transfer summary Mail: {err}")
                    mail_meta["result"] = "ERROR_SMTP"
                    mail_meta["error"] = err

        # Statusdatei mit finalem Mailstatus aktualisieren
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({"results": results, "mail": mail_meta}, f, indent=2)
        except Exception as e:
            debug_print(f"Fehler beim Aktualisieren von {info_path}: {e}")

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

if __name__ == "__main__":
    mgr = FTPManager()
    try:
        mgr.connect()
    except Exception as e:
        mgr.send_failure_notification(str(e))
    finally:
        mgr.disconnect()