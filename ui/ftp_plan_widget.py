#!/usr/bin/env python3
# ftp_plan_widget.py
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime
from typing import Optional, Dict, List
from PySide6 import QtWidgets, QtCore, QtGui

from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager
from ui.transfer_plan_dialog import TransferPlanDialog
from ui.transfer_queue_dialog import TransferQueueDialog


def resource_path(relative_path):
    """Gibt den absoluten Pfad zur Ressource zurück – funktioniert im Entwicklungsmodus und im PyInstaller-Bundle."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class TransferPlanWidget(QtWidgets.QFrame):
    """
    Collapsible Anzeige eines Transferplans (Design aus stable-v42).

    Änderungen:
      - KEINE eingebauten Status/Queue-Elemente mehr.
      - "Jetzt ausführen" startet sofort den Transfer und
        leitet Ereignisse via Signale an den übergeordneten List-Container weiter.
    """

    # ---------- Signale nach oben (List-Widget) ----------
    sig_log = QtCore.Signal(str)
    # Liste von Items (je Datei): {"key", "direction", "file", "destination"}
    sig_transfer_init = QtCore.Signal(list)
    sig_transfer_progress = QtCore.Signal(str, str, int)   # key, status, percent
    sig_transfer_finished = QtCore.Signal()

    ROLE_KEY = QtCore.Qt.UserRole + 100  # (interne Rolle, falls gebraucht)

    def __init__(self, plan_data: dict, parent=None):
        super().__init__(parent)
        self.plan_data = dict(plan_data or {})
        self.body_visible = self.plan_data.get("body_visible", False)

        self.icon_expand = QtGui.QIcon(resource_path("assets/dropdown_list.png"))
        self.icon_collapse = QtGui.QIcon(resource_path("assets/close_list.png"))

        # Laufzeitobjekt für manuellen Run
        self._queue_dialog: Optional[TransferQueueDialog] = None

        self.setup_ui()
        self.update_labels()

    # ---------------- UI ----------------
    def setup_ui(self):
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Titelzeile (grauer Balken)
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("background-color: #2b2b2b;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        self.title_label = QtWidgets.QLabel(self.plan_data.get("name", "Unbenannt"))
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(self.title_label, 1, QtCore.Qt.AlignVCenter)

        self.toggle_btn = QtWidgets.QPushButton()
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setIcon(self.icon_collapse if self.body_visible else self.icon_expand)
        self.toggle_btn.clicked.connect(self.on_toggle_body)
        title_layout.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.title_bar)

        # Subheader (dunkler Balken darunter)
        self.subheader_frame = QtWidgets.QFrame()
        self.subheader_frame.setFixedHeight(30)
        self.subheader_frame.setStyleSheet("background-color: #b0b0b0;")
        subheader_layout = QtWidgets.QHBoxLayout(self.subheader_frame)
        subheader_layout.setContentsMargins(10, 5, 10, 5)
        subheader_layout.setSpacing(0)

        self.subheader_label = QtWidgets.QLabel("...")
        self.subheader_label.setStyleSheet("color: #000000; font-weight: bold;")
        subheader_layout.addWidget(self.subheader_label, 1, QtCore.Qt.AlignLeft)
        main_layout.addWidget(self.subheader_frame)

        # Body
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        # Details-Group
        self.config_group = QtWidgets.QGroupBox("Details")
        self.config_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        cfg_layout = QtWidgets.QVBoxLayout(self.config_group)
        row = 0
        self.lbl_src  = self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_src)
        self.lbl_tgt  = self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_tgt)
        self.lbl_ftp  = self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_ftp)
        self.lbl_ver  = self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_ver)
        self.lbl_sched= self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_sched)
        self.lbl_move = self._create_row_label("", row); row += 1; cfg_layout.addWidget(self.lbl_move)
        self.config_group.setLayout(cfg_layout)
        body_layout.addWidget(self.config_group)

        # Button-Leiste
        self.button_bar = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(self.button_bar)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        button_layout.addStretch()

        self.edit_btn = QtWidgets.QPushButton("Bearbeiten")
        self.edit_btn.clicked.connect(self.on_edit)
        button_layout.addWidget(self.edit_btn)

        self.run_btn = QtWidgets.QPushButton("Jetzt ausführen")
        self.run_btn.clicked.connect(self.on_run_now)
        button_layout.addWidget(self.run_btn)

        body_layout.addWidget(self.button_bar)

        self.body_widget.setLayout(body_layout)
        main_layout.addWidget(self.body_widget)

        # Startzustand
        self.body_widget.setVisible(self.body_visible)
        self._log("Bereit.")

    # ---------------- kleine Helfer ----------------
    def _create_row_label(self, text, row_index):
        lbl = QtWidgets.QLabel(text)
        lbl.setMinimumHeight(24)
        lbl.setStyleSheet(f"""
            color: #000000;
            padding: 4px;
            background-color: {'#f7f7f7' if row_index % 2 == 0 else '#e5e5e5'};
        """)
        return lbl

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        debug_print(line)
        self.sig_log.emit(line)

    # ---------------- Verhalten ----------------
    def on_toggle_body(self):
        self.body_visible = not self.body_visible
        self.body_widget.setVisible(self.body_visible)
        self.toggle_btn.setIcon(self.icon_collapse if self.body_visible else self.icon_expand)
        self.plan_data["body_visible"] = self.body_visible
        mgr = TransferPlanConfigManager()
        mgr.update_plan(self.plan_data["id"], self.plan_data)

    def on_edit(self):
        try:
            dlg = TransferPlanDialog(self.plan_data, parent=self)
        except TypeError as e:
            debug_print(f"[TransferPlanWidget] Dialog-Init ohne manager fehlgeschlagen: {e} -> Fallback mit manager=None")
            try:
                dlg = TransferPlanDialog(self.plan_data, None, self)
            except TypeError as e2:
                debug_print(f"[TransferPlanWidget] Dialog-Init mit manager=None fehlgeschlagen: {e2}")
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Dialog konnte nicht geöffnet werden:\n{e2}")
                return

        exec_method = getattr(dlg, "exec_", None)
        result = exec_method() if callable(exec_method) else dlg.exec()

        if result == QtWidgets.QDialog.Accepted:
            debug_print("TransferPlan geändert, update and reload.")
            mgr = TransferPlanConfigManager()
            mgr.update_plan(self.plan_data["id"], self.plan_data)

            parent_widget = self.parent()
            while parent_widget and not hasattr(parent_widget, "load_plans"):
                parent_widget = parent_widget.parent()
            if parent_widget and hasattr(parent_widget, "load_plans"):
                parent_widget.load_plans()

    def on_run_now(self):
        """
        Manuelle Ausführung dieses Plans:
          - Öffnet TransferQueueDialog (non-modal).
          - Leitet Worker-Ereignisse per Signal an das List-Widget weiter.
        """
        plan_name = self.plan_data.get("name", "Unbenannt")
        self._log(f"Manueller Start für Plan '{plan_name}' …")

        dlg = TransferQueueDialog(self.plan_data, parent=self)
        self._queue_dialog = dlg

        # Initiale Queue-Items an ListWidget senden
        init_items: List[Dict[str, str]] = []
        for entry in dlg.file_list:
            if entry["mode"] == "local_src":
                key = entry["src_path"]
                direction = "UPLOAD" if self.plan_data.get("use_ftp", False) else "COPY"
                file_disp = entry["src_path"]
            else:
                key = f"{entry['src_server']}:{entry['src_remote']}"
                direction = "DOWNLOAD" if not self.plan_data.get("use_ftp", False) else "RELAY"
                file_disp = entry["src_remote"]
            dest = entry.get("dest_hint", "")
            init_items.append({
                "key": key,
                "direction": direction,
                "file": file_disp,
                "destination": dest
            })
        self.sig_transfer_init.emit(init_items)

        # Worker-Signale nach oben durchreichen
        def after_started():
            try:
                if dlg.worker:
                    dlg.worker.progress.connect(self._forward_progress, QtCore.Qt.QueuedConnection)
                    dlg.finished.connect(self._forward_finished, QtCore.Qt.QueuedConnection)
                else:
                    self._log("Hinweis: Kein Worker verfügbar (keine Dateien?).")
            except Exception as e:
                self._log(f"Progress-Hook fehlgeschlagen: {e}")

        dlg.setWindowModality(QtCore.Qt.NonModal)
        dlg.show()
        dlg.start_transfer()
        QtCore.QTimer.singleShot(0, after_started)

    @QtCore.Slot(str, str, int)
    def _forward_progress(self, key: str, status: str, percent: int):
        self.sig_transfer_progress.emit(key, status, percent)
        # zusätzlich Logzeile
        self._log(f"{status}: {key} ({percent}%)")

    @QtCore.Slot()
    def _forward_finished(self):
        self._log("Transfer abgeschlossen.")
        self.sig_transfer_finished.emit()

    # ---------------- label updates ----------------
    def update_labels(self):
        debug_print("TransferPlanWidget.update_labels()")
        self.title_label.setText(self.plan_data.get("name", "Unbenannt"))

        src = self.plan_data.get("source_path", "")
        tgt = self.plan_data.get("target_path", "")

        def get_last_n_components(path, n):
            norm = os.path.normpath(path)
            components = norm.split(os.sep)
            if len(components) < n:
                return norm
            return os.sep.join(components[-n:])

        subheader_depth = 2
        src_sub = get_last_n_components(src, subheader_depth) if src else "(none)"
        tgt_sub = get_last_n_components(tgt, subheader_depth) if tgt else "(none)"
        self.subheader_label.setText(f"{src_sub} -> {tgt_sub}")

        self.lbl_src.setText(f"Quellordner: {src or '(none)'}")
        self.lbl_tgt.setText(f"Zielordner: {tgt or '(none)'}")

        if self.plan_data.get("use_ftp"):
            ftp_server = self.plan_data.get("ftp_server", "")
            ftp_str = f"FTP-Server: {ftp_server}"
        else:
            ftp_str = "Lokal (kein FTP)"
        self.lbl_ftp.setText(ftp_str)

        version_mode = self.plan_data.get("versioning_mode", "mirror")
        suffix_fmt = self.plan_data.get("suffix_format", "_v{n}")
        version_str = f"Versionierung: {version_mode} (Suffix={suffix_fmt})"
        self.lbl_ver.setText(version_str)

        schedule_type = self.plan_data.get("schedule_type", "once")
        schedule_time = self.plan_data.get("schedule_time", "(none)")
        sched_str = f"Zeitplan: {schedule_type} @ {schedule_time}"
        self.lbl_sched.setText(sched_str)

        move_after = self.plan_data.get("move_after", "(none)")
        move_str = f"Nach Transfer verschieben: {move_after}"
        self.lbl_move.setText(move_str)