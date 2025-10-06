# PRisM-RAC_x86_64.spec
#🪄 Option 1 (empfohlen): x86-64 Build über Rosetta Terminal
#	1.	Öffne ein neues Terminal im Rosetta-Modus:
#arch -x86_64 zsh
#	2.	Erstelle ein neues virtuelles Environment:
#cd ~/Documents/PycharmProjects/PRisM-RAC
 #python3 -m venv .venv_x86_64
 #source .venv_x86_64/bin/activate
#	3.	Installiere erneut deine Dependencies:
#pip install -r requirements.txt
#	4.	Dann Baue dein x86-Bundle:
#/usr/bin/env bash choose_arch_and_build.sh

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# --- Projekt-Root robust ermitteln ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
except NameError:
    PROJECT_ROOT = Path.cwd()

# --- Sicherstellen, dass das Projekt im sys.path liegt ---
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Version zentral aus prism_version.py ---
try:
    from prism_version import __version__ as APP_VERSION
except ImportError:
    APP_VERSION = "1.1.0"  # Fallback falls Import scheitert

block_cipher = None

# ===== App-Metadaten =====
APP_NAME = "PRisM-RAC"
APP_SCRIPT = "main.py"
ARCH = "x86_64"  # feste Architektur

# ===== Suchpfade =====
pathex = [str(PROJECT_ROOT)]

# ===== Imports / Bundling-Helfer =====
hidden_imports = []

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import certifi

# PySide6 vollständig berücksichtigen
hidden_imports += collect_submodules("PySide6")

# Optional: SFTP / Paramiko / Cryptography
try:
    import paramiko  # noqa: F401
    hidden_imports += collect_submodules("paramiko")
    hidden_imports += collect_submodules("cryptography")
except Exception:
    pass

# ===== Daten =====
datas = [
    ("assets", "assets"),
    ("jsx_templates", "jsx_templates"),
    ("config", "config"),
]
datas += collect_data_files("PySide6", includes=["Qt/plugins/**"])
datas += [(certifi.where(), "certifi")]

# ===== PyInstaller-Analyse =====
a = Analysis(
    [APP_SCRIPT],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ===== Executable =====
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=ARCH,  # x86_64
)

# ===== Collect =====
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

# ===== App-Bundle =====
icon_path = str(PROJECT_ROOT / "PRisM_Icon.icns")

app = BUNDLE(
    coll,
    name=f"{APP_NAME}-{ARCH}.app",  # dist/PRisM-RAC-x86_64.app
    icon=icon_path,
    bundle_identifier=f"com.svenbeau.prismrac.{ARCH}",
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "CFBundleDevelopmentRegion": "en",
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "© 2025 Sven Schoenauer",
    },
)