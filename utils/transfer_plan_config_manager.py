#!/usr/bin/env python3
# transfer_plan_config_manager.py
# -*- coding: utf-8 -*-

import os
import json
import uuid
from datetime import datetime
from utils.config_manager import debug_print

# Speicherort für die Transferpläne:
TRANSFER_PLANS_FILE = os.path.expanduser(
    "~/Library/Application Support/PRisM-CC/transfer_plans.json"
)

class TransferPlanConfigManager:
    """
    Liest und schreibt transfer_plans.json,
    in dem ein Array von Plan-Dictionaries liegt.
    Jeder Plan: { "id":..., "name":..., ... }
    """

    def __init__(self):
        self.plans = self.load_plans()

    # ---------------- I/O ----------------
    def load_plans(self):
        abs_path = os.path.abspath(TRANSFER_PLANS_FILE)
        debug_print(f"load_plans() wird aufgerufen. Speicherort: {abs_path}")
        if not os.path.exists(TRANSFER_PLANS_FILE):
            debug_print("transfer_plans.json existiert nicht. Rückgabe eines leeren Arrays.")
            return []
        try:
            with open(TRANSFER_PLANS_FILE, "r", encoding="utf-8") as f:
                plans = json.load(f)
                debug_print("load_plans() gelesen:\n" + json.dumps(plans, indent=2, ensure_ascii=False))
                return plans
        except Exception as e:
            debug_print(f"Fehler beim Lesen von transfer_plans.json: {e}")
            return []

    def save_plans(self):
        abs_path = os.path.abspath(TRANSFER_PLANS_FILE)
        debug_print(f"save_plans() wird aufgerufen. Speicherort: {abs_path}")
        os.makedirs(os.path.dirname(TRANSFER_PLANS_FILE), exist_ok=True)
        try:
            with open(TRANSFER_PLANS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.plans, f, indent=2, ensure_ascii=False)
            debug_print("save_plans() schreibt folgenden Inhalt in " + abs_path + ":\n" + json.dumps(self.plans, indent=2, ensure_ascii=False))
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von transfer_plans.json: {e}")

    # ---------------- CRUD ----------------
    def get_plans(self):
        return self.plans

    def get_plan(self, plan_id: str):
        """
        Frisches Re-Load von Disk (um Race-Conditions mit UI-Snapshots zu vermeiden),
        dann Suche nach der ID. Gibt dict oder None zurück.
        """
        self.plans = self.load_plans()
        for p in self.plans:
            if p.get("id") == plan_id:
                return p
        return None

    def add_plan(self, plan_data: dict):
        """
        Fügt einen Plan hinzu (ohne Doppelprüfung). Speichert anschließend.
        """
        self.plans.append(plan_data)
        debug_print("add_plan(): Neuer Plan hinzugefügt:\n" + json.dumps(plan_data, indent=2, ensure_ascii=False))
        self.save_plans()

    def remove_plan(self, plan_id: str):
        self.plans = [p for p in self.plans if p.get("id") != plan_id]
        debug_print(f"remove_plan(): Plan mit id {plan_id} entfernt.")
        self.save_plans()

    def update_plan(self, plan_id: str, new_data: dict):
        """
        Aktualisiert den Plan mit passender ID. Falls nicht gefunden, wird er angelegt.
        """
        debug_print(f"update_plan(): Aktualisiere Plan mit id {plan_id}")
        updated = False
        for idx, plan in enumerate(self.plans):
            if plan.get("id") == plan_id:
                self.plans[idx] = new_data
                updated = True
                debug_print("update_plan(): Neuer Inhalt:\n" + json.dumps(new_data, indent=2, ensure_ascii=False))
                break

        if not updated:
            debug_print(f"update_plan(): Plan id {plan_id} nicht gefunden – füge als neuen Plan hinzu.")
            self.plans.append(new_data)

        self.save_plans()

    # ---------------- Defaults/Factory ----------------
    def create_default_plan(self) -> dict:
        """
        Erzeugt einen lauffähigen Default-Plan (felderkompatibel zu stable-v42/43).
        Achtung: Zeiten werden als 'YYYY-MM-DD HH:MM' vorbefüllt.
        """
        new_id = str(uuid.uuid4())
        # sinnvolle Defaults, konsistent zu deinen Logs
        default_plan = {
            "id": new_id,
            "name": "Neuer Transfer-Plan",
            "source_path": "",
            "use_ftp": False,                 # lokal → lokal als Default
            "ftp_server": "",                 # Name aus servers.json, falls use_ftp=True
            "target_path": "",
            "versioning_mode": "mirror",      # "mirror" | "suffix"
            "suffix_format": "_v{n}",         # genutzt bei "suffix"
            "schedule_type": "once",          # "once" | "daily" | "weekly"
            "schedule_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "move_after": "",
            "body_visible": True,

            # Quelle kann auch ein FTP sein (optional)
            "source_is_ftp": False,
            "source_ftp_server": "",
            "source_remote_path": "",
            "source_remote_archive": "",

            # Robustheit/Verify
            "retry_count": 5,
            "verify_mode": "size_only",       # "size_only" | "md5"

            # Cleaner (move_after Aging)
            "auto_delete_after_move_enabled": False,
            "auto_delete_after_move_hours": 48,

            # Scheduler/Housekeeping
            "last_run": ""
        }
        return default_plan