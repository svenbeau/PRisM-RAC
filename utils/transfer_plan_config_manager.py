#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
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

    def load_plans(self):
        abs_path = os.path.abspath(TRANSFER_PLANS_FILE)
        debug_print(f"load_plans() wird aufgerufen. Speicherort: {abs_path}")
        if not os.path.exists(TRANSFER_PLANS_FILE):
            debug_print("transfer_plans.json existiert nicht. Rückgabe eines leeren Arrays.")
            return []
        try:
            with open(TRANSFER_PLANS_FILE, "r", encoding="utf-8") as f:
                plans = json.load(f)
                debug_print("load_plans() gelesen:\n" + json.dumps(plans, indent=2))
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
                json.dump(self.plans, f, indent=2)
            debug_print("save_plans() schreibt folgenden Inhalt in " + abs_path + ":\n" + json.dumps(self.plans, indent=2))
        except Exception as e:
            debug_print(f"Fehler beim Schreiben von transfer_plans.json: {e}")

    def get_plans(self):
        return self.plans

    def add_plan(self, plan_data):
        self.plans.append(plan_data)
        debug_print("add_plan(): Neuer Plan hinzugefügt:\n" + json.dumps(plan_data, indent=2))
        self.save_plans()

    def remove_plan(self, plan_id):
        self.plans = [p for p in self.plans if p.get("id") != plan_id]
        debug_print(f"remove_plan(): Plan mit id {plan_id} entfernt.")
        self.save_plans()

    def update_plan(self, plan_id, new_data):
        debug_print(f"update_plan(): Aktualisiere Plan mit id {plan_id}")
        for idx, plan in enumerate(self.plans):
            if plan.get("id") == plan_id:
                self.plans[idx] = new_data
                debug_print("update_plan(): Neuer Inhalt:\n" + json.dumps(new_data, indent=2))
                break
        self.save_plans()