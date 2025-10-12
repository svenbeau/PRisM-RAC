#!/usr/bin/env python3
# transfer_executor.py
# -*- coding: utf-8 -*-

import os
import time
import tempfile
import subprocess
import shutil
import json
from datetime import datetime, timezone
from PySide6.QtCore import QObject, QThread, Signal, QEventLoop
from PySide6.QtWidgets import QApplication

from utils.config_manager import debug_print, get_ftp_transfer_log_path
from utils.ftp_manager import FTPManager

# Optional: Local TZ für menschenlesbare Stempel
try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo("Europe/Berlin")
except Exception:
    _LOCAL_TZ = None

def _now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def _now_local_iso():
    if _LOCAL_TZ is None:
        return None
    return datetime.now(_LOCAL_TZ).isoformat()

# ------------------------------------------------------------
# CopyWorker: Optimiert für macOS mit verschiedenen Strategien, ohne Kopierton
# ------------------------------------------------------------
class CopyWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal()

    def __init__(self, file_list, dest_folder):
        super().__init__()
        self.file_list = file_list
        self.dest_folder = dest_folder
        self.abort = False

    def run(self):
        # Prüfe, ob das Zielverzeichnis erreichbar ist.
        if not check_destination_connection(self.dest_folder, timeout=10):
            debug_print("Zielverzeichnis nicht erreichbar. Abbruch des Kopiervorgangs.")
            self.finished.emit()
            return

        total = len(self.file_list)
        current = 0

        # Sicherstellen, dass das Zielverzeichnis existiert
        os.makedirs(self.dest_folder, exist_ok=True)

        # Prüfen, ob Quelle und Ziel auf demselben Volume sind
        sample_source = self.file_list[0] if self.file_list else None
        same_volume = False
        if sample_source:
            source_stat = os.stat(os.path.dirname(sample_source))
            dest_stat = os.stat(self.dest_folder)
            same_volume = source_stat.st_dev == dest_stat.st_dev
            debug_print(f"Quelle und Ziel auf gleichem Volume: {same_volume}")

        # Temporäres Verzeichnis auf anderem Volume einrichten, wenn auf gleichem Volume
        temp_dir = None
        if same_volume:
            try:
                temp_dir = tempfile.mkdtemp(prefix="dateisammler_temp_")
                debug_print(f"Temporäres Verzeichnis erstellt: {temp_dir}")
                temp_stat = os.stat(temp_dir)
                if temp_stat.st_dev == source_stat.st_dev:
                    debug_print("Temp-Verzeichnis ist auf gleichem Volume, verwende andere Strategie")
                    shutil.rmtree(temp_dir)
                    temp_dir = None
            except Exception as e:
                debug_print(f"Fehler beim Erstellen des temporären Verzeichnisses: {e}")
                temp_dir = None

        # Setze Finder-Ton initial auf "aus"
        if same_volume:
            try:
                mute_sound_script = '''
                tell application "System Events"
                    set volume without output muted
                    set volume output volume 0
                end tell
                '''
                subprocess.run(["osascript", "-e", mute_sound_script], capture_output=True, text=True)
                debug_print("Finder-Ton deaktiviert")
            except Exception as e:
                debug_print(f"Fehler beim Deaktivieren des Finder-Tons: {e}")

        for path in self.file_list:
            if self.abort:
                debug_print("Kopiervorgang abgebrochen.")
                break

            current += 1
            filename = os.path.basename(path)
            dest_path = os.path.join(self.dest_folder, filename)
            self.progress.emit(current, total, filename)

            # Prüfen, ob Quell- und Zieldatei identisch sind
            if os.path.abspath(path) == os.path.abspath(dest_path):
                debug_print(f"Quell- und Zieldatei sind identisch: {path}")
                continue

            # Prüfen, ob die Datei im Zielverzeichnis bereits existiert
            if os.path.exists(dest_path):
                try:
                    debug_print(f"Datei existiert bereits im Ziel, wird gelöscht: {dest_path}")
                    os.remove(dest_path)
                except Exception as e:
                    debug_print(f"Fehler beim Löschen der vorhandenen Datei: {e}")
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_path = os.path.join(self.dest_folder, f"{base}_{timestamp}{ext}")
                    debug_print(f"Verwende alternativen Dateinamen: {dest_path}")

            success = False

            # Strategieauswahl basierend auf Volume-Typ
            if not same_volume:
                max_retries = 3
                retry_delay = 0.5
                retries = 0
                while not success and retries < max_retries and not self.abort:
                    cmd = ["ditto", path, dest_path]
                    debug_print(f"Führe aus: {' '.join(cmd)} (Versuch {retries + 1})")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        success = True
                        debug_print(f"Datei erfolgreich kopiert: {path}")
                    else:
                        debug_print(f"Fehler beim Kopieren: {path}\n{result.stderr.strip()} (Versuch {retries + 1})")
                        retries += 1
                        time.sleep(0.5)
            else:
                try:
                    debug_print(f"Kopiere mit stillem AppleScript: {path} -> {dest_path}")
                    applescript = f'''
                    tell application "Finder"
                        set volume output volume 0
                        set source_file to POSIX file "{path}" as alias
                        set target_folder to POSIX file "{self.dest_folder}" as alias
                        duplicate source_file to target_folder with replacing
                    end tell
                    '''
                    result = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
                    if result.returncode == 0:
                        success = True
                        debug_print(f"Datei erfolgreich mit AppleScript kopiert: {path}")
                    else:
                        debug_print(f"AppleScript fehlgeschlagen: {result.stderr}")
                        if not success:
                            try:
                                debug_print(f"Versuche JXA-Kopie")
                                jxa_script = f'''
                                function run() {{
                                    ObjC.import('Foundation');
                                    var fm = $.NSFileManager.defaultManager;
                                    var source = $.NSURL.fileURLWithPath("{path}");
                                    var dest = $.NSURL.fileURLWithPath("{dest_path}");
                                    var error = Ref();
                                    var result = fm.copyItemAtURLToURLErrorWithResourcesMetaData(source, dest, error, true);
                                    if (!result) {{
                                        return "Fehler: " + error[0].localizedDescription.js;
                                    }}
                                    return "Erfolg";
                                }}
                                '''
                                result = subprocess.run(["osascript", "-l", "JavaScript", "-e", jxa_script],
                                                        capture_output=True, text=True)
                                if "Erfolg" in result.stdout:
                                    success = True
                                    debug_print(f"Datei erfolgreich mit JXA kopiert: {path}")
                                else:
                                    debug_print(f"JXA fehlgeschlagen: {result.stdout} {result.stderr}")
                            except Exception as e:
                                debug_print(f"Fehler bei JXA: {e}")
                        if not success and temp_dir:
                            try:
                                debug_print(f"Versuche Umweg über temporäres Verzeichnis")
                                temp_path = os.path.join(temp_dir, filename)
                                temp_cmd = ["ditto", path, temp_path]
                                temp_result = subprocess.run(temp_cmd, capture_output=True, text=True)
                                if temp_result.returncode == 0:
                                    final_cmd = ["ditto", temp_path, dest_path]
                                    final_result = subprocess.run(final_cmd, capture_output=True, text=True)
                                    if final_result.returncode == 0:
                                        success = True
                                        debug_print(f"Datei erfolgreich über Temp kopiert: {path}")
                                    else:
                                        debug_print(f"Temp->Ziel fehlgeschlagen: {final_result.stderr}")
                                else:
                                    debug_print(f"Quelle->Temp fehlgeschlagen: {temp_result.stderr}")
                            except Exception as e:
                                debug_print(f"Fehler beim Kopieren über Temp: {e}")
                except Exception as e:
                    debug_print(f"Fehler bei AppleScript: {e}")

                if not success:
                    try:
                        debug_print(f"Versuche direktes Kopieren von Dateiinhalt für: {path}")
                        with open(path, 'rb') as src_file:
                            file_data = src_file.read()
                        with open(dest_path, 'wb') as dest_file:
                            dest_file.write(file_data)
                        success = True
                        debug_print(f"Datei erfolgreich manuell kopiert: {path}")
                    except Exception as e:
                        debug_print(f"Fehler beim manuellen Kopieren: {e}")

            if not success:
                debug_print(f"Endgültiger Fehler beim Kopieren: {path}")

            time.sleep(0.1)

        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                debug_print(f"Temporäres Verzeichnis entfernt: {temp_dir}")
            except Exception as e:
                debug_print(f"Fehler beim Entfernen des temporären Verzeichnisses: {e}")

        self.finished.emit()

# ------------------------------------------------------------
# Hilfsfunktion: check_destination_connection
def check_destination_connection(path, timeout=10):
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            return False
    return True

# ------------------------------------------------------------
# Kernfunktion: execute_transfer_plan
def execute_transfer_plan(plan_data):
    debug_print(f"execute_transfer_plan() gestartet: {plan_data}")
    source_path = plan_data.get("source_path", "")
    target_path = plan_data.get("target_path", "")
    move_after = plan_data.get("move_after", "")
    fault_after = plan_data.get("fault_after", "")
    use_ftp = plan_data.get("use_ftp", False)
    version_mode = plan_data.get("versioning_mode", "mirror")
    retry_count = plan_data.get("retry_count", 5)

    # Neu: optionaler Trigger (z. B. "scheduler" oder "manual"), Standard "manual"
    trigger = plan_data.get("trigger", "manual")

    results = []

    if not os.path.exists(source_path):
        msg = f"Quellverzeichnis existiert nicht: {source_path}"
        debug_print(msg)
        results.append({
            "file": source_path,
            "direction": "NONE",
            "status": "FAILED",
            "error": msg,
            "event_time_utc": _now_utc_iso(),
            "event_time_local": _now_local_iso(),
            "trigger": trigger
        })
        return results

    # ------------------------------------------------------------
    # 1) Dateiliste sammeln (rekursiv)
    # ------------------------------------------------------------
    file_list = []
    for root, dirs, files in os.walk(source_path):
        # Überspringe versteckte Ordner
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        # Falls move_after definiert und innerhalb von source_path, diesen Ordner ausschließen
        if move_after:
            abs_move_after = os.path.abspath(move_after)
            dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) != abs_move_after]
        for f in files:
            # Überspringe versteckte Dateien
            if f.startswith('.'):
                continue
            full_path = os.path.join(root, f)
            file_list.append(full_path)
    debug_print(f"Zu übertragende Dateien: {file_list}")

    # ------------------------------------------------------------
    # 2) FTP vs. Lokaler Transfer
    # ------------------------------------------------------------
    if use_ftp:
        ftp_mgr = FTPManager()
        ftp_mgr.versioning_mode = version_mode
        try:
            ftp_mgr.connect()
        except Exception as e:
            debug_print(f"FTP-Verbindung fehlgeschlagen: {e}")
            now_utc = _now_utc_iso()
            now_local = _now_local_iso()
            for fpath in file_list:
                results.append({
                    "file": fpath,
                    "direction": "UPLOAD",
                    "status": "FAILED",
                    "error": "FTP Connect Error: " + str(e),
                    "event_time_utc": now_utc,
                    "event_time_local": now_local,
                    "trigger": trigger
                })
            return results

        for local_file in file_list:
            attempts = 0
            success = False
            while attempts < retry_count and not success:
                attempts += 1
                try:
                    rel_path = os.path.relpath(local_file, source_path)
                    remote_sub = target_path.rstrip("/") + "/" + os.path.dirname(rel_path).replace("\\", "/")
                    ftp_mgr.upload_file(local_file, remote_sub)
                    results.append({
                        "file": local_file,
                        "direction": "UPLOAD",
                        "status": "SUCCESS",
                        "event_time_utc": _now_utc_iso(),
                        "event_time_local": _now_local_iso(),
                        "trigger": trigger
                    })
                    success = True
                except Exception as e:
                    debug_print(f"FTP-Upload Fehlversuch: {local_file}: {e} (Versuch {attempts}/{retry_count})")
                    if attempts >= retry_count:
                        results.append({
                            "file": local_file,
                            "direction": "UPLOAD",
                            "status": "FAILED",
                            "error": str(e),
                            "event_time_utc": _now_utc_iso(),
                            "event_time_local": _now_local_iso(),
                            "trigger": trigger
                        })
                    else:
                        time.sleep(1.0)
        ftp_mgr.disconnect()
    else:
        for local_file in file_list:
            attempts = 0
            success = False
            while attempts < retry_count and not success:
                attempts += 1
                rel_path = os.path.relpath(local_file, source_path)
                dest_dir = os.path.join(target_path, os.path.dirname(rel_path))
                os.makedirs(dest_dir, exist_ok=True)
                worker = CopyWorker([local_file], dest_dir)
                thread = QThread()
                worker.moveToThread(thread)
                worker.finished.connect(thread.quit)
                thread.started.connect(worker.run)
                thread.start()
                loop = QEventLoop()
                thread.finished.connect(loop.quit)
                loop.exec_()
                thread.wait()
                thread.deleteLater()

                dest_file = os.path.join(dest_dir, os.path.basename(local_file))
                if os.path.exists(dest_file):
                    success = True
                    results.append({
                        "file": local_file,
                        "direction": "LOCAL_COPY",
                        "status": "SUCCESS",
                        "event_time_utc": _now_utc_iso(),
                        "event_time_local": _now_local_iso(),
                        "trigger": trigger
                    })
                else:
                    debug_print(f"CopyWorker hat {local_file} nicht erfolgreich kopiert (Versuch {attempts}/{retry_count}).")
                    if attempts >= retry_count:
                        results.append({
                            "file": local_file,
                            "direction": "LOCAL_COPY",
                            "status": "FAILED",
                            "error": "CopyWorker failed",
                            "event_time_utc": _now_utc_iso(),
                            "event_time_local": _now_local_iso(),
                            "trigger": trigger
                        })
                    else:
                        time.sleep(1.0)

    # ------------------------------------------------------------
    # 3) Nach Transfer verschieben (move_after / fault_after)
    # ------------------------------------------------------------
    if move_after:
        for r in results:
            if r["status"] == "SUCCESS":
                local_file = r["file"]
                if os.path.exists(local_file):
                    rel_path = os.path.relpath(local_file, source_path)
                    new_path = os.path.join(move_after, rel_path)
                    os.makedirs(os.path.dirname(new_path), exist_ok=True
                    )
                    try:
                        shutil.move(local_file, new_path)
                    except Exception as e:
                        debug_print(f"Fehler beim Verschieben {local_file} -> {new_path}: {e}")
    if fault_after:
        for r in results:
            if r["status"] == "FAILED":
                local_file = r["file"]
                if os.path.exists(local_file):
                    rel_path = os.path.relpath(local_file, source_path)
                    fault_path = os.path.join(fault_after, rel_path)
                    os.makedirs(os.path.dirname(fault_path), exist_ok=True)
                    try:
                        shutil.move(local_file, fault_path)
                    except Exception as e:
                        debug_print(f"Fehler beim Verschieben in fault_after: {local_file} -> {fault_path}: {e}")

    # ------------------------------------------------------------
    # 4) E-Mail-Benachrichtigung
    # ------------------------------------------------------------
    ftp_temp = FTPManager()
    ftp_temp.send_transfer_summary_email(results)

    # ------------------------------------------------------------
    # 5) Logging in ftptransfer_log.json (nicht destruktiv, aber präziser)
    #    - wir behalten dein bestehendes Format bei
    #    - verwenden jetzt pro Result dessen Ereigniszeit (falls vorhanden)
    # ------------------------------------------------------------
    log_entries = []
    for r in results:
        # Fallbacks: falls event_time_* wider Erwarten leer sind
        evt_utc = r.get("event_time_utc") or _now_utc_iso()
        evt_local = r.get("event_time_local") or _now_local_iso()

        # Bewahre dein bisheriges "timestamp" Muster (nur lokale Legacy-Ansicht)
        # Wir formatieren 'timestamp' aus event_time_local, sofern vorhanden
        legacy_ts = None
        if evt_local:
            try:
                # evt_local ist ISO, wir zeigen gleich ISO weiter
                legacy_ts = evt_local.replace("T", " ")[:19]  # YYYY-MM-DD HH:MM:SS
            except Exception:
                legacy_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            legacy_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = {
            "timestamp": legacy_ts,                     # beibehaltener Legacy-Feldname
            "event_time_utc": evt_utc,                  # neu, maschinenlesbar
            "event_time_local": evt_local,              # neu, menschenlesbar
            "direction": r["direction"],
            "source": r["file"],
            "target": "FTP" if r["direction"] == "UPLOAD" else "LOCAL",
            "status": r["status"],
            "trigger": r.get("trigger", "manual")       # neu: Herkunft
        }
        if r["status"] == "FAILED":
            entry["error_message"] = r.get("error", "")
        log_entries.append(entry)

    log_path = get_ftp_transfer_log_path()
    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as lf:
                old_data = json.load(lf)
        else:
            old_data = []
        old_data.extend(log_entries)
        with open(log_path, "w", encoding="utf-8") as lf:
            json.dump(old_data, lf, indent=2)
    except Exception as e:
        debug_print(f"Fehler beim Schreiben in ftptransfer_log.json: {e}")

    debug_print("execute_transfer_plan() fertig.")
    return results