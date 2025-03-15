#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from PySide6 import QtWidgets, QtCore
from utils.transfer_plan_manager import load_transfer_plans, add_transfer_plan, remove_transfer_plan, update_transfer_plan
from ui.ftp_plan_widget import FtpPlanWidget
from ui.ftp_plan_dialog import FtpPlanDialog

class FtpScheduleWidget(QtWidgets.QWidget):
    """
    Widget zur Verwaltung der Transferpläne.
    Oben befinden sich Buttons zum Hinzufügen und Entfernen.
    Darunter eine ScrollArea, in der für jeden Transferplan ein FtpPlanWidget angezeigt wird.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_plans()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Transferplan hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Transferplan entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(10)
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.add_btn.clicked.connect(self.add_plan)
        self.del_btn.clicked.connect(self.remove_plan)

    def load_plans(self):
        # Alte Widgets entfernen
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.plans = load_transfer_plans()
        for plan in self.plans:
            widget = FtpPlanWidget(plan, parent=self.container_widget)
            widget.editRequested.connect(self.edit_plan)
            widget.deleteRequested.connect(self.delete_plan)
            self.container_layout.addWidget(widget)
        self.container_layout.addStretch()

    def add_plan(self):
        dlg = FtpPlanDialog(parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_plan = dlg.get_plan()
            add_transfer_plan(new_plan)
            self.load_plans()

    def edit_plan(self, plan):
        dlg = FtpPlanDialog(plan, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            updated_plan = dlg.get_plan()
            update_transfer_plan(updated_plan)
            self.load_plans()

    def delete_plan(self, plan_id):
        reply = QtWidgets.QMessageBox.question(self, "Löschen",
                                               "Transferplan wirklich löschen?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            remove_transfer_plan(plan_id)
            self.load_plans()

    def remove_plan(self):
        # Beispielweise: Entferne den ersten Plan (oder implementiere eine Auswahl)
        plans = load_transfer_plans()
        if not plans:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Transferpläne vorhanden.")
            return
        plan_id = plans[0].get("id")
        self.delete_plan(plan_id)