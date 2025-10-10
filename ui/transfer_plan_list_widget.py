#!/usr/bin/env python3
# transfer_plan_list_widget.py
# -*- coding: utf-8 -*-

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager

from ui.ftp_plan_widget import TransferPlanWidget


class TransferPlanListWidget(QtWidgets.QWidget):
    """
    Container für alle Transfer-Pläne + globale Status/Queue.
      - Oben: Toolbar + Scrollliste der Pläne
      - Unten: gemeinsamer Status + Warteschlange (per Splitter individuell höhenverstellbar)
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.cm = TransferPlanConfigManager()

        self._building = False
        self._last_focused_widget: Optional[TransferPlanWidget] = None

        # Mapping: key -> Liste von Queue-Items (falls Keys mehrfach vorkommen)
        self._key_to_items: Dict[str, List[QtWidgets.QTreeWidgetItem]] = {}

        self.init_ui()
        self.load_plans()

    # ---------------- UI ----------------
    def init_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(5)

        # Toolbar
        bar = QtWidgets.QHBoxLayout()
        self.btn_new = QtWidgets.QPushButton("Neu")
        self.btn_del = QtWidgets.QPushButton("Ausgewählten Plan löschen")
        self.btn_reload = QtWidgets.QPushButton("Aktualisieren")
        bar.addWidget(self.btn_new)
        bar.addWidget(self.btn_del)
        bar.addStretch()
        bar.addWidget(self.btn_reload)

        # Oberer Bereich: Scrollliste
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QtWidgets.QWidget()
        self.vbox = QtWidgets.QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(8)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.container)

        # Unterer Bereich: gemeinsamer Status + Warteschlange (getrennt verstellbar)
        bottom_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        status_group = QtWidgets.QGroupBox("Status")
        sg_layout = QtWidgets.QVBoxLayout(status_group)
        self.status_edit = QtWidgets.QPlainTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMaximumBlockCount(1000)
        sg_layout.addWidget(self.status_edit)

        queue_group = QtWidgets.QGroupBox("Warteschlange")
        qg_layout = QtWidgets.QVBoxLayout(queue_group)
        self.queue = QtWidgets.QTreeWidget()
        self.queue.setColumnCount(8)
        self.queue.setHeaderLabels([
            "Direction", "File", "Destination", "Status", "Progress",
            "Started", "Finished", "Error"
        ])
        self.queue.setSortingEnabled(True)
        self.queue.setColumnWidth(1, 320)
        qg_layout.addWidget(self.queue)

        bottom_split.addWidget(status_group)
        bottom_split.addWidget(queue_group)
        bottom_split.setSizes([200, 200])  # Nutzer kann danach frei ziehen

        # Gesamtlayout
        main_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top_container = QtWidgets.QWidget()
        top_v = QtWidgets.QVBoxLayout(top_container)
        top_v.setContentsMargins(0, 0, 0, 0)
        top_v.addLayout(bar)
        top_v.addWidget(self.scroll)
        main_split.addWidget(top_container)
        main_split.addWidget(bottom_split)
        main_split.setSizes([600, 300])

        root.addWidget(main_split)

        # Signals
        self.btn_new.clicked.connect(self.on_new_plan)
        self.btn_del.clicked.connect(self.on_delete_selected)
        self.btn_reload.clicked.connect(self.load_plans)

    # ---------------- Daten laden ----------------
    def clear_list(self):
        while self.vbox.count() > 1:
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def load_plans(self):
        if self._building:
            return
        self._building = True
        try:
            debug_print("[TransferPlanListWidget] load_plans()")
            self.clear_list()
            plans = self.cm.get_plans()
            for plan in plans:
                w = TransferPlanWidget(plan, parent=self.container)
                w.installEventFilter(self)  # fokussierten Plan merken
                # an globale Status/Queue anklemmen
                w.sig_log.connect(self._append_status)
                w.sig_transfer_init.connect(self._on_transfer_init)
                w.sig_transfer_progress.connect(self._on_transfer_progress)
                w.sig_transfer_finished.connect(self._on_transfer_finished)
                self.vbox.insertWidget(self.vbox.count() - 1, w)
        finally:
            self._building = False

    # ---------------- Toolbar-Aktionen ----------------
    def _make_default_plan(self) -> dict:
        """
        Erzeugt einen minimalen Standard-Plan im stable-v42-Format.
        (Kein create_default_plan() im Manager notwendig.)
        """
        pid = uuid.uuid4().hex
        dt = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        return {
            "id": pid,
            "name": "Neuer Transfer-Plan",
            "source_path": "",
            "target_path": "",
            "use_ftp": False,           # Ziel ist lokal; wenn True → ftp_server + target_path (remote)
            "ftp_server": "",
            "versioning_mode": "mirror",
            "suffix_format": "_v{n}",
            "schedule_type": "once",
            "schedule_time": dt,
            "move_after": "",
            "body_visible": True,
            # ggf. Felder, die TransferQueueDialog/Worker verstehen:
            "source_is_ftp": False,
            "source_ftp_server": "",
            "source_remote_path": "",
            "source_remote_archive": "",
            "verify_mode": "size_only",
            "retry_count": 5,
            "auto_delete_after_move_enabled": False,
            "auto_delete_after_move_hours": 48,
        }

    def on_new_plan(self):
        plan = self._make_default_plan()
        # robustes Persistieren: add_plan() falls vorhanden, sonst update_plan() als "Insert"
        try:
            if hasattr(self.cm, "add_plan"):
                self.cm.add_plan(plan)
            else:
                self.cm.update_plan(plan["id"], plan)
            self.load_plans()
            QtWidgets.QMessageBox.information(self, "Plan", "Neuer Transfer-Plan angelegt.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Plan konnte nicht angelegt werden:\n{e}")

    def on_delete_selected(self):
        target = self._last_focused_widget
        if not isinstance(target, TransferPlanWidget):
            QtWidgets.QMessageBox.information(self, "Löschen", "Bitte zuerst einen Plan fokussieren (Titel anklicken).")
            return
        pid = target.plan_data.get("id")
        name = target.plan_data.get("name", "(unbenannt)")
        if not pid:
            return
        if QtWidgets.QMessageBox.question(
            self, "Löschen bestätigen",
            f"Soll der Plan „{name}“ wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) != QtWidgets.QMessageBox.Yes:
            return

        try:
            if hasattr(self.cm, "remove_plan"):
                self.cm.remove_plan(pid)
            else:
                # Fallback: hart laden/speichern, falls Manager keine remove_plan hat
                plans = [p for p in self.cm.get_plans() if p.get("id") != pid]
                if hasattr(self.cm, "save_plans"):
                    self.cm.save_plans(plans)  # type: ignore[attr-defined]
                else:
                    # Minimal-Fallback: update_plan auf "gelöschte" leere Struktur
                    self.cm.update_plan(pid, {})  # überschreibt – abhängig von Implementierung
        finally:
            self.load_plans()

    # ---------------- Fokus/Selektion verfolgen ----------------
    def eventFilter(self, obj, event):
        if isinstance(obj, TransferPlanWidget):
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self._last_focused_widget = obj
        return super().eventFilter(obj, event)

    # ---------------- Gemeinsamer Status/Queue ----------------
    def _append_status(self, line: str):
        self.status_edit.appendPlainText(line)

    def _queue_add(self, direction: str, file_disp: str, destination: str, key: str):
        item = QtWidgets.QTreeWidgetItem([
            direction, (os.path.basename(file_disp) if "/" in file_disp or "\\" in file_disp else file_disp),
            destination, "Queued", "0%",
            QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "", ""
        ])
        self.queue.addTopLevelItem(item)
        self._key_to_items.setdefault(key, []).append(item)
        return item

    def _queue_update(self, item: QtWidgets.QTreeWidgetItem, *, status=None, progress=None, finished=False, error=None):
        if status is not None:
            item.setText(3, status)
        if progress is not None:
            item.setText(4, f"{progress}%" if isinstance(progress, int) else "–")
        if finished and not item.text(6):
            item.setText(6, QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))
        if error:
            item.setText(7, error)

    # -- Signal-Handler der Plan-Widgets --
    @QtCore.Slot(list)
    def _on_transfer_init(self, items: List[dict]):
        for it in items:
            key = str(it.get("key", ""))
            direction = str(it.get("direction", ""))
            file_disp = str(it.get("file", ""))
            dest = str(it.get("destination", ""))
            item = self._queue_add(direction, file_disp, dest, key)
            self._queue_update(item, status="Wartet", progress=0)

    @QtCore.Slot(str, str, int)
    def _on_transfer_progress(self, key: str, status: str, percent: int):
        lst = self._key_to_items.get(key) or []
        target = None
        for it in reversed(lst):
            if not it.text(6):  # Finished leer
                target = it
                break
        if target is None and lst:
            target = lst[-1]
        if target is None:
            target = self._queue_add("?", key, "", key)
        self._queue_update(target, status=status, progress=percent,
                           finished=(status in ("SUCCESS", "FAILED", "Abgebrochen")))

    @QtCore.Slot()
    def _on_transfer_finished(self):
        # optional: hier könnte man einen Summen-Eintrag/Abschlusslog ergänzen
        pass