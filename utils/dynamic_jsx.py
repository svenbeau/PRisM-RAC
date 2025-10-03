# utils/dynamic_jsx.py
import json, tempfile, os
from utils.utils import debug_print, run_jsx_in_photoshop  # vorhandene Funktionen

def _q(v):
    # JS-String sicher quoten
    if v is None: v = ""
    return json.dumps(str(v))

def make_header_from_recipe(recipe: dict, extra: dict = None, debug=True) -> str:
    # bekannte Felder + optionale Extras in JS-Variablen wandeln
    fields = {
        "actionFolderName": recipe.get("actionFolderName", ""),
        "basicWandFiles":   recipe.get("basicWandFiles", ""),
        "csvWandFile":      recipe.get("csvWandFile", ""),
        "wandFileSavePath": recipe.get("wandFileSavePath", ""),
    }
    if extra:
        fields.update(extra)

    lines = []
    lines.append("// ===== PRisM-RAC injected config (auto-generated) =====")
    lines.append(f"var DEBUG_OUTPUT = {str(bool(debug)).lower()};")
    for k, v in fields.items():
        lines.append(f"var {k} = {_q(v)};")
    # Debug-Echo
    lines.append('$.writeln("[PRiSM-JSX] Injection Start");')
    for k in ["actionFolderName","basicWandFiles","csvWandFile","wandFileSavePath"]:
        lines.append(f'$.writeln("[PRiSM-JSX] {k}=" + {k});')
    lines.append("// ===== end injected config =====\n")
    return "\n".join(lines)

def build_dynamic_jsx(original_jsx_path: str, header: str) -> str:
    with open(original_jsx_path, "r", encoding="utf-8") as f:
        body = f.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_dyn.jsx")
    with open(tmp.name, "w", encoding="utf-8") as g:
        g.write(header)
        g.write(body)
    return tmp.name

def run_jsx_with_recipe(original_jsx_path: str, recipe: dict, extra: dict = None, debug=True):
    header = make_header_from_recipe(recipe or {}, extra=extra, debug=debug)
    dyn_path = build_dynamic_jsx(original_jsx_path, header)
    debug_print(f"[DynamicJSX] Built: {dyn_path} for {original_jsx_path}")
    rc, out = run_jsx_in_photoshop(dyn_path)
    debug_print(f"[DynamicJSX] RC={rc}")
    if out:
        debug_print(f"[DynamicJSX] JSX stdout:\n{out}")
    try:
        os.unlink(dyn_path)
    except OSError:
        pass
    return rc, out