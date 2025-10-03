#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import shutil
from datetime import datetime
from PySide6 import QtCore, QtWidgets, QtGui

from utils.config_manager import debug_print
from utils.ftp_manager import FTPManager

class TransferQueueDialog(QtWidgets.QDialog):
    """
    Zeigt eine Liste aller zu übertragenden Dateien mit Fortschrittsanzeige.
    Der Transfer wird asynchron in einem Worker-Thread ausgeführt.
    """
    def __init__(self, plan_data, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.setWindowTitle("Transfer Queue")
        self.resize(800, 600)

        self.worker_thread = None
        self.worker = None
        self.file_list = []
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Tabelle mit 3 Spalten: Datei, Status, Fortschritt (%)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Datei", "Status", "Fortschritt (%)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self.on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.file_list = self.collect_files()
        self.populate_table()

    def collect_files(self):
        source_path = self.plan_data.get("source_path", "")
        if not os.path.exists(source_path):
            debug_print(f"Quelle existiert nicht: {source_path}")
            return []
        file_list = []
        for root, dirs, files in os.walk(source_path):
            # Überspringe versteckte Ordner
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            # Falls move_after definiert, diesen Ordner ausschließen
            move_after = self.plan_data.get("move_after", "")
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
        return file_list

    def populate_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, fpath in enumerate(self.file_list):
            item_file = QtWidgets.QTableWidgetItem(fpath)
            item_status = QtWidgets.QTableWidgetItem("Wartet")
            progress_bar = QtWidgets.QProgressBar()
            progress_bar.setValue(0)
            self.table.setItem(row, 0, item_file)
            self.table.setItem(row, 1, item_status)
            self.table.setCellWidget(row, 2, progress_bar)

    def start_transfer(self):
        self.worker_thread = QtCore.QThread()
        self.worker = TransferQueueWorker(self.plan_data, self.file_list)
        self.worker.moveToThread(self.worker_thread)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def on_progress(self, file_path, status, percent):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == file_path:
                self.table.item(row, 1).setText(status)
                progress_bar = self.table.cellWidget(row, 2)
                if progress_bar:
                    progress_bar.setValue(percent)
                break

    def on_worker_finished(self):
        debug_print("TransferQueueDialog: Worker finished.")
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None

    def on_cancel(self):
        if self.worker:
            self.worker.request_abort()
        else:
            self.close()


class TransferQueueWorker(QtCore.QObject):
    """
    Führt den Transfer (FTP oder lokal) aus und meldet den Fortschritt.
    """
    # Signal: file_path, status, percent (0-100)
    progress = QtCore.Signal(str, str, int)
    finished = QtCore.Signal()

    def __init__(self, plan_data, file_list):
        super().__init__()
        self.plan_data = plan_data
        self.file_list = file_list
        self._abort = False

    def request_abort(self):
        self._abort = True

    def run(self):
        debug_print("TransferQueueWorker: run() gestartet.")
        source_path = self.plan_data.get("source_path", "")
        target_path = self.plan_data.get("target_path", "")
        use_ftp = self.plan_data.get("use_ftp", False)
        version_mode = self.plan_data.get("versioning_mode", "mirror")
        retry_count = self.plan_data.get("retry_count", 5)

        if use_ftp:
            self.ftp_transfer(source_path, target_path, version_mode, retry_count)
        else:
            self.local_transfer(source_path, target_path, retry_count)
        self.finished.emit()

    def ftp_transfer(self, source_path, target_path, version_mode, retry_count):
        ftp_mgr = FTPManager()
        ftp_mgr.versioning_mode = version_mode
        try:
            ftp_mgr.connect()
        except Exception as e:
            debug_print(f"FTP connect fail: {e}")
            for fpath in self.file_list:
                self.progress.emit(fpath, "FTP-Connect-Error", 0)
            return

        for local_file in self.file_list:
            if self._abort:
                self.progress.emit(local_file, "Abgebrochen", 0)
                continue
            attempts = 0
            success = False
            # Für FTP setzen wir bei Erfolg 100%
            while attempts < retry_count and not success and not self._abort:
                attempts += 1
                try:
                    rel_path = os.path.relpath(local_file, source_path)
                    remote_sub = target_path.rstrip("/") + "/" + os.path.dirname(rel_path).replace("\\", "/")
                    ftp_mgr.upload_file(local_file, remote_sub)
                    self.progress.emit(local_file, "SUCCESS", 100)
                    success = True
                except Exception as e:
                    debug_print(f"FTP upload fail: {local_file}, {e}, Versuch {attempts}/{retry_count}")
                    if attempts >= retry_count:
                        self.progress.emit(local_file, f"FAILED: {e}", 0)
                    else:
                        time.sleep(1.0)
        ftp_mgr.disconnect()

    def local_transfer(self, source_path, target_path, retry_count):
        for local_file in self.file_list:
            if self._abort:
                self.progress.emit(local_file, "Abgebrochen", 0)
                continue
            attempts = 0
            success = False
            rel_path = os.path.relpath(local_file, source_path)
            dest_dir = os.path.join(target_path, os.path.dirname(rel_path))
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, os.path.basename(local_file))
            while attempts < retry_count and not success and not self._abort:
                attempts += 1
                try:
                    self.copy_file_with_progress(local_file, dest_file)
                    if os.path.exists(dest_file):
                        self.progress.emit(local_file, "SUCCESS", 100)
                        success = True
                    else:
                        self.progress.emit(local_file, "FAILED", 0)
                except Exception as e:
                    debug_print(f"Lokaler Transfer Fehlversuch: {local_file}, {e}, Versuch {attempts}/{retry_count}")
                    if attempts >= retry_count:
                        self.progress.emit(local_file, "FAILED", 0)
                    else:
                        time.sleep(1.0)

    def copy_file_with_progress(self, src, dest):
        total_size = os.path.getsize(src)
        copied = 0
        buffer_size = 1024 * 64  # 64 KB
        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdst:
            while True:
                if self._abort:
                    raise Exception("Transfer abgebrochen")
                buf = fsrc.read(buffer_size)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                percent = int((copied / total_size) * 100)
                self.progress.emit(src, "In Progress", percent)
                # Kurze Pause, um UI-Aktualisierungen zu ermöglichen
                time.sleep(0.01)