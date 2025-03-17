# PRisM-RAC_arm64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.building.datastruct import Tree  # Verwende Tree aus diesem Modul

block_cipher = None

APP_NAME = "PRisM-CC"
APP_SCRIPT = "wrapper.py"

pathex = [os.path.abspath('.')]

hidden_imports = []

# Mit Tree werden alle Dateien im Ordner "assets" (sowie in den anderen Ordnern) rekursiv aufgenommen.
datas = [
    Tree("assets", prefix="assets"),
    Tree("scripts", prefix="scripts"),
    Tree("config", prefix="config"),
    Tree("jsx_templates", prefix="jsx_templates"),
]

from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE

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
    pyz,
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
    name='PRisM-CC.app',
    icon='/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/PRisM_Icon.icns',
    bundle_identifier='com.svenbeau.prismcc.arm64',
    info_plist={
        'CFBundleName': 'PRisM-CC',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDevelopmentRegion': 'en',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': '© 2025 Sven Schoenauer',
    }
)