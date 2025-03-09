#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
from datetime import datetime
from PySide6 import QtWidgets, QtCore, QtGui
from utils.log_manager import load_global_log, reset_global_log
from utils.utils import debug_print

class LogfileWidget(QtWidgets.QWidget):
    """
    Zeigt das globale Logfile (global_log.json) in einer tabellarischen Ansicht an.
    Es gibt Filterfelder (Datum und Suchbegriffe), einen Button zum Export als CSV,
    einen Reset-Button und einen Refresh-Button.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings  # wird hier nicht mehr für Logs verwendet
        self.all_logs = []
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Filterbereich
        filter_group = QtWidgets.QGroupBox("Filter")
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

        main_layout.addWidget(filter_group)

        # Tabellarische Ansicht
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID", "Timestamp", "Filename", "Author", "Description",
            "Keywords", "Headline", "CheckType", "Status", "AppliedScript",
            "MissingLayers", "MissingMetadata"
        ])

        # WICHTIG: Spaltenbreite vom Nutzer änderbar machen
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        # Für horizontales Scrollen (falls die Summe der Spaltenbreiten > Widgetbreite)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_layout.addWidget(self.table, stretch=1)

        self.export_btn = QtWidgets.QPushButton("Export CSV", self)
        self.export_btn.clicked.connect(self.export_csv)
        main_layout.addWidget(self.export_btn, alignment=QtCore.Qt.AlignRight)

        self.load_logs()

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
            debug_print("Reset Log abgebrochen.")

    def load_logs(self):
        debug_print("LogfileWidget: loading logs from global_log.json...")
        self.all_logs = load_global_log()
        self.populate_table(self.all_logs)

    def populate_table(self, log_entries):
        self.table.setRowCount(0)
        for entry in log_entries:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

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
                self.table.setItem(row_position, col, item)

    def apply_filter(self):
        filtered = []
        start_date = self.start_date_edit.date().toPyDate()
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
        self.populate_table(filtered)

    def reset_filter(self):
        self.start_date_edit.setDate(QtCore.QDate.currentDate().addMonths(-1))
        self.end_date_edit.setDate(QtCore.QDate.currentDate())
        self.search_edit.clear()
        self.populate_table(self.all_logs)

    def export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV exportieren", "", "CSV-Dateien (*.csv)")
        if not path:
            return

        rows = self.table.rowCount()
        cols = self.table.columnCount()
        data = []

        headers = []
        for col in range(cols):
            header = self.table.horizontalHeaderItem(col).text()
            headers.append(header)
        data.append(headers)

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")
                writer.writerows(data)
            QtWidgets.QMessageBox.information(self, "Export", "CSV-Datei erfolgreich exportiert.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren:\n{e}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = LogfileWidget(settings={})
    widget.show()
    sys.exit(app.exec_())