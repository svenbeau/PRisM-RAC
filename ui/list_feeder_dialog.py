#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional

from PySide6 import QtWidgets, QtCore, QtGui

from utils.list_feeder import ListFeederWorker
from utils.hotfolder_config_manager import HotfolderConfigManager


SETTINGS_SCOPE_ORG = "PRiSM-CC"
SETTINGS_SCOPE_APP = "PRiSM-CC"
S_KEY_GEOMETRY = "list_feeder/geometry"
S_KEY_LAST_CONTEXT_ID = "list_feeder/last_context_id"
S_KEY_RECENT_CSV = "list_feeder/recent_csv"
S_KEY_LAST_CSV_DIR = "list_feeder/last_csv_dir"
RECENT_CSV_LIMIT = 12


def _info_label(parent: QtWidgets.QWidget, text: str, tooltip_html: str) -> QtWidgets.QWidget:
    """Label mit kleinem Info-Button (🛈) für die linke Spalte eines QFormLayout."""
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
    Fester Modus: In den Monitor-Ordner einspeisen (Kopie/Link mit Copy-Fallback) – Quelle bleibt unverändert.
    Mit Warteschlangen-Anzeige, farbigem Fortschritt und persistenten Einstellungen.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PRiSM – Listen-Einspeisung (CSV → Monitor)")
        self.setMinimumWidth(760)

        self.settings = QtCore.QSettings(SETTINGS_SCOPE_ORG, SETTINGS_SCOPE_APP)

        self._hf_manager = HotfolderConfigManager()
        self._hotfolders = self._hf_manager.get_hotfolders() or []

        self.worker: Optional[ListFeederWorker] = None
        self._total = 0
        self._processed = 0
        self._fails = 0

        self._build_ui()
        self._wire()
        self._restore_geometry()
        self._populate_hotfolders()
        self._load_recent_csv()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        # WICHTIG: rechte Spalte darf wachsen, damit Texte nicht „verschwinden“
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        # Kontext-Hotfolder
        self.context_combo = QtWidgets.QComboBox()
        self.context_combo.setMinimumWidth(420)
        self.context_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form.addRow(
            _info_label(self, "Kontext-Hotfolder:",
                        "<b>Profil/Kontext</b><br>Bestimmt Monitorpfad und Reporting."),
            self.context_combo
        )

        # Monitor (auto)
        self.monitor_edit = QtWidgets.QLineEdit()
        self.monitor_edit.setReadOnly(True)
        self.monitor_btn = QtWidgets.QPushButton("Monitor-Ordner wählen…")
        self.monitor_btn.setEnabled(False)  # aktuell immer auto aus Kontext
        mon_box = QtWidgets.QHBoxLayout()
        mon_box.setContentsMargins(0, 0, 0, 0)
        mon_box.setSpacing(6)
        mon_w = QtWidgets.QWidget()
        mon_w.setLayout(mon_box)
        mon_box.addWidget(self.monitor_edit, 1)
        mon_box.addWidget(self.monitor_btn)
        form.addRow(
            _info_label(self, "Monitor-Ordner:",
                        "Automatisch aus dem gewählten Kontext-Hotfolder."),
            mon_w
        )

        # CSV – als ComboBox (editierbar), merkt sich die letzten Pfade
        self.csv_combo = QtWidgets.QComboBox()
        self.csv_combo.setEditable(True)
        self.csv_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.csv_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        # gleiche Mindestbreite und expansive Policy wie der Kontext-Dropdown
        self.csv_combo.setMinimumWidth(self.context_combo.minimumWidth())
        self.csv_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.csv_btn = QtWidgets.QPushButton("CSV wählen…")

        csv_box = QtWidgets.QHBoxLayout()
        csv_box.setContentsMargins(0, 0, 0, 0)
        csv_box.setSpacing(6)
        csv_w = QtWidgets.QWidget()
        csv_w.setLayout(csv_box)
        csv_box.addWidget(self.csv_combo, 1)
        csv_box.addWidget(self.csv_btn)

        form.addRow(
            _info_label(self, "CSV-Datei:",
                        "Pflichtspalte: <code>file_path</code> (absolut oder relativ zur CSV).<br>"
                        "Optional: <code>target_subdir</code>, <code>rename_to</code>."),
            csv_w
        )

        # Modus-Hinweis (NUR Erklärung; kein erneutes „Modus:“ im Text)
        self.mode_hint = QtWidgets.QLabel(
            "<b>In Monitor einspeisen</b> (kopieren/Link mit Copy-Fallback) – Quelle bleibt unverändert."
        )
        self.mode_hint.setWordWrap(True)
        self.mode_hint.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.mode_hint.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        form.addRow(_info_label(self, "Modus:", "Fester Modus für sichere Verarbeitung."), self.mode_hint)

        # Optionen
        self.unique_chk = QtWidgets.QCheckBox("Bei Kollisionen eindeutige Namen erzeugen")
        self.unique_chk.setChecked(True)
        # Checkbox bekommt ebenfalls Expanding, damit die rechte Spalte nicht kollabiert
        self.unique_chk.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form.addRow(QtWidgets.QLabel("Optionen:"), self.unique_chk)

        # Intervall
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setSuffix(" s Pause")
        self.interval_spin.setRange(0.0, 60.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(0.5)
        form.addRow(_info_label(self, "Intervall:",
                                "Kurze Pause nach jedem Eintrag, damit der HF seriell verarbeitet."),
                    self.interval_spin)

        layout.addLayout(form)

        # Warteschlange + Fortschritt
        queue_box = QtWidgets.QHBoxLayout()
        queue_box.setContentsMargins(0, 0, 0, 0)
        queue_box.setSpacing(12)

        self.queue_label = QtWidgets.QLabel("Warteschlange: 0/0")
        self.current_label = QtWidgets.QLabel("Aktuell: —")
        self.result_label = QtWidgets.QLabel("")  # ✓/✗ Kurzfeedback

        queue_box.addWidget(self.queue_label, 0, QtCore.Qt.AlignLeft)
        queue_box.addWidget(self.current_label, 1, QtCore.Qt.AlignLeft)
        queue_box.addWidget(self.result_label, 0, QtCore.Qt.AlignRight)

        layout.addLayout(queue_box)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self._set_progress_neutral()
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

    def _wire(self) -> None:
        self.csv_btn.clicked.connect(self._pick_csv)
        self.monitor_btn.clicked.connect(self._pick_monitor)
        self.context_combo.currentIndexChanged.connect(self._on_context_changed)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self._cancel)
        self.close_btn.clicked.connect(self.close)

    # ---------- Daten ----------

    def _populate_hotfolders(self) -> None:
        self.context_combo.clear()
        self.context_combo.addItem("— bitte wählen —", userData=None)
        for hf in self._hotfolders:
            self.context_combo.addItem(hf.get("name", "Unbenannt"), userData=hf)

        last_id = self.settings.value(S_KEY_LAST_CONTEXT_ID, "", str)
        if last_id:
            for i in range(1, self.context_combo.count()):
                hf = self.context_combo.itemData(i)
                if isinstance(hf, dict) and hf.get("id") == last_id:
                    self.context_combo.setCurrentIndex(i)
                    break
        elif len(self._hotfolders) == 1:
            self.context_combo.setCurrentIndex(1)

    def _load_recent_csv(self) -> None:
        recents = self.settings.value(S_KEY_RECENT_CSV, [], list)
        if not isinstance(recents, list):
            recents = []
        self.csv_combo.clear()
        self.csv_combo.addItems(recents)

    def _remember_csv_path(self, path: str) -> None:
        if not path:
            return
        recents = self.settings.value(S_KEY_RECENT_CSV, [], list)
        if not isinstance(recents, list):
            recents = []
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        if len(recents) > RECENT_CSV_LIMIT:
            recents = recents[:RECENT_CSV_LIMIT]
        self.settings.setValue(S_KEY_RECENT_CSV, recents)
        self.settings.setValue(S_KEY_LAST_CSV_DIR, os.path.dirname(path))
        self.csv_combo.blockSignals(True)
        self.csv_combo.clear()
        self.csv_combo.addItems(recents)
        self.csv_combo.setCurrentIndex(0)
        self.csv_combo.blockSignals(False)

    # ---------- Actions ----------

    def _on_context_changed(self, idx: int) -> None:
        hf = self.context_combo.currentData()
        mon = hf.get("monitor_dir", "") if isinstance(hf, dict) else ""
        self.monitor_edit.setText(mon or "")
        if isinstance(hf, dict):
            self.settings.setValue(S_KEY_LAST_CONTEXT_ID, hf.get("id", ""))

    def _pick_csv(self) -> None:
        start_dir = self.settings.value(S_KEY_LAST_CSV_DIR, "", str) or ""
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSV wählen", start_dir, "CSV (*.csv)")
        if path:
            self._remember_csv_path(path)

    def _pick_monitor(self) -> None:
        # (derzeit deaktiviert – Monitor kommt aus Kontext)
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Monitor-Ordner wählen", "")
        if path:
            self.monitor_edit.setText(path)

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def _set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for w in (self.csv_combo, self.csv_btn, self.context_combo,
                  self.monitor_btn, self.interval_spin, self.unique_chk):
            w.setEnabled(not running)

    # ---------- Progressbar-Farben ----------

    def _set_progress_neutral(self) -> None:
        self.progress.setStyleSheet("")  # Standard

    def _set_progress_success(self) -> None:
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #3aa657; }")

    def _set_progress_warning(self) -> None:
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #e67e22; }")

    def _set_progress_error(self) -> None:
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #d9534f; }")

    # ---------- Start / Cancel ----------

    def _start(self) -> None:
        hf = self.context_combo.currentData()
        if not isinstance(hf, dict):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte zuerst einen Kontext-Hotfolder wählen.")
            return

        csv_path = (self.csv_combo.currentText() or "").strip()
        monitor_dir = (hf.get("monitor_dir") or "").strip()

        if not csv_path or not os.path.exists(csv_path):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte gültige CSV angeben.")
            return
        if not monitor_dir or not os.path.isdir(monitor_dir):
            QtWidgets.QMessageBox.warning(self, "Fehler",
                                          "Der Monitor-Ordner des gewählten Hotfolders ist ungültig.")
            return

        self._remember_csv_path(csv_path)

        self.log.clear()
        self.progress.setValue(0)
        self._set_progress_neutral()
        self._processed = 0
        self._fails = 0
        self._total = 0
        self.queue_label.setText("Warteschlange: 0/0")
        self.current_label.setText("Aktuell: —")
        self.result_label.setText("")

        self.worker = ListFeederWorker(
            csv_path=csv_path,
            monitor_dir=monitor_dir,
            move_files=False,  # fester Modus
            interval_seconds=float(self.interval_spin.value()),
            ensure_unique_names=self.unique_chk.isChecked(),
            links_only=False,
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._append_log)
        self.worker.error.connect(self._on_error)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)
        if hasattr(self.worker, "item_started"):
            self.worker.item_started.connect(self._on_item_started)  # type: ignore[attr-defined]
        if hasattr(self.worker, "item_result"):
            self.worker.item_result.connect(self._on_item_result)    # type: ignore[attr-defined]

        self._set_running(True)
        self._append_log(f"Kontext: {hf.get('name','?')}")
        self._append_log("Starte Einspeisung …")
        self.worker.start()

    def _cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self._append_log("Breche ab …")

    # ---------- Worker-Callbacks ----------

    def _on_item_started(self, src: str, idx: int, total: int) -> None:
        self._total = total
        self.current_label.setText(f"Aktuell: [{idx}/{total}] {os.path.basename(src)}")
        self.queue_label.setText(f"Warteschlange: {self._processed}/{total}")
        self.result_label.setText("")

    def _on_item_result(self, ok: bool, dst: str, idx: int) -> None:
        if ok:
            self.result_label.setText("✓ OK")
            self.result_label.setStyleSheet("color:#3aa657;")
        else:
            self.result_label.setText("✗ Fehler")
            self.result_label.setStyleSheet("color:#d9534f;")
            self._fails += 1

    def _on_progress(self, processed: int, total: int) -> None:
        self._processed = processed
        self._total = total or self._total
        pct = 0 if self._total == 0 else int(100 * processed / self._total)
        self.progress.setValue(pct)
        self.queue_label.setText(f"Warteschlange: {processed}/{self._total}")
        if self._fails > 0:
            self._set_progress_warning()

    def _on_error(self, msg: str) -> None:
        self._append_log(f"[FEHLER] {msg}")
        QtWidgets.QMessageBox.critical(self, "Fehler", msg)
        self._set_running(False)
        self._set_progress_error()

    def _on_finished(self) -> None:
        self._append_log("Fertig.")
        self.progress.setValue(100)
        self._set_running(False)
        if self._fails == 0:
            self._set_progress_success()
            self.result_label.setText("✓ Alle erledigt")
            self.result_label.setStyleSheet("color:#3aa657;")
        else:
            self._set_progress_warning()
            self.result_label.setText(f"⚠️ Fertig mit {self._fails} Fehler(n)")
            self.result_label.setStyleSheet("color:#e67e22;")

    def _on_cancelled(self) -> None:
        self._append_log("Abgebrochen.")
        self._set_running(False)
        self._set_progress_error()
        self.result_label.setText("✗ Abgebrochen")
        self.result_label.setStyleSheet("color:#d9534f;")

    # ---------- Geometry persist ----------

    def _restore_geometry(self) -> None:
        geo = self.settings.value(S_KEY_GEOMETRY, None)
        if isinstance(geo, QtCore.QByteArray) and not geo.isEmpty():
            try:
                self.restoreGeometry(geo)
            except Exception:
                pass

    def _save_geometry(self) -> None:
        try:
            self.settings.setValue(S_KEY_GEOMETRY, self.saveGeometry())
        except Exception:
            pass

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._save_geometry()
        super().closeEvent(event)

    def reject(self) -> None:
        self._save_geometry()
        super().reject()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dlg = ListFeederDialog()
    dlg.show()
    app.exec()