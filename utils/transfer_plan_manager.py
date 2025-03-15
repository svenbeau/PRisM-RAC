#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from utils.config_manager import debug_print

# Pfad zur Transferplan-Datei:
TRANSFER_PLAN_FILE = os.path.expanduser(
    "~/Library/Application Support/PRisM-CC/config/transferplan_settings.json"
)

class TransferPlanManager:
    """
    Verwalten der Transferpläne in transferplan_settings.json.
    Jeder Eintrag könnte z.B. so aussehen:
      {
        "id": "uuid-string",
        "name": "Plan-Name",
        "source_path": "/lokaler/ordner" oder "ftp://...",
        "destination_path": "/lokaler/ordner" oder "ftp://...",
        "use_ftp": False,
        "ftp_server": "",   # Name aus der Server-Verwaltung, falls use_ftp=True
        "versioning": "mirror" oder "suffix",
        "suffix_format": "_v",
        "schedule": "none" / "daily" / "weekly" / "once",
        "scheduled_time": "2025-03-15 20:00",  # optional
        "move_after_transfer": "/some/folder", # optional
        "body_visible": True
      }
    """

    def __init__(self):
        os.makedirs(os.path.dirname(TRANSFER_PLAN_FILE), exist_ok=True)
        self._plans = self._load_plans()

    def _load_plans(self):
        if not os.path.exists(TRANSFER_PLAN_FILE):
            return []
        try:
            with open(TRANSFER_PLAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            debug_print(f"Error reading {TRANSFER_PLAN_FILE}: {e}")
            return []

    def _save_plans(self):
        try:
            with open(TRANSFER_PLAN_FILE, "w", encoding="utf-8") as f:
                json.dump(self._plans, f, indent=2)
        except Exception as e:
            debug_print(f"Error saving {TRANSFER_PLAN_FILE}: {e}")

    def get_plans(self):
        return self._plans

    def add_plan(self, plan_data):
        """
        plan_data = dict mit mind.:
          {
            "name": "...",
            "source_path": "...",
            ...
          }
        """
        if "id" not in plan_data:
            plan_data["id"] = str(uuid.uuid4())
        self._plans.append(plan_data)
        self._save_plans()

    def update_plan(self, plan_id, new_data):
        """
        Sucht den Plan mit plan_id und aktualisiert die Felder.
        """
        for idx, plan in enumerate(self._plans):
            if plan.get("id") == plan_id:
                self._plans[idx].update(new_data)
                self._save_plans()
                return

    def remove_plan(self, plan_id):
        """
        Entfernt den Plan mit plan_id.
        """
        before_count = len(self._plans)
        self._plans = [p for p in self._plans if p.get("id") != plan_id]
        after_count = len(self._plans)
        if after_count != before_count:
            self._save_plans()
        else:
            debug_print(f"Plan mit id={plan_id} nicht gefunden.")

    def save_plans(self):
        """
        Falls du explizit speichern willst.
        """
        self._save_plans()