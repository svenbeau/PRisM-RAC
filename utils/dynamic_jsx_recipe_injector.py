# -*- coding: utf-8 -*-
"""
Dynamischer Recipe-Injektor für Produktions-JSX:
- Liest ein Recipe-Dict (z.B. aus ~/Library/Application Support/PRisM-CC/config/script_config.json)
- Erzeugt eine temporäre JSX-Datei, die VOR das originale Skript einen Header injiziert.
- Der Header:
  * definiert __PRISM_RECIPE (als flaches Objekt mit relevanten Keys wie csvWandFile, json_folder, ...)
  * OVERRIDERT loadConfiguration() so, dass sie __PRISM_RECIPE zurückgibt (kein Dateizugriff, kein Alert)
  * setzt optional DEBUG_OUTPUT
- Gibt den Pfad zur temporären JSX zurück.

Kompatibel mit Python 3.9 (kein | in Typannotationen).
"""

import os
import tempfile
from typing import Optional, Dict, Any

from utils.utils import debug_print


def _escape_js_string(value: str) -> str:
    """Entschärft Python-Strings für JS-Literale (einfaches Quoting)."""
    if value is None:
        return ""
    # Backslashes zuerst escapen
    value = value.replace("\\", "\\\\")
    # Quotes escapen
    value = value.replace('"', '\\"')
    # Zeilenumbrüche neutralisieren
    value = value.replace("\n", "\\n").replace("\r", "\\r")
    return value


def _make_recipe_header(recipe: Dict[str, Any],
                        extra: Optional[Dict[str, Any]] = None,
                        debug_output: bool = True) -> str:
    """
    Erzeugt den JS-Header, der:
      - __PRISM_RECIPE als Objekt bereitstellt (nur bekannte Keys)
      - loadConfiguration() überschreibt und __PRISM_RECIPE zurückgibt
      - optional Alerts unterdrückt, falls ein fremdes Skript dennoch eine "Script config not found" Meldung erzeugt
    """

    # Erlaubte / relevante Keys (je nach Skript unterschiedlich genutzt)
    allowed_keys = [
        "name",
        "script_path",
        "json_folder",
        "actionFolderName",
        "basicWandFiles",
        "csvWandFile",
        "wandFileSavePath",
        "id",
        "body_visible",
    ]

    flat: Dict[str, Any] = {}
    for k in allowed_keys:
        if k in recipe:
            flat[k] = recipe[k]

    # Extra-Merge (falls gewünscht)
    if extra:
        for k, v in extra.items():
            flat[k] = v

    # JS-Objekt bauen (nur primitive Typen sauber serialisieren)
    js_props = []
    for k, v in flat.items():
        if isinstance(v, str):
            js_props.append(f'"{k}": "{_escape_js_string(v)}"')
        elif isinstance(v, bool):
            js_props.append(f'"{k}": {"true" if v else "false"}')
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            js_props.append(f'"{k}": {v}')
        else:
            # Fallback: als String
            js_props.append(f'"{k}": "{_escape_js_string(str(v))}"')

    js_object_literal = "{ " + ", ".join(js_props) + " }"
    js_debug_flag = "true" if debug_output else "false"

    # Wichtig: loadConfiguration() hier überschreiben. In ExtendScript werden Funktionsdeklarationen zwar geparst,
    # aber unsere Zuweisung (function-Expression) zur Laufzeit ausgeführt und überschreibt die deklarierte Funktion.
    # Dadurch wird kein Dateizugriff im Basis-JSX mehr gemacht.
    header = f"""// ===== PRisM-RAC injected RECIPE header (auto-generated) =====
var DEBUG_OUTPUT = {js_debug_flag};

// Globale Recipe-Daten aus Python:
var __PRISM_RECIPE = {js_object_literal};

// Optionale, gezielte Unterdrückung einer lästigen Warnung, falls Drittcode sie dennoch wirft
// (sollte durch unseren loadConfiguration-Override eigentlich nie mehr auftreten).
(function() {{
    try {{
        var __orig_alert__ = alert;
        alert = function(msg) {{
            try {{
                var s = String(msg);
                if (s.indexOf("Script config not found:") !== -1) {{
                    // Unterdrücken
                    return;
                }}
            }} catch(e) {{}}
            return __orig_alert__(msg);
        }};
    }} catch(e) {{}}
}})();

// WICHTIG: Override von loadConfiguration(), so dass Produktions-JSX die injizierte Konfiguration bekommt
// und NICHT versucht, relativ zum Temp-Pfad eine config/script_config.json zu lesen.
var loadConfiguration = function() {{
    if (DEBUG_OUTPUT) {{
        try {{
            $.writeln("[PRISM] loadConfiguration() overridden, returning injected recipe for: " + (__PRISM_RECIPE.script_path || "unknown"));
        }} catch(e) {{}}
    }}
    // Rückgabe: exakt das Objekt, das die Skripte erwarten (bei GRIS_ReadWriteCSV_2025.jsx z.B. csvWandFile)
    return __PRISM_RECIPE;
}};

// ===== end injected RECIPE header =====

"""

    return header


def create_temp_jsx_with_recipe(*,
                                recipe: Dict[str, Any],
                                base_jsx_path: str,
                                extra: Optional[Dict[str, Any]] = None,
                                debug_output: bool = False) -> Optional[str]:
    """
    Baut eine temporäre JSX-Datei aus:
      [Injected-Header mit loadConfiguration-Override]
      +
      [Original-JSX-Inhalt]

    Rückgabe: Pfad zur temporären Datei oder None bei Fehler.
    """
    try:
        if not base_jsx_path or not os.path.exists(base_jsx_path):
            debug_print(f"[RecipeInjector] Base JSX not found: {base_jsx_path}")
            return None

        with open(base_jsx_path, "r", encoding="utf-8") as f:
            original_jsx = f.read()

        header = _make_recipe_header(recipe=recipe, extra=extra, debug_output=debug_output)

        # Zusammenführen
        combined = header + "\n" + original_jsx

        # Temp-Datei erzeugen
        fd, tmp_path = tempfile.mkstemp(prefix="dynamic_recipe_", suffix=".jsx")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(combined)
        except Exception:
            # Falls Schreiben via fdopen schief geht, Datei schließen/löschen
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            raise

        debug_print(f"[dynamic_jsx_recipe_injector] Temporary JSX created: {tmp_path}")
        return tmp_path

    except Exception as e:
        debug_print(f"[RecipeInjector] Error creating temp JSX for {base_jsx_path}: {e}")
        return None