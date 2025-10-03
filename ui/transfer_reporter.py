#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smtplib
from email.message import EmailMessage
from typing import Dict, Any, Optional
from utils.config_manager import load_smtp_settings, debug_print

def _build_subject(plan: Dict[str, Any], summary: Dict[str, int]) -> str:
    name = plan.get("name", "Transfer-Plan")
    ok = summary.get("ok", 0)
    failed = summary.get("failed", 0)
    aborted = summary.get("aborted", 0)
    return f"[PRisM-CC] Transfer-Report: {name} — OK:{ok} FAIL:{failed} ABRT:{aborted}"

def send_transfer_report(plan_data: Dict[str, Any], report_text: str,
                         summary: Optional[Dict[str, int]] = None) -> bool:
    """
    Versendet den Transfer-Report als Text-Mail auf Basis der SMTP-Settings aus config_manager.
    - Nutzt TLS (STARTTLS), falls Port üblich (z.B. 587).
    - Authentifiziert nur, wenn 'user' + 'password' gesetzt sind.
    - Empfänger: settings['notify_email']
    Rückgabe: True/False für Erfolg.
    """
    settings = load_smtp_settings()
    if not settings or not settings.get("enabled"):
        debug_print("[transfer_reporter] SMTP disabled; überspringe Mailversand.")
        return False

    host = settings.get("host", "")
    port = int(settings.get("port", 587))
    user = settings.get("user", "")
    pwd  = settings.get("password", "")  # optional; falls nicht vorhanden, wird ohne Login gesendet
    to   = settings.get("notify_email", "")

    if not host or not to:
        debug_print("[transfer_reporter] host/notify_email fehlen; Mailversand abgebrochen.")
        return False

    if summary is None:
        summary = {"ok": 0, "failed": 0, "aborted": 0}

    subject = _build_subject(plan_data, summary)

    msg = EmailMessage()
    msg["From"] = user if user else f"no-reply@{host}"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(report_text)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            try:
                smtp.starttls()
            except Exception:
                # Einige Server benötigen/erlauben kein STARTTLS
                pass
            if user and pwd:
                smtp.login(user, pwd)
            smtp.send_message(msg)
        debug_print("[transfer_reporter] Report erfolgreich versendet.")
        return True
    except Exception as e:
        debug_print(f"[transfer_reporter] Mailversand fehlgeschlagen: {e}")
        return False