#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import tempfile
from utils.config_manager import debug_print

def create_temp_jsx_with_config(base_jsx_path,
                                keyword_check_enabled,
                                keyword_check_word,
                                required_layers,
                                required_metadata,
                                keyword_layers,
                                keyword_metadata,
                                logfiles_dir):
    """
    Erzeugt eine temporäre JSX-Datei, in der folgende Platzhalter ersetzt werden:
      /*PYTHON_INSERT_REQUIRED_LAYERS*/    -> JSON-String der Standard-Ebenen (required_layers)
      /*PYTHON_INSERT_REQUIRED_METADATA*/  -> JSON-String der Standard-Metadaten (required_metadata)
      /*PYTHON_INSERT_KEYWORD_LAYERS*/       -> JSON-String der Keyword-Ebenen (keyword_layers)
      /*PYTHON_INSERT_KEYWORD_METADATA*/     -> JSON-String der Keyword-Metadaten (keyword_metadata)
      /*PYTHON_INSERT_LOGFOLDER*/            -> JSON-String des Logfiles-Verzeichnisses (logfiles_dir)

    Zusätzlich wird Injektions-Code erzeugt, der zur Laufzeit im JSX entscheidet,
    ob der Keyword-basierte Check aktiv ist und welche Kriterien (Ebenen/Metadaten) verwendet werden sollen.
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

    # Konvertiere die Konfigurationswerte in JSON-Strings
    required_layers_str = json.dumps(required_layers)
    required_metadata_str = json.dumps(required_metadata)
    keyword_layers_str = json.dumps(keyword_layers)
    keyword_metadata_str = json.dumps(keyword_metadata)
    logfiles_str = json.dumps(logfiles_dir)

    # Ersetze die Platzhalter im Template
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_REQUIRED_LAYERS*/", required_layers_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_REQUIRED_METADATA*/", required_metadata_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_KEYWORD_LAYERS*/", keyword_layers_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_KEYWORD_METADATA*/", keyword_metadata_str)
    jsx_template = jsx_template.replace("/*PYTHON_INSERT_LOGFOLDER*/", logfiles_str)

    # Injektions-Code: Dieser Code wird zu Beginn des JSX-Skripts eingefügt.
    injection = (
        "var DEBUG_OUTPUT = false;\n"
        "var keywordCheckEnabled = " + str(keyword_check_enabled).lower() + ";\n"
        "var keywordCheckWord = " + json.dumps(keyword_check_word) + ";\n"
        "var fileKeywords = (typeof getFileKeywords === 'function') ? getFileKeywords() : '';\n"
        "var checkType;\n"
        "if (keywordCheckEnabled && String(fileKeywords).trim().toLowerCase() === keywordCheckWord.toLowerCase()) {\n"
        "    checkType = 'Keyword-based';\n"
        "} else {\n"
        "    checkType = 'Standard';\n"
        "}\n"
        "// Bestimme die effektiven Kriterien basierend auf checkType\n"
        "var effectiveLayers, effectiveMetadata;\n"
        "if (checkType === 'Keyword-based') {\n"
        "    effectiveLayers = JSON.parse('/*PYTHON_INSERT_KEYWORD_LAYERS*/');\n"
        "    effectiveMetadata = JSON.parse('/*PYTHON_INSERT_KEYWORD_METADATA*/');\n"
        "} else {\n"
        "    effectiveLayers = JSON.parse('/*PYTHON_INSERT_REQUIRED_LAYERS*/');\n"
        "    effectiveMetadata = JSON.parse('/*PYTHON_INSERT_REQUIRED_METADATA*/');\n"
        "}\n"
        "// logFolderPath wird aus der Konfiguration übernommen\n"
        "var logFolderPath = JSON.parse('/*PYTHON_INSERT_LOGFOLDER*/');\n"
        "if (DEBUG_OUTPUT) { $.writeln('DEBUG: Logfiles werden geschrieben in: ' + logFolderPath); }\n"
    )

    # Kombiniere Injektion und Template
    combined_code = injection + jsx_template

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsx", prefix="dynamic_contentcheck_")
        os.close(tmp_fd)
        with open(tmp_path, "w", encoding="utf-8") as tmp_f:
            tmp_f.write(combined_code)
        debug_print(f"Temporary JSX created: {tmp_path} "
                    f"(keywordCheckEnabled={keyword_check_enabled}, keywordCheckWord={keyword_check_word}, "
                    f"required_layers={required_layers}, required_metadata={required_metadata}, "
                    f"keyword_layers={keyword_layers}, keyword_metadata={keyword_metadata}, "
                    f"logFolderPath={logfiles_dir})")
        return tmp_path
    except Exception as e:
        debug_print(f"Error writing temporary JSX script: {e}")
        return None

if __name__ == "__main__":
    # Dummy-Daten zur Überprüfung
    base_jsx = "contentcheck_template.jsx"  # Pfad zum Template
    temp_jsx = create_temp_jsx_with_config(
        base_jsx_path=base_jsx,
        keyword_check_enabled=True,
        keyword_check_word="Rueckseite",
        required_layers=["Freisteller", "Messwerte", "Korrektur"],
        required_metadata=["author", "description", "keywords"],
        keyword_layers=["SpezialLayer1", "SpezialLayer2"],
        keyword_metadata=["author", "description"],
        logfiles_dir="/dein/konfigurierter/pfad/zum/logfiles_ordner"  # Hier den individuell konfigurierbaren Pfad eintragen
    )
    if temp_jsx:
        print("Generated temporary JSX script:", temp_jsx)
    else:
        print("Error generating temporary JSX script.")