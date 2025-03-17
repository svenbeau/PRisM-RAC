#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

# Beispiel-Utility-Funktion für Debug:
def debug_print(msg):
    print("[HotfolderManager]", msg)

class HotfolderConfigManager:
    """
    Verwaltet das Laden und Speichern der hotfolder_config.json
    sowie das Hinzufügen, Updaten und Löschen von Hotfoldern.
    """
    CONFIG_FILENAME = "hotfolder_config.json"

    def __init__(self):
        pass

    def load_config(self):
        """
        Lädt die gesamte JSON in eine Liste von Hotfolder-Dictionaries.
        """
        if not os.path.exists(self.CONFIG_FILENAME):
            debug_print("hotfolder_config.json nicht gefunden, gebe leere Liste zurück.")
            return []
        try:
            with open(self.CONFIG_FILENAME, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            debug_print(f"Fehler beim Laden von {self.CONFIG_FILENAME}: {e}")
            return []

    def save_config(self, hotfolders):
        """
        Speichert die übergebene Liste von Hotfolder-Dictionaries in die JSON.
        """
        try:
            with open(self.CONFIG_FILENAME, "w", encoding="utf-8") as f:
                json.dump(hotfolders, f, indent=4)
            debug_print(f"Speichern in {self.CONFIG_FILENAME} erfolgreich.")
        except Exception as e:
            debug_print(f"Fehler beim Speichern in {self.CONFIG_FILENAME}: {e}")

    def get_hotfolder_by_id(self, hf_id):
        """
        Gibt das Hotfolder-Dict mit passender ID zurück oder None, falls nicht vorhanden.
        """
        hotfolders = self.load_config()
        for hf in hotfolders:
            if hf.get("id") == hf_id:
                return hf
        return None

    def add_hotfolder(self, hotfolder_dict):
        """
        Fügt einen neuen Eintrag in der Liste hinzu und speichert.
        """
        hotfolders = self.load_config()
        hotfolders.append(hotfolder_dict)
        self.save_config(hotfolders)

    def update_hotfolder(self, hf_id, new_data):
        """
        Aktualisiert den bestehenden Eintrag mit hf_id und speichert.
        """
        hotfolders = self.load_config()
        for idx, hf in enumerate(hotfolders):
            if hf.get("id") == hf_id:
                hotfolders[idx] = new_data
                break
        self.save_config(hotfolders)

    def remove_hotfolder(self, hf_id):
        """
        Löscht den Hotfolder-Eintrag mit der angegebenen ID und speichert.
        """
        hotfolders = self.load_config()
        updated_list = [hf for hf in hotfolders if hf.get("id") != hf_id]
        self.save_config(updated_list)