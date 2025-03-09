# ui/main_window.py

import os
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Signal, Slot, QThreadPool, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QProgressBar, QProgressDialog
from PySide6.QtGui import QIcon

from ui.hotfolder_widget import HotfolderListWidget
from ui.hotfolder_config import HotfolderConfigDialog
from ui.logfile_widget import LogfileWidget

from ui.script_config_widget import ScriptConfigWidget

from ui.process_worker import ProcessWorker
from ui.settings_widget import SettingsWidget
from ui.action_set_widget import ActionSetWidget
from ui.backup_widget import BackupWidget
from ui.advanced_search_widget import AdvancedSearchWidget

from utils.config_manager import load_settings, save_settings, debug_print
from utils.log_manager import LogManager, load_global_log, reset_global_log
from utils import photoshop_controller


class MainWindow(QMainWindow):
    process_finished_signal = Signal()

    def __init__(self, config_manager=None, log_manager=None, parent=None):
        super().__init__(parent=parent)
        self.config_manager = config_manager
        self.log_manager = log_manager

        self.setWindowTitle("PRisM-RAC")
        self.setWindowIcon(QIcon("images/app_icon.png"))
        self.thread_pool = QThreadPool()
        debug_print(f"Thread pool with maxThreadCount = {self.thread_pool.maxThreadCount()}")

        self.hotfolder_list_widget = HotfolderListWidget()
        self.logfile_widget = LogfileWidget()

        # NEU: Erzeuge nun ein ScriptConfigDialog-Objekt, anstatt ScriptConfigWidget
        self.script_config_widget = ScriptConfigWidget()

        self.settings_widget = SettingsWidget()
        self.action_set_widget = ActionSetWidget()
        self.backup_widget = BackupWidget()
        self.advanced_search_widget = AdvancedSearchWidget()

        self.init_ui()
        self.setup_connections()
        self.load_ui_settings()

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_hotfolders_auto)
        self.auto_monitor_interval = 60  # Sekunden

    def init_ui(self):
        self.setMinimumSize(1200, 800)
        self.setCentralWidget(self.hotfolder_list_widget)

    def setup_connections(self):
        self.hotfolder_list_widget.process_files_signal.connect(self.on_process_files_requested)
        self.hotfolder_list_widget.open_log_signal.connect(self.show_logfile_widget)
        self.hotfolder_list_widget.open_script_config_signal.connect(self.show_script_config)
        self.hotfolder_list_widget.open_settings_signal.connect(self.show_settings)
        self.hotfolder_list_widget.open_action_set_signal.connect(self.show_action_set)
        self.hotfolder_list_widget.open_backup_signal.connect(self.show_backup_widget)
        self.hotfolder_list_widget.open_advanced_search_signal.connect(self.show_advanced_search_widget)
        self.hotfolder_list_widget.start_auto_monitor_signal.connect(self.start_auto_monitor)
        self.hotfolder_list_widget.stop_auto_monitor_signal.connect(self.stop_auto_monitor)

        self.logfile_widget.reset_log_signal.connect(self.reset_log)
        self.logfile_widget.refresh_log_signal.connect(self.refresh_log)

        # Hier nutze ich nun ScriptConfigDialog
        self.script_config_widget.save_script_config_signal.connect(self.save_script_config)
        self.script_config_widget.test_photoshop_signal.connect(self.test_photoshop_connection)

        self.settings_widget.save_settings_signal.connect(self.save_settings)

        self.action_set_widget.refresh_action_sets_signal.connect(self.refresh_action_sets)

        self.backup_widget.backup_files_signal.connect(self.on_backup_requested)
        self.advanced_search_widget.search_signal.connect(self.on_advanced_search_requested)

    def load_ui_settings(self):
        ui_settings = load_settings()
        geometry = ui_settings.get("main_window_geometry")
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))

    def save_ui_settings(self):
        ui_settings = load_settings()
        ui_settings["main_window_geometry"] = self.saveGeometry().hex()
        save_settings(ui_settings)

    def closeEvent(self, event):
        self.save_ui_settings()
        super().closeEvent(event)

    @Slot()
    def on_process_files_requested(self, hotfolder_data):
        debug_print(f"Process files requested for hotfolder: {hotfolder_data.get('name', 'Unknown')}")
        worker = ProcessWorker(hotfolder_data)
        worker.signals.finished.connect(self.on_process_finished)
        worker.signals.progress.connect(self.on_progress_update)
        self.thread_pool.start(worker)

    def on_process_finished(self):
        debug_print("Process finished!")
        self.process_finished_signal.emit()

    def on_progress_update(self, progress):
        pass

    @Slot()
    def show_logfile_widget(self):
        self.setCentralWidget(self.logfile_widget)

    @Slot()
    def show_script_config(self):
        self.setCentralWidget(self.script_config_widget)

    @Slot()
    def show_settings(self):
        self.setCentralWidget(self.settings_widget)

    @Slot()
    def show_action_set(self):
        self.setCentralWidget(self.action_set_widget)

    @Slot()
    def show_backup_widget(self):
        self.setCentralWidget(self.backup_widget)

    @Slot()
    def show_advanced_search_widget(self):
        self.setCentralWidget(self.advanced_search_widget)

    def reset_log(self):
        answer = QMessageBox.question(self, "Log zurücksetzen", "Willst du wirklich den gesamten Log löschen?")
        if answer == QMessageBox.Yes:
            reset_global_log()
            self.refresh_log()

    def refresh_log(self):
        self.logfile_widget.load_log_data()

    def save_script_config(self, script_config):
        debug_print("Speichere Script-Konfiguration...")
        if self.config_manager:
            # self.config_manager.save_something(script_config)
            pass

    def test_photoshop_connection(self):
        debug_print("Teste Verbindung zu Photoshop...")
        try:
            version = photoshop_controller.get_photoshop_version()
            QMessageBox.information(self, "Photoshop Verbindung", f"Photoshop Version: {version}")
        except Exception as e:
            QMessageBox.critical(self, "Photoshop Fehler", f"Fehler: {e}")

    def save_settings(self, settings_data):
        debug_print("Speichere Anwendungseinstellungen...")
        save_settings(settings_data)

    def refresh_action_sets(self):
        debug_print("Action Sets aktualisieren...")
        self.action_set_widget.refresh_action_sets()

    def on_backup_requested(self, backup_data):
        debug_print(f"Backup requested: {backup_data}")

    def on_advanced_search_requested(self, search_criteria):
        debug_print(f"Advanced Search requested: {search_criteria}")

    def start_auto_monitor(self, interval):
        debug_print(f"Starting auto-monitor with interval = {interval}s")
        self.auto_monitor_interval = interval
        self.monitor_timer.start(self.auto_monitor_interval * 1000)

    def stop_auto_monitor(self):
        debug_print("Stopping auto-monitor.")
        self.monitor_timer.stop()

    def monitor_hotfolders_auto(self):
        debug_print("Auto-monitor triggered.")
        hotfolders = []
        if self.config_manager:
            hotfolders = self.config_manager.get_hotfolders()

        for hf in hotfolders:
            debug_print(f"Auto-checking hotfolder: {hf.get('name')}")
            worker = ProcessWorker(hf)
            worker.signals.finished.connect(self.on_process_finished)
            worker.signals.progress.connect(self.on_progress_update)
            self.thread_pool.start(worker)