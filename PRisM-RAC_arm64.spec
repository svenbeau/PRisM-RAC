# PRisM-RAC_arm64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# ===== App-Metadaten =====
APP_NAME = "PRisM-RAC"
APP_SCRIPT = "main.py"  # Einstiegsskript

# ===== Suchpfade =====
pathex = [os.path.abspath(".")]

# ===== Imports / Bundling-Helfer =====
hidden_imports = []

# WICHTIG: Qt-Plugins + Daten einsammeln
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import certifi

# PySide6 vollständig berücksichtigen (Import-Pfade, Styles, etc.)
hidden_imports += collect_submodules("PySide6")

# Optional: Paramiko/Cryptography (nur falls installiert/benötigt – SFTP)
try:
    import paramiko  # noqa: F401
    hidden_imports += collect_submodules("paramiko")
    hidden_imports += collect_submodules("cryptography")
except Exception:
    # Wenn nicht installiert, ignorieren wir SFTP-spezifische Hidden-Imports
    pass

# Daten, die wir ins Bundle nehmen
datas = [
    # Deine Projekt-Ressourcen
    ("assets", "assets"),
    ("jsx_templates", "jsx_templates"),
    # Default-Configs als Seed (post_build kopiert sie später ins App-Support-Verzeichnis)
    ("config", "config"),
]

# Qt-Plugins (plattformen, imageformats, iconengines, etc.)
datas += collect_data_files("PySide6", includes=["Qt/plugins/**"])

# CA-Bundle für TLS/SSL (SMTP/FTPS/HTTPS)
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
    excludes=["PyQt5", "PyQt6", "PySide2"],  # nur PySide6 verwenden
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=False,                  # macOS: stabiler ohne UPX
    console=False,
    disable_windowed_traceback=False,
    target_arch="arm64",
)

# ===== Collect-Phase =====
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

# ===== App-Bundle =====
icon_path = "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/PRisM_Icon.icns"

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=icon_path,
    bundle_identifier="com.svenbeau.prismrac.arm64",
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleDevelopmentRegion": "en",
        # Apple Silicon i. d. R. ab 12.0 sinnvoll; 10.13 war Intel-Ära
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "© 2025 Sven Schoenauer",
    },
)