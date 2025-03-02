#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore
from config.config_manager import save_settings, debug_print
from ui.script_recipe_widget import ScriptRecipeWidget

class SettingsWidget(QtWidgets.QWidget):
    """
    Widget für Einstellungen, enthält zwei Tabs:
      1) Allgemein
      2) Script › Rezept Zuordnung
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # Tab 1: Allgemein
        self.general_tab = QtWidgets.QWidget()
        self.general_layout = QtWidgets.QVBoxLayout(self.general_tab)
        self.general_layout.addWidget(QtWidgets.QLabel("Allgemeine Einstellungen (noch leer)"))
        self.general_layout.addStretch()
        self.tab_widget.addTab(self.general_tab, "Allgemein")

        # Tab 2: Script-Rezept Zuordnung
        self.script_recipe_tab = QtWidgets.QWidget()
        self.script_recipe_layout = QtWidgets.QVBoxLayout(self.script_recipe_tab)
        # Wir erstellen das ScriptRecipeWidget:
        self.script_recipe_widget = ScriptRecipeWidget(self.settings, parent=self.script_recipe_tab)
        self.script_recipe_layout.addWidget(self.script_recipe_widget, stretch=1)
        self.tab_widget.addTab(self.script_recipe_tab, "Script › Rezept Zuordnung")

        # Unten ein Button zum Speichern (optional)
        self.btn_save = QtWidgets.QPushButton("Einstellungen speichern")
        self.btn_save.clicked.connect(self.save_settings)
        main_layout.addWidget(self.btn_save, alignment=QtCore.Qt.AlignRight)

    def save_settings(self):
        # Wir speichern die settings.json
        save_settings(self.settings)
        debug_print("Einstellungen gespeichert.")