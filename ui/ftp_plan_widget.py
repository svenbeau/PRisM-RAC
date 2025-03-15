#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore
from utils.config_manager import debug_print

class TransferPlanWidget(QtWidgets.QWidget):
    """
    Ein collapsibles Widget, das die Daten eines einzelnen Transfer-Plans anzeigt/bearbeitet.
    Ähnlich wie ScriptRecipeWidget.
    """

    def __init__(self, plan_data, manager, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.manager = manager
        self.is_collapsed = not plan_data.get("body_visible", True)
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)

        # (A) Kopfzeile (Name + Collapse/Expand-Button)
        header_layout = QtWidgets.QHBoxLayout()
        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        self.toggle_btn.setStyleSheet("font-weight: bold;")
        self.toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.clicked.connect(self.toggle_body)

        self.name_label = QtWidgets.QLabel(self.plan_data.get("name", "Neuer Transfer-Plan"))
        header_layout.addWidget(self.toggle_btn)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # (B) Body-Container => Felder
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QFormLayout(self.body_widget)

        # Beispiel-Felder:
        self.edit_name = QtWidgets.QLineEdit(self.plan_data.get("name", ""))
        body_layout.addRow("Plan-Name:", self.edit_name)

        source_type = self.plan_data.get("source_type", "local")
        self.source_type_combo = QtWidgets.QComboBox()
        self.source_type_combo.addItems(["local", "ftp"])
        self.source_type_combo.setCurrentText(source_type)
        body_layout.addRow("Quelle (Typ):", self.source_type_combo)

        self.edit_source_path = QtWidgets.QLineEdit(self.plan_data.get("source_path", ""))
        body_layout.addRow("Quelle (Pfad):", self.edit_source_path)

        self.edit_destination_path = QtWidgets.QLineEdit(self.plan_data.get("destination_path", ""))
        body_layout.addRow("Ziel (Pfad):", self.edit_destination_path)

        version_mode = self.plan_data.get("version_mode", "mirror")
        self.version_mode_combo = QtWidgets.QComboBox()
        self.version_mode_combo.addItems(["mirror", "suffix"])
        self.version_mode_combo.setCurrentText(version_mode)
        body_layout.addRow("Versionierung:", self.version_mode_combo)

        self.edit_schedule = QtWidgets.QLineEdit(self.plan_data.get("schedule", ""))
        body_layout.addRow("Zeitplan:", self.edit_schedule)

        # Buttons "Speichern" => aktualisiert die plan_data und ruft manager.update_plan(...)
        self.save_btn = QtWidgets.QPushButton("Speichern")
        self.save_btn.clicked.connect(self.save_plan)
        body_layout.addRow(self.save_btn)

        main_layout.addWidget(self.body_widget)

        # Collapsed?
        self.body_widget.setVisible(not self.is_collapsed)

    def toggle_body(self):
        self.is_collapsed = not self.is_collapsed
        self.body_widget.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("▼" if not self.is_collapsed else "▶")
        # Speichere body_visible in plan_data:
        self.plan_data["body_visible"] = (not self.is_collapsed)
        self.manager.update_plan(self.plan_data["id"], {"body_visible": not self.is_collapsed})

    def save_plan(self):
        """
        Liest die UI-Felder aus und aktualisiert self.plan_data + manager.
        """
        debug_print(f"TransferPlanWidget.save_plan() aufgerufen, plan_id={self.plan_data.get('id')}")
        self.plan_data["name"] = self.edit_name.text().strip()
        self.plan_data["source_type"] = self.source_type_combo.currentText()
        self.plan_data["source_path"] = self.edit_source_path.text().strip()
        self.plan_data["destination_path"] = self.edit_destination_path.text().strip()
        self.plan_data["version_mode"] = self.version_mode_combo.currentText()
        self.plan_data["schedule"] = self.edit_schedule.text().strip()

        # In Manager übernehmen
        self.manager.update_plan(self.plan_data["id"], self.plan_data)

        # Kopfzeile updaten
        self.name_label.setText(self.plan_data["name"])
        QtWidgets.QMessageBox.information(self, "Gespeichert", "Plan wurde aktualisiert.")