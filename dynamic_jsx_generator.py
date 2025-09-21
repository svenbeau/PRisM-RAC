#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import tempfile
from utils.config_manager import debug_print


PLACEHOLDERS = {
    "REQUIRED_LAYERS": "/*PYTHON_INSERT_REQUIRED_LAYERS*/",
    "REQUIRED_METADATA": "/*PYTHON_INSERT_REQUIRED_METADATA*/",
    "KEYWORD_LAYERS": "/*PYTHON_INSERT_KEYWORD_LAYERS*/",
    "KEYWORD_METADATA": "/*PYTHON_INSERT_KEYWORD_METADATA*/",
    "LOGFOLDER": "/*PYTHON_INSERT_LOGFOLDER*/",
    "KW_ENABLED": "/*PYTHON_INSERT_KW_ENABLED*/",
    "KW_WORD": "/*PYTHON_INSERT_KW_WORD*/",
}


def _ensure_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    # falls in der Config mal als String gespeichert wurde
    return [str(value)]


def _safe_json(value):
    """
    JSON-Dump mit UTF-8 und ohne unnötige Whitespaces.
    Wichtig: Strings werden mit Anführungszeichen serialisiert,
    Booleans als 'true'/'false' usw.
    """
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def create_temp_jsx_with_config(
    base_jsx_path,
    keyword_check_enabled,
    keyword_check_word,
    required_layers,
    required_metadata,
    keyword_layers,
    keyword_metadata,
    logfiles_dir,
):
    """
    Erzeugt eine temporäre JSX-Datei auf Basis des Templates (contentcheck_template.jsx),
    indem ausschließlich die Platzhalter ersetzt werden.

    Erwartete Platzhalter im Template:
      - /*PYTHON_INSERT_REQUIRED_LAYERS*/
      - /*PYTHON_INSERT_REQUIRED_METADATA*/
      - /*PYTHON_INSERT_KEYWORD_LAYERS*/
      - /*PYTHON_INSERT_KEYWORD_METADATA*/
      - /*PYTHON_INSERT_LOGFOLDER*/
      - /*PYTHON_INSERT_KW_ENABLED*/
      - /*PYTHON_INSERT_KW_WORD*/

    Keine weitere Logik wird injiziert! Die Entscheidung (Keyword-based vs. Standard)
    passiert vollständig im Template.
    """

    # 1) Template prüfen & lesen
    if not base_jsx_path or not os.path.exists(base_jsx_path):
        debug_print(f"[DynamicJSX] Error: Base JSX script not found at {base_jsx_path}")
        return None

    try:
        with open(base_jsx_path, "r", encoding="utf-8") as f:
            jsx_template = f.read()
    except Exception as e:
        debug_print(f"[DynamicJSX] Error reading base JSX script {base_jsx_path}: {e}")
        return None

    # 2) Eingaben normalisieren
    req_layers = _ensure_list(required_layers)
    req_meta = _ensure_list(required_metadata)
    kw_layers = _ensure_list(keyword_layers)
    kw_meta = _ensure_list(keyword_metadata)
    kw_enabled_bool = bool(keyword_check_enabled)
    kw_word_str = "" if keyword_check_word is None else str(keyword_check_word)
    log_dir = "" if logfiles_dir is None else str(logfiles_dir)

    # 3) Platzhalter ersetzen
    #    Wichtig: Reihenfolge ist hier egal, da sich Platzhalter nicht überlappen.
    replacements = {
        PLACEHOLDERS["REQUIRED_LAYERS"]: _safe_json(req_layers),
        PLACEHOLDERS["REQUIRED_METADATA"]: _safe_json(req_meta),
        PLACEHOLDERS["KEYWORD_LAYERS"]: _safe_json(kw_layers),
        PLACEHOLDERS["KEYWORD_METADATA"]: _safe_json(kw_meta),
        PLACEHOLDERS["LOGFOLDER"]: _safe_json(log_dir),
        PLACEHOLDERS["KW_ENABLED"]: "true" if kw_enabled_bool else "false",
        PLACEHOLDERS["KW_WORD"]: _safe_json(kw_word_str),
    }

    for ph, val in replacements.items():
        if ph not in jsx_template:
            debug_print(f"[DynamicJSX] WARN: Placeholder not found in template: {ph}")
        jsx_template = jsx_template.replace(ph, val)

    # 4) Temporäre Datei schreiben
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            tmp_f.write(jsx_template)

        debug_print(
            "[DynamicJSX] Temporary JSX created: {path}\n"
            "  keywordCheckEnabled={kw_enabled}\n"
            "  keywordCheckWord={kw_word}\n"
            "  required_layers={req_layers}\n"
            "  required_metadata={req_meta}\n"
            "  keyword_layers={kw_layers}\n"
            "  keyword_metadata={kw_meta}\n"
            "  logFolderPath={logdir}".format(
                path=tmp_path,
                kw_enabled=kw_enabled_bool,
                kw_word=kw_word_str,
                req_layers=req_layers,
                req_meta=req_meta,
                kw_layers=kw_layers,
                kw_meta=kw_meta,
                logdir=log_dir,
            )
        )
        return tmp_path
    except Exception as e:
        debug_print(f"[DynamicJSX] Error writing temporary JSX script: {e}")
        return None


# Optionaler Selbsttest
if __name__ == "__main__":
    base_jsx = "contentcheck_template.jsx"
    temp_jsx = create_temp_jsx_with_config(
        base_jsx_path=base_jsx,
        keyword_check_enabled=True,
        keyword_check_word="Rueckseite",
        required_layers=["Freisteller", "Messwerte", "Korrektur"],
        required_metadata=["author", "description", "keywords"],
        keyword_layers=["Freisteller", "Messwerte"],
        keyword_metadata=["author", "description"],
        logfiles_dir="/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/04_Logfiles",
    )
    print("Generated temporary JSX script:", temp_jsx)