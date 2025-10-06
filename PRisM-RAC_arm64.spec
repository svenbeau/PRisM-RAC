# PRisM-RAC_arm64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# --- Projekt-Root robust ermitteln ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent   # normaler Weg
except NameError:
    PROJECT_ROOT = Path.cwd()                        # Fallback wenn __file__ fehlt

# Sicherstellen, dass das Projekt im sys.path ist (für prism_version-Import)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Version zentral aus prism_version.py ---
from prism_version import __version__ as APP_VERSION

block_cipher = None

# ===== App-Metadaten =====
APP_NAME   = "PRisM-RAC"
APP_SCRIPT = "main.py"  # Einstiegsskript

# ===== Suchpfade =====
pathex = [str(PROJECT_ROOT)]

# ===== Imports / Bundling-Helfer =====
hidden_imports = []

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import certifi

# PySide6 vollständig berücksichtigen
hidden_imports += collect_submodules("PySide6")

# Optional: Paramiko/Cryptography (SFTP), nur falls installiert
try:
    import paramiko  # noqa: F401
    hidden_imports += collect_submodules("paramiko")
    hidden_imports += collect_submodules("cryptography")
except Exception:
    pass

# ===== Daten, die ins Bundle kommen =====
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # macOS: stabiler ohne UPX
    console=False,
    disable_windowed_traceback=False,
    target_arch="arm64",
)

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

icon_path = str(PROJECT_ROOT / "PRisM_Icon.icns")

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=icon_path,
    bundle_identifier="com.svenbeau.prismrac.arm64",
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": APP_VERSION,  # z. B. 1.1.0
        "CFBundleVersion": APP_VERSION,             # Build-Nummer
        "CFBundleDevelopmentRegion": "en",
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "© 2025 Sven Schoenauer",
    },
)