#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
processors/contentcheck_runner.py

Startet den Content-Check für eine Datei:
- Öffnet die Datei in Photoshop
- Erzeugt die dynamische JSX via Wrapper (nur ROH-Werte injizieren!)
- Führt JSX aus
- Liest Logs ein und gibt sie zurück

WICHTIG: KEINE effective_*-Vorberechnung in Python.
Die Entscheidung „Standard vs Keyword-based“ findet ausschließlich im JSX statt.
"""

import os
import subprocess
import time
import json
from typing import Dict, Any, Optional

from utils.hotfolder_config_manager import debug_print
# NEU: Wrapper statt direkter Generator-Import
from utils.contentcheck_bridge import build_contentcheck_jsx


def _open_in_photoshop(path: str) -> None:
    # macOS: via `open -a` (so wie in deinen Logs)
    try:
        subprocess.run(["open", "-a", "Adobe Photoshop 2024", path], check=False)
    except Exception:
        # Fallback: Standard-open
        subprocess.run(["open", "-a", "Adobe Photoshop", path], check=False)


def _active_doc_count(timeout_sec: int = 15) -> int:
    """
    Optionaler Helfer: fragt via AppleScript die Anzahl geöffneter PS-Dokumente ab.
    Nutzt du bereits woanders, kannst du diesen Teil entfernen oder anpassen.
    """
    script = '''
        tell application "Adobe Photoshop 2024"
            try
                return (count of documents) as integer
            on error
                return 0
            end try
        end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout_sec)
        out = (res.stdout or "").strip()
        return int(out) if out.isdigit() else 0
    except Exception:
        return 0


def _run_jsx(jsx_path: str, timeout_sec: int = 60) -> int:
    """
    Führt die JSX mit Photoshop aus. Je nach deinem bestehenden Mechanismus anpassen.
    Hier: minimaler Aufruf via osascript, das die JSX in PS lädt/ausführt.
    """
    apple_script = f'''
        tell application "Adobe Photoshop 2024"
            do javascript file posix file "{jsx_path}"
        end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", apple_script],
                             capture_output=True, text=True, timeout=timeout_sec)
        debug_print(f"JSX execution result: RC={res.returncode}")
        if res.stdout:
            debug_print(f"JSX stdout: {res.stdout.strip()}")
        if res.stderr:
            debug_print(f"JSX stderr: {res.stderr.strip()}")
        return res.returncode
    except Exception as e:
        debug_print(f"Error executing JSX: {e}")
        return 1


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_print(f"Failed to read JSON '{path}': {e}")
        return None


def run_content_check_for_file(
    file_path: str,
    hf_cfg: Dict[str, Any],
    base_jsx_path: str,
) -> Dict[str, Any]:
    """
    Führt den Content-Check für `file_path` aus, basierend auf der Hotfolder-Config `hf_cfg`.

    Erwartete Keys in `hf_cfg`:
      - contentcheck_enabled (bool)
      - required_layers (list[str])
      - required_metadata (list[str])
      - keyword_check_enabled (bool)
      - keyword_check_word (str)
      - keyword_layers (list[str])
      - keyword_metadata (list[str])
      - logfiles_dir (str)  # oder hf_cfg["logfiles_dir"]
      - keyword_logic ("AUTO"|"ANY"|"ALL")  # optional, Default via Wrapper: "AUTO"
    """

    result: Dict[str, Any] = {
        "ok": False,
        "logs": {},
        "jsx_path": None,
        "errors": [],
    }

    if not bool(hf_cfg.get("contentcheck_enabled", False)):
        result["ok"] = True
        return result

    # Rohwerte direkt aus der HF-Config (KEINE effective_* Logik!)
    required_layers   = hf_cfg.get("required_layers", [])
    required_metadata = hf_cfg.get("required_metadata", [])
    keyword_layers    = hf_cfg.get("keyword_layers", [])
    keyword_metadata  = hf_cfg.get("keyword_metadata", [])
    kw_enabled        = bool(hf_cfg.get("keyword_check_enabled", False))
    kw_word           = str(hf_cfg.get("keyword_check_word", "") or "")
    log_dir           = hf_cfg.get("logfiles_dir") or hf_cfg.get("logfiles") or os.path.dirname(file_path)

    debug_print(
        "[ContentCheck] Using RAW config for injection: "
        f"required_layers={required_layers}, required_metadata={required_metadata}, "
        f"keyword_layers={keyword_layers}, keyword_metadata={keyword_metadata}, "
        f"keywordCheckEnabled={kw_enabled}, keywordCheckWord='{kw_word}', log_dir='{log_dir}'"
    )

    # Datei in PS öffnen (falls das dein bestehender Flow ist)
    _open_in_photoshop(file_path)

    # Kurzes Warten, bis PS das Dokument registriert
    for _ in range(20):
        time.sleep(0.25)
        cnt = _active_doc_count()
        debug_print(f"Photoshop document count: {cnt}")
        if cnt >= 1:
            break

    # JSX erzeugen (nur ROH-Werte injizieren!) – jetzt über den Wrapper,
    # der keyword_logic automatisch übernimmt (Default "AUTO").
    tmp_jsx = build_contentcheck_jsx(
        hf_cfg,
        base_jsx_path=base_jsx_path,
        debug_output=False,
    )
    result["jsx_path"] = tmp_jsx
    if not tmp_jsx:
        result["errors"].append("Failed to create temporary JSX.")
        return result

    # JSX ausführen
    rc = _run_jsx(tmp_jsx)
    if rc != 0:
        result["errors"].append(f"JSX execution non-zero: {rc}")

    # Logdateien einsammeln
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    content_log = os.path.join(log_dir, f"{base_name}_01_log_contentcheck.json")
    fail_log    = os.path.join(log_dir, f"{base_name}_01_log_fail.json")

    logs = {}
    if os.path.exists(content_log):
        logs["contentcheck"] = _read_json(content_log)
    if os.path.exists(fail_log):
        logs["fail"] = _read_json(fail_log)

    result["logs"] = logs
    result["ok"] = True
    return result