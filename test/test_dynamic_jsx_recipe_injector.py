import os
import json
import tempfile
import pytest

# Wir importieren die privaten Funktionen aus hotfolder_monitor,
# weil _find_recipe_for_script dort implementiert ist.
from hotfolder_monitor import _find_recipe_for_script, APP_SUPPORT_SCRIPT_CONFIG


@pytest.fixture
def dummy_config_file(tmp_path, monkeypatch):
    """
    Erzeugt eine Dummy-config mit zwei Script-Einträgen
    und patched APP_SUPPORT_SCRIPT_CONFIG dorthin.
    """
    scripts = [
        {
            "name": "Recipe A",
            "script_path": "/Users/testuser/Projects/scripts/GRIS_ReadWriteCSV_2025.jsx",
            "csvWandFile": "/dummy/csv_A.csv"
        },
        {
            "name": "Recipe B",
            "script_path": "/Users/testuser/Projects/scripts/GRIS_Wandabbildungen_2024_dynamisch.jsx",
            "basicWandFiles": "/dummy/path_B"
        }
    ]
    config = {"scripts": scripts}
    cfg_file = tmp_path / "script_config.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    # Patch globalen Config-Pfad
    monkeypatch.setattr("hotfolder_monitor.APP_SUPPORT_SCRIPT_CONFIG", str(cfg_file))
    return scripts


def test_exact_filename_match(dummy_config_file):
    recipe = _find_recipe_for_script("/any/path/GRIS_ReadWriteCSV_2025.jsx")
    assert recipe is not None
    assert recipe["name"] == "Recipe A"
    assert recipe["csvWandFile"] == "/dummy/csv_A.csv"


def test_fallback_partial_match(dummy_config_file):
    # Script liegt in anderem Pfad, Name ist aber Substring
    recipe = _find_recipe_for_script("/another/location/GRIS_Wandabbildungen_2024_dynamisch.jsx")
    assert recipe is not None
    assert recipe["name"] == "Recipe B"
    assert "basicWandFiles" in recipe


def test_no_match_returns_none(dummy_config_file):
    recipe = _find_recipe_for_script("/unrelated/OtherScript.jsx")
    assert recipe is None