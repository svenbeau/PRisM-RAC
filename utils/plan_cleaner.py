# utils/plan_cleaner.py
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class SimpleSignal:
    def __init__(self):
        self._subs: List[Callable[..., None]] = []
    def connect(self, cb: Callable[..., None]):
        if callable(cb):
            self._subs.append(cb)
    def emit(self, *args, **kwargs):
        for cb in list(self._subs):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass


@dataclass
class CleanerConfig:
    transfer_plans_path: Path = field(
        default_factory=lambda: Path.home() / "Library" / "Application Support" / "PRisM-CC" / "transfer_plans.json"
    )
    # Alle gängigen Orte für die Hotfolder-Konfig
    hotfolder_config_paths: List[Path] = field(default_factory=lambda: [
        Path.home() / "Library" / "Application Support" / "PRisM-CC" / "config" / "hotfolder_config.json",
        Path.home() / "Library" / "Application Support" / "PRisM-CC" / "hotfolder_config.json",
        Path.cwd() / "config" / "hotfolder_config.json",
    ])
    interval_ms: int = 10 * 60 * 1000
    dry_run: bool = False
    remove_empty_dirs: bool = False
    follow_symlinks: bool = True

    # 'always' | 'gate' | 'never'
    hf_gate_mode: str = "gate"
    hf_gate_file: Path = field(
        default_factory=lambda: Path.home() / "Library" / "Application Support" / "PRisM-CC" / ".hf_monitor_running"
    )

    hotfolder_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None
    hotfolder_running_provider: Optional[Callable[[], bool]] = None

    # NEU: erster Lauf sofort (True) oder erst nach dem ersten Intervall (False)
    run_immediately: bool = True


def _load_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"[Cleaner] WARN: Konnte JSON nicht lesen: {path} – {e}")
        return None


def _iter_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    try:
        return [p for p in root.iterdir()]
    except Exception:
        return []


def _is_older_than(p: Path, cutoff: datetime) -> bool:
    try:
        ts = datetime.fromtimestamp(p.stat().st_mtime)
        return ts < cutoff
    except Exception:
        return False


def _safe_delete(path: Path, dry_run: bool) -> Tuple[bool, Optional[str]]:
    try:
        if not path.exists():
            return True, None
        if dry_run:
            return True, None

        if path.is_dir():
            for child in sorted(path.glob("**/*"), key=lambda x: len(x.parts), reverse=True):
                try:
                    if child.is_file():
                        child.unlink(missing_ok=True)
                    elif child.is_dir():
                        child.rmdir()
                except Exception:
                    pass
            try:
                path.rmdir()
            except Exception:
                pass
        else:
            path.unlink(missing_ok=True)
        return True, None
    except Exception as e:
        return False, str(e)


def _remove_empty_dirs(root: Path):
    if not root.exists():
        return
    dirs = sorted([d for d in root.glob("**/*") if d.is_dir()], key=lambda p: len(p.parts), reverse=True)
    for d in dirs:
        try:
            next(d.iterdir())
        except StopIteration:
            try:
                d.rmdir()
            except Exception:
                pass
        except Exception:
            pass


class PlanCleaner:
    """
    Räumt auf in:
      • Transfer-Plänen (move_after + auto_delete_after_move_enabled)
      • Hotfoldern (02_Success / 03_Fault, wenn Auto-Delete aktiv ist)
    HF-Löschung abhängig von hf_gate_mode: 'always' (immer), 'gate' (nur wenn Gate aktiv), 'never' (nie).

    Neu:
      • config.run_immediately=False -> erster Lauf erst nach dem ersten Intervall.
    """

    def __init__(self, config: CleanerConfig, config_manager: Optional[Any] = None):
        self.config = config
        self._config_manager = config_manager
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running_lock = threading.Lock()
        self._is_running = False

        # Signale
        self.sig_log = SimpleSignal()
        self.sig_error = SimpleSignal()
        self.sig_deleted = SimpleSignal()  # für main.py

    def _log(self, msg: str):
        logger.debug(msg)
        try:
            self.sig_log.emit(msg)
        except Exception:
            pass

    def _err(self, msg: str):
        logger.debug(msg)
        try:
            self.sig_error.emit(msg)
        except Exception:
            pass

    def set_hotfolder_provider(self, provider: Callable[[], List[Dict[str, Any]]]):
        self.config.hotfolder_provider = provider

    def set_hotfolder_running_provider(self, provider: Callable[[], bool]):
        self.config.hotfolder_running_provider = provider

    def start(self):
        with self._running_lock:
            if self._is_running:
                self._log("[Cleaner] bereits gestartet – ignoriere zweiten Start.")
                return
            self._is_running = True
        self._stop.clear()
        interval_s = max(1, int(self.config.interval_ms / 1000))
        initial_delay_s = 0 if (self.config.run_immediately is True) else interval_s

        if initial_delay_s > 0:
            self._log(
                f"[Cleaner] gestartet (Intervall={self.config.interval_ms} ms, dry_run={self.config.dry_run}) – "
                f"erster Lauf in {initial_delay_s}s."
            )
        else:
            self._log(f"[Cleaner] gestartet (Intervall={self.config.interval_ms} ms, dry_run={self.config.dry_run}).")

        self._thread = threading.Thread(
            target=self._run_loop, args=(interval_s, initial_delay_s), daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=10.0)
        with self._running_lock:
            self._is_running = False
        self._log("[Cleaner] Stop abgeschlossen.")

    def _run_loop(self, interval_s: int, initial_delay_s: int = 0):
        try:
            # optionaler Start-Delay
            if initial_delay_s > 0:
                for _ in range(initial_delay_s):
                    if self._stop.is_set():
                        return
                    time.sleep(1)

            while not self._stop.is_set():
                self.run()
                for _ in range(interval_s):
                    if self._stop.is_set():
                        break
                    time.sleep(1)
        finally:
            pass

    def run(self):
        try:
            self._process_transfer_plans()
        except Exception as e:
            self._err(f"[Cleaner] ERROR Transfer: {e}")

        try:
            self._process_hotfolders()
        except Exception as e:
            self._err(f"[Cleaner] ERROR HF: {e}")

    # ---------- Transfer-Pläne ----------

    def _load_plans(self) -> List[Dict[str, Any]]:
        data = _load_json(self.config.transfer_plans_path)
        if not isinstance(data, list):
            data = []
        logger.debug(f"[Cleaner] Transfer-Pläne geladen: {self.config.transfer_plans_path}")
        return data

    def _process_transfer_plans(self):
        plans = self._load_plans()
        for plan in plans:
            try:
                name = plan.get("name", "<ohne Name>")
                move_after = plan.get("move_after") or ""
                ad_enabled = bool(plan.get("auto_delete_after_move_enabled"))
                ad_hours = int(plan.get("auto_delete_after_move_hours") or 0)
                if not (ad_enabled and ad_hours > 0 and move_after):
                    continue

                cutoff = datetime.now() - timedelta(hours=ad_hours)
                root = Path(move_after)

                self._log(f"[Cleaner] TransferPlan:{name} – prüfe: {root}, cutoff={cutoff.isoformat()}")
                if not root.exists():
                    continue

                for p in _iter_files(root):
                    if _is_older_than(p, cutoff):
                        ok, err = _safe_delete(p, self.config.dry_run)
                        if ok:
                            self._log(f"[Cleaner] TransferPlan:{name} – gelöscht: {p}")
                            try:
                                self.sig_deleted.emit(str(p))
                            except Exception:
                                pass
                        else:
                            self._err(f"[Cleaner] TransferPlan:{name} – FEHLER beim Löschen: {p} – {err}")

                if self.config.remove_empty_dirs:
                    _remove_empty_dirs(root)

            except Exception as e:
                self._err(f"[Cleaner] TransferPlan: Fehler bei '{plan.get('name', '')}': {e}")

    # ---------- Hotfolder ----------

    def _gate_hotfolders_running(self) -> bool:
        # externer Provider?
        if self.config.hotfolder_running_provider:
            try:
                return bool(self.config.hotfolder_running_provider())
            except Exception as e:
                self._err(f"[Cleaner] HF: Provider-Fehler im Running-Check – {e}")

        # config_manager Hooks?
        if self._config_manager is not None:
            for attr in ("is_hotfolder_running", "is_running", "get_hf_running"):
                fn = getattr(self._config_manager, attr, None)
                if callable(fn):
                    try:
                        return bool(fn())
                    except Exception as e:
                        self._err(f"[Cleaner] HF: config_manager.{attr}() Fehler – {e}")

        # Modus aus Konfiguration
        mode = (self.config.hf_gate_mode or "gate").lower()
        if mode == "always":
            return True
        if mode == "never":
            return False
        try:
            return self.config.hf_gate_file.exists()
        except Exception as e:
            self._err(f"[Cleaner] HF: Gate-File-Check Fehler – {e}")
            return False

    def _extract_hf_list(self, data: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Akzeptiert sowohl:
          • [ {...}, {...} ]  (reine Liste)
          • { "hotfolders": [ ... ] }
          • { "items": [ ... ] }
          • { "list": [ ... ] }
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("hotfolders", "items", "list", "hotfolder_list"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
        return None

    def _load_hotfolders(self) -> List[Dict[str, Any]]:
        # Provider?
        if self.config.hotfolder_provider:
            try:
                hfs = self.config.hotfolder_provider() or []
                logger.debug(f"[Cleaner] HF: provider lieferte {len(hfs)} Hotfolder.")
                return hfs
            except Exception as e:
                self._err(f"[Cleaner] HF: Provider-Fehler – {e}")

        # config_manager?
        if self._config_manager is not None:
            for attr in ("get_hotfolders", "get_hotfolder_list", "load_hotfolders"):
                fn = getattr(self._config_manager, attr, None)
                if callable(fn):
                    try:
                        hfs = fn() or []
                        if isinstance(hfs, list):
                            logger.debug(f"[Cleaner] HF: geladen via config_manager.{attr} – {len(hfs)} Einträge.")
                            return hfs
                    except Exception as e:
                        self._err(f"[Cleaner] HF: config_manager.{attr}() Fehler – {e}")

        # JSON-Fallbacks
        for candidate in self.config.hotfolder_config_paths:
            candidate = Path(candidate).expanduser()
            data = _load_json(candidate)
            hfs = self._extract_hf_list(data)
            if isinstance(hfs, list) and len(hfs) > 0:
                logger.debug(f"[Cleaner] HF: geladen aus {candidate} – {len(hfs)} Einträge.")
                return hfs

        # Wenn Datei existiert, aber keine Liste extrahierbar ist, explizit leeren Zustand loggen
        for candidate in self.config.hotfolder_config_paths:
            candidate = Path(candidate).expanduser()
            if candidate.exists():
                logger.debug("[HF] gelesen:\n[]")
                return []

        logger.debug("[Cleaner] HF: keine Konfiguration gefunden.")
        return []

    def _process_hotfolders(self):
        if not self._gate_hotfolders_running():
            self._log("[Cleaner] HF: übersprungen (Gate nicht aktiv).")
            return

        hotfolders = self._load_hotfolders()
        if not hotfolders:
            return

        active = []
        for hf in hotfolders:
            if hf.get("auto_delete_success_enabled") or hf.get("auto_delete_fault_enabled"):
                active.append(hf)

        if not active:
            self._log("[Cleaner] HF: keine Auto-Delete-aktiven Hotfolder.")
            return

        for hf in active:
            try:
                name = hf.get("name", "<ohne Name>")

                if bool(hf.get("auto_delete_success_enabled")):
                    hours = int(hf.get("auto_delete_success_hours") or 0)
                    success_dir = Path(hf.get("success_dir") or "")
                    if hours > 0 and success_dir:
                        self._clean_hf_dir(name, "02_Success", success_dir, hours)

                if bool(hf.get("auto_delete_fault_enabled")):
                    hours = int(hf.get("auto_delete_fault_hours") or 0)
                    fault_dir = Path(hf.get("fault_dir") or "")
                    if hours > 0 and fault_dir:
                        self._clean_hf_dir(name, "03_Fault", fault_dir, hours)

            except Exception as e:
                self._err(f"[Cleaner] HF: Fehler bei '{hf.get('name','')}': {e}")

    def _clean_hf_dir(self, hf_name: str, label: str, root: Path, hours: int):
        cutoff = datetime.now() - timedelta(hours=hours)
        self._log(f"[Cleaner] HF: {hf_name} – prüfe {label}: {root}, cutoff={cutoff.isoformat()}")

        if not root.exists():
            return

        for p in _iter_files(root):
            if _is_older_than(p, cutoff):
                ok, err = _safe_delete(p, self.config.dry_run)
                if ok:
                    self._log(f"[Cleaner] HF: {hf_name} – gelöscht in {label}: {p}")
                    try:
                        self.sig_deleted.emit(str(p))
                    except Exception:
                        pass
                else:
                    self._err(f"[Cleaner] HF: {hf_name} – FEHLER beim Löschen in {label}: {p} – {err}")

        if self.config.remove_empty_dirs:
            _remove_empty_dirs(root)