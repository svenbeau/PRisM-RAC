#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from ui.script_recipe_widget import ScriptRecipeWidget


class SettingsWidget(QtWidgets.QWidget):
    """
    Das Settings‑Widget enthält zwei Tabs:
      - "Allgemein" (der vorerst leer ist)
      - "Script › Rezept Zuordnung", in dem Du die Zuordnung der Skripte und zugehörigen JSON‑Ordner konfigurieren kannst.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # Allgemein Tab – vorerst leer
        general_tab = QtWidgets.QWidget()
        general_layout = QtWidgets.QVBoxLayout(general_tab)
        general_label = QtWidgets.QLabel("Allgemeine Einstellungen (noch leer)")
        general_layout.addWidget(general_label)
        general_layout.addStretch()
        self.tab_widget.addTab(general_tab, "Allgemein")

        # Script › Rezept Zuordnung Tab
        script_recipe_tab = QtWidgets.QWidget()
        script_recipe_layout = QtWidgets.QVBoxLayout(script_recipe_tab)
        self.script_recipe_widget = ScriptRecipeWidget(self.settings, parent=self)
        script_recipe_layout.addWidget(self.script_recipe_widget)
        self.tab_widget.addTab(script_recipe_tab, "Script › Rezept Zuordnung")

        layout.addStretch()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    test_settings = {"script_configs": []}
    widget = SettingsWidget(test_settings)
    widget.show()
    sys.exit(app.exec_())