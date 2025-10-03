#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from utils.hotfolder_config_manager import HotfolderConfigManager, debug_print
# Falls Du für Transferpläne noch keinen Manager hast, kann man hier analog
# die Transferpläne laden. Beispiel: load_transfer_plans() etc.

def delete_files_older_than(folder_path, max_age_hours):
    """
    Löscht alle Dateien in 'folder_path', die älter als 'max_age_hours' sind.
    Unterordner werden hier NICHT behandelt; ggf. anpassen falls benötigt.
    """
    if not os.path.isdir(folder_path):
        return

    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    debug_print(f"Datei gelöscht: {file_path}, älter als {max_age_hours} Stunden.")
                except Exception as e:
                    debug_print(f"Fehler beim Löschen von {file_path}: {e}")

def auto_delete_for_hotfolders():
    """
    Durchsucht alle Hotfolder aus der JSON-Konfiguration und löscht
    ggf. alte Dateien in 02_Success und 03_Fault, wenn diese Funktion aktiviert ist.
    """
    hf_manager = HotfolderConfigManager()
    all_hotfolders = hf_manager.load_config()  # Oder wie auch immer Du die Liste bekommst

    for hf in all_hotfolders:
        # 02_Success
        if hf.get("auto_delete_success_enabled", False):
            success_dir = hf.get("success_dir", "")
            if success_dir:
                hours = hf.get("auto_delete_success_hours", 24)
                delete_files_older_than(success_dir, hours)

        # 03_Fault
        if hf.get("auto_delete_fault_enabled", False):
            fault_dir = hf.get("fault_dir", "")
            if fault_dir:
                hours = hf.get("auto_delete_fault_hours", 72)
                delete_files_older_than(fault_dir, hours)

def auto_delete_for_transferplans(transfer_plans):
    """
    Beispiel, wenn Du eine Liste von Transfer-Plänen (transfer_plans) hast,
    die jeweils z. B. so aussehen:
    {
        "move_after": "/Pfad/wohin",
        "auto_delete_after_move_enabled": True,
        "auto_delete_after_move_hours": 48,
        ...
    }
    Dann wird hier die Auto-Delete-Funktion ausgeführt.
    """
    for plan in transfer_plans:
        if plan.get("auto_delete_after_move_enabled", False):
            move_path = plan.get("move_after", "")
            if move_path:
                hours = plan.get("auto_delete_after_move_hours", 48)
                delete_files_older_than(move_path, hours)

def run_auto_delete():
    """
    Diese Funktion ruft beide Bereiche auf.
    Sie kann z. B. in einem Timer oder Scheduler
    periodisch ausgeführt werden.
    """
    auto_delete_for_hotfolders()

    # Falls Du Transfer-Pläne aus einem Manager lädst:
    # transfer_plans = load_transfer_plans()  # (Beispiel)
    # auto_delete_for_transferplans(transfer_plans)

    # Oder Du hast sie lokal:
    # auto_delete_for_transferplans(my_plan_list)

if __name__ == "__main__":
    """
    Beispiel: Wenn Du das Skript direkt ausführst, 
    werden alle Auto-Delete-Optionen geprüft und ausgeführt.
    """
    run_auto_delete()