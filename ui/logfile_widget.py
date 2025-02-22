#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import datetime
from PyQt5 import QtWidgets, QtCore
from config.config_manager import save_settings, debug_print

class LogfileWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Tabelle
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nr.", "Zeit", "Caption", "Datei", "JSX"])
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.export_btn = QtWidgets.QPushButton("Export CSV")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.export_btn.clicked.connect(self.export_csv)
        self.reset_btn.clicked.connect(self.reset_log)

        self.load_log_entries()

    def load_log_entries(self):
        # log_entries: [{"nr":1, "time":"...", "caption":"...", "file":"...", "jsx":"..."}]
        log_entries = self.settings.setdefault("log_entries", [])
        self.table.setRowCount(len(log_entries))
        for row_idx, entry in enumerate(log_entries):
            self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(entry.get("nr",""))))
            self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(entry.get("time","")))
            self.table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(entry.get("caption","")))
            self.table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(entry.get("file","")))
            self.table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(entry.get("jsx","")))

    def export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        log_entries = self.settings.get("log_entries", [])
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Nr.", "Zeit", "Caption", "Datei", "JSX"])
                for e in log_entries:
                    writer.writerow([e.get("nr",""), e.get("time",""), e.get("caption",""), e.get("file",""), e.get("jsx","")])
            QtWidgets.QMessageBox.information(self, "Export", "CSV exportiert.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def reset_log(self):
        confirm = QtWidgets.QMessageBox.question(self, "Reset", "Wirklich Log-Einträge löschen?")
        if confirm == QtWidgets.QMessageBox.Yes:
            self.settings["log_entries"] = []
            save_settings(self.settings)
            self.load_log_entries()

    def add_log_entry(self, caption, file, jsx):
        # Füge einen neuen Log-Eintrag hinzu
        log_entries = self.settings.setdefault("log_entries", [])
        nr = len(log_entries) + 1
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "nr": nr,
            "time": now_str,
            "caption": caption,
            "file": file,
            "jsx": jsx
        }
        log_entries.append(entry)
        save_settings(self.settings)
        self.load_log_entries()