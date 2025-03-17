# PRisM-RAC_arm64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# Name der Anwendung
APP_NAME = "PRisM-RAC"

# Hauptskript, das als Einstieg dient
APP_SCRIPT = "main.py"

# Pfade, in denen PyInstaller nach Modulen und Ressourcen suchen soll
pathex = [
    os.path.abspath('.'),
]

# Optionale versteckte Importe
hidden_imports = []

# Hier definieren wir die Assets-Ordner und andere Daten
datas = [
    ("assets", "assets"),  # Dies kopiert den gesamten assets-Ordner in das Bundle
]

# Füge settings.json hinzu, wenn vorhanden
if os.path.exists("settings.json"):
    datas.append(("settings.json", "."))

a = Analysis(
    [APP_SCRIPT],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2'],  # Schließe andere Qt-Bibliotheken aus
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Wichtig: Two-File-Modus statt One-File-Modus
exe = EXE(
    pyz,
    a.scripts,
    [],  # Leere Liste bedeutet: Keine Binärdateien einbetten
    exclude_binaries=True,  # Sehr wichtig: Binärdateien und Assets NICHT in die EXE einbetten
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch='arm64',
)

# Sammlung von Dateien, die neben der EXE platziert werden
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,  # Wichtig: Verwende die Sammlung statt der EXE
    name=f'{APP_NAME}.app',
    icon='/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/PRisM_Icon.icns',
    bundle_identifier='com.svenbeau.prismrac.arm64',
    info_plist={
        'CFBundleName': APP_NAME,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDevelopmentRegion': 'en',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': '© 2025 Sven Schoenauer',
    }
)