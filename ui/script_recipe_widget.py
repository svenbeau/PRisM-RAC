#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6 import QtWidgets, QtCore, QtGui
from utils.script_config_manager import debug_print, ScriptConfigManager
from ui.script_recipe_dialog import ScriptRecipeDialog

def resource_path(relative_path):
    """Gibt den absoluten Pfad zur Ressource zurück – funktioniert im Entwicklungsmodus und im PyInstaller-Bundle."""
    try:
        # Wenn wir per PyInstaller laufen:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ScriptRecipeWidget(QtWidgets.QFrame):
    def __init__(self, script_data: dict, parent=None):
        super().__init__(parent)
        self.script_data = script_data
        # Wir lesen body_visible aus dem Dictionary
        self.body_visible = script_data.get("body_visible", False)

        self.icon_expand = QtGui.QIcon(resource_path("assets/dropdown_list.png"))
        self.icon_collapse = QtGui.QIcon(resource_path("assets/close_list.png"))
        self.setup_ui()

    def setup_ui(self):
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Titelzeile
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("background-color: #2b2b2b;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        self.title_label = QtWidgets.QLabel(self.script_data.get("name", "Unbenannt"))
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(self.title_label, 1, QtCore.Qt.AlignVCenter)

        self.toggle_btn = QtWidgets.QPushButton()
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setIcon(self.icon_collapse if self.body_visible else self.icon_expand)
        self.toggle_btn.clicked.connect(self.on_toggle_body)
        title_layout.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.title_bar)

        # Subheader
        self.subheader_frame = QtWidgets.QFrame()
        self.subheader_frame.setFixedHeight(30)
        self.subheader_frame.setStyleSheet("background-color: #b0b0b0;")
        subheader_layout = QtWidgets.QHBoxLayout(self.subheader_frame)
        subheader_layout.setContentsMargins(10, 5, 10, 5)
        subheader_layout.setSpacing(0)
        self.subheader_label = QtWidgets.QLabel("Script, JSON-Folder, Action Folder, Basic Wand Files, CSV Wand File, Wand File Save Path")
        self.subheader_label.setStyleSheet("color: #000000; font-weight: bold;")
        subheader_layout.addWidget(self.subheader_label, 1, QtCore.Qt.AlignLeft)
        main_layout.addWidget(self.subheader_frame)

        # Body
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        self.config_group = QtWidgets.QGroupBox("Konfiguration")
        self.config_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        config_layout = QtWidgets.QVBoxLayout(self.config_group)

        self.script_label = self.create_label("Script: " + (os.path.basename(self.script_data.get("script_path","")) or "(none)"), 0)
        self.json_label   = self.create_label("JSON-Folder: " + self.script_data.get("json_folder",""), 1)
        self.action_label = self.create_label("Action Folder: " + self.script_data.get("actionFolderName",""), 2)
        self.basic_label  = self.create_label("Basic Wand Files: " + self.script_data.get("basicWandFiles",""), 3)
        self.csv_label    = self.create_label("CSV Wand File: " + self.script_data.get("csvWandFile",""), 4)
        self.save_label   = self.create_label("Wand File Save Path: " + self.script_data.get("wandFileSavePath",""), 5)

        for lbl in [self.script_label, self.json_label, self.action_label,
                    self.basic_label, self.csv_label, self.save_label]:
            config_layout.addWidget(lbl)

        body_layout.addWidget(self.config_group)
        self.body_widget.setLayout(body_layout)
        main_layout.addWidget(self.body_widget)

        # Button-Leiste unten
        self.button_bar = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(self.button_bar)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit)
        button_layout.addWidget(self.edit_btn)
        main_layout.addWidget(self.button_bar)

        # Sichtbarkeit
        self.body_widget.setVisible(self.body_visible)
        self.update_labels()

    def create_label(self, text, row_index):
        lbl = QtWidgets.QLabel(text)
        lbl.setMinimumHeight(24)
        lbl.setStyleSheet(f"""
            color: #000000;
            padding: 4px;
            background-color: {'#f7f7f7' if row_index % 2 == 0 else '#e5e5e5'};
        """)
        return lbl

    def on_toggle_body(self):
        self.body_visible = not self.body_visible
        self.body_widget.setVisible(self.body_visible)
        self.toggle_btn.setIcon(self.icon_collapse if self.body_visible else self.icon_expand)
        self.script_data["body_visible"] = self.body_visible

        # Speichern der body_visible-Änderung
        mgr = ScriptConfigManager()
        mgr.update_script(self.script_data["id"], self.script_data)

    def on_edit(self):
        dlg = ScriptRecipeDialog(self.script_data, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            debug_print("ScriptRecipe geändert, reload.")
            self.update_labels()
            # Neu laden
            parent_widget = self.parent()
            while parent_widget and not hasattr(parent_widget, "load_scripts"):
                parent_widget = parent_widget.parent()
            if parent_widget and hasattr(parent_widget, "load_scripts"):
                parent_widget.load_scripts()
        else:
            debug_print("ScriptRecipe-Dialog abgebrochen.")

    def update_labels(self):
        debug_print("Aktualisiere ScriptRecipeWidget-Labels.")
        self.title_label.setText(self.script_data.get("name", "Unbenannt"))
        self.script_label.setText("Script: " + (os.path.basename(self.script_data.get("script_path","")) or "(none)"))
        self.json_label.setText("JSON-Folder: " + self.script_data.get("json_folder",""))
        self.action_label.setText("Action Folder: " + self.script_data.get("actionFolderName",""))
        self.basic_label.setText("Basic Wand Files: " + self.script_data.get("basicWandFiles",""))
        self.csv_label.setText("CSV Wand File: " + self.script_data.get("csvWandFile",""))
        self.save_label.setText("Wand File Save Path: " + self.script_data.get("wandFileSavePath",""))