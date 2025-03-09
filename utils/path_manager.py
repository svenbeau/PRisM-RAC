# utils/path_manager.py

import os
from pathlib import Path

def get_app_support_dir():
    """
    Gibt den Pfad zu ~/Library/Application Support/PRisM-CC zurück
    und legt ihn (inkl. Elternverzeichnisse) an, falls nicht vorhanden.
    """
    base_path = Path(os.path.expanduser("~/Library/Application Support/PRisM-CC"))
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path

def get_config_path():
    """
    ~/Library/Application Support/PRisM-CC/config/script_config.json
    """
    app_support = get_app_support_dir()
    config_dir = app_support / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return str(config_dir / "script_config.json")

def get_log_path():
    """
    ~/Library/Application Support/PRisM-CC/logs/global_log.json
    """
    app_support = get_app_support_dir()
    logs_dir = app_support / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir / "global_log.json")

def get_settings_path():
    """
    ~/Library/Application Support/PRisM-CC/settings.json
    """
    app_support = get_app_support_dir()
    return str(app_support / "settings.json")