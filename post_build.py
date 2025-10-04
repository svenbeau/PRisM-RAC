#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
post_build.py
- Kopiert Default-Konfigs in ~/Library/Application Support/PRisM-CC/
- Spiegelt jsx_templates dorthin (editierbar), falls noch nicht vorhanden
- Legt sinnvolle Basis-Dateien an, wenn sie fehlen (global_log.json, script_config.json, settings.json, ftptransfer_log.json)
- Optional: schreibt einen kurzen Self-Check-Report
"""

import os
import sys
import shutil
import json
from pathlib import Path

APP_NAME = "PRisM-RAC"
VENDOR_DIRNAME = "PRisM-CC"  # App-Support-Basis
HOME = Path.home()

APP_SUPPORT_DIR = HOME / "Library" / "Application Support" / VENDOR_DIRNAME
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

# Pfade innerhalb des dist-Bundles (nach pyinstaller build)
DIST_DIR = Path("dist")
APP_BUNDLE = DIST_DIR / f"{APP_NAME}.app"
MACOS_DIR = APP_BUNDLE / "Contents" / "MacOS"

# Quellen IM Bundle
BUNDLE_CONFIG_DIR = MACOS_DIR / "config"
BUNDLE_JSX_DIR = MACOS_DIR / "jsx_templates"

# Ziele IM App-Support
TARGET_CONFIG_DIR = APP_SUPPORT_DIR
TARGET_JSX_DIR = APP_SUPPORT_DIR / "jsx_templates"

DEFAULT_FILES = {
    "settings.json": {
        "version": "1.0.0",
        "ui": {
            "theme": "system",
            "language": "de",
            "body_visible": False  # Merkt sich, ob Script/„Rezept“-Info aufgeklappt ist
        },
        "paths": {
            "last_open_dir": str(HOME),
            "recent_dirs": []
        },
        "mail": {
            "smtp_host": "",
            "smtp_port": 587,
            "use_starttls": True,
            "user": "",
            "from": "",
            "to_default": []
        },
        "ftp": {
            "mode": "FTP",  # FTP | FTPS | SFTP
            "host": "",
            "port": 21,
            "user": "",
            "remote_base": "/",
            "passive": True
        }
    },
    "script_config.json": {
        "configs": []  # Wird von dir per ID geführt (wie Hotfolder)
    },
    "global_log.json": {
        "entries": []  # Globale Prozess-/Verarbeitungs-Logs
    },
    "ftptransfer_log.json": []
}

def copy_tree_if_missing(src: Path, dst: Path):
    if not src.exists():
        return
    if not dst.exists():
        shutil.copytree(src, dst)
        print(f"[post_build] Kopiert Ordner: {src} -> {dst}")
    else:
        print(f"[post_build] Überspringe (existiert bereits): {dst}")

def seed_defaults():
    # 1) Default-Konfigs aus dem Bundle falls vorhanden → App-Support
    if BUNDLE_CONFIG_DIR.exists():
        for item in BUNDLE_CONFIG_DIR.glob("*"):
            target = TARGET_CONFIG_DIR / item.name
            if item.is_file() and not target.exists():
                shutil.copy2(item, target)
                print(f"[post_build] Default-Config kopiert: {item.name}")

    # 2) Fehlen noch Standard-Dateien? → Minimal anlegen
    for fname, default_content in DEFAULT_FILES.items():
        target = TARGET_CONFIG_DIR / fname
        if not target.exists():
            try:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                print(f"[post_build] Default-Datei erstellt: {fname}")
            except Exception as e:
                print(f"[post_build] Konnte {fname} nicht schreiben: {e}")

    # 3) jsx_templates vom Bundle → App-Support spiegeln (nur wenn noch nicht da)
    copy_tree_if_missing(BUNDLE_JSX_DIR, TARGET_JSX_DIR)

def write_selfcheck():
    report = {
        "app_support_dir": str(APP_SUPPORT_DIR),
        "has_settings": (APP_SUPPORT_DIR / "settings.json").exists(),
        "has_script_config": (APP_SUPPORT_DIR / "script_config.json").exists(),
        "has_global_log": (APP_SUPPORT_DIR / "global_log.json").exists(),
        "has_ftptransfer_log": (APP_SUPPORT_DIR / "ftptransfer_log.json").exists(),
        "has_jsx_templates": TARGET_JSX_DIR.exists(),
    }
    try:
        with open(APP_SUPPORT_DIR / "post_build_selfcheck.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("[post_build] Self-Check-Report geschrieben.")
    except Exception as e:
        print(f"[post_build] Self-Check-Report Fehler: {e}")

def main():
    if not APP_BUNDLE.exists():
        print(f"[post_build] Achtung: {APP_BUNDLE} nicht gefunden. Bitte erst bauen.")
        sys.exit(1)

    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    seed_defaults()
    write_selfcheck()

    print("\n[post_build] Fertig. Hinweise:")
    print(f"  • App-Support: {APP_SUPPORT_DIR}")
    print(f"  • JSX-Templates: {TARGET_JSX_DIR}")
    print("  • Default-Configs sind vorhanden oder wurden erzeugt.")

if __name__ == "__main__":
    main()