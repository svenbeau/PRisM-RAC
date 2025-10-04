#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
utils/self_check.py
System-/Netzwerk-Selbsttests für PRisM-RAC.

Fixes:
- HTTPS-Fallback ohne 'requests' (nutzt urllib + ssl + certifi)
- FTP-Exception-Handling stabil: ftplib.all_errors
- Robustere Dataclasses/Defaults
"""

from __future__ import annotations
import os
import ssl
import smtplib
import socket
import json
import time
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

# Optional 'requests' (für Komfort); wir haben jetzt Fallback ohne requests
try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore

# CA-Bundle
try:
    import certifi  # type: ignore
except Exception:
    certifi = None  # type: ignore

# FTP/FTPS über ftplib
import ftplib

# Optional: Paramiko für SFTP
try:
    import paramiko  # type: ignore
except Exception:
    paramiko = None  # type: ignore


APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "PRisM-CC"
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SmtpConfig:
    host: str
    port: int = 587
    use_starttls: bool = True
    user: str = ""
    password: str = ""
    from_addr: str = ""
    to_default: Optional[list] = None


@dataclass
class FtpConfig:
    mode: str = "FTP"  # FTP | FTPS | SFTP
    host: str = ""
    port: int = 21
    user: str = ""
    password: str = ""
    passive: bool = True
    remote_base: str = "/"


def load_settings() -> Dict[str, Any]:
    """
    Lädt settings.json aus App-Support. Falls fehlt/kaputt: Minimal-Objekt.
    """
    path = APP_SUPPORT_DIR / "settings.json"
    if not path.exists():
        return {
            "mail": {
                "smtp_host": "",
                "smtp_port": 587,
                "use_starttls": True,
                "user": "",
                "from": "",
                "to_default": []
            },
            "smtp": {
                "host": "",
                "port": 587,
                "use_starttls": True,
                "user": ""
            },
            "ftp": {
                "mode": "FTP",
                "host": "",
                "port": 21,
                "user": "",
                "passive": True,
                "remote_base": "/"
            }
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_error": f"settings.json konnte nicht gelesen werden: {e}"}


def get_certifi_verify_path() -> Optional[str]:
    if certifi is None:
        return None
    try:
        return certifi.where()
    except Exception:
        return None


def test_https(url: str = "https://www.python.org", timeout: int = 8) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Testet eine HTTPS-Verbindung.
    - Wenn 'requests' vorhanden ist, verwenden wir es (bequemer).
    - Sonst Fallback mit urllib.request + SSL-Kontext (certifi, wenn vorhanden).
    """
    verify_path = get_certifi_verify_path()
    info = {"certifi": bool(verify_path), "url": url}

    # Variante 1: requests
    if requests is not None:
        kwargs = {"timeout": timeout}
        if verify_path:
            kwargs["verify"] = verify_path
        t0 = time.time()
        try:
            r = requests.get(url, **kwargs)
            dt = round((time.time() - t0) * 1000)
            ok = 200 <= r.status_code < 400
            msg = f"GET {url} → Status {r.status_code} in {dt} ms"
            info.update({"status": r.status_code, "elapsed_ms": dt})
            return ok, msg, info
        except Exception as e:
            return False, f"HTTPS-Fehler (requests): {e}", info

    # Variante 2: urllib Fallback
    try:
        import urllib.request
        ctx = ssl.create_default_context(cafile=verify_path) if verify_path else ssl.create_default_context()
        req = urllib.request.Request(url, method="GET")
        t0 = time.time()
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            dt = round((time.time() - t0) * 1000)
        ok = 200 <= status < 400
        msg = f"GET {url} → Status {status} in {dt} ms"
        info.update({"status": status, "elapsed_ms": dt})
        return ok, msg, info
    except Exception as e:
        return False, f"HTTPS-Fehler (urllib): {e}", info


def test_smtp(cfg: SmtpConfig, timeout: int = 8, do_login: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Testet SMTP-Verbindung (SSL oder STARTTLS) und optionalen Login.
    """
    verify_path = get_certifi_verify_path()
    context = ssl.create_default_context(cafile=verify_path) if verify_path else ssl.create_default_context()

    info = {
        "host": cfg.host, "port": cfg.port, "use_starttls": cfg.use_starttls,
        "user_set": bool(cfg.user), "certifi": bool(verify_path)
    }

    try:
        if cfg.port == 465 and not cfg.use_starttls:
            # SMTP über SSL
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=timeout, context=context) as server:
                server.ehlo()
                if do_login and cfg.user and cfg.password:
                    server.login(cfg.user, cfg.password)
        else:
            # Plain + STARTTLS (falls aktiviert)
            with smtplib.SMTP(cfg.host, cfg.port, timeout=timeout) as server:
                server.ehlo()
                if cfg.use_starttls:
                    server.starttls(context=context)
                    server.ehlo()
                if do_login and cfg.user and cfg.password:
                    server.login(cfg.user, cfg.password)
        return True, "SMTP-Verbindung ok.", info
    except (smtplib.SMTPException, socket.timeout, OSError) as e:
        return False, f"SMTP-Fehler: {e}", info


def test_ftp(cfg: FtpConfig, timeout: int = 8, listdir: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Testet FTP oder FTPS (explicit TLS) Login und optional LIST/PWD.
    """
    mode = (cfg.mode or "FTP").upper()
    info = {"mode": mode, "host": cfg.host, "port": cfg.port, "user_set": bool(cfg.user)}

    try:
        if mode == "FTPS":
            verify_path = get_certifi_verify_path()
            tls_ctx = ssl.create_default_context(cafile=verify_path) if verify_path else ssl.create_default_context()
            ftps = ftplib.FTP_TLS()
            ftps.connect(cfg.host, cfg.port or 21, timeout=timeout)
            ftps.auth()             # explizites TLS
            ftps.prot_p()           # Datenkanal schützen
            ftps.login(cfg.user or "anonymous", cfg.password or "")
            ftps.set_pasv(bool(cfg.passive))
            if listdir:
                _ = ftps.pwd()
                _ = ftps.nlst(cfg.remote_base or ".")
            ftps.quit()
        elif mode == "FTP":
            ftp = ftplib.FTP()
            ftp.connect(cfg.host, cfg.port or 21, timeout=timeout)
            ftp.login(cfg.user or "anonymous", cfg.password or "")
            ftp.set_pasv(bool(cfg.passive))
            if listdir:
                _ = ftp.pwd()
                _ = ftp.nlst(cfg.remote_base or ".")
            ftp.quit()
        else:
            return False, f"FTP-Test: Modus {mode} nicht unterstützt (verwende test_sftp).", info

        return True, f"{mode} Verbindung ok.", info

    except (ftplib.all_errors, socket.timeout, OSError) as e:  # <- sicherer Catch
        return False, f"{mode} Fehler: {e}", info


def test_sftp(cfg: FtpConfig, timeout: int = 8, listdir: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Testet SFTP via Paramiko. Nur verfügbar, wenn paramiko installiert ist.
    """
    info = {"mode": "SFTP", "host": cfg.host, "port": cfg.port, "user_set": bool(cfg.user)}
    if paramiko is None:
        return False, "Paramiko nicht installiert.", info

    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            cfg.host, port=cfg.port or 22,
            username=cfg.user or None,
            password=cfg.password or None,
            timeout=timeout,
            allow_agent=True, look_for_keys=True
        )
        sftp = client.open_sftp()
        if listdir:
            base = cfg.remote_base or "."
            _ = sftp.listdir(base)
        sftp.close()
        client.close()
        return True, "SFTP Verbindung ok.", info
    except Exception as e:
        try:
            if client:
                client.close()
        except Exception:
            pass
        return False, f"SFTP Fehler: {e}", info


def test_write_access(target_dir: Path = APP_SUPPORT_DIR) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Prüft Schreib-/Lese-/Löschrecht im Zielverzeichnis.
    """
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        probe = target_dir / ".write_probe.tmp"
        data = {"ok": True}
        with open(probe, "w", encoding="utf-8") as f:
            json.dump(data, f)
        with open(probe, "r", encoding="utf-8") as f:
            obj = json.load(f)
        probe.unlink(missing_ok=True)
        return bool(obj.get("ok")), f"Write-Check ok in {target_dir}", {"dir": str(target_dir)}
    except Exception as e:
        return False, f"Write-Check Fehler: {e}", {"dir": str(target_dir)}