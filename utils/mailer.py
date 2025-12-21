#!/usr/bin/env python3
# utils/mailer.py
# -*- coding: utf-8 -*-

"""
Vereinheitlichter Mailer für PRisM-RAC.

Enthält:
- Funktions-API: send_transfer_summary_email(...)
- Kompatibilitäts-Klasse: Mailer (für Alt-Code, z.B. contentcheck_email_notifier)
  - Mailer.send(to, subject, body, results=None, plan=None) -> bool
  - Mailer.send_simple(to, subject, body) -> bool
  - Mailer.send_summary(to, subject, body, results=None, plan=None) -> bool
"""

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import keyring

from utils.config_manager import load_settings, debug_print


# --------- interne Helfer ---------

def _smtp_from_settings(settings: Dict[str, Any]):
    """
    Erwartete Struktur:
      settings["smtp"] = {
        "enabled": True|False,
        "mode": "SSL" | "STARTTLS" | "PLAIN",
        "host": "smtp.example.com",
        "port": 465/587/25,
        "user": "mailer@example.com",
      }
      settings["notify_email"] = "empfaenger@example.com"  # optional
    """
    smtp = (settings or {}).get("smtp", {}) or {}
    mode = str(smtp.get("mode") or "SSL").upper()
    host = str(smtp.get("host") or "").strip()
    port = int(smtp.get("port") or (465 if mode == "SSL" else 587 if mode == "STARTTLS" else 25))
    user = str(smtp.get("user") or "").strip()
    enabled = bool(smtp.get("enabled")) if "enabled" in smtp else True
    return enabled, mode, host, port, user


def _get_password(user: str) -> str:
    # Passwort wie beim Testmail-Dialog: Keyring "PRisM-SMTP"
    if not user:
        return ""
    return keyring.get_password("PRisM-SMTP", user) or ""


def _build_message(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    results: Optional[List[Dict[str, Any]]] = None,
    plan: Optional[Dict[str, Any]] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender or recipient
    msg["To"] = recipient
    msg["Subject"] = subject

    # Einfache Text-Zusammenfassung
    lines = [body.rstrip(), ""]
    if plan:
        lines.append(f"Plan-ID: {plan.get('id', '')}")
        lines.append(f"Quelle:  {plan.get('source_path', '')}")
        lines.append(f"Ziel:    {plan.get('target_path', '')}")
        lines.append("")
    if results:
        ok = sum(1 for r in results if str(r.get("status", "")).upper() == "SUCCESS")
        fail = sum(1 for r in results if str(r.get("status", "")).upper() == "FAILED")
        lines.append(f"Ergebnisse: success={ok}, failed={fail}, total={len(results)}")
        lines.append("")
        lines.append("Richtung | Datei | Status | Fehler")
        lines.append("-----------------------------------")
        for r in results[:50]:  # begrenzen
            lines.append(
                f"{r.get('direction','')} | "
                f"{r.get('file','')} | "
                f"{r.get('status','')} | "
                f"{(r.get('error') or '')}"
            )
        if len(results) > 50:
            lines.append(f"... und {len(results)-50} weitere Zeilen.")
    msg.set_content("\n".join(lines))
    return msg


def _send_via_smtp(mode: str, host: str, port: int, user: str, password: str, msg: EmailMessage) -> bool:
    mode = (mode or "SSL").upper()
    debug_print(f"[Mailer] Sende via {mode} {host}:{port} als {user or '(ohne Benutzer)'}")

    if mode == "SSL":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
            return True

    if mode == "STARTTLS":
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
            return True

    if mode == "PLAIN":
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
            return True

    debug_print(f"[Mailer] Unbekannter Modus: {mode}")
    return False


# --------- öffentliche Funktions-API ---------

def send_transfer_summary_email(
    notify_email: str,
    subject: str,
    body: str,
    results: Optional[List[Dict[str, Any]]] = None,
    plan: Optional[Dict[str, Any]] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Versendet eine Zusammenfassung; gibt True bei Erfolg zurück.
    """
    if not notify_email:
        debug_print("[Mailer] Keine Notify-Adresse gesetzt.")
        return False

    if settings is None:
        try:
            settings = load_settings() or {}
        except Exception:
            settings = {}

    enabled, mode, host, port, user = _smtp_from_settings(settings)
    if not enabled:
        debug_print("[Mailer] SMTP ist deaktiviert.")
        return False
    if not host:
        debug_print("[Mailer] Kein SMTP-Host konfiguriert.")
        return False

    password = _get_password(user)
    if user and not password and mode != "PLAIN":
        debug_print("[Mailer] Warnung: Kein Passwort im Keyring gefunden.")

    sender = user or notify_email
    msg = _build_message(sender, notify_email, subject, body, results, plan)
    return _send_via_smtp(mode, host, port, user, password, msg)


# --------- Kompatibilitäts-Klasse für Alt-Code ---------

class Mailer:
    """
    Kompatibilitätsschicht für bestehenden Code:
       from utils.mailer import Mailer
       mailer = Mailer(settings=...)  # settings optional
       mailer.send(to, subject, body, results=None, plan=None)
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        if settings is None:
            try:
                settings = load_settings() or {}
            except Exception:
                settings = {}
        self.settings = settings

    def send(self,
             to: str,
             subject: str,
             body: str,
             results: Optional[List[Dict[str, Any]]] = None,
             plan: Optional[Dict[str, Any]] = None) -> bool:
        """Generischer Sender (Summary fähig)."""
        return send_transfer_summary_email(
            notify_email=to,
            subject=subject,
            body=body,
            results=results,
            plan=plan,
            settings=self.settings,
        )

    # einige Alt-Aufrufer nutzen evtl. diese Alias-Namen:
    def send_simple(self, to: str, subject: str, body: str) -> bool:
        return self.send(to=to, subject=subject, body=body, results=None, plan=None)

    def send_summary(self,
                     to: str,
                     subject: str,
                     body: str,
                     results: Optional[List[Dict[str, Any]]] = None,
                     plan: Optional[Dict[str, Any]] = None) -> bool:
        return self.send(to=to, subject=subject, body=body, results=results, plan=plan)