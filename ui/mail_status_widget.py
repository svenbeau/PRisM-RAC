#!/usr/bin/env python3
# ui/mail_status_widget.py
# -*- coding: utf-8 -*-

import os
import json
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView
)

# --- robuster Import mit Fallback auf Standardpfad ---
try:
    from utils.config_manager import get_mail_transfer_info_path, debug_print
    _HAS_GET_PATH = True
except Exception:
    _HAS_GET_PATH = False
    def debug_print(*_args, **_kwargs):  # weiches Fallback
        pass
# -----------------------------------------------------


class MailStatusWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("MailStatusWidget")
        self.setWindowTitle("Mail-Status (Scheduler)")

        # Pfad ermitteln (Fallback, falls get_mail_transfer_info_path nicht vorhanden)
        if _HAS_GET_PATH:
            self.info_path = get_mail_transfer_info_path()
        else:
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PRisM-CC")
            self.info_path = os.path.join(base, "mail_transfer_info.json")

        self.info_dir = os.path.dirname(self.info_path)

        # --- UI ---
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Header mit Buttons
        header = QHBoxLayout()
        self.lbl_path = QLabel(self.info_path)
        self.lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.addWidget(self.lbl_path, 1)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_open = QPushButton("Datei öffnen")
        self.btn_copy = QPushButton("Pfad kopieren")
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_open)
        header.addWidget(self.btn_copy)
        root.addLayout(header)

        # Mail-Metadaten
        meta_group = QGroupBox("Mail-Metadaten")
        meta_layout = QGridLayout(meta_group)
        meta_layout.setContentsMargins(8, 8, 8, 8)

        r = 0
        self.v_enabled = self._add_kv(meta_layout, r, "Enabled"); r += 1
        self.v_host = self._add_kv(meta_layout, r, "Host"); r += 1
        self.v_port = self._add_kv(meta_layout, r, "Port"); r += 1
        self.v_user_present = self._add_kv(meta_layout, r, "User vorhanden"); r += 1
        self.v_notify_present = self._add_kv(meta_layout, r, "Notify-Email vorhanden"); r += 1
        self.v_mode = self._add_kv(meta_layout, r, "Modus (SSL/STARTTLS/PLAIN)"); r += 1
        self.v_attempted = self._add_kv(meta_layout, r, "Attempted (UTC)"); r += 1

        # Ergebnis mit farbigem Label
        self.lbl_result_key = QLabel("Result")
        self.lbl_result_val = QLabel("-")
        self.lbl_result_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        meta_layout.addWidget(self.lbl_result_key, r, 0)
        meta_layout.addWidget(self.lbl_result_val, r, 1); r += 1

        # Fehlertext
        self.v_error = self._add_kv(meta_layout, r, "Fehler"); r += 1

        root.addWidget(meta_group)

        # Zusammenfassung & Tabelle
        summary_group = QGroupBox("Transfer-Zusammenfassung")
        summary_layout = QGridLayout(summary_group)

        self.v_count_total = self._add_kv(summary_layout, 0, "Anzahl Einträge")
        self.v_count_success = self._add_kv(summary_layout, 1, "Erfolgreich")
        self.v_count_failed = self._add_kv(summary_layout, 2, "Fehlgeschlagen")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Richtung", "Datei", "Status", "Fehler"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)

        summary_layout.addWidget(self.table, 0, 2, 3, 1)
        root.addWidget(summary_group, 1)

        # Footer
        foot = QHBoxLayout()
        foot.addStretch(1)
        self.lbl_hint = QLabel("Hinweis: Datei wird automatisch neu eingelesen, sobald sie geändert wird.")
        self.lbl_hint.setStyleSheet("color: gray;")
        foot.addWidget(self.lbl_hint)
        root.addLayout(foot)

        # --- Logik ---
        self.watcher = QFileSystemWatcher(self)
        if os.path.isdir(self.info_dir):
            self.watcher.addPath(self.info_dir)
        if os.path.isfile(self.info_path):
            self.watcher.addPath(self.info_path)

        self.watcher.directoryChanged.connect(self._on_dir_changed)
        self.watcher.fileChanged.connect(self._on_file_changed)

        self.btn_refresh.clicked.connect(self.reload)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_copy.clicked.connect(self.copy_path)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self.reload)

        self.reload()  # initial

    # ---------- UI-Helfer ----------

    def _add_kv(self, layout: QGridLayout, row: int, key: str) -> QLabel:
        k = QLabel(key)
        v = QLabel("-")
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(k, row, 0)
        layout.addWidget(v, row, 1)
        return v

    def _set_result_color(self, result: str):
        ru = (result or "").upper()
        if ru == "SENT":
            color = "#2e7d32"
        elif ru.startswith("SKIPPED"):
            color = "#e65100"
        elif ru.startswith("ERROR"):
            color = "#b71c1c"
        else:
            color = "#666666"
        self.lbl_result_val.setStyleSheet(f"font-weight: 600; color: {color};")

    # ---------- FS-Ereignisse ----------

    def _on_dir_changed(self, _path: str):
        try:
            if os.path.isfile(self.info_path) and self.info_path not in self.watcher.files():
                self.watcher.addPath(self.info_path)
        except Exception:
            pass
        self._debounce_timer.start()

    def _on_file_changed(self, _path: str):
        self._debounce_timer.start()

    # ---------- Aktionen ----------

    def reload(self):
        ok, mail_meta, results = self._read_and_normalize()
        if not ok:
            self._set_empty()
            return

        self.v_enabled.setText(self._yesno(mail_meta.get("enabled")))
        self.v_host.setText(str(mail_meta.get("host") or ""))
        self.v_port.setText(str(mail_meta.get("port") or ""))
        self.v_user_present.setText(self._yesno(mail_meta.get("user_present")))
        self.v_notify_present.setText(self._yesno(mail_meta.get("notify_email_present")))
        self.v_mode.setText(str(mail_meta.get("mode") or "unknown"))
        self.v_attempted.setText(str(mail_meta.get("attempted_at_utc") or ""))

        result = str(mail_meta.get("result") or "-")
        self.lbl_result_val.setText(result)
        self._set_result_color(result)

        err = str(mail_meta.get("error") or "")
        self.v_error.setText(err if err else "-")

        total = len(results)
        failed = sum(1 for r in results if (r.get("status") or "").upper() == "FAILED")
        success = sum(1 for r in results if (r.get("status") or "").upper() == "SUCCESS")

        self.v_count_total.setText(str(total))
        self.v_count_success.setText(str(success))
        self.v_count_failed.setText(str(failed))

        self.table.setRowCount(0)
        for r in results[:200]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r.get("direction") or "")))
            self.table.setItem(row, 1, QTableWidgetItem(str(r.get("file") or "")))

            st = str(r.get("status") or "")
            it_status = QTableWidgetItem(st)
            if st.upper() == "FAILED":
                it_status.setForeground(Qt.red)
            elif st.upper() == "SUCCESS":
                it_status.setForeground(Qt.darkGreen)
            self.table.setItem(row, 2, it_status)
            self.table.setItem(row, 3, QTableWidgetItem(str(r.get("error", ""))))

    def open_file(self):
        if os.path.isfile(self.info_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.info_path))
        else:
            QMessageBox.information(self, "Mail-Status", "Die Status-Datei existiert noch nicht.")

    def copy_path(self):
        QGuiApplication.clipboard().setText(self.info_path)

    # ---------- Datenzugriff ----------

    def _read_and_normalize(self) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]]]:
        if not os.path.isfile(self.info_path):
            return False, {}, []

        try:
            with open(self.info_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            debug_print(f"MailStatusWidget: JSON-Fehler: {e}")
            return False, {}, []

        if isinstance(raw, dict):
            mail = raw.get("mail") or {}
            results = raw.get("results") or raw.get("files") or []
            if not isinstance(results, list):
                results = []
            if not isinstance(mail, dict):
                mail = {}
            return True, mail, results

        if isinstance(raw, list):
            results = raw
            mail = {
                "enabled": None,
                "host": "",
                "port": "",
                "user_present": None,
                "notify_email_present": None,
                "mode": "unknown",
                "attempted_at_utc": "",
                "result": "SKIPPED_NO_META",
                "error": ""
            }
            return True, mail, results

        return False, {}, []

    def _set_empty(self):
        for v in [self.v_enabled, self.v_host, self.v_port,
                  self.v_user_present, self.v_notify_present,
                  self.v_mode, self.v_attempted, self.v_error]:
            v.setText("-")
        self.lbl_result_val.setText("-")
        self._set_result_color("-")
        self.v_count_total.setText("0")
        self.v_count_success.setText("0")
        self.v_count_failed.setText("0")
        self.table.setRowCount(0)

    @staticmethod
    def _yesno(v: Any) -> str:
        if v is None:
            return "Unbekannt"
        return "Ja" if bool(v) else "Nein"


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = MailStatusWidget()
    w.resize(900, 520)
    w.show()
    sys.exit(app.exec())