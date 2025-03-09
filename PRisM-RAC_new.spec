# PRisM-RAC_new.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Name der Anwendung
APP_NAME = "PRisM-CC"

# Wrapper-Skript, das als Einstieg dient
APP_SCRIPT = "wrapper.py"

# Pfade, in denen PyInstaller nach Modulen und Ressourcen suchen soll
# Passe die Pfade hier an deine Struktur an
pathex = [
    os.path.abspath('.'),
    # Falls du ein src-Verzeichnis hast, etc.:
    # os.path.abspath('src'),
]

# Optional: Weitere versteckte Importe suchen
# (Beispielsweise wenn du Module per importlib lädst)
hidden_imports = collect_submodules('some_package')  # nur Beispiel

# Falls du weitere Daten / Ordner ins Bundle kopieren willst
# Nutze das Schema: ( <Quelldatei-oder-Ordner>, <Zielordner-im-Bundle> )
datas = [
    # Beispiel: Ganze Ordner
    # ("Reports/*", "Reports"),
    # ("Migration/*", "Migration"),
    # ("images/*", "images"),
    # ...
]

# Hier definieren wir, welche Skripte analysiert werden.
# 'main.py' ist oft der Haupteinstieg – oder du setzt "wrapper.py" als erstes Script.
# Du kannst noch weitere .py-Dateien angeben, falls sie direkt ausgeführt werden müssen.
a = Analysis(
    [APP_SCRIPT],               # als Einstieg
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

# Erstellung eines ausführbaren Programms (für Konsolenmode oder GUI).
# Für macOS GUI-Anwendungen setzen wir normalerweise console=False.
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
    # icon='PRisM_Icon.icns',
)

app = BUNDLE(
    exe,
    name='PRisM-CC.app',
    icon='/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/PRisM_Icon.icns',
    bundle_identifier='com.svenbeau.prismcc',
    info_plist={
        'CFBundleName': 'PRisM-CC',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDevelopmentRegion': 'en',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': '© 2025 Sven Schoenauer',
    }
)