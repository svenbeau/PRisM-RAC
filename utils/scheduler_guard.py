#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Einfacher Singleton-Guard für einmalige Starts (z. B. Scheduler, Cleaner).

Verwendung:
    from utils.scheduler_guard import start_once
    started = start_once("main_scheduler", lambda: scheduler.start())
    # True  -> jetzt gestartet
    # False -> lief bereits; Start wurde unterdrückt
"""

from typing import Callable, Dict
from threading import Lock

__all__ = ["start_once", "reset_guard"]

_started: Dict[str, bool] = {}
_lock = Lock()


def start_once(key: str, start_callable: Callable[[], None]) -> bool:
    """
    Startet eine Komponente nur einmal pro Key.

    :param key: Eindeutiger Name (z. B. "main_scheduler")
    :param start_callable: Funktion, die den Start ausführt
    :return: True wenn gestartet, False wenn bereits lief
    """
    if not key:
        raise ValueError("key must not be empty")
    with _lock:
        if _started.get(key, False):
            return False
        _started[key] = True
    # außerhalb des Locks starten (falls blockierend)
    start_callable()
    return True


def reset_guard(key: str | None = None) -> None:
    """Nur für Tests: Guard-Zustand zurücksetzen."""
    with _lock:
        if key is None:
            _started.clear()
        else:
            _started.pop(key, None)