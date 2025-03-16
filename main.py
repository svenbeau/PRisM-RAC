#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6 import QtWidgets, QtGui, QtCore
from datetime import datetime, timedelta

from utils.config_manager import load_settings, save_settings, debug_print
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget
from ui.ftp_transfer_widget import FtpTransferWidget
from ui.script_recipe_list_widget import ScriptRecipeListWidget

# TransferPlanListWidget
from ui.transfer_plan_list_widget import TransferPlanListWidget

# Executor + PlanConfigManager
from utils.transfer_executor import execute_transfer_plan
from utils.transfer_plan_config_manager import TransferPlanConfigManager

DEBUG_OUTPUT = True

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-CC")
        self.resize(1200, 900)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # (A) Obere Leiste: Logo + Debug-Button
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        logo_label = QtWidgets.QLabel()
        logo_paths = [
            os.path.join("assets", "logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png"),
            os.path.join(os.path.dirname(sys.executable), "assets", "logo.png"),
            os.path.join(os.path.abspath("."), "assets", "logo.png"),
        ]
        logo_found = False
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                debug_print(f"Logo gefunden unter: {logo_path}")
                pixmap = QtGui.QPixmap(logo_path)
                pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                logo_found = True
                break
        if not logo_found:
            debug_print("Logo konnte nicht gefunden werden. Gesuchte Pfade:")
            for path in logo_paths:
                debug_print(f" - {path}")
            logo_label.setText("LOGO")

        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)
        top_bar.addStretch()

        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # (B) Hauptbereich: Links Buttons, Rechts StackedWidget
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.script_recipe_btn = QtWidgets.QPushButton("Script › Rezept")
        self.json_editor_btn = QtWidgets.QPushButton("JSON-Editor")
        self.settings_btn = QtWidgets.QPushButton("Einstellungen")
        self.ftp_transfer_btn = QtWidgets.QPushButton("FTP-Transfer")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.plan_btn = QtWidgets.QPushButton("Transfer-Pläne")

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.script_recipe_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addWidget(self.settings_btn)
        left_vlayout.addWidget(self.ftp_transfer_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.plan_btn)
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        self.stack = QtWidgets.QStackedWidget()
        main_hlayout.addWidget(self.stack, stretch=1)

        # Versch. Widgets registrieren
        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.hotfolder_list_widget)

        self.script_recipe_list_widget = ScriptRecipeListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.script_recipe_list_widget)

        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.json_explorer_widget)

        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.settings_widget)

        self.ftp_transfer_widget = FtpTransferWidget(parent=self.stack)
        self.stack.addWidget(self.ftp_transfer_widget)

        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.logfile_widget)

        # NEU: Transfer-Pläne
        self.transfer_plan_list_widget = TransferPlanListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.transfer_plan_list_widget)

        self.stack.setCurrentIndex(0)

        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.script_recipe_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.ftp_transfer_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(5))
        self.plan_btn.clicked.connect(lambda: self.stack.setCurrentIndex(6))

        # (C) Scheduler einrichten: Alle 60 Sekunden wird die Methode check_scheduled_transfers() aufgerufen.
        self.schedule_timer = QtCore.QTimer(self)
        self.schedule_timer.setInterval(60000)  # alle 60 Sekunden
        self.schedule_timer.timeout.connect(self.check_scheduled_transfers)
        self.schedule_timer.start()

    def check_scheduled_transfers(self):
        """
        Prüft jede Minute, ob ein Plan fällig ist.
        Wir erlauben ein Toleranzfenster von 60 Sekunden.
        Wenn die aktuelle Zeit innerhalb dieses Fensters liegt (>= plan_dt und < plan_dt+60s),
        wird der Plan ausgeführt und bei daily/weekly der nächste Termin gesetzt.
        """
        debug_print("check_scheduled_transfers() aufgerufen.")
        mgr = TransferPlanConfigManager()
        plans = mgr.get_plans()
        now_dt = datetime.now()

        for plan in plans:
            schedule_type = plan.get("schedule_type", "once")
            schedule_time_str = plan.get("schedule_time", "")
            if not schedule_time_str:
                continue

            try:
                plan_dt = datetime.strptime(schedule_time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue

            # Toleranzfenster: Wenn now_dt >= plan_dt und now_dt < plan_dt + 60 Sekunden
            if plan_dt <= now_dt < (plan_dt + timedelta(seconds=60)):
                debug_print(f"Plan fällig: {plan.get('name', '(ohne Name)')}")
                try:
                    execute_transfer_plan(plan)
                except Exception as e:
                    debug_print(f"Fehler bei check_scheduled_transfers -> execute_transfer_plan: {e}")

                # Aktualisiere schedule_time, falls daily oder weekly
                if schedule_type == "daily":
                    new_dt = plan_dt + timedelta(days=1)
                    plan["schedule_time"] = new_dt.strftime("%Y-%m-%d %H:%M")
                elif schedule_type == "weekly":
                    new_dt = plan_dt + timedelta(days=7)
                    plan["schedule_time"] = new_dt.strftime("%Y-%m-%d %H:%M")
                # Bei "once" wird nichts geändert

                mgr.update_plan(plan["id"], plan)

    def toggle_debug(self):
        global DEBUG_OUTPUT
        if self.debug_toggle_btn.isChecked():
            DEBUG_OUTPUT = True
            self.debug_toggle_btn.setText("Debug Stop")
        else:
            DEBUG_OUTPUT = False
            self.debug_toggle_btn.setText("Debug Start")
        debug_print(f"DEBUG_OUTPUT={DEBUG_OUTPUT}")

    def closeEvent(self, event):
        save_settings(self.settings)
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()