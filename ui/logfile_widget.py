#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import json
from datetime import datetime
from PySide6 import QtWidgets, QtCore, QtGui

from utils.log_manager import load_global_log, reset_global_log
# Falls du load_ftptransfer_log/reset_ftptransfer_log lieber in utils.log_manager hast, importiere sie von dort.
def load_ftptransfer_log():
    path = os.path.expanduser("~/Library/Application Support/PRisM-CC/ftptransfer_log.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def reset_ftptransfer_log():
    path = os.path.expanduser("~/Library/Application Support/PRisM-CC/ftptransfer_log.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    except:
        pass

class LogfileWidget(QtWidgets.QWidget):
    """
    Zeigt zwei Logs in Tabs:
      - Tab 1: global_log.json (Hotfolder Log) mit Filter
      - Tab 2: ftptransfer_log.json (Transfer Log) mit Filter
    Mit fester Spaltenbreite pro Spalte.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        self.all_logs = []           # Hotfolder (global_log)
        self.all_transfer_logs = []  # Transfer (ftptransfer_log)

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # QTabWidget mit 2 Tabs
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # --------------------------------------------------
        # Tab 1: Hotfolder Log
        # --------------------------------------------------
        self.tab_hotfolder = QtWidgets.QWidget()
        tab1_layout = QtWidgets.QVBoxLayout(self.tab_hotfolder)
        tab1_layout.setContentsMargins(5, 5, 5, 5)
        tab1_layout.setSpacing(5)

        # Filter (Hotfolder)
        filter_group = QtWidgets.QGroupBox("Filter (Hotfolder Log)")
        filter_layout = QtWidgets.QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(5, 5, 5, 5)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QtWidgets.QLabel("Startdatum:"))
        self.start_date_edit = QtWidgets.QDateEdit(self)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(QtCore.QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.start_date_edit)

        filter_layout.addWidget(QtWidgets.QLabel("Enddatum:"))
        self.end_date_edit = QtWidgets.QDateEdit(self)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(QtCore.QDate.currentDate())
        filter_layout.addWidget(self.end_date_edit)

        filter_layout.addWidget(QtWidgets.QLabel("Suchbegriffe:"))
        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setPlaceholderText("z.B. Max, Fehler")
        filter_layout.addWidget(self.search_edit)

        self.filter_btn = QtWidgets.QPushButton("Filtern", self)
        self.filter_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_btn)

        self.reset_btn = QtWidgets.QPushButton("Reset Log", self)
        self.reset_btn.clicked.connect(self.on_reset_log)
        filter_layout.addWidget(self.reset_btn)

        self.refresh_btn = QtWidgets.QPushButton("Refresh", self)
        self.refresh_btn.clicked.connect(self.load_logs)
        filter_layout.addWidget(self.refresh_btn)

        tab1_layout.addWidget(filter_group)

        # Tabelle Hotfolder
        self.table_hotfolder = QtWidgets.QTableWidget(self)
        self.table_hotfolder.setColumnCount(12)
        self.table_hotfolder.setHorizontalHeaderLabels([
            "ID", "Timestamp", "Filename", "Author", "Description",
            "Keywords", "Headline", "CheckType", "Status", "AppliedScript",
            "MissingLayers", "MissingMetadata"
        ])

        # --- Feste Spaltenbreite pro Spalte (Beispielwerte) ---
        self.table_hotfolder.setColumnWidth(0, 80)   # ID
        self.table_hotfolder.setColumnWidth(1, 150)  # Timestamp
        self.table_hotfolder.setColumnWidth(2, 250)  # Filename
        self.table_hotfolder.setColumnWidth(3, 100)  # Author
        self.table_hotfolder.setColumnWidth(4, 140)  # Description
        self.table_hotfolder.setColumnWidth(5, 120)  # Keywords
        self.table_hotfolder.setColumnWidth(6, 120)  # Headline
        self.table_hotfolder.setColumnWidth(7, 90)   # CheckType
        self.table_hotfolder.setColumnWidth(8, 80)   # Status
        self.table_hotfolder.setColumnWidth(9, 100)  # AppliedScript
        self.table_hotfolder.setColumnWidth(10, 130) # MissingLayers
        self.table_hotfolder.setColumnWidth(11, 130) # MissingMetadata

        tab1_layout.addWidget(self.table_hotfolder, stretch=1)

        self.export_btn = QtWidgets.QPushButton("Export CSV (Hotfolder)", self)
        self.export_btn.clicked.connect(self.export_csv_hotfolder)
        tab1_layout.addWidget(self.export_btn, alignment=QtCore.Qt.AlignRight)

        self.tab_hotfolder.setLayout(tab1_layout)
        self.tab_widget.addTab(self.tab_hotfolder, "Hotfolder Log")

        # --------------------------------------------------
        # Tab 2: Transfer Log
        # --------------------------------------------------
        self.tab_transfer = QtWidgets.QWidget()
        tab2_layout = QtWidgets.QVBoxLayout(self.tab_transfer)
        tab2_layout.setContentsMargins(5, 5, 5, 5)
        tab2_layout.setSpacing(5)

        # Filter (Transfer)
        transfer_filter_group = QtWidgets.QGroupBox("Filter (Transfer Log)")
        transfer_filter_layout = QtWidgets.QHBoxLayout(transfer_filter_group)
        transfer_filter_layout.setContentsMargins(5, 5, 5, 5)
        transfer_filter_layout.setSpacing(10)

        transfer_filter_layout.addWidget(QtWidgets.QLabel("Startdatum:"))
        self.start_date_edit_transfer = QtWidgets.QDateEdit(self)
        self.start_date_edit_transfer.setCalendarPopup(True)
        self.start_date_edit_transfer.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit_transfer.setDate(QtCore.QDate.currentDate().addMonths(-1))
        transfer_filter_layout.addWidget(self.start_date_edit_transfer)

        transfer_filter_layout.addWidget(QtWidgets.QLabel("Enddatum:"))
        self.end_date_edit_transfer = QtWidgets.QDateEdit(self)
        self.end_date_edit_transfer.setCalendarPopup(True)
        self.end_date_edit_transfer.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit_transfer.setDate(QtCore.QDate.currentDate())
        transfer_filter_layout.addWidget(self.end_date_edit_transfer)

        transfer_filter_layout.addWidget(QtWidgets.QLabel("Suchbegriffe:"))
        self.search_edit_transfer = QtWidgets.QLineEdit(self)
        self.search_edit_transfer.setPlaceholderText("z.B. Upload, FAILED")
        transfer_filter_layout.addWidget(self.search_edit_transfer)

        self.filter_transfer_btn = QtWidgets.QPushButton("Filtern (Transfer)", self)
        self.filter_transfer_btn.clicked.connect(self.apply_transfer_filter)
        transfer_filter_layout.addWidget(self.filter_transfer_btn)

        self.reset_transfer_btn = QtWidgets.QPushButton("Reset Transfer Log", self)
        self.reset_transfer_btn.clicked.connect(self.on_reset_transfer_log)
        transfer_filter_layout.addWidget(self.reset_transfer_btn)

        self.refresh_transfer_btn = QtWidgets.QPushButton("Refresh", self)
        self.refresh_transfer_btn.clicked.connect(self.load_transfer_logs)
        transfer_filter_layout.addWidget(self.refresh_transfer_btn)

        tab2_layout.addWidget(transfer_filter_group)

        # Tabelle Transfer Log
        self.table_transfer = QtWidgets.QTableWidget(self)
        self.table_transfer.setColumnCount(6)
        self.table_transfer.setHorizontalHeaderLabels([
            "Index", "Timestamp", "Direction", "Source", "Target", "Status"
        ])

        # --- Feste Spaltenbreite pro Spalte (Beispielwerte) ---
        self.table_transfer.setColumnWidth(0, 80)   # Index
        self.table_transfer.setColumnWidth(1, 150)  # Timestamp
        self.table_transfer.setColumnWidth(2, 80)   # Direction
        self.table_transfer.setColumnWidth(3, 220)  # Source
        self.table_transfer.setColumnWidth(4, 220)  # Target
        self.table_transfer.setColumnWidth(5, 80)   # Status

        tab2_layout.addWidget(self.table_transfer, stretch=1)

        self.export_transfer_btn = QtWidgets.QPushButton("Export CSV (Transfer)", self)
        self.export_transfer_btn.clicked.connect(self.export_csv_transfer)
        tab2_layout.addWidget(self.export_transfer_btn, alignment=QtCore.Qt.AlignRight)

        self.tab_transfer.setLayout(tab2_layout)
        self.tab_widget.addTab(self.tab_transfer, "Transfer Log")

        main_layout.addStretch()

        # Logs initial laden
        self.load_logs()
        self.load_transfer_logs()

    # --------------------------------------------------------
    # HOTFOLDER (global_log) - Methoden
    # --------------------------------------------------------
    def on_reset_log(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reset Log",
            "Möchten Sie das globale Log wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            reset_global_log()
            self.load_logs()
        else:
            print("Reset Log abgebrochen.")

    def load_logs(self):
        self.all_logs = load_global_log()
        self.populate_table_hotfolder(self.all_logs)

    def populate_table_hotfolder(self, log_entries):
        self.table_hotfolder.setRowCount(0)
        for entry in log_entries:
            if not isinstance(entry, dict):
                continue
            row_position = self.table_hotfolder.rowCount()
            self.table_hotfolder.insertRow(row_position)

            id_val = entry.get("id", "")
            timestamp_val = entry.get("timestamp", "")
            filename_val = entry.get("filename", "")
            metadata = entry.get("metadata", {})
            author = metadata.get("author", "")
            description = metadata.get("description", "")
            keywords = metadata.get("keywords", "")
            headline = metadata.get("headline", "")
            checkType = entry.get("checkType", "")
            status = entry.get("status", "")
            applied_script = entry.get("applied_script", "")
            details = entry.get("details", {})
            missing_layers = details.get("missingLayers", [])
            if isinstance(missing_layers, list):
                missing_layers = ", ".join(missing_layers)
            missing_meta = details.get("missingMetadata", [])
            if isinstance(missing_meta, list):
                missing_meta = ", ".join(missing_meta)

            values = [
                id_val,
                timestamp_val,
                filename_val,
                author,
                description,
                keywords,
                headline,
                checkType,
                status,
                applied_script,
                missing_layers,
                missing_meta
            ]
            for col, val in enumerate(values):
                item = QtWidgets.QTableWidgetItem(val)
                self.table_hotfolder.setItem(row_position, col, item)

    def apply_filter(self):
        filtered = []
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPyDate()
        search_text = self.search_edit.text().strip().lower()
        search_terms = [term.strip() for term in search_text.split(",") if term.strip()] if search_text else []

        for entry in self.all_logs:
            ts_str = entry.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                continue
            if not (start_date <= ts.date() <= end_date):
                continue

            entry_text = " ".join([
                entry.get("id", ""),
                ts_str,
                entry.get("filename", ""),
                entry.get("metadata", {}).get("author", ""),
                entry.get("metadata", {}).get("description", ""),
                entry.get("metadata", {}).get("keywords", ""),
                entry.get("metadata", {}).get("headline", ""),
                entry.get("checkType", ""),
                entry.get("status", ""),
                entry.get("applied_script", "")
            ]).lower()

            if search_terms and not all(term in entry_text for term in search_terms):
                continue

            filtered.append(entry)
        self.populate_table_hotfolder(filtered)

    def export_csv_hotfolder(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV exportieren (Hotfolder)", "", "CSV-Dateien (*.csv)")
        if not path:
            return

        rows = self.table_hotfolder.rowCount()
        cols = self.table_hotfolder.columnCount()
        data = []

        headers = []
        for col in range(cols):
            header = self.table_hotfolder.horizontalHeaderItem(col).text()
            headers.append(header)
        data.append(headers)

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table_hotfolder.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")
                writer.writerows(data)
            QtWidgets.QMessageBox.information(self, "Export", "CSV-Datei erfolgreich exportiert (Hotfolder).")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren (Hotfolder):\n{e}")

    # --------------------------------------------------------
    # TRANSFER (ftptransfer_log) - Methoden
    # --------------------------------------------------------
    def on_reset_transfer_log(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reset Transfer Log",
            "Möchten Sie das Transfer Log wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            reset_ftptransfer_log()
            self.load_transfer_logs()
        else:
            print("Reset Transfer Log abgebrochen.")

    def load_transfer_logs(self):
        self.all_transfer_logs = load_ftptransfer_log()
        self.populate_table_transfer(self.all_transfer_logs)

    def populate_table_transfer(self, log_entries):
        self.table_transfer.setRowCount(0)
        for entry in log_entries:
            if not isinstance(entry, dict):
                continue
            row_position = self.table_transfer.rowCount()
            self.table_transfer.insertRow(row_position)

            index_val = entry.get("index", "")
            timestamp_val = entry.get("timestamp", "")
            direction_val = entry.get("direction", "")
            source_val = entry.get("source", "")
            target_val = entry.get("target", "")
            status_val = entry.get("status", "")  # SUCCESS/FAILED

            values = [
                index_val,
                timestamp_val,
                direction_val,
                source_val,
                target_val,
                status_val
            ]
            for col, val in enumerate(values):
                item = QtWidgets.QTableWidgetItem(val)
                self.table_transfer.setItem(row_position, col, item)

    def apply_transfer_filter(self):
        filtered = []
        start_date = self.start_date_edit_transfer.date().toPython()
        end_date = self.end_date_edit_transfer.date().toPyDate()
        search_text = self.search_edit_transfer.text().strip().lower()
        search_terms = [term.strip() for term in search_text.split(",") if term.strip()] if search_text else []

        for entry in self.all_transfer_logs:
            ts_str = entry.get("timestamp", "")
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if not (start_date <= ts.date() <= end_date):
                continue

            entry_text = " ".join([
                entry.get("index", ""),
                ts_str,
                entry.get("direction", ""),
                entry.get("source", ""),
                entry.get("target", ""),
                entry.get("status", "")
            ]).lower()

            if search_terms and not all(term in entry_text for term in search_terms):
                continue

            filtered.append(entry)
        self.populate_table_transfer(filtered)

    def export_csv_transfer(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV exportieren (Transfer)", "", "CSV-Dateien (*.csv)")
        if not path:
            return

        rows = self.table_transfer.rowCount()
        cols = self.table_transfer.columnCount()
        data = []

        headers = []
        for col in range(cols):
            header = self.table_transfer.horizontalHeaderItem(col).text()
            headers.append(header)
        data.append(headers)

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table_transfer.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")
                writer.writerows(data)
            QtWidgets.QMessageBox.information(self, "Export", "CSV-Datei erfolgreich exportiert (Transfer).")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren (Transfer):\n{e}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = LogfileWidget(settings={})
    widget.show()
    sys.exit(app.exec())