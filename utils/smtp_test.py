#!/usr/bin/env python3
import smtplib
from email.message import EmailMessage
from utils.config_manager import load_smtp_settings, debug_print


def send_test_mail():
    # Lade die SMTP-Einstellungen aus smtp_settings.json
    smtp_conf = load_smtp_settings()
    debug_print(f"SMTP-Einstellungen: {smtp_conf}")

    # Prüfe, ob alle nötigen Einstellungen vorhanden sind
    if not smtp_conf.get("host") or not smtp_conf.get("user") or not smtp_conf.get("notify_email"):
        debug_print("Fehlende SMTP-Einstellungen (host, user oder notify_email)")
        return

    SMTP_HOST = smtp_conf.get("host")
    SMTP_PORT = smtp_conf.get("port")
    SMTP_USER = smtp_conf.get("user")
    # Hier verwenden wir das Passwort aus dem Keyring; alternativ könntest du es auch in der Datei speichern (nicht empfohlen)
    # Für diesen Test muss das Passwort jedoch vorher im Keyring hinterlegt worden sein.
    import keyring
    SMTP_PASS = keyring.get_password("PRisM-SMTP", SMTP_USER)
    if not SMTP_PASS:
        debug_print("Kein SMTP-Passwort im Keyring gefunden.")
        return
    NOTIFY_EMAIL = smtp_conf.get("notify_email")

    msg = EmailMessage()
    msg.set_content("Dies ist eine Testmail, um den SMTP-Versand zu prüfen.")
    msg["Subject"] = "SMTP Test"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL

    try:
        debug_print(f"Versuche Mailversand über {SMTP_HOST}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        debug_print("Testmail wurde erfolgreich versendet!")
    except Exception as e:
        debug_print(f"Fehler beim Senden der Testmail: {e}")


if __name__ == "__main__":
    send_test_mail()