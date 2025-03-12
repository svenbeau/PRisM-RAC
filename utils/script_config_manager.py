#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from utils.path_manager import get_config_path

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG script_config_manager]", msg)

class ScriptConfigManager:
    """
    Verwalten von Script-Konfigurationen (script_config.json).
    Jeder Eintrag besitzt eine 'id', damit wir analog zu Hotfoldern
    Update und Remove auf Basis der ID durchführen können.
    """
    def __init__(self):
        self.config_file = self._get_script_config_path()
        self.data = {"scripts": []}
        self.load_data()

    def _get_script_config_path(self):
        """
        Gibt den Pfad zurück zu ~/Library/Application Support/PRisM-CC/config/script_config.json
        """
        return get_config_path()  # Falls du denselben Pfad wie hotfolder_config.json nutzt,
                                  # aber eben 'script_config.json' als Dateinamen

    def load_data(self):
        """Lädt das JSON aus script_config.json."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                # Falls 'scripts' fehlt, legen wir eine leere Liste an
                if "scripts" not in self.data:
                    self.data["scripts"] = []
            except Exception as e:
                debug_print(f"Fehler beim Laden von {self.config_file}: {e}")
                self.data = {"scripts": []}
        else:
            # Falls die Datei nicht existiert, legen wir sie an
            self.save_data()

    def save_data(self):
        """Speichert self.data in script_config.json."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            debug_print(f"Fehler beim Speichern von {self.config_file}: {e}")

    def get_scripts(self):
        """Gibt die Liste aller Scripts zurück."""
        return self.data.get("scripts", [])

    def get_script_by_id(self, script_id):
        """Liefert das Script-Dict mit passender ID oder None."""
        for s in self.data.get("scripts", []):
            if s.get("id") == script_id:
                return s
        return None

    def add_script(self, script_dict):
        """
        Fügt ein neues Script-Dict hinzu. Falls keine 'id' vorhanden ist,
        erzeugen wir eine. Speichert anschließend.
        """
        if not script_dict.get("id"):
            script_dict["id"] = str(uuid.uuid4())
            debug_print(f"add_script: Keine ID vorhanden, neu erzeugt: {script_dict['id']}")
        self.data.setdefault("scripts", []).append(script_dict)
        self.save_data()
        debug_print(f"Script mit ID={script_dict['id']} hinzugefügt.")

    def update_script(self, script_id, updated_dict):
        """
        Aktualisiert ein Script mit passender ID, wenn vorhanden.
        Falls nicht gefunden, wird nichts angelegt.
        """
        scripts = self.data.get("scripts", [])
        for i, s in enumerate(scripts):
            if s.get("id") == script_id:
                scripts[i] = updated_dict
                debug_print(f"Script mit ID={script_id} aktualisiert.")
                self.save_data()
                return
        debug_print(f"update_script: Kein Script mit ID={script_id} gefunden. Keine Aktualisierung erfolgt.")

    def remove_script(self, script_id):
        """
        Entfernt das Script mit der passenden ID.
        """
        old_len = len(self.data.get("scripts", []))
        self.data["scripts"] = [s for s in self.data.get("scripts", []) if s.get("id") != script_id]
        new_len = len(self.data["scripts"])
        self.save_data()
        debug_print(f"remove_script: ID={script_id}, entfernt: {old_len - new_len} Eintrag(e).")