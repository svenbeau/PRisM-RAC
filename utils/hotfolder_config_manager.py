#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import uuid
from utils.path_manager import get_hotfolder_config_path

def debug_print(msg):
    print(f"[HotfolderManager] {msg}")

class HotfolderConfigManager:
    """
    Verwaltet das Laden und Speichern der hotfolder_config.json
    sowie das Hinzufügen, Updaten und Löschen von Hotfoldern.
    """
    CONFIG_FILENAME = get_hotfolder_config_path()

    def __init__(self):
        self.data = {"hotfolders": []}
        self.load_config()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILENAME):
            try:
                with open(self.CONFIG_FILENAME, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                debug_print(f"Fehler beim Laden der Konfiguration: {e}")
        else:
            self.save_config()

    def save_config(self):
        try:
            with open(self.CONFIG_FILENAME, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            debug_print(f"Fehler beim Speichern der Konfiguration: {e}")

    def get_hotfolders(self):
        return self.data.get("hotfolders", [])

    def add_hotfolder(self, hotfolder):
        self.data.setdefault("hotfolders", []).append(hotfolder)
        self.save_config()

    def update_hotfolder(self, hotfolder_id, updated_data):
        for hf in self.data.get("hotfolders", []):
            if hf.get("id") == hotfolder_id:
                hf.update(updated_data)
                break
        self.save_config()

    def remove_hotfolder(self, hotfolder_id):
        self.data["hotfolders"] = [hf for hf in self.data.get("hotfolders", []) if hf.get("id") != hotfolder_id]
        self.save_config()

    def get_hotfolder_by_id(self, hotfolder_id):
        for hf in self.data.get("hotfolders", []):
            if hf.get("id") == hotfolder_id:
                return hf
        return None

    def generate_hotfolder_id(self):
        return str(uuid.uuid4())

    def export_hotfolders(self, export_path):
        try:
            hotfolders = self.get_hotfolders()
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(hotfolders, f, indent=4, ensure_ascii=False)
            debug_print("Hotfolders erfolgreich exportiert.")
        except Exception as e:
            debug_print(f"Exportfehler: {e}")

    def import_hotfolders(self, import_path):
        try:
            if os.path.exists(import_path):
                with open(import_path, "r", encoding="utf-8") as f:
                    hotfolders = json.load(f)
                self.data["hotfolders"] = hotfolders
                self.save_config()
                debug_print("Hotfolders erfolgreich importiert.")
            else:
                debug_print("Importdatei nicht gefunden.")
        except Exception as e:
            debug_print(f"Importfehler: {e}")