#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
prism_scheduled_transfer.py
---------------------------
Wird extern gestartet (cron/launchd/TaskScheduler oder per 'Jetzt ausführen' Button),
um einen FTP/SFTP-Transfer anhand eines Plans durchzuführen,
OHNE dass PRisM-RAC laufen muss.

Nutzung:
    python prism_scheduled_transfer.py --plan <PlanName>
"""

import os
import sys
import argparse
import traceback

from ftp_manager import FTPManager
from utils.config_manager import debug_print, load_backup_plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Name des Backup-Plans")
    args = parser.parse_args()

    plan_name = args.plan
    plan = load_backup_plan(plan_name)
    if not plan:
        print(f"Plan '{plan_name}' nicht gefunden.")
        sys.exit(1)

    # Prüfen, ob pausiert
    if plan.get("paused", False) is True:
        print(f"Plan '{plan_name}' ist pausiert. Transfer wird nicht ausgeführt.")
        sys.exit(0)

    mgr = FTPManager()

    # Falls der Plan individuelle Einstellungen hat, überschreiben wir sie:
    if "ftp_protocol" in plan:
        mgr.ftp_protocol = plan["ftp_protocol"]
    if "ftp_host" in plan:
        mgr.host = plan["ftp_host"]
    if "ftp_user" in plan:
        mgr.user = plan["ftp_user"]
    if "versioning_mode" in plan:
        mgr.versioning_mode = plan["versioning_mode"]
    if "keep_timestamp" in plan:
        mgr.keep_timestamp = plan["keep_timestamp"]

    source = plan.get("source_path", "")
    target = plan.get("remote_path", "")

    if not os.path.isdir(source):
        print(f"Lokaler Ordner existiert nicht: {source}")
        sys.exit(1)

    try:
        mgr.connect()
        mgr.upload_folder(source, target)
    except Exception as e:
        print(f"Fehler im Scheduled Transfer: {e}")
        traceback.print_exc()
        mgr.send_failure_notification(str(e))
        sys.exit(2)
    finally:
        mgr.disconnect()

    print("Transfer abgeschlossen.")


if __name__ == "__main__":
    main()