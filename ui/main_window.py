#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6 import QtWidgets, QtGui, QtCore

from utils.config_manager import load_settings, save_settings, debug_print
from ui.hotfolder_widget import HotfolderListWidget
from ui.logfile_widget import LogfileWidget
from ui.json_explorer_widget import JSONExplorerWidget
from ui.settings_widget import SettingsWidget

# Optional import: Der Dialog ist Teil von Variante 1
try:
    from ui.list_feeder_dialog import ListFeederDialog
except Exception:
    ListFeederDialog = None

DEBUG_OUTPUT = True

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRisM-RAC")
        self.resize(1500, 1200)
        self.settings = load_settings()
        self.init_ui()
        self._build_menu()
        self._build_toolbar()

    def init_ui(self):
        # Haupt-Widget + Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QtWidgets.QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(5, 5, 5, 5)
        main_vlayout.setSpacing(5)

        # Obere Leiste: Logo links, Debug-Button rechts
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)

        # Logo (linksbündig, 200x21px)
        logo_label = QtWidgets.QLabel()
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QtGui.QPixmap(logo_path)
            pixmap = pixmap.scaled(200, 21, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")
        top_bar.addWidget(logo_label, alignment=QtCore.Qt.AlignLeft)

        top_bar.addStretch()

        # Debug-Button
        self.debug_toggle_btn = QtWidgets.QPushButton("Debug Stop")
        self.debug_toggle_btn.setCheckable(True)
        self.debug_toggle_btn.setChecked(True)
        self.debug_toggle_btn.clicked.connect(self.toggle_debug)
        top_bar.addWidget(self.debug_toggle_btn, alignment=QtCore.Qt.AlignRight)

        main_vlayout.addLayout(top_bar)

        # Hauptbereich (horizontal): Links Buttons, rechts StackedWidget
        main_hlayout = QtWidgets.QHBoxLayout()
        main_vlayout.addLayout(main_hlayout, stretch=1)

        # Linke Buttons (Navigation)
        left_widget = QtWidgets.QWidget()
        left_vlayout = QtWidgets.QVBoxLayout(left_widget)
        left_vlayout.setContentsMargins(5, 5, 5, 5)

        self.hotfolder_btn = QtWidgets.QPushButton("Hotfolder")
        self.logfile_btn = QtWidgets.QPushButton("Logfile")
        self.json_editor_btn = QtWidgets.QPushButton("JSON-Editor")
        self.settings_btn = QtWidgets.QPushButton("Einstellungen")

        # NEU: Direkt zugänglicher Button für die Listen-Einspeisung
        self.feed_list_btn = QtWidgets.QPushButton("Liste einspeisen…")
        self.feed_list_btn.clicked.connect(self._open_list_feeder_dialog)

        left_vlayout.addWidget(self.hotfolder_btn)
        left_vlayout.addWidget(self.logfile_btn)
        left_vlayout.addWidget(self.json_editor_btn)
        left_vlayout.addWidget(self.settings_btn)
        left_vlayout.addSpacing(12)
        left_vlayout.addWidget(self.feed_list_btn)  # NEU
        left_vlayout.addStretch()

        main_hlayout.addWidget(left_widget, stretch=0)

        # Rechter Bereich: StackedWidget
        self.stack = QtWidgets.QStackedWidget()
        main_hlayout.addWidget(self.stack, stretch=1)

        # Widget 0: Hotfolder
        self.hotfolder_list_widget = HotfolderListWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.hotfolder_list_widget)

        # Widget 1: Logfile
        self.logfile_widget = LogfileWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.logfile_widget)

        # Widget 2: JSON Explorer
        self.json_explorer_widget = JSONExplorerWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.json_explorer_widget)

        # Widget 3: Settings
        self.settings_widget = SettingsWidget(self.settings, parent=self.stack)
        self.stack.addWidget(self.settings_widget)

        # Standard: Hotfolder (Index 0)
        self.stack.setCurrentIndex(0)

        # Button-Klicks
        self.hotfolder_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.logfile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.json_editor_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))

    # Menüleiste (macOS: oben am Bildschirm)
    def _build_menu(self):
        menubar = self.menuBar()

        # Datei-Menü (Platzhalter)
        menubar.addMenu("&Datei")

        # Extras-Menü
        extras_menu = menubar.addMenu("&Extras")
        self.action_feed_list = QtWidgets.QAction("Liste einspeisen…", self)
        self.action_feed_list.setShortcut(QtGui.QKeySequence("Ctrl+L"))  # macOS = ⌘L
        self.action_feed_list.setStatusTip("CSV-Liste auswählen und in einen Monitor-Ordner einspeisen")
        self.action_feed_list.triggered.connect(self._open_list_feeder_dialog)
        extras_menu.addAction(self.action_feed_list)

        # Hilfe-Menü (Platzhalter)
        menubar.addMenu("&Hilfe")

    # Optional: Toolbar-Icon für schnellen Zugriff
    def _build_toolbar(self):
        tb = self.addToolBar("Aktionen")
        tb.setMovable(False)
        act = QtWidgets.QAction("Liste einspeisen…", self)
        act.triggered.connect(self._open_list_feeder_dialog)
        tb.addAction(act)

    def _open_list_feeder_dialog(self):
        if ListFeederDialog is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Modul fehlt",
                "Der Dialog 'ListFeederDialog' ist nicht verfügbar.\n\n"
                "Bitte stelle sicher, dass die Datei\n"
                "ui/list_feeder_dialog.py\n"
                "im Projekt vorhanden ist."
            )
            return

        dlg = ListFeederDialog(self)

        # OPTIONAL: Wenn das Hotfolder-Widget einen aktuellen Monitor-Pfad liefert,
        # hier vorbelegen (API deines Widgets erforderlich).
        # Beispiel:
        # if hasattr(self.hotfolder_list_widget, "get_current_monitor_dir"):
        #     mon = self.hotfolder_list_widget.get_current_monitor_dir()
        #     if mon:
        #         dlg.monitor_edit.setText(mon)

        dlg.exec()

    def toggle_debug(self):
        global DEBUG_OUTPUT
        if self.debug_toggle_btn.isChecked():
            DEBUG_OUTPUT = True
            self.debug_toggle_btn.setText("Debug Stop")
        else:
            DEBUG_OUTPUT = False
            self.debug_toggle_btn.setText("Debug Start")
        debug_print(f"DEBUG_OUTPUT={DEBUG_OUTPUT}")

    def closeEvent(self, event):
        save_settings(self.settings)
        super().closeEvent(event)

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()