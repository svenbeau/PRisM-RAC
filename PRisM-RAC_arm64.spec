# PRisM-RAC_arm64.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

APP_NAME = "PRisM-CC"
APP_SCRIPT = "wrapper.py"

pathex = [os.path.abspath('.')]

hidden_imports = []

def collect_datas(source, target):
    """
    Sammelt rekursiv alle Dateien aus dem Ordner 'source' und ordnet sie dem Zielordner 'target' zu.
    Liefert eine Liste von Tupeln (Quelle, Zielpfad relativ zum Bundle).
    """
    datas = []
    for root, dirs, files in os.walk(source):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(root, source)
            # Falls der relative Pfad '.', dann wird nur target benutzt
            target_path = os.path.join(target, rel_path) if rel_path != '.' else target
            datas.append((full_path, target_path))
    return datas

datas = []
datas += collect_datas("assets", "assets")
datas += [(os.path.abspath("scripts"), "scripts")]
datas += [(os.path.abspath("config"), "config")]
datas += [(os.path.abspath("jsx_templates"), "jsx_templates")]

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