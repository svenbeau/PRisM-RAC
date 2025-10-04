#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from utils.mailer import Mailer
from utils.config_manager import debug_print

if __name__ == "__main__":
    mailer = Mailer()
    subject = "Testmail von PRisM-CC"
    body = "Dies ist eine Testmail (gesendet über utils.mailer)."

    ok = mailer.send_mail(subject, body)

    if ok:
        debug_print("Testmail wurde erfolgreich versendet.")
    else:
        debug_print("Testmail konnte NICHT versendet werden. Bitte SMTP-Einstellungen prüfen.")