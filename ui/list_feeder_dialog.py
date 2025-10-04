#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore, QtGui

from utils.list_feeder import ListFeederWorker
from utils.hotfolder_config_manager import HotfolderConfigManager


def _info_label(parent: QtWidgets.QWidget, text: str, tooltip_html: str) -> QtWidgets.QWidget:
    """
    Label + kleines Info-Icon (Tooltip). Für die linke Spalte im QFormLayout.
    """
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
    Listen-Feeder: CSV -> ausgewählter Hotfolder (Kontext).
    Aktuell fester Modus: In den Monitor-Ordner *einspeisen* (link mit Copy-Fallback, niemals verschieben).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRiSM – Listen-Einspeisung (CSV → Monitor)")
        self.setMinimumWidth(760)

        # Hotfolder-Daten
        self._hf_manager = HotfolderConfigManager()
        self._hotfolders = self._hf_manager.get_hotfolders() or []  # list[dict]

        # Worker
        self.worker: ListFeederWorker | None = None

        self._build_ui()
        self._wire()
        self._populate_hotfolders()

    # ---------- UI ----------

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)

        # --- Kontext-Hotfolder ---
        self.context_combo = QtWidgets.QComboBox()
        self.context_combo.setMinimumWidth(420)
        ctx_label = _info_label(
            self,
            "Kontext-Hotfolder:",
            "<b>Profil/Kontext</b><br>"
            "Wähle den Hotfolder, dessen Konfiguration (v. a. Monitor-Pfad, Log/Reporting) "
            "für die Einspeisung gelten soll."
        )
        form.addRow(ctx_label, self.context_combo)

        # --- Monitor (auto aus Kontext) ---
        self.monitor_edit = QtWidgets.QLineEdit()
        self.monitor_edit.setReadOnly(True)
        self.monitor_btn = QtWidgets.QPushButton("Monitor-Ordner wählen…")
        self.monitor_btn.setEnabled(False)  # solange „kontextgeführt“
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
            "Wird automatisch aus dem gewählten Kontext-Hotfolder übernommen.<br>"
            "<i>(Später können wir hier eine manuelle Übersteuerung anbieten.)</i>"
        )
        form.addRow(mon_label, mon_box_w)

        # --- CSV ---
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
            "Pflichtspalte: <code>file_path</code> (absolut oder relativ zur CSV).<br>"
            "Optional: <code>target_subdir</code> (Unterordner im Monitor), "
            "<code>rename_to</code> (neuer Dateiname im Monitor)."
        )
        form.addRow(csv_label, csv_box_w)

        # --- Hinweis auf Modus (fix „kopieren/link mit Copy-Fallback“) ---
        self.mode_hint = QtWidgets.QLabel(
            "Modus: <b>In Monitor einspeisen (kopieren)</b> – Quelle bleibt unverändert. "
            "System nutzt ggf. Link mit Copy-Fallback. "
            "Später verfügbar: <i>Direktmodus (ohne Monitor)</i>."
        )
        self.mode_hint.setWordWrap(True)
        form.addRow(_info_label(self, "Modus:", "Fester Modus für sichere Verarbeitung."), self.mode_hint)

        # --- Optionen (minimal) ---
        self.unique_chk = QtWidgets.QCheckBox("Bei Kollisionen eindeutige Namen erzeugen")
        self.unique_chk.setChecked(True)
        self.unique_chk.setToolTip(
            "Wenn im Ziel bereits eine Datei mit gleichem Namen existiert, "
            "wird automatisch ein Zähler angehängt (__1, __2, …)."
        )
        form.addRow(QtWidgets.QLabel("Optionen:"), self.unique_chk)

        # --- Intervall ---
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setSuffix(" s Pause")
        self.interval_spin.setRange(0.0, 60.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(0.5)
        interval_label = _info_label(
            self,
            "Intervall:",
            "<b>Pause nach jedem Eintrag</b> – hilft, dass der Hotfolder/Photoshop nacheinander arbeitet."
        )
        form.addRow(interval_label, self.interval_spin)

        layout.addLayout(form)

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

    # ---------- Wiring ----------

    def _wire(self):
        self.csv_btn.clicked.connect(self._pick_csv)
        self.monitor_btn.clicked.connect(self._pick_monitor)  # aktuell deaktiviert
        self.context_combo.currentIndexChanged.connect(self._on_context_changed)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self._cancel)
        self.close_btn.clicked.connect(self.close)

    # ---------- Daten ----------

    def _populate_hotfolders(self):
        self.context_combo.clear()
        self.context_combo.addItem("— bitte wählen —", userData=None)
        for hf in self._hotfolders:
            name = hf.get("name", "Unbenannt")
            self.context_combo.addItem(name, userData=hf)

        # Wenn nur 1 HF existiert, direkt auswählen
        if len(self._hotfolders) == 1:
            self.context_combo.setCurrentIndex(1)

    # ---------- Actions ----------

    def _on_context_changed(self, idx: int):
        hf = self.context_combo.currentData()
        mon = hf.get("monitor_dir", "") if isinstance(hf, dict) else ""
        self.monitor_edit.setText(mon or "")
        # (Monitor manuell wählen ist deaktiviert – daher Button disabled lassen.)

    def _pick_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV wählen", "", "CSV (*.csv)")
        if path:
            self.csv_edit.setText(path)

    def _pick_monitor(self):
        # derzeit deaktiviert (Kontext-gesteuert). Funktion bleibt für später erhalten.
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Monitor-Ordner wählen", "")
        if path:
            self.monitor_edit.setText(path)

    def _append_log(self, text: str):
        self.log.appendPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def _set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for w in (
            self.csv_edit, self.csv_btn, self.context_combo,
            self.monitor_btn, self.interval_spin, self.unique_chk
        ):
            w.setEnabled(not running)

    def _start(self):
        # Validierung
        hf = self.context_combo.currentData()
        if not isinstance(hf, dict):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte zuerst einen Kontext-Hotfolder wählen.")
            return

        csv_path = self.csv_edit.text().strip()
        monitor_dir = (hf.get("monitor_dir") or "").strip()

        if not csv_path or not os.path.exists(csv_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültige CSV angeben.")
            return
        if not monitor_dir or not os.path.isdir(monitor_dir):
            QtWidgets.QMessageBox.warning(
                self, "Fehler",
                "Der Monitor-Ordner des gewählten Hotfolders ist ungültig oder nicht vorhanden."
            )
            return

        self.log.clear()
        self.progress.setValue(0)

        # Fester Modus: NICHT verschieben, KEIN „nur verlinken“ -> Worker darf kopieren.
        self.worker = ListFeederWorker(
            csv_path=csv_path,
            monitor_dir=monitor_dir,
            move_files=False,                       # niemals verschieben
            interval_seconds=float(self.interval_spin.value()),
            ensure_unique_names=self.unique_chk.isChecked(),
            links_only=False,                       # Link erlaubt, aber Copy-Fallback OK
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._append_log)
        self.worker.error.connect(self._on_error)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)

        self._set_running(True)
        self._append_log(f"Kontext: {hf.get('name','?')}")
        self._append_log("Starte Einspeisung …")
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self._append_log("Breche ab …")

    # ---------- Worker-Callbacks ----------

    def _on_progress(self, processed: int, total: int):
        pct = 0 if total == 0 else int(100 * processed / total)
        self.progress.setValue(pct)

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