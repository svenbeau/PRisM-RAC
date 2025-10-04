#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import socket
from PySide6 import QtWidgets, QtGui, QtCore

from utils.splash_screen import SplashScreen
from utils.config_manager import load_settings, save_settings, debug_print, load_ftp_servers

from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget
from ui.ftp_transfer_widget import FtpTransferWidget
from ui.script_recipe_list_widget import ScriptRecipeListWidget
from ui.transfer_plan_list_widget import TransferPlanListWidget

from utils.transfer_plan_config_manager import TransferPlanConfigManager
from utils.plan_scheduler import PlanScheduler, SchedulerConfig
from utils.plan_cleaner import PlanCleaner, CleanerConfig

DEBUG_OUTPUT = True


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-CC")
        self.resize(1200, 900)
        self.settings = load_settings()

        # Referenzen halten:
        self.scheduler: PlanScheduler | None = None
        self.cleaner: PlanCleaner | None = None

        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # (A) Top-Bar
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        logo_label = QtWidgets.QLabel()
        logo_paths = [
            os.path.join("assets", "logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png"),
            os.path.join(os.path.dirname(sys.executable), "assets", "logo.png"),
            os.path.join(os.path.abspath("."), "assets", "logo.png"),
        ]
        pixmap = None
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                debug_print(f"Logo gefunden unter: {logo_path}")
                pixmap = QtGui.QPixmap(logo_path)
                pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                break
        if pixmap is not None:
            logo_label.setPixmap(pixmap)
        else:
            debug_print("Logo konnte nicht gefunden werden.")
            logo_label.setText("LOGO")

        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)
        top_bar.addStretch()

        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # (B) Hauptbereich
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.script_recipe_btn = QtWidgets.QPushButton("Script › Rezept")
        self.json_editor_btn = QtWidgets.QPushButton("JSON-Editor")
        self.ftp_transfer_btn = QtWidgets.QPushButton("FTP-Transfer")
        self.plan_btn = QtWidgets.QPushButton("Transfer-Pläne")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.settings_btn = QtWidgets.QPushButton("Einstellungen")

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.script_recipe_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addWidget(self.ftp_transfer_btn)
        left_vlayout.addWidget(self.plan_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.settings_btn)
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        self.stack = QtWidgets.QStackedWidget()
        main_hlayout.addWidget(self.stack, stretch=1)

        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.script_recipe_list_widget = ScriptRecipeListWidget(self.settings, parent=self.stack)
        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.ftp_transfer_widget = FtpTransferWidget(parent=self.stack)
        self.transfer_plan_list_widget = TransferPlanListWidget(self.settings, parent=self.stack)
        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)

        self.stack.addWidget(self.hotfolder_list_widget)       # 0
        self.stack.addWidget(self.script_recipe_list_widget)   # 1
        self.stack.addWidget(self.json_explorer_widget)        # 2
        self.stack.addWidget(self.ftp_transfer_widget)         # 3
        self.stack.addWidget(self.transfer_plan_list_widget)   # 4
        self.stack.addWidget(self.logfile_widget)              # 5
        self.stack.addWidget(self.settings_widget)             # 6
        self.stack.setCurrentIndex(0)

        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.script_recipe_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.ftp_transfer_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.plan_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(5))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(6))

    def toggle_debug(self):
        from utils.config_manager import debug_print  # lokal gehalten
        global DEBUG_OUTPUT
        if self.debug_toggle_btn.isChecked():
            DEBUG_OUTPUT = True
            self.debug_toggle_btn.setText("Debug Stop")
        else:
            DEBUG_OUTPUT = False
            self.debug_toggle_btn.setText("Debug Start")
        debug_print(f"DEBUG_OUTPUT={DEBUG_OUTPUT}")

    def closeEvent(self, event):
        """
        Sicherer Stop der Worker-Threads VOR dem App-Teardown.
        (Nur hier stoppen; keinen zusätzlichen aboutToQuit-Fallback -> vermeidet doppelte Stop-Logs.)
        """
        try:
            if self.scheduler is not None:
                try:
                    self.scheduler.stop()
                except Exception:
                    pass
                # falls verfügbar, zusätzlich warten
                if hasattr(self.scheduler, "wait"):
                    try:
                        self.scheduler.wait(5000)
                    except Exception:
                        pass
        finally:
            pass

        try:
            if self.cleaner is not None:
                try:
                    # unsere PlanCleaner-API nutzt .stop() ohne Parameter
                    self.cleaner.stop()
                except Exception:
                    pass
                if hasattr(self.cleaner, "wait"):
                    try:
                        self.cleaner.wait(7000)
                    except Exception:
                        pass
        finally:
            pass

        save_settings(self.settings)
        super().closeEvent(event)


def run():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("PRisM-RAC")

    # Splash
    splash = SplashScreen(app)
    splash.show()
    for i in range(0, 101, 20):
        splash.update_progress(f"Starte PRisM-RAC... {i}%", i)
        app.processEvents()

    # Hauptfenster
    main_window = MainWindow()

    # ---------- Transfer-Plan Infrastruktur ----------
    cm = TransferPlanConfigManager()

    # Reachability/VPN-Precheck (nur für FTP/SFTP)
    def vpn_precheck(plan: dict) -> bool:
        if not plan.get("use_ftp"):
            return True
        server_name = plan.get("ftp_server", "")
        host, port, proto = None, None, "ftp"
        for s in load_ftp_servers():
            if s.get("name") == server_name:
                host = s.get("host")
                proto = (s.get("protocol") or "ftp").lower()
                port = int(s.get("port", 21))
                if proto == "sftp":
                    port = 22
                break
        if not host or not port:
            return False
        try:
            with socket.create_connection((host, port), timeout=2.5):
                return True
        except Exception:
            debug_print("[Scheduler] Precheck: Server nicht erreichbar (VPN/Netz?) – überspringe Tick.")
            return False

    # ---------- Scheduler ----------
    scheduler = PlanScheduler(
        config_manager=cm,
        precheck=vpn_precheck,
        config=SchedulerConfig(
            scan_interval_ms=30_000,
            once_guard_window_s=90,
            retry_count=1,
            retry_backoff_s=5,
            connect_timeout_s=20,
        ),
    )
    # Wichtig: KEIN sig_log → debug_print, um doppelte Start/Logzeilen zu vermeiden.
    # scheduler.sig_log.connect(lambda msg: debug_print(msg))
    scheduler.sig_plan_started.connect(lambda pid, name: debug_print(f"[Scheduler] Start: {name} ({pid})"))
    scheduler.sig_plan_finished.connect(
        lambda pid, ok, msg: debug_print(f"[Scheduler] Ende ({'OK' if ok else 'FAIL'}): {pid} – {msg}")
    )
    scheduler.start()
    main_window.scheduler = scheduler

    # ---------- Cleaner ----------
    cleaner = PlanCleaner(
        config=CleanerConfig(
            interval_ms=10 * 60 * 1000,
            remove_empty_dirs=True,
            follow_symlinks=False,
            dry_run=False,
        ),
        config_manager=cm,
    )
    cleaner.sig_log.connect(lambda msg: debug_print(msg))
    cleaner.sig_error.connect(lambda msg: debug_print(msg))
    cleaner.sig_deleted.connect(lambda path: debug_print(f"[Cleaner] Gelöscht: {path}"))
    # optional: Gate-Badge/Status
    # cleaner.sig_gate_changed.connect(lambda is_open: debug_print(f"[Cleaner] Gate {'aktiv' if is_open else 'inaktiv'}"))
    cleaner.start()
    main_window.cleaner = cleaner

    splash.finish(main_window)
    main_window.show()
    return app.exec()


# wrapper.py kompatibel halten
run = run

if __name__ == "__main__":
    sys.exit(run())