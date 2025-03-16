#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from PySide6 import QtWidgets
from utils.config_manager import debug_print
from utils.transfer_plan_config_manager import TransferPlanConfigManager
from ui.transfer_plan_widget import TransferPlanWidget
from ui.transfer_plan_dialog import TransferPlanDialog
import json

class TransferPlanListWidget(QtWidgets.QWidget):
    """
    Entspricht dem ScriptRecipeListWidget, nur für Transfer-Pläne:
      - Oben Buttons: "Transfer-Plan hinzufügen" / "Transfer-Plan entfernen"
      - ScrollArea mit collapsiblen Widgets (TransferPlanWidget)
      - Lädt und speichert über TransferPlanConfigManager (transfer_plans.json)
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = TransferPlanConfigManager()  # Liest/schreibt transfer_plans.json
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Buttons oben
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transfer-Plan hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Transfer-Plan entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # ScrollArea
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(10)
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Connect
        self.add_btn.clicked.connect(self.add_transfer_plan)
        self.del_btn.clicked.connect(self.remove_transfer_plan)

        self.load_plans()

    def load_plans(self):
        debug_print("TransferPlanListWidget.load_plans() aufgerufen.")
        # Alte Widgets entfernen
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        plans = self.manager.get_plans()
        debug_print("Plans=" + json.dumps(plans, indent=2))
        for p_data in plans:
            widget = TransferPlanWidget(p_data, parent=self.container_widget)
            self.container_layout.addWidget(widget)

        self.container_layout.addStretch()

    def add_transfer_plan(self):
        new_id = str(uuid.uuid4())
        new_plan = {
            "id": new_id,
            "name": "Neuer Transfer-Plan",
            "source_path": "",
            "use_ftp": False,
            "ftp_server": "",
            "target_path": "",
            "versioning_mode": "mirror",
            "suffix_format": "_v",
            "schedule_type": "once",
            "schedule_time": "",
            "move_after": "",
            "body_visible": True  # Für Kollabieren
        }
        # Zuerst den neuen Plan hinzufügen (Standardwerte)
        self.manager.add_plan(new_plan)

        # Dann den Dialog zum Bearbeiten öffnen
        dlg = TransferPlanDialog(new_plan, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            debug_print("TransferPlanDialog: Plan gespeichert.")
            debug_print("Neuer Plan (nach Dialog):\n" + json.dumps(new_plan, indent=2))
            # Den aktualisierten Plan in die Konfiguration schreiben
            self.manager.update_plan(new_id, new_plan)
        else:
            debug_print("TransferPlanDialog abgebrochen, evtl. leeren Plan entfernen?")
            # Optional: Den Plan entfernen, wenn abgebrochen:
            # self.manager.remove_plan(new_id)

        # Manager neu laden und Widgets aktualisieren
        self.manager = TransferPlanConfigManager()
        self.load_plans()

    def remove_transfer_plan(self):
        plans = self.manager.get_plans()
        if not plans:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Transfer-Pläne vorhanden.")
            return
        idx, ok = QtWidgets.QInputDialog.getInt(
            self, "Plan entfernen",
            "Index (1-basiert):", 1, 1, len(plans)
        )
        if ok:
            real_idx = idx - 1
            if 0 <= real_idx < len(plans):
                plan_id = plans[real_idx].get("id")
                self.manager.remove_plan(plan_id)
                self.manager = TransferPlanConfigManager()
                self.load_plans()