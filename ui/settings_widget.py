#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.script_recipe_widget import ScriptRecipeWidget

class SettingsWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
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
        gen_layout.addWidget(QtWidgets.QLabel("Allgemeine Einstellungen (noch leer)"))
        gen_layout.addStretch()
        # Optional: am Ende "Speichern" etc.

        # 2) Script-Rezept
        self.script_recipe_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.script_recipe_tab, "Script › Rezept")

        tab_layout = QtWidgets.QVBoxLayout(self.script_recipe_tab)
        self.script_recipe_widget = ScriptRecipeWidget(self.settings, parent=self.script_recipe_tab)
        tab_layout.addWidget(self.script_recipe_widget, stretch=1)

        # Optional: Unten ein Save-Button oder so
        btn_hlay = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")
        btn_hlay.addStretch()
        btn_hlay.addWidget(self.save_btn)
        tab_layout.addLayout(btn_hlay)

        # Connect
        self.save_btn.clicked.connect(self.on_save)

    def on_save(self):
        # Falls du hier globale Settings speichern willst:
        # z.B. self.script_recipe_widget.on_save()
        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")