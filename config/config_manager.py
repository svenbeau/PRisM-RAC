#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

DEBUG_OUTPUT = True
def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "hotfolder_config.json")

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def load_config():
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                debug_print(f"Fehler beim Laden der Konfiguration: {e}")
                return {}
    return {}

def save_config(config_data):
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def get_recent_dirs(folder_type: str):
    config = load_config()
    recent_paths = config.setdefault("recent_paths", {
        "monitor": [],
        "success": [],
        "fault": [],
        "logfiles": []
    })
    return recent_paths.get(folder_type, [])

def update_recent_dirs(folder_type: str, new_path: str):
    config = load_config()
    recent_paths = config.setdefault("recent_paths", {
        "monitor": [],
        "success": [],
        "fault": [],
        "logfiles": []
    })
    if new_path in recent_paths[folder_type]:
        recent_paths[folder_type].remove(new_path)
    recent_paths[folder_type].insert(0, new_path)
    recent_paths[folder_type] = recent_paths[folder_type][:5]
    save_config(config)