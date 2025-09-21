#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import tempfile
from utils.config_manager import debug_print

def create_temp_jsx_with_config(
    base_jsx_path,
    keyword_check_enabled,
    keyword_check_word,
    required_layers,
    required_metadata,
    keyword_layers,
    keyword_metadata,
    logfiles_dir,
    debug_output=False,
):
    """
    Erzeugt eine temporäre JSX-Datei und setzt VOR das Template
    einen Header mit Variablenzuweisungen. Die eigentliche
    Entscheidungslogik (Keyword vs. Standard) liegt im Template.
    """

    if not base_jsx_path or not os.path.exists(base_jsx_path):
        debug_print(f"Error: Base JSX script not found at {base_jsx_path}")
        return None

    try:
        with open(base_jsx_path, "r", encoding="utf-8") as f:
            jsx_template = f.read()
    except Exception as e:
        debug_print(f"Error reading base JSX script {base_jsx_path}: {e}")
        return None

    header_lines = [
        f"var DEBUG_OUTPUT = {str(bool(debug_output)).lower()};",
        f"var keywordCheckEnabled = {str(bool(keyword_check_enabled)).lower()};",
        f"var keywordCheckWord = {json.dumps((keyword_check_word or '').strip())};",
        f"var required_layers = {json.dumps(required_layers or [])};",
        f"var required_metadata = {json.dumps(required_metadata or [])};",
        f"var keyword_layers = {json.dumps(keyword_layers or [])};",
        f"var keyword_metadata = {json.dumps(keyword_metadata or [])};",
        f"var logFolderPath = {json.dumps(logfiles_dir or '')};",
        "",  # Leerzeile
    ]
    header = "\n".join(header_lines)
    combined_code = header + jsx_template

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(tmp_fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            tmp_f.write(combined_code)

        debug_print(
            "Temporary JSX created: {} (keywordCheckEnabled={}, keywordCheckWord={}, "
            "required_layers={}, required_metadata={}, keyword_layers={}, keyword_metadata={}, "
            "logFolderPath={}, DEBUG_OUTPUT={})".format(
                tmp_path,
                keyword_check_enabled,
                keyword_check_word,
                required_layers,
                required_metadata,
                keyword_layers,
                keyword_metadata,
                logfiles_dir,
                debug_output,
            )
        )
        return tmp_path
    except Exception as e:
        debug_print(f"Error writing temporary JSX script: {e}")
        return None

# Manual test
if __name__ == "__main__":
    base_jsx = "contentcheck_template.jsx"
    temp_jsx = create_temp_jsx_with_config(
        base_jsx_path=base_jsx,
        keyword_check_enabled=True,
        keyword_check_word="Rueckseite",
        required_layers=["Freisteller", "Messwerte", "Korrektur"],
        required_metadata=["author", "description", "keywords"],
        keyword_layers=["SpezialLayer1", "SpezialLayer2"],
        keyword_metadata=["author", "description"],
        logfiles_dir="/tmp/PRiSM-logs",
        debug_output=True,
    )
    print("Generated temporary JSX script:", temp_jsx)