#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from PyQt5 import QtWidgets, QtCore


class JSONEditorDialog(QtWidgets.QDialog):
    """
    Ein einfacher JSON-Editor-Dialog.
    Lädt den Inhalt einer JSON-Datei in ein QPlainTextEdit,
    ermöglicht die Bearbeitung und speichert die Datei nach Validierung.
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
        # Optionale Anpassungen: Schriftart, Tabstopps etc.
        font = self.text_edit.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit)

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
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der Datei:\n{e}")

    def save_json(self):
        try:
            json_str = self.text_edit.toPlainText()
            # Validierung des JSON-Formats
            data = json.loads(json_str)
            with open(self.json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Datei:\n{e}")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # Beispiel: Pfad zur JSON-Datei (anpassen)
    editor = JSONEditorDialog("config/GrisebachRecipes_2025_01/BeispielRezept.json")
    if editor.exec_() == QtWidgets.QDialog.Accepted:
        print("JSON erfolgreich gespeichert!")
    sys.exit(app.exec_())