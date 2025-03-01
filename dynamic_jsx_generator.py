#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import tempfile

DEBUG_OUTPUT = True


def debug_print(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)


def generate_hybrid_jsx(hf_config: dict, template_path: str) -> str:
    """
    Liest das JSX‑Template, ersetzt die Platzhalter mit den in hf_config definierten
    required_layers, required_metadata und logfiles_dir und gibt den Pfad zur temporären Datei zurück.
    """
    required_layers = hf_config.get("required_layers", [])
    required_metadata = hf_config.get("required_metadata", [])
    logfiles_dir = hf_config.get("logfiles_dir", "")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_template_path = os.path.join(base_dir, "jsx_templates", "contentcheck_template.jsx")
    if not os.path.exists(abs_template_path):
        raise FileNotFoundError(f"JSX-Template nicht gefunden: {abs_template_path}")

    with open(abs_template_path, "r", encoding="utf-8") as f:
        jsx_template = f.read()

    # Ersetze die Platzhalter – dabei gehen wir davon aus, dass das Template
    # keine eigenen Defaultwerte mehr setzt.
    layers_str = json.dumps(required_layers)
    metadata_str = json.dumps(required_metadata)
    logfiles_str = logfiles_dir.replace("\\", "/")

    jsx_code = jsx_template
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_LAYERS*/", layers_str)
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_METADATA*/", metadata_str)
    jsx_code = jsx_code.replace("/*PYTHON_INSERT_LOGFOLDER*/", json.dumps(logfiles_str))

    debug_print("Generierter JSX-Code:")
    debug_print(jsx_code)

    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, "dynamic_contentcheck.jsx")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(jsx_code)
    debug_print(f"Hybrid-JSX-Skript erzeugt: {tmp_path}")
    return tmp_path


def generate_jsx_script(hf_config: dict, target_filename: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "jsx_templates", "contentcheck_template.jsx")
    return generate_hybrid_jsx(hf_config, template_path)