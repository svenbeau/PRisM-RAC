#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from utils.config_manager import debug_print

# Kanonischer Speicherort der Transferpläne (ein Array von Dictionaries)
TRANSFER_PLAN_FILE = os.path.expanduser(
    "~/Library/Application Support/PRisM-CC/config/transferplan_settings.json"
)

_DEFAULT_PLAN: Dict[str, Any] = {
    "id": None,
    "name": "Neuer Transfer-Plan",
    "source_type": "local",                 # "local" | "ftp" (später ausbaufähig)
    "source_path": "",
    "destination_path": "",
    "use_ftp": False,
    "ftp_server_name": "",
    "version_mode": "mirror",               # "mirror" | "suffix"
    "suffix_format": "_v{n}",
    # --- Scheduler (mit ftp_schedule_widget kompatibel) ---
    # Zeitpunkt im lokalen Format "YYYY-MM-DD HH:MM"
    "schedule_type": "once",                # "once" | "daily" | "weekly"
    "schedule_time": "",                    # z.B. "2025-10-03 22:00"
    # Laufzeit-Marker, werden vom Scheduler geschrieben:
    "last_run": "",
    "completed_once_at": "",
    # UI
    "body_visible": True,
}

class TransferPlanManager:
    """
    Verwaltung der Transferpläne in einer JSON-Datei.

    Jeder Plan ist ein Dict und nutzt das oben definierte Schema.
    Nicht vorhandene Felder werden beim Laden mit Defaults aufgefüllt,
    damit alle Module konsistente Keys sehen.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._path = storage_path or TRANSFER_PLAN_FILE
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._plans: List[Dict[str, Any]] = self._load_plans()

    # ---------- IO ----------
    def _load_plans(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            plans = []
            for p in raw or []:
                plans.append(self._apply_defaults(p))
            return plans
        except Exception as e:
            debug_print(f"[TransferPlanManager] Error reading {self._path}: {e}")
            return []

    def _save_plans(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._plans, f, indent=2, ensure_ascii=False)
        except Exception as e:
            debug_print(f"[TransferPlanManager] Error saving {self._path}: {e}")

    # ---------- Helpers ----------
    def _apply_defaults(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(_DEFAULT_PLAN)
        out.update(plan or {})
        # id sicherstellen
        if not out.get("id"):
            out["id"] = str(uuid.uuid4())
        # Backward-Compat: vereinheitliche alte Keys
        # - "target_path" -> "destination_path"
        if "target_path" in out and not out.get("destination_path"):
            out["destination_path"] = out.pop("target_path")
        # - "versioning_mode" -> "version_mode"
        if "versioning_mode" in out and not out.get("version_mode"):
            out["version_mode"] = out.pop("versioning_mode")
        # - "schedule" (freitext) -> keine direkte Übernahme; falls Datum erkennbar, nutze als schedule_time
        return out

    # ---------- Public API (instanzbasiert) ----------
    def list_plans(self) -> List[Dict[str, Any]]:
        return list(self._plans)

    def add_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        plan = self._apply_defaults(plan_data)
        # neue ID vergeben, falls nötig
        if not plan.get("id"):
            plan["id"] = str(uuid.uuid4())
        self._plans.append(plan)
        self._save_plans()
        return plan

    def update_plan(self, plan_id: str, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for idx, plan in enumerate(self._plans):
            if plan.get("id") == plan_id:
                merged = self._apply_defaults({**plan, **(new_data or {})})
                self._plans[idx] = merged
                self._save_plans()
                return merged
        debug_print(f"[TransferPlanManager] update_plan: id={plan_id} not found.")
        return None

    def remove_plan(self, plan_id: str) -> bool:
        before = len(self._plans)
        self._plans = [p for p in self._plans if p.get("id") != plan_id]
        if len(self._plans) != before:
            self._save_plans()
            return True
        debug_print(f"[TransferPlanManager] remove_plan: id={plan_id} not found.")
        return False


# ---------- Modulweite Convenience-Funktionen ----------
# Viele bestehende Widgets importieren diese Funktions-API.
# Wir stellen diese hier über ein Singleton bereit.
_singleton: Optional[TransferPlanManager] = None

def _mgr() -> TransferPlanManager:
    global _singleton
    if _singleton is None:
        _singleton = TransferPlanManager()
    return _singleton

def load_transfer_plans() -> List[Dict[str, Any]]:
    """Liefert eine Liste aller Pläne."""
    return _mgr().list_plans()

def add_transfer_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fügt einen Plan hinzu und gibt den gespeicherten Plan zurück (mit id)."""
    return _mgr().add_plan(plan_data)

def update_transfer_plan(plan_id: str, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Aktualisiert einen Plan; gibt den gemergten Plan zurück oder None, wenn id unbekannt ist."""
    return _mgr().update_plan(plan_id, new_data)

def remove_transfer_plan(plan_id: str) -> bool:
    """Entfernt einen Plan. True, wenn erfolgreich."""
    return _mgr().remove_plan(plan_id)