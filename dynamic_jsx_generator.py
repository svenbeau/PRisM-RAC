#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dynamic_jsx_generator.py
Erzeugt eine temporäre JSX-Datei für den Contentcheck:
- Präfix-Injektionsheader (v25-konform)
- Fallback: ersetzt alte /*PYTHON_INSERT_...*/ Platzhalter, falls vorhanden
- Sanity-Check: loggt die ersten Zeilen der generierten Datei
"""

import os
import json
import tempfile

# Passe ggf. den Importpfad an euer Projekt an:
from utils.hotfolder_config_manager import debug_print


# ---------- Hilfsfunktionen ----------

def _ensure_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [str(value)]

def _js_bool(py_bool):
    return "true" if bool(py_bool) else "false"

def _js_string(s):
    # JSON-escape + immer als JS-String
    return json.dumps("" if s is None else str(s), ensure_ascii=False)

def _js_array(seq):
    # kompakter JSON-Array-Dump (gilt in JS 1:1)
    return json.dumps(_ensure_list(seq), ensure_ascii=False, separators=(",", ":"))


# ---------- Kernfunktion ----------

def create_temp_jsx_with_config(
    base_jsx_path: str,
    keyword_check_enabled: bool,
    keyword_check_word: str,
    required_layers,
    required_metadata,
    keyword_layers,
    keyword_metadata,
    logfiles_dir: str,
    debug_output: bool = False,
):
    """
    Erzeugt eine temporäre JSX-Datei, indem ein JS-Variablen-Header vor das Template
    geschrieben wird. Zusätzlich werden (falls vorhanden) alte Platzhalter im Template ersetzt.

    Erwartete Variablen im Template (v25-Stil):
      - required_layers, required_metadata
      - keyword_layers, keyword_metadata
      - keywordCheckEnabled, keywordCheckWord
      - logFolderPath
      - DEBUG_OUTPUT (optional)
    """

    # 1) Template lesen
    if not base_jsx_path or not os.path.exists(base_jsx_path):
        debug_print(f"[DynamicJSX] Error: Base JSX script not found at {base_jsx_path}")
        return None

    try:
        with open(base_jsx_path, "r", encoding="utf-8") as f:
            jsx_template = f.read()
    except Exception as e:
        debug_print(f"[DynamicJSX] Error reading base JSX script {base_jsx_path}: {e}")
        return None

    # 2) Werte serialisieren
    js_required_layers   = _js_array(required_layers)
    js_required_metadata = _js_array(required_metadata)
    js_keyword_layers    = _js_array(keyword_layers)
    js_keyword_metadata  = _js_array(keyword_metadata)

    js_kw_enabled = _js_bool(keyword_check_enabled)
    js_kw_word    = _js_string(keyword_check_word)

    js_log_dir    = _js_string(logfiles_dir)
    js_debug      = _js_bool(debug_output)

    # 3) Injektions-Header (v25)
    injection_header = (
        "// ===== PRisM-RAC injected config (auto-generated) =====\n"
        "var DEBUG_OUTPUT        = {dbg};\n"
        "var required_layers     = {req_layers};\n"
        "var required_metadata   = {req_meta};\n"
        "var keyword_layers      = {kw_layers};\n"
        "var keyword_metadata    = {kw_meta};\n"
        "var keywordCheckEnabled = {kw_enabled};\n"
        "var keywordCheckWord    = {kw_word};\n"
        "var logFolderPath       = {log_dir};\n"
        "// ===== end injected config =====\n\n"
    ).format(
        dbg=js_debug,
        req_layers=js_required_layers,
        req_meta=js_required_metadata,
        kw_layers=js_keyword_layers,
        kw_meta=js_keyword_metadata,
        kw_enabled=js_kw_enabled,
        kw_word=js_kw_word,
        log_dir=js_log_dir,
    )

    # 4) Fallback-Replacements für alte Templates mit Platzhaltern
    #    (Wir ersetzen nur, wenn die Marker vorkommen – sonst bleibt das Template unverändert.)
    replacements = {
        "/*PYTHON_INSERT_REQUIRED_LAYERS*/":   js_required_layers,
        "/*PYTHON_INSERT_REQUIRED_METADATA*/": js_required_metadata,
        "/*PYTHON_INSERT_KEYWORD_LAYERS*/":    js_keyword_layers,
        "/*PYTHON_INSERT_KEYWORD_METADATA*/":  js_keyword_metadata,
        "/*PYTHON_INSERT_LOGFOLDER*/":         js_log_dir,
        "/*PYTHON_INSERT_KW_ENABLED*/":        js_kw_enabled,
        "/*PYTHON_INSERT_KW_WORD*/":           js_kw_word,
        # ältere Varianten, falls vorhanden:
        "/*PYTHON_INSERT_DEBUG_OUTPUT*/":      js_debug,
    }

    tmpl_after_fallback = jsx_template
    for marker, value in replacements.items():
        if marker in tmpl_after_fallback:
            tmpl_after_fallback = tmpl_after_fallback.replace(marker, value)

    # 5) Kombinieren und temporär speichern
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            # Header zuerst, dann (ggf. ersetztes) Template
            tmp_f.write(injection_header)
            tmp_f.write(tmpl_after_fallback)

        # Zusammenfassung ins Debug
        debug_print(
            "[DynamicJSX] Temporary JSX created: {path} "
            "(keywordCheckEnabled={kw_enabled}, keywordCheckWord={kw_word}, "
            "required_layers={req_layers}, required_metadata={req_meta}, "
            "keyword_layers={kw_layers}, keyword_metadata={kw_meta}, "
            "logFolderPath={logdir}, DEBUG_OUTPUT={dbg})".format(
                path=tmp_path,
                kw_enabled=keyword_check_enabled,
                kw_word=keyword_check_word,
                req_layers=_ensure_list(required_layers),
                req_meta=_ensure_list(required_metadata),
                kw_layers=_ensure_list(keyword_layers),
                kw_meta=_ensure_list(keyword_metadata),
                logdir=logfiles_dir,
                dbg=debug_output,
            )
        )

        # 6) Sanity-Check – die ersten 40 Zeilen loggen
        try:
            head_lines = []
            with open(tmp_path, "r", encoding="utf-8") as check_f:
                for _ in range(40):
                    line = check_f.readline()
                    if not line:
                        break
                    head_lines.append(line.rstrip("\n"))
            debug_print("[DynamicJSX] --- Sanity Check: First 40 lines of generated JSX ---")
            for ln in head_lines:
                debug_print(ln)
            debug_print("[DynamicJSX] --- End of Sanity Check ---")
        except Exception as e:
            debug_print(f"[DynamicJSX] Sanity check failed: {e}")

        return tmp_path

    except Exception as e:
        debug_print(f"[DynamicJSX] Error writing temporary JSX script: {e}")
        return None


# ---------- Optionaler Selbsttest ----------
if __name__ == "__main__":
    base_jsx = "contentcheck_template.jsx"  # Pfad zu eurem Template
    temp_jsx = create_temp_jsx_with_config(
        base_jsx_path=base_jsx,
        keyword_check_enabled=True,
        keyword_check_word="Rueckseite",
        required_layers=["Freisteller", "Messwerte", "Korrektur"],
        required_metadata=["author", "description", "keywords"],
        keyword_layers=["Freisteller", "Messwerte"],
        keyword_metadata=["author", "description"],
        logfiles_dir="/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/04_Logfiles",
        debug_output=True,
    )
    print("Generated temporary JSX script:", temp_jsx)