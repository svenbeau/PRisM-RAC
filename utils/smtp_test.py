#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from utils.config_manager import load_smtp_settings, debug_print
import keyring
import smtplib

smtp_conf = load_smtp_settings()
debug_print("SMTP-Einstellungen: " + str(smtp_conf))
debug_print(f"Versuche Mailversand über {smtp_conf.get('host')}:{smtp_conf.get('port')}")

smtp_user = smtp_conf.get("user")
smtp_pass = keyring.get_password("PRisM-SMTP", smtp_user)
notify_email = smtp_conf.get("notify_email")

if smtp_user and smtp_pass and notify_email:
    subject = "Testmail von PRisM-CC"
    body = "Dies ist eine Testmail."
    msg = f"From: {smtp_user}\r\nTo: {notify_email}\r\nSubject: {subject}\r\n\r\n{body}"
    try:
        with smtplib.SMTP(smtp_conf.get("host"), smtp_conf.get("port"), timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [notify_email], msg)
        debug_print("Testmail wurde erfolgreich versendet.")
    except Exception as e:
        debug_print(f"Fehler beim Senden der Testmail: {e}")
else:
    debug_print("Unvollständige SMTP-Einstellungen oder Passwort nicht gefunden.")