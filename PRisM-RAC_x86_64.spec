# PRisM-RAC_x86_64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Name der Anwendung (angepasst für x86_64)
APP_NAME = "PRisM-CC_x86_64"

# Wrapper-Skript, das als Einstieg dient
APP_SCRIPT = "wrapper.py"

# Pfade, in denen PyInstaller nach Modulen und Ressourcen suchen soll
pathex = [
    os.path.abspath('.'),
]

# Optionale versteckte Importe – hier ggf. anpassen
hidden_imports = []  # Entferne den collect_submodules Aufruf, wenn das Paket nicht existiert

# Hier definieren wir die Assets-Ordner und andere Daten, die ins Bundle aufgenommen werden
datas = [
    ("assets", "assets"),  # Füge das komplette assets-Verzeichnis hinzu
    ("scripts", "scripts"),  # Füge auch das scripts-Verzeichnis hinzu
    ("config", "config"),   # Füge auch das config-Verzeichnis hinzu
]

a = Analysis(
    [APP_SCRIPT],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,  # Wichtig: Stelle sicher, dass pyz hier enthalten ist
    a.scripts,
    [],  # Leere Liste hier
    exclude_binaries=True,  # Wichtig: Verwende exclude_binaries=True
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    # icon='PRisM_Icon.icns',
)

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
    coll,  # Verwende coll statt exe
    name='PRisM-CC_x86_64.app',
    icon='/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/PRisM_Icon.icns',
    bundle_identifier='com.svenbeau.prismcc.x86_64',
    info_plist={
        'CFBundleName': 'PRisM-CC_x86_64',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDevelopmentRegion': 'en',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': '© 2025 Sven Schoenauer',
    }
)