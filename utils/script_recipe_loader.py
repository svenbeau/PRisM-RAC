# utils/script_recipe_loader.py
import json, os

APP_SUPPORT_CONFIG = os.path.expanduser("~/Library/Application Support/PRisM-CC/config/script_config.json")

def load_all_recipes():
    try:
        with open(APP_SUPPORT_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("scripts", [])
    except Exception:
        return []

def find_recipe_for_script(script_path_or_name: str):
    """Findet die passende Recipe anhand vollständigem Pfad ODER nur Dateiname."""
    scripts = load_all_recipes()
    if not scripts:
        return None
    needle = script_path_or_name.replace("\\", "/").split("/")[-1].lower()
    # 1) exakter Dateiname
    for s in scripts:
        name = str(s.get("script_path", "")).replace("\\", "/").split("/")[-1].lower()
        if name == needle:
            return s
    # 2) Teilpfad (Fallback)
    for s in scripts:
        path = str(s.get("script_path", "")).replace("\\", "/").lower()
        if needle in path:
            return s
    return None