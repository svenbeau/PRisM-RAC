#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui

# Import your existing widgets:
# (Only if you have them in the same package, e.g. `ui.hotfolder_widget`, `ui.logfile_widget`, etc.)
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget
from ui.script_recipe_widget import ScriptRecipeWidget

from config.config_manager import load_settings, save_settings, debug_print

class MainWindow(QtWidgets.QMainWindow):
    """
    The main window of PRisM-RAC, with:
      - A top logo area
      - A left sidebar with buttons for each page (Hotfolder, Logfile, JSON Editor, Settings, Script:Rezeptzuordnung)
      - A central QStackedWidget to hold the pages
      - A "Debug Stop" button at the bottom or top-right
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-RAC")
        self.resize(1200, 800)

        # Load main settings from disk
        self.settings = load_settings()

        # Main central widget
        central_widget = QtWidgets.QWidget(self)
        central_layout = QtWidgets.QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Top bar with logo & debug button
        self.top_bar = QtWidgets.QWidget()
        self.top_bar.setFixedHeight(60)
        self.top_bar.setStyleSheet("background-color: #f0f0f0;")
        top_bar_layout = QtWidgets.QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(10, 5, 10, 5)
        top_bar_layout.setSpacing(10)

        # Logo on the left
        self.logo_label = QtWidgets.QLabel()
        # Load your existing image asset if you have it:
        # example: pix = QtGui.QPixmap("assets/logo.png")
        # self.logo_label.setPixmap(pix.scaledToHeight(40, QtCore.Qt.SmoothTransformation))
        self.logo_label.setText("RECOM ART CARE")  # fallback text
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(14)
        self.logo_label.setFont(font)

        top_bar_layout.addWidget(self.logo_label, 0, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        # Spacer
        top_bar_layout.addStretch()

        # Debug Stop button on the right
        self.debug_button = QtWidgets.QPushButton("Debug Stop")
        self.debug_button.clicked.connect(self.on_debug_stop)
        top_bar_layout.addWidget(self.debug_button, 0, QtCore.Qt.AlignRight)

        central_layout.addWidget(self.top_bar, 0)

        # Main content area: horizontal split: left side nav, right side stacked pages
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left side navigation
        self.nav_widget = QtWidgets.QWidget()
        self.nav_widget.setFixedWidth(120)
        nav_layout = QtWidgets.QVBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(5)

        self.btn_hotfolder = QtWidgets.QPushButton("Hotfolder")
        self.btn_hotfolder.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        nav_layout.addWidget(self.btn_hotfolder)

        self.btn_logfile = QtWidgets.QPushButton("Logfile")
        self.btn_logfile.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav_layout.addWidget(self.btn_logfile)

        self.btn_jsoneditor = QtWidgets.QPushButton("JSON-Editor")
        self.btn_jsoneditor.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        nav_layout.addWidget(self.btn_jsoneditor)

        self.btn_settings = QtWidgets.QPushButton("Einstellungen")
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        nav_layout.addWidget(self.btn_settings)

        self.btn_script_recipe = QtWidgets.QPushButton("Script\nRezept")
        self.btn_script_recipe.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        nav_layout.addWidget(self.btn_script_recipe)

        nav_layout.addStretch()

        content_layout.addWidget(self.nav_widget, 0)

        # Stacked widget for pages
        self.stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        central_layout.addWidget(content_widget, 1)

        # Now create each page:
        self.hotfolder_page = self.create_hotfolder_page()
        self.logfile_page = self.create_logfile_page()
        self.json_page = self.create_jsoneditor_page()
        self.settings_page = self.create_settings_page()
        self.script_recipe_page = self.create_script_recipe_page()

        # Add them to the stacked widget
        self.stack.addWidget(self.hotfolder_page)
        self.stack.addWidget(self.logfile_page)
        self.stack.addWidget(self.json_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.script_recipe_page)

        self.stack.setCurrentIndex(0)

    def create_hotfolder_page(self):
        """Wrap the HotfolderListWidget in a simple layout/page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.hotfolder_widget = HotfolderListWidget(self.settings, parent=page)
        layout.addWidget(self.hotfolder_widget, 1)

        return page

    def create_logfile_page(self):
        """Wrap the LogfileWidget in a simple layout/page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.logfile_widget = LogfileWidget(self.settings, parent=page)
        layout.addWidget(self.logfile_widget, 1)

        return page

    def create_jsoneditor_page(self):
        """Wrap the JSONExplorerWidget in a simple layout/page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=page)
        layout.addWidget(self.json_explorer_widget, 1)

        return page

    def create_settings_page(self):
        """Wrap the SettingsWidget in a simple layout/page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.settings_widget = SettingsWidget(self.settings, parent=page)
        layout.addWidget(self.settings_widget, 1)

        return page

    def create_script_recipe_page(self):
        """Wrap the ScriptRecipeWidget in a simple layout/page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.script_recipe_widget = ScriptRecipeWidget(self.settings, parent=page)
        layout.addWidget(self.script_recipe_widget, 1)

        return page

    def on_debug_stop(self):
        debug_print("Debug Stop clicked.")
        # You can put any debugging or close logic here
        self.close()


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())