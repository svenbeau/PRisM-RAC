#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from utils.config_manager import load_smtp_settings, debug_print
from utils.mailer import Mailer


def _format_contentcheck_mail(content_check: dict, file_path: str) -> str:
    """
    Baut den menschenlesbaren E-Mailtext für Contentcheck-Fehler.
    """
    email_body = "Content Check Fail Log Report:\n\n"
    email_body += f"Datei: {file_path}\n\n"

    if content_check:
        details = content_check.get("details", {})
        layer_status = details.get("layerStatus", "N/A")
        meta_status = details.get("metaStatus", "N/A")
        missing_layers = details.get("missingLayers", [])
        missing_metadata = details.get("missingMetadata", [])

        email_body += f"Layer Status: {layer_status}\n"
        email_body += f"Metadata Status: {meta_status}\n"
        if missing_layers:
            email_body += f"Fehlende Ebenen: {', '.join(missing_layers)}\n"
        if missing_metadata:
            email_body += f"Fehlende Metadaten: {', '.join(missing_metadata)}\n"
        email_body += "\n"

        metadata = content_check.get("metadata", {})
        if metadata:
            email_body += "metadata:\n"
            for key, value in metadata.items():
                email_body += f"  {key}: {value}\n"
            email_body += "\n"

        email_body += "details:\n"
        for key, value in details.items():
            if key in ["layerStatus", "metaStatus", "missingLayers", "missingMetadata"]:
                continue
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    email_body += f"  {key}.{sub_key}: {sub_value}\n"
            else:
                email_body += f"  {key}: {value}\n"
    else:
        email_body += "Kein Contentcheck-Inhalt vorhanden.\n"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_body += f"\nGesendet am: {now_str}\n"
    return email_body


def send_fail_email_from_content(content_check: dict, file_path: str) -> None:
    """
    Versendet die Contentcheck-Fehler-E-Mail über utils.mailer.Mailer.
    Nutzt die globalen SMTP-Einstellungen; notify_email wird automatisch gezogen.
    """
    # Vorab prüfen, ob SMTP überhaupt aktiviert/konfiguriert ist
    smtp_settings = load_smtp_settings() or {}
    if not smtp_settings.get("enabled", False):
        debug_print("SMTP ist nicht aktiviert. Keine Contentcheck-E-Mail wird gesendet.")
        return
    if not smtp_settings.get("notify_email"):
        debug_print("Kein notify_email konfiguriert. Keine Contentcheck-E-Mail wird gesendet.")
        return

    try:
        body = _format_contentcheck_mail(content_check, file_path)
        subject = "Content Check Fail Log Report"

        mailer = Mailer()
        # Empfänger nicht explizit übergeben → Mailer nimmt notify_email
        mailer.send_mail(subject=subject, body=body)

        debug_print("Content Check Fail E-Mail erfolgreich gesendet (über Mailer).")
    except Exception as e:
        debug_print(f"Fehler beim Senden der Content Check Fail E-Mail: {e}")


if __name__ == "__main__":
    # Beispielaufruf zum Testen
    example_content_check = {
        "metadata": {
            "documentTitle": "undefined",
            "author": "undefined",
            "authorPosition": "undefined",
            "description": "undefined",
            "descriptionWriter": "undefined",
            "keywords": "undefined",
            "copyrightNotice": "undefined",
            "copyrightURL": "undefined",
            "city": "undefined",
            "stateProvince": "undefined",
            "country": "undefined",
            "creditLine": "undefined",
            "source": "undefined",
            "headline": "undefined",
            "instructions": "undefined",
            "transmissionRef": "undefined"
        },
        "details": {
            "layers": {},
            "missingLayers": [],
            "missingMetadata": ["author", "description"],
            "layerStatus": "OK",
            "metaStatus": "FAIL",
            "checkType": "Standard",
            "keywordCheck": {"enabled": True, "keyword": "Rueckseite"}
        }
    }
    test_file_path = "/Pfad/zur/Datei/beispiel.psd"
    send_fail_email_from_content(example_content_check, test_file_path)