#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
from PySide6 import QtWidgets, QtCore, QtGui

from utils.list_feeder import ListFeederWorker
from utils.direct_list_processor import DirectListProcessorWorker

class ListFeederDialog(QtWidgets.QDialog):
    """
    Zwei Modi:
      - Monitor-Feed (Link-First): speist in Monitor-Ordner ein (euer bisheriger Weg)
      - Direktmodus (No-Touch): öffnet Quelle direkt via Callback, ohne Dateien anzufassen
    """
    # Einhängestelle: von außen zu setzen (siehe main.py)
    # Signatur: (file_path:str, target_subdir:Optional[str], rename_to:Optional[str]) -> (ok:bool, message:str)
    direct_process_callback = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRiSM – Listen-Einspeisung / Direktverarbeitung")
        self.setMinimumWidth(900)
        self.worker = None
        self._queue = []
        self._build_ui()
        self._wire()

    # ---------- UI ----------

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Modus
        mode_box = QtWidgets.QGroupBox("Modus")
        rb_layout = QtWidgets.QHBoxLayout(mode_box)
        self.rb_feed  = QtWidgets.QRadioButton("Monitor-Feed (Links/Kopie)")
        self.rb_direct = QtWidgets.QRadioButton("Direkt (No-Touch)")
        self.rb_feed.setChecked(True)
        rb_layout.addWidget(self.rb_feed)
        rb_layout.addWidget(self.rb_direct)
        rb_layout.addStretch(1)
        layout.addWidget(mode_box)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)

        # CSV
        self.csv_edit = QtWidgets.QLineEdit()
        self.csv_btn = QtWidgets.QPushButton("CSV wählen…")
        csv_row = QtWidgets.QHBoxLayout()
        csv_row.setContentsMargins(0,0,0,0)
        csv_row.setSpacing(6)
        csv_w = QtWidgets.QWidget()
        csv_w.setLayout(csv_row)
        csv_row.addWidget(self.csv_edit, 1)
        csv_row.addWidget(self.csv_btn)
        form.addRow("CSV-Datei:", csv_w)

        # Monitor-Ordner (nur im Feed-Modus)
        self.monitor_edit = QtWidgets.QLineEdit()
        self.monitor_btn = QtWidgets.QPushButton("Monitor-Ordner wählen…")
        mon_row = QtWidgets.QHBoxLayout()
        mon_row.setContentsMargins(0,0,0,0)
        mon_row.setSpacing(6)
        mon_w = QtWidgets.QWidget()
        mon_w.setLayout(mon_row)
        mon_row.addWidget(self.monitor_edit, 1)
        mon_row.addWidget(self.monitor_btn)
        form.addRow("Monitor-Ordner:", mon_w)

        # Optionen (Feed)
        self.move_chk = QtWidgets.QCheckBox("Dateien verschieben (statt verlinken)")
        self.unique_chk = QtWidgets.QCheckBox("Bei Kollisionen eindeutige Namen erzeugen")
        self.unique_chk.setChecked(True)
        self.links_only_chk = QtWidgets.QCheckBox("Nur verlinken (kein Copy-Fallback)")
        self.wait_chk = QtWidgets.QCheckBox("Nächste Datei erst, wenn HF fertig ist")
        self.wait_chk.setChecked(True)

        # Optionen (Direct)
        self.direct_pause_spin = QtWidgets.QDoubleSpinBox()
        self.direct_pause_spin.setSuffix(" s Pause (optional)")
        self.direct_pause_spin.setRange(0.0, 60.0)
        self.direct_pause_spin.setDecimals(1)
        self.direct_pause_spin.setValue(0.0)

        opts_grid = QtWidgets.QGridLayout()
        opts_grid.addWidget(self.move_chk, 0, 0)
        opts_grid.addWidget(self.unique_chk, 0, 1)
        opts_grid.addWidget(self.links_only_chk, 1, 0)
        opts_grid.addWidget(self.wait_chk, 1, 1)
        opts_grid.addWidget(QtWidgets.QLabel("Direkt-Pause:"), 2, 0)
        opts_grid.addWidget(self.direct_pause_spin, 2, 1)

        opts_w = QtWidgets.QWidget()
        opts_w.setLayout(opts_grid)
        form.addRow("Optionen:", opts_w)

        layout.addLayout(form)

        # Linie
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line)

        # Queue-Tabelle
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Datei", "Ziel (relativ)", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, 1)

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

        # UI initial an Modus anpassen
        self._apply_mode()

    def _apply_mode(self):
        feed = self.rb_feed.isChecked()
        # Monitor-Felder nur im Feed-Modus
        for w in (self.monitor_edit, self.monitor_btn, self.move_chk, self.unique_chk, self.links_only_chk, self.wait_chk):
            w.setEnabled(feed)
        # Direkt-Pause nur im Direkt-Modus
        self.direct_pause_spin.setEnabled(self.rb_direct.isChecked())

    def _wire(self):
        self.csv_btn.clicked.connect(self._pick_csv)
        self.monitor_btn.clicked.connect(self._pick_monitor)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self._cancel)
        self.close_btn.clicked.connect(self.close)
        self.rb_feed.toggled.connect(self._apply_mode)
        self.rb_direct.toggled.connect(self._apply_mode)

    # ---------- Actions ----------

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
        self._queue = []
        self.table.setRowCount(0)
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or "file_path" not in reader.fieldnames:
                    return
                for row in reader:
                    fp = (row.get("file_path") or "").strip()
                    if not fp:
                        continue
                    sub = (row.get("target_subdir") or "").strip()
                    rn  = (row.get("rename_to") or "").strip()
                    self._queue.append((fp, sub, rn))
        except Exception:
            return

        for fp, sub, rn in self._queue:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = os.path.basename(fp)
            target_rel = os.path.join(sub, rn or name) if sub else (rn or name)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(target_rel))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem("Queued"))
        self.table.resizeColumnsToContents()

    def _set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for w in (
            self.csv_edit, self.csv_btn, self.monitor_edit, self.monitor_btn,
            self.move_chk, self.unique_chk, self.links_only_chk, self.wait_chk,
            self.direct_pause_spin, self.rb_feed, self.rb_direct
        ):
            w.setEnabled(not running)

    # ---------- Start/Cancel ----------

    def _start(self):
        csv_path = self.csv_edit.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültige CSV angeben.")
            return

        # Reset Status-Spalte
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem("Queued"))

        # FEED-MODUS (Monitor)
        if self.rb_feed.isChecked():
            monitor_dir = self.monitor_edit.text().strip()
            if not monitor_dir or not os.path.isdir(monitor_dir):
                QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültigen Monitor-Ordner angeben.")
                return
            self.worker = ListFeederWorker(
                csv_path=csv_path,
                monitor_dir=monitor_dir,
                move_files=self.move_chk.isChecked(),
                interval_seconds=0.0,  # gating übernimmt
                ensure_unique_names=self.unique_chk.isChecked(),
                links_only=self.links_only_chk.isChecked(),
                wait_until_consumed=self.wait_chk.isChecked(),
                consumption_poll_seconds=0.5,
                consumption_timeout_seconds=0.0,
                parent=self
            )
        else:
            # DIREKTMODUS
            if not callable(self.direct_process_callback):
                QtWidgets.QMessageBox.critical(
                    self, "Konfiguration fehlt",
                    "Kein Direct-Process-Callback gesetzt.\n"
                    "Bitte im MainWindow beim Öffnen des Dialogs setzen."
                )
                return
            self.worker = DirectListProcessorWorker(
                csv_path=csv_path,
                direct_process_callback=self.direct_process_callback,
                pause_seconds=float(self.direct_pause_spin.value()),
                parent=self
            )

        # gemeinsame Signale
        self.worker.progress.connect(self._on_progress)
        self.worker.error.connect(self._on_error)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)
        # Status je Item
        if hasattr(self.worker, "item_status"):
            self.worker.item_status.connect(self._on_item_status)

        self._set_running(True)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()

    # ---------- Callbacks ----------

    def _on_progress(self, processed: int, total: int):
        self.setWindowTitle(f"PRiSM – Liste ({processed}/{total})")

    def _on_error(self, msg: str):
        QtWidgets.QMessageBox.critical(self, "Fehler", msg)
        self._set_running(False)

    def _on_finished(self):
        self._set_running(False)

    def _on_cancelled(self):
        self._set_running(False)

    def _on_item_status(self, index: int, status: str, info: str):
        if 0 <= index < self.table.rowCount():
            mapping = {
                "queued": "Queued",
                "transferring": "Übertrage…",
                "waiting": "Warte auf HF…",
                "processing": "Verarbeite…",
                "done": "Fertig",
                "skipped": "Übersprungen",
                "error": "Fehler",
                "timeout": "Timeout",
            }
            text = mapping.get(status, status)
            self.table.setItem(index, 2, QtWidgets.QTableWidgetItem(text))
            it = self.table.item(index, 2)
            if it:
                it.setToolTip(info)