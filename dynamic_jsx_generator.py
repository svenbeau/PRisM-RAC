#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import tempfile
from utils.config_manager import get_resource_path, debug_print

DEBUG_OUTPUT = True
def debug_print_local(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

def generate_hybrid_jsx(hf_config: dict, template_path: str = None) -> str:
    """
       Liest das JSX-Template, ersetzt die Platzhalter mit den in hf_config definierten
       required_layers, required_metadata und logfiles_dir und gibt den Pfad zur temporären Datei zurück.

       Falls kein Template-Pfad übergeben wurde, wird der relative Pfad aus dem Konfigurationsmanager verwendet.
       """

    # Falls kein Template-Pfad übergeben wurde, verwende den relativen Pfad aus dem Konfigurationsmanager
    if not template_path:
        template_path = os.path.join(get_resource_path("jsx_templates"), "contentcheck_template.jsx")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"JSX-Template nicht gefunden: {template_path}")
    with open(template_path, "r", encoding="utf-8") as f:
        jsx_template = f.read()
    # Hole die aus der Hotfolder-Konfiguration übergebenen Werte
    required_layers = hf_config.get("required_layers", [])
    required_metadata = hf_config.get("required_metadata", [])
    logfiles_dir = hf_config.get("logfiles_dir", "")
    # Ersetze die Platzhalter – hier wird logFolderPath als JSON‑String (in Anführungszeichen) gesetzt
    layers_str = json.dumps(required_layers)
    metadata_str = json.dumps(required_metadata)
    logfiles_str = json.dumps(logfiles_dir.replace("\\", "/"))
    jsx_code = jsx_template
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_LAYERS*/", layers_str)
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_METADATA*/", metadata_str)
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_LOGFOLDER*/", logfiles_str)
    debug_print_local("Generierter JSX-Code:")
    debug_print_local(jsx_code)
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, "dynamic_contentcheck.jsx")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(jsx_code)
    debug_print_local(f"Hybrid-JSX-Skript erzeugt: {tmp_path}")
    return tmp_path

def generate_jsx_script(hf_config: dict, target_filename: str) -> str:
    """
    Erzeugt das temporäre JSX-Skript anhand der Hotfolder-Konfiguration.
    """
    template_path = os.path.join(get_resource_path("jsx_templates"), "contentcheck_template.jsx")
    return generate_hybrid_jsx(hf_config, template_path)