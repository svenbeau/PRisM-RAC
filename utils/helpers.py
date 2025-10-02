# -*- coding: utf-8 -*-
"""
Kleines Helfer-Modul, damit bestehende Imports in utils.ftp_manager funktionieren,
ohne andere Dateien umzubauen. Reicht debug_print durch an config_manager.debug_print
und stellt einen Fallback bereit, falls etwas schiefgeht.
"""

from __future__ import annotations

try:
    # Bevorzugt den bestehenden Logger aus config_manager nutzen
    from utils.config_manager import debug_print as _cfg_debug_print
except Exception:
    _cfg_debug_print = None


def debug_print(*args, **kwargs):
    """
    Wrapper um config_manager.debug_print (falls vorhanden).
    Fallback: print(*args, **kwargs)
    """
    if _cfg_debug_print is not None:
        try:
            _cfg_debug_print(*args, **kwargs)
            return
        except Exception:
            # Falls der delegierte Logger selbst Probleme macht, nicht crashen.
            pass
    # Fallback auf print, damit Logs nicht verloren gehen
    print(*args, **kwargs)