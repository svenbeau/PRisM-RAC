#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from PySide6 import QtWidgets, QtCore, QtGui
from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager
from ui.transfer_plan_dialog import TransferPlanDialog


def resource_path(relative_path):
    """Gibt den absoluten Pfad zur Ressource zurück – funktioniert im Entwicklungsmodus und im PyInstaller-Bundle."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class TransferPlanWidget(QtWidgets.QFrame):
    def __init__(self, plan_data: dict, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.body_visible = plan_data.get("body_visible", False)

        self.icon_expand = QtGui.QIcon(resource_path("assets/dropdown_list.png"))
        self.icon_collapse = QtGui.QIcon(resource_path("assets/close_list.png"))
        self.setup_ui()

    # ---------------------------------------------------------------
    # UI Aufbau
    # ---------------------------------------------------------------
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

        # Subheader (hellgrauer Balken)
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

        # Body (sichtbar/unsichtbar)
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        # GroupBox für Details
        self.config_group = QtWidgets.QGroupBox("Details")
        self.config_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        cfg_layout = QtWidgets.QVBoxLayout(self.config_group)

        row = 0
        self.lbl_src = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_src)
        self.lbl_tgt = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_tgt)
        self.lbl_ftp = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_ftp)
        self.lbl_ver = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_ver)
        self.lbl_sched = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_sched)
        self.lbl_move = self.create_label("", row); row += 1
        cfg_layout.addWidget(self.lbl_move)

        self.config_group.setLayout(cfg_layout)
        body_layout.addWidget(self.config_group)
        self.body_widget.setLayout(body_layout)
        main_layout.addWidget(self.body_widget)

        # Button-Leiste (Bearbeiten / Jetzt ausführen)
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

        main_layout.addWidget(self.button_bar)

        self.body_widget.setVisible(self.body_visible)
        self.update_labels()

    # ---------------------------------------------------------------
    # Hilfsfunktionen
    # ---------------------------------------------------------------
    def create_label(self, text, row_index):
        lbl = QtWidgets.QLabel(text)
        lbl.setMinimumHeight(24)
        lbl.setStyleSheet(f"""
            color: #000000;
            padding: 4px;
            background-color: {'#f7f7f7' if row_index % 2 == 0 else '#e5e5e5'};
        """)
        return lbl

    # ---------------------------------------------------------------
    # Events
    # ---------------------------------------------------------------
    def on_toggle_body(self):
        self.body_visible = not self.body_visible
        self.body_widget.setVisible(self.body_visible)
        self.toggle_btn.setIcon(self.icon_collapse if self.body_visible else self.icon_expand)
        self.plan_data["body_visible"] = self.body_visible
        mgr = TransferPlanConfigManager()
        mgr.update_plan(self.plan_data["id"], self.plan_data)

    def on_edit(self):
        """Öffnet den Bearbeitungsdialog, robust gegen alte Signaturen."""
        try:
            dlg = TransferPlanDialog(self.plan_data, parent=self)
        except TypeError as e:
            debug_print(f"[TransferPlanWidget] Dialog-Init ohne manager fehlgeschlagen: {e} -> Fallback")
            try:
                dlg = TransferPlanDialog(self.plan_data, None, self)
            except TypeError as e2:
                QtWidgets.QMessageBox.critical(self, "Fehler", f"Dialog konnte nicht geöffnet werden:\n{e2}")
                return

        exec_method = getattr(dlg, "exec_", None)
        if callable(exec_method):
            result = dlg.exec_()
        else:
            result = dlg.exec()

        if result == QtWidgets.QDialog.Accepted:
            debug_print("TransferPlan geändert, update and reload.")
            mgr = TransferPlanConfigManager()
            mgr.update_plan(self.plan_data["id"], self.plan_data)

            parent_widget = self.parent()
            while parent_widget and not hasattr(parent_widget, "load_plans"):
                parent_widget = parent_widget.parent()
            if parent_widget and hasattr(parent_widget, "load_plans"):
                parent_widget.load_plans()
        else:
            debug_print("TransferPlan-Dialog abgebrochen.")

    # ---------------------------------------------------------------
    # Neuer Codeblock: Plan frisch laden vor manuellem Start
    # ---------------------------------------------------------------
    def on_run_now(self):
        """Startet den Transfer mit der aktuellen gespeicherten Planversion."""
        plan_id = self.plan_data.get("id")
        debug_print(f"TransferPlanWidget: on_run_now() => Starte Transfer für Plan-ID {plan_id}")

        cm = TransferPlanConfigManager()
        fresh_plan = cm.get_plan(plan_id) if hasattr(cm, "get_plan") else None
        if not fresh_plan:
            debug_print("[TransferPlanWidget] Kein aktueller Plan gefunden – verwende lokalen Snapshot.")
            fresh_plan = self.plan_data

        # Dialog anzeigen und Transfer starten
        from ui.transfer_queue_dialog import TransferQueueDialog
        dlg = TransferQueueDialog(fresh_plan, parent=self)
        dlg.show()
        dlg.start_transfer()

    # ---------------------------------------------------------------
    # Label Update
    # ---------------------------------------------------------------
    def update_labels(self):
        debug_print("TransferPlanWidget.update_labels()")
        self.title_label.setText(self.plan_data.get("name", "Unbenannt"))

        src = self.plan_data.get("source_path", "")
        tgt = self.plan_data.get("target_path", "")

        def get_last_n_components(path, n):
            norm = os.path.normpath(path)
            parts = norm.split(os.sep)
            if len(parts) < n:
                return norm
            return os.sep.join(parts[-n:])

        sub_depth = 2
        src_sub = get_last_n_components(src, sub_depth) if src else "(none)"
        tgt_sub = get_last_n_components(tgt, sub_depth) if tgt else "(none)"
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
        self.lbl_ver.setText(f"Versionierung: {version_mode} (Suffix={suffix_fmt})")

        schedule_type = self.plan_data.get("schedule_type", "once")
        schedule_time = self.plan_data.get("schedule_time", "(none)")
        self.lbl_sched.setText(f"Zeitplan: {schedule_type} @ {schedule_time}")

        move_after = self.plan_data.get("move_after", "(none)")
        self.lbl_move.setText(f"Nach Transfer verschieben: {move_after}")