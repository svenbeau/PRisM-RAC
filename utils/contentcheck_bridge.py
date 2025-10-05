#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
utils/contentcheck_bridge.py

Zentraler Wrapper für die Erzeugung der temporären JSX-Datei zum Contentcheck.
- Liest alle nötigen Felder aus einer Hotfolder-Config (dict)
- Setzt sichere Defaults (inkl. keyword_logic="AUTO", falls nicht vorhanden)
- Ruft dynamic_jsx_generator.create_temp_jsx_with_config(...) korrekt auf
- Loggt eine kurze Zusammenfassung
"""

from typing import Optional, Dict, Any

from utils.hotfolder_config_manager import debug_print
from dynamic_jsx_generator import create_temp_jsx_with_config


def build_contentcheck_jsx(hf_cfg: Dict[str, Any],
                           base_jsx_path: Optional[str] = None,
                           debug_output: Optional[bool] = None) -> Optional[str]:
    """
    Erzeugt die temporäre JSX-Datei für den Contentcheck anhand der Hotfolder-Config.

    :param hf_cfg: Hotfolder-Konfiguration (dict)
    :param base_jsx_path: Pfad zum JSX-Template (optional; wenn None, wird aus hf_cfg["selected_jsx"] genommen)
    :param debug_output: Debug-Flag überschreiben (optional; sonst hf_cfg.get("debug_output", False))
    :return: Pfad zur temporär erzeugten JSX-Datei oder None bei Fehler
    """
    if hf_cfg is None:
        debug_print("[contentcheck_bridge] Fehler: hf_cfg ist None")
        return None

    # Quelle für das Template
    base_jsx = base_jsx_path or hf_cfg.get("selected_jsx", "")
    if not base_jsx:
        debug_print("[contentcheck_bridge] Warnung: selected_jsx ist leer – kein Contentcheck-Template gesetzt.")
        return None

    # Pflicht-/Optionale Felder aus der Config (sichere Defaults)
    keyword_check_enabled = bool(hf_cfg.get("keyword_check_enabled", False))
    keyword_check_word    = hf_cfg.get("keyword_check_word", "") or ""
    required_layers       = hf_cfg.get("required_layers", []) or []
    required_metadata     = hf_cfg.get("required_metadata", []) or []
    keyword_layers        = hf_cfg.get("keyword_layers", []) or []
    keyword_metadata      = hf_cfg.get("keyword_metadata", []) or []
    logfiles_dir          = hf_cfg.get("logfiles_dir", "") or ""
    debug_flag            = bool(hf_cfg.get("debug_output", False) if debug_output is None else debug_output)

    # NEU: keyword_logic – Default "AUTO", falls Key nicht existiert
    keyword_logic         = (hf_cfg.get("keyword_logic", "AUTO") or "AUTO").upper()
    if keyword_logic not in ("AUTO", "ANY", "ALL"):
        debug_print(f"[contentcheck_bridge] Unbekannte keyword_logic='{keyword_logic}', fallback auf 'AUTO'")
        keyword_logic = "AUTO"

    # Aufruf des Generators
    tmp_jsx_path = create_temp_jsx_with_config(
        base_jsx_path=base_jsx,
        keyword_check_enabled=keyword_check_enabled,
        keyword_check_word=keyword_check_word,
        required_layers=required_layers,
        required_metadata=required_metadata,
        keyword_layers=keyword_layers,
        keyword_metadata=keyword_metadata,
        logfiles_dir=logfiles_dir,
        debug_output=debug_flag,
        keyword_logic=keyword_logic,     # <-- hier wird der neue Parameter sauber übergeben
    )

    debug_print(
        "[contentcheck_bridge] JSX erzeugt: {path} "
        "(kw_enabled={kw_en}, kw_word='{kw_word}', kw_logic={kw_logic}, "
        "req_layers={rl}, req_meta={rm}, kw_layers={kl}, kw_meta={km})".format(
            path=tmp_jsx_path,
            kw_en=keyword_check_enabled,
            kw_word=keyword_check_word,
            kw_logic=keyword_logic,
            rl=required_layers,
            rm=required_metadata,
            kl=keyword_layers,
            km=keyword_metadata,
        )
    )

    return tmp_jsx_path