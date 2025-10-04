#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import keyring
import smtplib
from utils.config_manager import load_smtp_settings, debug_print

def send_transfer_report(plan_data: dict, body_text: str, summary: dict = None):
    """
    Versendet den Transfer-Report per E-Mail, wenn SMTP aktiviert ist.
    Fällt ansonsten still auf Debug-Log zurück.
    """
    smtp = load_smtp_settings()
    if not smtp.get("enabled", False):
        debug_print("SMTP disabled – Report nicht versendet.")
        return

    host = smtp.get("host", "")
    port = int(smtp.get("port", 587))
    user = smtp.get("user", "")
    to_addr = smtp.get("notify_email", "")

    if not host or not user or not to_addr:
        debug_print("SMTP-Konfiguration unvollständig – Report nicht versendet.")
        return

    smtp_pass = keyring.get_password("PRisM-SMTP", user)
    if smtp_pass is None:
        debug_print("SMTP-Passwort nicht im Keyring – Report nicht versendet.")
        return

    subject = f"[PRisM-RAC] Transfer-Report: {plan_data.get('name','(ohne)')}"
    msg = f"From: {user}\r\nTo: {to_addr}\r\nSubject: {subject}\r\n\r\n{body_text}"

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, smtp_pass)
            server.sendmail(user, [to_addr], msg)
        debug_print("Transfer-Report per Mail versendet.")
    except Exception as e:
        debug_print(f"Fehler beim Versenden des Transfer-Reports: {e}")