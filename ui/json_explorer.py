#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui

class JSONHighlighter(QtGui.QSyntaxHighlighter):
    """
    Ein einfacher Syntax-Highlighter für JSON.
    Hebt Schlüssel, Strings, Zahlen, boolesche Werte und null hervor.
    """
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        # Format für Schlüssel (Feldnamen)
        keyFormat = QtGui.QTextCharFormat()
        keyFormat.setForeground(QtGui.QColor("darkblue"))
        keyFormat.setFontWeight(QtGui.QFont.Bold)
        keyPattern = QtCore.QRegExp(r'\"(\\.|[^\"])*\"(?=\s*:)')
        self.rules.append((keyPattern, keyFormat))
        # Format für Strings
        stringFormat = QtGui.QTextCharFormat()
        stringFormat.setForeground(QtGui.QColor("darkgreen"))
        stringPattern = QtCore.QRegExp(r'\"(\\.|[^\"])*\"')
        self.rules.append((stringPattern, stringFormat))
        # Format für Zahlen
        numberFormat = QtGui.QTextCharFormat()
        numberFormat.setForeground(QtGui.QColor("darkred"))
        numberPattern = QtCore.QRegExp(r'\b[-+]?[0-9]*\.?[0-9]+\b')
        self.rules.append((numberPattern, numberFormat))
        # Format für boolesche Werte
        booleanFormat = QtGui.QTextCharFormat()
        booleanFormat.setForeground(QtGui.QColor("purple"))
        booleanPattern = QtCore.QRegExp(r'\b(true|false)\b')
        self.rules.append((booleanPattern, booleanFormat))
        # Format für null
        nullFormat = QtGui.QTextCharFormat()
        nullFormat.setForeground(QtGui.QColor("gray"))
        nullPattern = QtCore.QRegExp(r'\bnull\b')
        self.rules.append((nullPattern, nullFormat))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

class JSONEditorDialog(QtWidgets.QDialog):
    """
    Ein einfacher JSON-Editor-Dialog mit Syntax-Highlighting.
    Lädt den Inhalt einer JSON-Datei in ein QPlainTextEdit,
    ermöglicht die Bearbeitung und speichert nach Validierung.
    """
    def __init__(self, json_file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Editor")
        self.resize(1200, 600)
        self.json_file_path = json_file_path
        self.init_ui()
        self.load_json()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.text_edit = QtWidgets.QPlainTextEdit(self)
        font = QtGui.QFont("Courier New", 10)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit)
        self.highlighter = JSONHighlighter(self.text_edit.document())
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_json)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_json(self):
        try:
            with open(self.json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            json_str = json.dumps(data, indent=4, ensure_ascii=False)
            self.text_edit.setPlainText(json_str)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Fehler beim Laden der Datei:\n{e}")

    def save_json(self):
        try:
            json_str = self.text_edit.toPlainText()
            # Validierung
            data = json.loads(json_str)
            with open(self.json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Fehler beim Speichern der Datei:\n{e}")

class JSONExplorerDialog(QtWidgets.QDialog):
    """
    Ein JSON-Explorer, der:
      - Über ein Dropdown (mit den fünf zuletzt verwendeten Ordnern) einen Ordner auswählt.
      - In diesem Ordner werden alle JSON-Dateien in einer Liste angezeigt.
      - Bei Auswahl (Doppelklick oder über einen "Öffnen"-Button) wird der JSONEditorDialog geöffnet.
    """
    def __init__(self, recent_dirs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Explorer")
        self.resize(600, 400)
        self.recent_dirs = recent_dirs  # Liste der zuletzt verwendeten Ordner
        self.current_folder = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Dropdown für Ordner
        self.folder_combo = QtWidgets.QComboBox(self)
        self.folder_combo.addItems(self.recent_dirs)
        self.folder_combo.currentIndexChanged.connect(self.load_file_list)
        layout.addWidget(self.folder_combo)
        # Liste der JSON-Dateien
        self.file_list = QtWidgets.QListWidget(self)
        self.file_list.itemDoubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.file_list, stretch=1)
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.open_btn = QtWidgets.QPushButton("Öffnen", self)
        self.cancel_btn = QtWidgets.QPushButton("Abbrechen", self)
        self.open_btn.clicked.connect(self.open_selected_file)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.load_file_list()

    def load_file_list(self):
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
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        filename = selected_items[0].text()
        full_path = os.path.join(self.current_folder, filename)
        editor = JSONEditorDialog(full_path, parent=self)
        editor.exec_()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Beispiel: Fünf zuletzt verwendete Ordner (können aus Einstellungen stammen)
    recent_dirs = [
        os.path.expanduser("~"),
        "/tmp",
        os.path.join(os.path.expanduser("~"), "Documents"),
        "/var",
        "/etc"
    ]
    explorer = JSONExplorerDialog(recent_dirs)
    explorer.exec_()
    sys.exit(app.exec_())