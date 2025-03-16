#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import smtplib
import keyring
from datetime import datetime
from utils.config_manager import load_smtp_settings, debug_print


def send_fail_email_from_content(content_check, file_path):
    """
    Versendet eine E-Mail mit den Contentcheck-Informationen in einem menschenlesbaren Format.
    Der Inhalt wird zeilenweise ausgegeben – z.B.:

    Content Check Fail Log Report:

    Datei: /Pfad/zur/Datei
    Layer Status: OK
    Metadata Status: FAIL
    Fehlende Metadaten: author, description

    metadata:
      documentTitle: undefined
      author: undefined
      authorPosition: undefined
      description: undefined
      ...

    details:
      checkType: Standard
      keywordCheck.enabled: True
      keywordCheck.keyword: Rueckseite
      ...

    :param content_check: Dictionary mit den Contentcheck-Ergebnissen (z.B. aus [Dateiname]_01_log_contentcheck.json)
    :param file_path: Pfad zur Datei, bei der der Contentcheck durchgeführt wurde
    """
    # Kopfzeile der E-Mail
    email_body = "Content Check Fail Log Report:\n\n"
    email_body += f"Datei: {file_path}\n\n"

    # Prüfe, ob es ein Contentcheck-Dictionary gibt
    if content_check:
        # Basisinformationen aus dem "details"-Block
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

        # Abschnitt "metadata"
        metadata = content_check.get("metadata", {})
        if metadata:
            email_body += "metadata:\n"
            for key, value in metadata.items():
                email_body += f"  {key}: {value}\n"
            email_body += "\n"

        # Weitere Details aus "details" (ohne die bereits ausgegebenen Felder)
        email_body += "details:\n"
        for key, value in details.items():
            if key in ["layerStatus", "metaStatus", "missingLayers", "missingMetadata"]:
                continue
            # Wenn der Wert ein verschachteltes Dictionary ist, iteriere auch darüber
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    email_body += f"  {key}.{sub_key}: {sub_value}\n"
            else:
                email_body += f"  {key}: {value}\n"
    else:
        email_body += "Kein Contentcheck-Inhalt vorhanden.\n"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_body += f"\nGesendet am: {now_str}\n"

    subject = "Content Check Fail Log Report"
    smtp_settings = load_smtp_settings()
    smtp_user = smtp_settings.get("user", "")
    notify_email = smtp_settings.get("notify_email", "")

    message = (f"From: {smtp_user}\r\n"
               f"To: {notify_email}\r\n"
               f"Subject: {subject}\r\n\r\n{email_body}")

    # SMTP-Einstellungen
    smtp_enabled = smtp_settings.get("enabled", False)
    smtp_host = smtp_settings.get("host", "")
    smtp_port = smtp_settings.get("port", 587)

    if not smtp_enabled or not notify_email:
        debug_print("SMTP ist nicht aktiviert oder keine Notify-E-Mail konfiguriert. E-Mail wird nicht gesendet.")
        return

    smtp_pass = keyring.get_password("PRisM-SMTP", smtp_user)
    if smtp_pass is None:
        debug_print("SMTP-Passwort nicht im Keyring, E-Mail kann nicht gesendet werden.")
        return

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [notify_email], message)
        debug_print("Content Check Fail E-Mail erfolgreich gesendet.")
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
    test_file_path = "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/01_Monitor/01_Render/4069284_Kirchner_3193_01_leer.psd"
    send_fail_email_from_content(example_content_check, test_file_path)