#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from utils.config_manager import debug_print

# Wir gehen davon aus, dass du in config_manager.py schon
# eine Konstante/Datei-Variable für transfer_plans.json hast,
# z. B. BACKUP_PLANS_FILE oder so. Hier mal "TRANSFER_PLANS_FILE":

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

    def load_plans(self):
        if not os.path.exists(TRANSFER_PLANS_FILE):
            return []
        try:
            with open(TRANSFER_PLANS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            debug_print(f"Fehler beim Lesen von transfer_plans.json: {e}")
            return []

    def save_plans(self):
        os.makedirs(os.path.dirname(TRANSFER_PLANS_FILE), exist_ok=True)
        try:
            with open(TRANSFER_PLANS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.plans, f, indent=2)
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von transfer_plans.json: {e}")

    def get_plans(self):
        return self.plans

    def add_plan(self, plan_data):
        self.plans.append(plan_data)
        self.save_plans()

    def remove_plan(self, plan_id):
        """
        Entfernt den Plan mit plan_id aus self.plans
        """
        self.plans = [p for p in self.plans if p.get("id") != plan_id]
        self.save_plans()

    def update_plan(self, plan_id, new_data):
        """
        Sucht den Plan in self.plans, aktualisiert ihn, speichert.
        """
        for idx, plan in enumerate(self.plans):
            if plan.get("id") == plan_id:
                self.plans[idx] = new_data
                break
        self.save_plans()