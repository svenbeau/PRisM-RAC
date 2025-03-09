#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore

# Wir verwenden den EditorDialog aus dem bisherigen json_explorer.py – bitte stelle sicher, dass diese Datei vorhanden ist!
from ui.json_explorer import JSONEditorDialog
from utils.config_manager import save_settings, debug_print
from ui.json_editor_dialog import JSONEditorDialog

class JSONExplorerWidget(QtWidgets.QWidget):
    """
    Ein Widget, das:
      - Über ein Dropdown die zuletzt verwendeten Ordner anzeigt
      - Zusätzlich einen 'Browse'-Button bereitstellt, um per QFileDialog einen neuen Ordner auszuwählen
      - In diesem Ordner alle JSON-Dateien auflistet
      - Per Doppelklick oder "Öffnen"-Button einen JSONEditorDialog öffnet
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Wir gehen davon aus, dass in settings der Schlüssel "recent_dirs" enthalten ist
        self.recent_dirs = self.settings.get("recent_dirs", [])
        if not self.recent_dirs:
            self.recent_dirs = [QtCore.QDir.homePath()]
        self.current_folder = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Oberer Bereich: Dropdown-Menü für Ordner und ein Browse-Button
        folder_layout = QtWidgets.QHBoxLayout()
        self.folder_combo = QtWidgets.QComboBox(self)
        self.folder_combo.addItems(self.recent_dirs)
        self.folder_combo.currentIndexChanged.connect(self.load_file_list)
        folder_layout.addWidget(self.folder_combo, stretch=1)

        self.browse_btn = QtWidgets.QPushButton("Browse", self)
        self.browse_btn.clicked.connect(self.browse_for_folder)
        folder_layout.addWidget(self.browse_btn, stretch=0)
        layout.addLayout(folder_layout)

        # Liste der JSON-Dateien
        self.file_list = QtWidgets.QListWidget(self)
        self.file_list.itemDoubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.file_list, stretch=1)

        # Button-Leiste unten
        btn_layout = QtWidgets.QHBoxLayout()
        self.open_btn = QtWidgets.QPushButton("Öffnen", self)
        self.open_btn.clicked.connect(self.open_selected_file)
        self.cancel_btn = QtWidgets.QPushButton("Zurück", self)
        self.cancel_btn.clicked.connect(self.on_back)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.load_file_list()

    def browse_for_folder(self):
        """
        Öffnet einen Dateiauswahldialog, um einen neuen Ordner auszuwählen.
        Wird ein Ordner ausgewählt, wird dieser in das Dropdown (an erster Stelle) eingefügt und
        die Liste der JSON-Dateien neu geladen.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", self.folder_combo.currentText())
        if folder:
            if folder not in self.recent_dirs:
                self.recent_dirs.insert(0, folder)
                self.folder_combo.insertItem(0, folder)
                self.folder_combo.setCurrentIndex(0)
            else:
                idx = self.folder_combo.findText(folder)
                self.folder_combo.setCurrentIndex(idx)

            self.settings["recent_dirs"] = self.recent_dirs
            save_settings(self.settings)
            self.load_file_list()

    def load_file_list(self):
        """Lädt die JSON-Dateien aus dem aktuell ausgewählten Ordner."""
        folder = self.folder_combo.currentText()
        self.current_folder = folder
        self.file_list.clear()
        if os.path.isdir(folder):
            files = os.listdir(folder)
            json_files = [f for f in files if f.lower().endswith(".json")]
            self.file_list.addItems(json_files)
        else:
            QtWidgets.QMessageBox.warning(self, "Warnung", "Kein gültiger Ordner ausgewählt.")

    def open_selected_file(self):
        """Öffnet den JSONEditorDialog für die ausgewählte JSON-Datei."""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        filename = selected_items[0].text()
        full_path = os.path.join(self.current_folder, filename)
        editor = JSONEditorDialog(full_path, parent=self)
        editor.exec_()

    def on_back(self):
        """
        Optional: Wenn "Zurück" gedrückt wird, kann der Eltern-Widget-Index gesetzt werden.
        Hier wird beispielsweise der QStackedWidget-Index auf 0 gesetzt.
        """
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, QtWidgets.QStackedWidget):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.setCurrentIndex(0)

if __name__ == "__main__":
    # Zum Testen des Widgets (direktes Ausführen)
    import sys
    app = QtWidgets.QApplication(sys.argv)
    test_settings = {"recent_dirs": [os.path.expanduser("~")]}
    widget = JSONExplorerWidget(test_settings)
    widget.show()
    sys.exit(app.exec_())