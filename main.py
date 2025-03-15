#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6 import QtWidgets, QtGui, QtCore

from utils.config_manager import load_settings, save_settings, debug_print
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget
from ui.ftp_transfer_widget import FtpTransferWidget
from ui.script_recipe_list_widget import ScriptRecipeListWidget

# NEU: TransferPlanListWidget
from ui.transfer_plan_list_widget import TransferPlanListWidget

# NEU: Wir benötigen den Executor + PlanConfigManager
from transfer_executor import execute_transfer_plan
from utils.transfer_plan_config_manager import TransferPlanConfigManager

from datetime import datetime, timedelta

DEBUG_OUTPUT = True


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-CC")
        self.resize(1200, 900)
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        # Haupt-Widget + Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # (A) Obere Leiste: Logo links, Debug-Button rechts
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

        # (B) Hauptbereich (horizontal): Links Buttons, rechts StackedWidget
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

        # NEU: Transfer-Pläne
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

        # Widget 0: Hotfolder
        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.hotfolder_list_widget)

        # Widget 1: ScriptRecipeListWidget
        self.script_recipe_list_widget = ScriptRecipeListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.script_recipe_list_widget)

        # Widget 2: JSON-Editor
        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.json_explorer_widget)

        # Widget 3: Einstellungen
        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.settings_widget)

        # Widget 4: FTP-Transfer
        self.ftp_transfer_widget = FtpTransferWidget(parent=self.stack)
        self.stack.addWidget(self.ftp_transfer_widget)

        # Widget 5: Logfile
        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.logfile_widget)

        # NEU: Widget 6: Transfer-Pläne
        self.transfer_plan_list_widget = TransferPlanListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.transfer_plan_list_widget)

        # Standard: Hotfolder (Index 0)
        self.stack.setCurrentIndex(0)

        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.script_recipe_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.ftp_transfer_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(5))
        self.plan_btn.clicked.connect(lambda: self.stack.setCurrentIndex(6))

        # NEU: Scheduler alle 60 Sekunden
        self.schedule_timer = QtCore.QTimer(self)
        self.schedule_timer.setInterval(60000)  # 1 Minute
        self.schedule_timer.timeout.connect(self.check_scheduled_transfers)
        self.schedule_timer.start()

    def check_scheduled_transfers(self):
        """
        Lädt die transfer_plans.json, sucht nach fälligen Terminen und
        führt die Pläne aus. Danach wird schedule_time hochgesetzt
        (z.B. bei daily: +1 Tag).
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
                # Ungültiges Datumsformat
                continue

            if plan_dt <= now_dt:
                debug_print(f"Plan fällig: {plan.get('name', '(ohne Name)')}")
                # Ausführen, wenn (once) noch nicht ausgeführt oder if daily/weekly
                # Du könntest z.B. auch "once_executed" Flag setzen,
                # wenn du "once" nach erstem Durchlauf nie mehr ausführen willst.

                try:
                    execute_transfer_plan(plan)
                except Exception as e:
                    debug_print(f"Fehler bei check_scheduled_transfers -> execute_transfer_plan: {e}")

                # Nächsten Termin berechnen
                if schedule_type == "daily":
                    new_dt = plan_dt + timedelta(days=1)
                    plan["schedule_time"] = new_dt.strftime("%Y-%m-%d %H:%M")
                elif schedule_type == "weekly":
                    new_dt = plan_dt + timedelta(days=7)
                    plan["schedule_time"] = new_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    # once => optional "disable" oder rausnehmen
                    # Hier machen wir nix, wenn du's so willst
                    pass

                # Speichern
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