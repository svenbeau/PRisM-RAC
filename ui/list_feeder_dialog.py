#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
from PySide6 import QtWidgets, QtCore, QtGui
from utils.list_feeder import ListFeederWorker


def _info_label(parent: QtWidgets.QWidget, text: str, tooltip_html: str) -> QtWidgets.QWidget:
    """Baut ein Label mit kleinem Info-Button (🛈) für Tooltips."""
    w = QtWidgets.QWidget(parent)
    hl = QtWidgets.QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    lab = QtWidgets.QLabel(text, w)
    info_btn = QtWidgets.QToolButton(w)
    info_btn.setAutoRaise(True)
    info_btn.setCursor(QtCore.Qt.PointingHandCursor)
    icon = w.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
    info_btn.setIcon(icon)
    info_btn.setIconSize(QtCore.QSize(14, 14))
    info_btn.setToolTip(tooltip_html)

    hl.addWidget(lab, 0, QtCore.Qt.AlignVCenter)
    hl.addWidget(info_btn, 0, QtCore.Qt.AlignVCenter)
    hl.addStretch(1)
    return w


class ListFeederDialog(QtWidgets.QDialog):
    """
    Dialog zum Einspeisen einer CSV-Liste in einen Monitor-Ordner.
    Zeigt zusätzlich eine Warteschlangen-Vorschau (Datei / Ziel / Status).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRiSM – Listen-Einspeisung (CSV → Monitor)")
        self.setMinimumWidth(800)
        self.worker: ListFeederWorker | None = None
        self.queue_data = []  # für Vorschau
        self._build_ui()
        self._wire()

    # ---- UI ----

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)

        # --- CSV-Pfad ---
        self.csv_edit = QtWidgets.QLineEdit()
        self.csv_btn = QtWidgets.QPushButton("CSV wählen…")
        csv_box = QtWidgets.QHBoxLayout()
        csv_box.setContentsMargins(0, 0, 0, 0)
        csv_box.setSpacing(6)
        csv_box_w = QtWidgets.QWidget()
        csv_box_w.setLayout(csv_box)
        csv_box.addWidget(self.csv_edit, 1)
        csv_box.addWidget(self.csv_btn)

        csv_label = _info_label(
            self,
            "CSV-Datei:",
            "<b>CSV mit Datei-Liste</b><br>"
            "Erwartet mindestens die Spalte <code>file_path</code> (absolut oder relativ).<br>"
            "Optional: <code>target_subdir</code> (Info-Feld), "
            "<code>rename_to</code> (neuer Name für Reporting oder Output)."
        )
        form.addRow(csv_label, csv_box_w)

        # --- Monitor-Ordner ---
        self.monitor_edit = QtWidgets.QLineEdit()
        self.monitor_btn = QtWidgets.QPushButton("Monitor-Ordner wählen…")
        mon_box = QtWidgets.QHBoxLayout()
        mon_box.setContentsMargins(0, 0, 0, 0)
        mon_box.setSpacing(6)
        mon_box_w = QtWidgets.QWidget()
        mon_box_w.setLayout(mon_box)
        mon_box.addWidget(self.monitor_edit, 1)
        mon_box.addWidget(self.monitor_btn)

        mon_label = _info_label(
            self,
            "Monitor-Ordner:",
            "<b>Hotfolder-Eingangsordner</b><br>"
            "Dorthin werden die Einträge der CSV eingespeist (verlinkt/verschoben/kopiert), "
            "damit PRiSM sie wie 'neu eingetroffen' verarbeitet."
        )
        form.addRow(mon_label, mon_box_w)

        # --- Optionen ---
        self.move_chk = QtWidgets.QCheckBox("Dateien verschieben (statt verlinken)")
        self.unique_chk = QtWidgets.QCheckBox("Bei Kollisionen eindeutige Namen erzeugen")
        self.unique_chk.setChecked(True)
        self.links_only_chk = QtWidgets.QCheckBox("Nur verlinken (kein Copy-Fallback)")

        opt_label = _info_label(
            self,
            "Optionen:",
            "<b>Verhalten beim Einspeisen</b><ul>"
            "<li><i>Verschieben</i>: Original wandert in den Monitor (kein Link).</li>"
            "<li><i>Eindeutige Namen</i>: Verhindert Konflikte bei gleichen Dateinamen.</li>"
            "<li><i>Nur verlinken</i>: Nie kopieren – brich ab, wenn Link nicht möglich.</li>"
            "</ul>"
        )
        opt_box = QtWidgets.QVBoxLayout()
        opt_box.setContentsMargins(0, 0, 0, 0)
        opt_box.setSpacing(4)
        opt_box.addWidget(self.move_chk)
        opt_box.addWidget(self.unique_chk)
        opt_box.addWidget(self.links_only_chk)
        opt_widget = QtWidgets.QWidget()
        opt_widget.setLayout(opt_box)
        form.addRow(opt_label, opt_widget)

        # --- Intervall ---
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setSuffix(" s Pause")
        self.interval_spin.setRange(0.0, 60.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(0.5)
        interval_label = _info_label(
            self,
            "Intervall:",
            "<b>Pause nach jeder Datei</b><br>"
            "Hilft dem Hotfolder/Photoshop, Dateien nacheinander zu erkennen.<br>"
            "Empfehlung: 0,5–1,0 s."
        )
        form.addRow(interval_label, self.interval_spin)
        layout.addLayout(form)

        # --- Warteschlangen-Tabelle ---
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Datei", "Ziel (Info)", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        self.table.model().setHeaderData(0, QtCore.Qt.Horizontal, "Originaldatei (file_path)", QtCore.Qt.ToolTipRole)
        self.table.model().setHeaderData(1, QtCore.Qt.Horizontal,
                                         "Kombination aus target_subdir / rename_to – Anzeige/Reporting, kein Dateisystem-Effekt",
                                         QtCore.Qt.ToolTipRole)
        self.table.model().setHeaderData(2, QtCore.Qt.Horizontal, "Verarbeitungsstatus", QtCore.Qt.ToolTipRole)
        layout.addWidget(self.table, 2)

        # Progress + Log
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        layout.addWidget(self.log, 1)

        # Buttons
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        self.start_btn = QtWidgets.QPushButton("Start")
        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.close_btn = QtWidgets.QPushButton("Schließen")
        self.cancel_btn.setEnabled(False)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    # ---- Logik ----

    def _wire(self):
        self.csv_btn.clicked.connect(self._pick_csv)
        self.monitor_btn.clicked.connect(self._pick_monitor)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self._cancel)
        self.close_btn.clicked.connect(self.close)

    def _pick_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV wählen", "", "CSV (*.csv)")
        if path:
            self.csv_edit.setText(path)
            self._load_csv_preview(path)

    def _pick_monitor(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Monitor-Ordner wählen", "")
        if path:
            self.monitor_edit.setText(path)

    def _load_csv_preview(self, path: str):
        """CSV einlesen und in der Tabelle als Warteschlange anzeigen."""
        self.table.setRowCount(0)
        self.queue_data.clear()
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_path = row.get("file_path", "").strip()
                    sub = row.get("target_subdir", "").strip()
                    rn = row.get("rename_to", "").strip()
                    if not file_path:
                        continue
                    name = os.path.basename(file_path)
                    target_rel = os.path.join(sub, rn or name) if sub else (rn or name)
                    row_idx = self.table.rowCount()
                    self.table.insertRow(row_idx)
                    self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(file_path))
                    self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(target_rel))
                    self.table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem("Bereit"))
                    self.queue_data.append((file_path, target_rel))
            self._append_log(f"CSV geladen: {len(self.queue_data)} Einträge.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"CSV konnte nicht gelesen werden:\n{e}")

    def _append_log(self, text: str):
        self.log.appendPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def _set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for w in (
            self.csv_edit, self.csv_btn, self.monitor_edit, self.monitor_btn,
            self.move_chk, self.unique_chk, self.links_only_chk, self.interval_spin
        ):
            w.setEnabled(not running)

    def _start(self):
        csv_path = self.csv_edit.text().strip()
        monitor_dir = self.monitor_edit.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültige CSV angeben.")
            return
        if not monitor_dir or not os.path.isdir(monitor_dir):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültigen Monitor-Ordner angeben.")
            return
        self.log.clear()
        self.progress.setValue(0)
        self.worker = ListFeederWorker(
            csv_path=csv_path,
            monitor_dir=monitor_dir,
            move_files=self.move_chk.isChecked(),
            interval_seconds=float(self.interval_spin.value()),
            ensure_unique_names=self.unique_chk.isChecked(),
            links_only=self.links_only_chk.isChecked(),
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._append_log)
        self.worker.error.connect(self._on_error)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)
        self._set_running(True)
        self._append_log("Starte…")
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self._append_log("Breche ab…")

    def _on_progress(self, processed: int, total: int):
        pct = 0 if total == 0 else int(100 * processed / total)
        self.progress.setValue(pct)
        if 0 <= processed - 1 < self.table.rowCount():
            self.table.setItem(processed - 1, 2, QtWidgets.QTableWidgetItem("OK"))

    def _on_error(self, msg: str):
        self._append_log(f"[FEHLER] {msg}")
        QtWidgets.QMessageBox.critical(self, "Fehler", msg)
        self._set_running(False)

    def _on_finished(self):
        self._append_log("Fertig.")
        self.progress.setValue(100)
        self._set_running(False)

    def _on_cancelled(self):
        self._append_log("Abgebrochen.")
        self._set_running(False)