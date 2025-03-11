#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore, QtGui

# Falls du den ScriptRecipeWidget weiter verwenden willst
from ui.script_recipe_widget import ScriptRecipeWidget

# Wenn du den ConfigManager zum Speichern verwenden möchtest:
from utils.config_manager import save_settings, debug_print

class SettingsWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Stelle sicher, dass resource_paths existiert
        if "resource_paths" not in self.settings:
            self.settings["resource_paths"] = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5)

        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # 1) Allgemein
        self.general_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.general_tab, "Allgemein")
        gen_layout = QtWidgets.QVBoxLayout(self.general_tab)
        gen_layout.setContentsMargins(5,5,5,5)
        gen_layout.setSpacing(5)

        # --- (A) Gruppe für allgemeine Einstellungen ---
        self.general_group = QtWidgets.QGroupBox("Allgemeine Einstellungen")
        self.general_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
            }
        """)
        group_layout = QtWidgets.QFormLayout(self.general_group)
        group_layout.setContentsMargins(5,5,5,5)
        group_layout.setSpacing(5)

        # (A1) Pfad für JSX-Templates
        self.jsx_templates_edit = QtWidgets.QLineEdit()
        self.jsx_templates_edit.setFixedWidth(500)  # feste Breite von 500 Pixeln
        # Vorbelegen mit dem aktuellen Wert aus settings
        current_jsx_path = self.settings["resource_paths"].get("jsx_templates", "")
        self.jsx_templates_edit.setText(current_jsx_path)

        self.jsx_browse_btn = QtWidgets.QPushButton("Browse")
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_folder)

        # Layout für das Label, QLineEdit und den Button
        jsx_layout = QtWidgets.QHBoxLayout()
        jsx_layout.addWidget(self.jsx_templates_edit, stretch=1)
        jsx_layout.addWidget(self.jsx_browse_btn, stretch=0)

        group_layout.addRow("JSX Templates:", jsx_layout)

        gen_layout.addWidget(self.general_group)
        gen_layout.addStretch()

        # 2) Script-Rezept
        self.script_recipe_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.script_recipe_tab, "Script › Rezept")

        tab_layout = QtWidgets.QVBoxLayout(self.script_recipe_tab)
        self.script_recipe_widget = ScriptRecipeWidget(self.settings, parent=self.script_recipe_tab)
        tab_layout.addWidget(self.script_recipe_widget, stretch=1)

        # (B) Unten ein Button zum Speichern
        btn_hlay = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")
        btn_hlay.addStretch()
        btn_hlay.addWidget(self.save_btn)
        tab_layout.addLayout(btn_hlay)

        # Connect
        self.save_btn.clicked.connect(self.on_save)

    def browse_jsx_folder(self):
        """
        Öffnet einen QFileDialog, damit der Benutzer einen Ordner für die JSX-Templates auswählen kann.
        """
        start_dir = self.jsx_templates_edit.text() or QtCore.QDir.homePath()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSX-Templates-Ordner auswählen", start_dir)
        if folder:
            self.jsx_templates_edit.setText(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Info", "Kein gültiger Ordner ausgewählt.")

    def on_save(self):
        """
        Wird aufgerufen, wenn der Benutzer auf "Einstellungen speichern" klickt.
        Speichert den Pfad zu den JSX-Templates in self.settings und ruft ggf. save_settings auf.
        """
        new_jsx_path = self.jsx_templates_edit.text().strip()
        if new_jsx_path:
            self.settings["resource_paths"]["jsx_templates"] = new_jsx_path
        else:
            # Falls der Nutzer das Feld geleert hat, kannst du hier entscheiden,
            # ob du den Eintrag entfernst oder einen Standardwert setzt.
            if "jsx_templates" in self.settings["resource_paths"]:
                del self.settings["resource_paths"]["jsx_templates"]

        # Beispiel: Globale Settings speichern
        save_settings(self.settings)
        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")