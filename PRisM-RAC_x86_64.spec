# PRisM-RAC_x86_64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Name der Anwendung
APP_NAME = "PRisM-CC_x86_64"

# Wrapper-Skript, das als Einstieg dient
APP_SCRIPT = "wrapper.py"

# Pfade, in denen PyInstaller nach Modulen und Ressourcen suchen soll
pathex = [
    os.path.abspath('.'),
]

# Beispiel für versteckte Importe (falls benötigt)
hidden_imports = collect_submodules('some_package')  # nur Beispiel

# Falls du weitere Daten/Ordner ins Bundle kopieren möchtest:
datas = [
    # ("assets/*", "assets"),
    # Weitere Ordner, falls nötig.
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
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

app = BUNDLE(
    exe,
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