# utils/mailer.py
# -*- coding: utf-8 -*-
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, Optional, Union
import keyring

from utils.config_manager import load_smtp_settings, debug_print


class Mailer:
    """
    Zentrale SMTP-Sendeinstanz.
    Liest Settings bei jedem Sendevorgang frisch (damit UI-Änderungen sofort wirken).
    Passwort liegt im Keyring (Service-Name: 'PRisM-SMTP').
    Unterstützt:
      - STARTTLS (Standard)
      - SSL/SMTPS (Port 465), via Settings-Feld 'use_ssl' (Bool)
    """
    SERVICE_NAME = "PRisM-SMTP"

    def __init__(self):
        pass

    # ---------------- Keychain Helpers ----------------
    @staticmethod
    def get_settings() -> dict:
        """
        Lädt SMTP-Settings und reichert sie — falls vorhanden — mit dem Keychain-Passwort an.
        Erwartete Felder in smtp_settings.json:
          - enabled: bool
          - host: str
          - port: int
          - user: str
          - notify_email: str
          - use_ssl: bool (NEU) -> True => SMTP_SSL; False => SMTP(+optional STARTTLS)
        """
        settings = load_smtp_settings() or {}
        user = settings.get("user", "").strip()
        # Passwort NICHT in der Datei speichern; wenn vorhanden, aus Keyring holen
        if user and not settings.get("password"):
            try:
                pw = keyring.get_password(Mailer.SERVICE_NAME, user) or ""
                if pw:
                    settings["password"] = pw
            except Exception:
                pass
        return settings

    @staticmethod
    def set_password(user: str, password: str):
        """PW im Keyring ablegen (wird nicht in JSON gespeichert)."""
        if user and password is not None:
            keyring.set_password(Mailer.SERVICE_NAME, user.strip(), password)

    @staticmethod
    def delete_password(user: str):
        """PW aus dem Keyring entfernen (falls vorhanden)."""
        if not user:
            return
        try:
            keyring.delete_password(Mailer.SERVICE_NAME, user.strip())
        except keyring.errors.PasswordDeleteError:
            # Kein Eintrag vorhanden – ist okay
            pass
        except Exception as e:
            debug_print(f"[Mailer] Passwort löschen fehlgeschlagen: {e}")

    # ---------------- Versand ----------------
    def send_mail(
        self,
        subject: str,
        body: str,
        to: Union[str, Iterable[str], None] = None,
        attachments: Optional[Iterable[str]] = None,
        from_override: Optional[str] = None,
    ) -> None:
        """
        Sendet eine E-Mail gemäß derzeitiger Settings.
        - to: String (ein Empfänger) oder Iterable von Adressen; None → nimmt notify_email
        - attachments: Pfade zu Dateien (optional)
        - from_override: falls du einen expliziten From-Header setzen willst
        Wirft Exceptions bei Verbindungs-/Sendeproblemen.
        """
        cfg = self.get_settings()
        if not cfg.get("enabled", False):
            debug_print("[Mailer] SMTP deaktiviert – E-Mail nicht gesendet.")
            return

        host = (cfg.get("host") or "").strip()
        port = int(cfg.get("port", 587) or 587)
        user = (cfg.get("user") or "").strip()
        password = cfg.get("password", "")
        default_to = (cfg.get("notify_email") or "").strip()
        use_ssl = bool(cfg.get("use_ssl", False) or port == 465)  # Port 465 ⇒ SSL erzwingen

        if not host or not user:
            raise RuntimeError("SMTP nicht korrekt konfiguriert (host/user fehlen).")

        # Empfänger auflösen
        if to is None or (isinstance(to, str) and not to.strip()):
            if not default_to:
                raise RuntimeError("Kein Empfänger angegeben und kein notify_email konfiguriert.")
            to_list = [default_to]
        elif isinstance(to, str):
            to_list = [to]
        else:
            to_list = list(to)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_override or user
        msg["To"] = ", ".join(to_list)
        msg.set_content(body)

        # Attachments (robust als octet-stream)
        if attachments:
            for path in attachments:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    msg.add_attachment(
                        data,
                        maintype="application",
                        subtype="octet-stream",
                        filename=path.split("/")[-1],
                    )
                except Exception as e:
                    debug_print(f"[Mailer] Attachment konnte nicht gelesen werden: {path} ({e})")

        # Versand
        context = ssl.create_default_context()
        if use_ssl:
            # SMTPS (Port 465)
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
                if user:
                    server.login(user, password or "")
                server.send_message(msg)
                debug_print(f"[Mailer] (SSL) E-Mail gesendet an {to_list}")
        else:
            # SMTP, optional STARTTLS
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                try:
                    server.starttls(context=context)
                    server.ehlo()
                except Exception:
                    # falls z. B. Port 25 ohne STARTTLS – weiter ohne TLS
                    pass
                if user:
                    server.login(user, password or "")
                server.send_message(msg)
                debug_print(f"[Mailer] E-Mail gesendet an {to_list}")