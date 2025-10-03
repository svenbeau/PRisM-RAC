#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore

from ui.json_explorer import JSONEditorDialog
from ui.json_editor_dialog import JSONEditorDialog
from utils.config_manager import get_recent_json_dirs, update_recent_json_dirs

class JSONExplorerWidget(QtWidgets.QWidget):
    """
    Ein Widget, das:
      - Über ein Dropdown die zuletzt verwendeten Ordner (für JSON-Dateien) anzeigt
      - Zusätzlich einen 'Browse'-Button bereitstellt, um per QFileDialog einen neuen Ordner auszuwählen
      - In diesem Ordner alle JSON-Dateien auflistet
      - Per Doppelklick oder "Öffnen"-Button einen JSONEditorDialog öffnet
    """
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        # Speichere das Settings-Dict (falls übergeben) oder ein leeres
        self.settings = settings or {}
        self.current_folder = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Oberer Bereich: Dropdown-Menü für Ordner + Browse-Button
        folder_layout = QtWidgets.QHBoxLayout()
        self.folder_combo = QtWidgets.QComboBox(self)
        self.refresh_folder_combo()
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

    def refresh_folder_combo(self):
        """
        Lädt die aktuelle Liste der JSON-Verzeichnisse und befüllt das ComboBox-Menü.
        """
        self.folder_combo.clear()
        dirs = get_recent_json_dirs()
        for d in dirs:
            self.folder_combo.addItem(d)

    def browse_for_folder(self):
        # Start im aktuell ausgewählten Ordner oder Home
        start_dir = self.folder_combo.currentText() or QtCore.QDir.homePath()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", start_dir)
        if folder:
            update_recent_json_dirs(folder)
            self.refresh_folder_combo()
            idx = self.folder_combo.findText(folder)
            if idx >= 0:
                self.folder_combo.setCurrentIndex(idx)
            self.load_file_list()
        else:
            QtWidgets.QMessageBox.warning(self, "Warnung", "Kein gültiger Ordner ausgewählt.")

    def load_file_list(self):
        """
        Lädt die JSON-Dateien aus dem aktuell ausgewählten Ordner und zeigt sie in self.file_list an.
        """
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
        """
        Öffnet den JSONEditorDialog für die ausgewählte JSON-Datei.
        """
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        filename = selected_items[0].text()
        full_path = os.path.join(self.current_folder, filename)
        if os.path.isfile(full_path):
            editor = JSONEditorDialog(full_path, parent=self)
            editor.exec_()
        else:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Datei nicht gefunden:\n{full_path}")

    def on_back(self):
        """
        Beispiel-Funktion: Wechselt im übergeordneten QStackedWidget zurück auf einen anderen Index.
        """
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, QtWidgets.QStackedWidget):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.setCurrentIndex(0)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Beispiel: Wir simulieren ein Settings-Dict
    test_settings = {}
    widget = JSONExplorerWidget(settings=test_settings)
    widget.show()
    sys.exit(app.exec_())