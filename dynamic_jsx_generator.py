# dynamic_jsx_generator.py
import os
import sys
import tempfile
import json
from utils.config_manager import debug_print, load_settings


# Hilfsfunktion, um Templates aus verschiedenen Pfaden zu finden
def find_template_file(template_name):
    """
    Sucht nach Template-Dateien an verschiedenen möglichen Speicherorten
    und gibt den ersten gefundenen Pfad zurück.
    """
    # Laden der Einstellungen, um den konfigurierten Pfad zu erhalten
    settings = load_settings()

    # Liste der möglichen Pfade, in denen das Template gefunden werden könnte
    possible_paths = []

    # 1. Konfigurierter Pfad in den Einstellungen
    if settings and "resource_paths" in settings and "jsx_templates" in settings["resource_paths"]:
        configured_path = os.path.join(settings["resource_paths"]["jsx_templates"], template_name)
        possible_paths.append(configured_path)

    # 2. PyInstaller Pfad (wenn kompiliert)
    if hasattr(sys, '_MEIPASS'):
        pyinstaller_path = os.path.join(sys._MEIPASS, "jsx_templates", template_name)
        possible_paths.append(pyinstaller_path)

    # 3. Relativer Pfad zum Skript
    script_relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jsx_templates", template_name)
    possible_paths.append(script_relative_path)

    # 4. Relativer Pfad zum Arbeitsverzeichnis
    working_dir_path = os.path.join(os.getcwd(), "jsx_templates", template_name)
    possible_paths.append(working_dir_path)

    # 5. Einfacher relativer Pfad
    simple_relative_path = os.path.join("jsx_templates", template_name)
    possible_paths.append(simple_relative_path)

    # Debug-Ausgaben
    debug_print(f"Suche nach Template: {template_name}")
    for path in possible_paths:
        debug_print(f"  Prüfe Pfad: {path}")
        if os.path.exists(path):
            debug_print(f"  Template gefunden unter: {path}")
            return path

    # Wenn kein Pfad funktioniert hat
    debug_print(f"FEHLER: Template {template_name} konnte nicht gefunden werden!")
    debug_print("Suchpfade waren:")
    for path in possible_paths:
        debug_print(f"  - {path}")

    return None


def create_contentcheck_jsx(layers, metadata_fields, keyword_check=None):
    """Erstellt ein dynamisches JSX-Skript für den Contentcheck basierend auf den übergebenen Parametern."""
    try:
        # Lade die Template-Datei mit der neuen Hilfsfunktion
        base_jsx_path = find_template_file("contentcheck_template.jsx")

        if not base_jsx_path:
            debug_print("Fehler: Base JSX script not found")
            return None

        with open(base_jsx_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Rest des Codes bleibt unverändert...

        # Konvertiere die Layer und Metadata-Felder in JavaScript-Arrays
        layers_js = json.dumps(layers)
        metadata_js = json.dumps(metadata_fields)

        # Ersetze die Platzhalter im Template
        template = template.replace("__REQUIRED_LAYERS__", layers_js)
        template = template.replace("__REQUIRED_METADATA__", metadata_js)

        # Füge optionale Keyword-Check-Funktionalität hinzu, wenn angegeben
        if keyword_check and isinstance(keyword_check, dict):
            keyword_enabled = "true" if keyword_check.get("enabled", False) else "false"
            keyword = json.dumps(keyword_check.get("keyword", ""))
            keyword_layers = json.dumps(keyword_check.get("layers", []))
            keyword_metadata = json.dumps(keyword_check.get("metadata", []))

            template = template.replace("__KEYWORD_CHECK_ENABLED__", keyword_enabled)
            template = template.replace("__KEYWORD_CHECK_WORD__", keyword)
            template = template.replace("__KEYWORD_CHECK_LAYERS__", keyword_layers)
            template = template.replace("__KEYWORD_CHECK_METADATA__", keyword_metadata)
        else:
            template = template.replace("__KEYWORD_CHECK_ENABLED__", "false")
            template = template.replace("__KEYWORD_CHECK_WORD__", '""')
            template = template.replace("__KEYWORD_CHECK_LAYERS__", "[]")
            template = template.replace("__KEYWORD_CHECK_METADATA__", "[]")

        # Erstelle eine temporäre JSX-Datei
        temp_jsx = tempfile.NamedTemporaryFile(suffix='.jsx', delete=False)
        temp_jsx.write(template.encode('utf-8'))
        temp_jsx.close()

        return temp_jsx.name
    except Exception as e:
        debug_print(f"Fehler beim Erstellen des dynamischen JSX-Skripts: {e}")
        return None