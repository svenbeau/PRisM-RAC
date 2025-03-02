#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Editor Dialog for PRisM-RAC.
Ermöglicht das Bearbeiten einer JSON-Datei mit den Optionen
"Speichern", "Speichern unter" und "Abbrechen".
"""

import os
import json
from PyQt5 import QtWidgets, QtCore

class JSONEditorDialog(QtWidgets.QDialog):
    def __init__(self, file_path, parent=None):
        super(JSONEditorDialog, self).__init__(parent)
        self.setWindowTitle("JSON Editor")
        self.resize(800, 600)
        self.file_path = file_path
        self.original_content = ""
        self.init_ui()
        self.load_file()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Textfeld zum Bearbeiten des JSON-Inhalts
        self.text_edit = QtWidgets.QTextEdit(self)
        layout.addWidget(self.text_edit)

        # Button-Leiste unten
        btn_layout = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Speichern", self)
        self.save_btn.clicked.connect(self.save_file)
        self.save_as_btn = QtWidgets.QPushButton("Speichern unter", self)
        self.save_as_btn.clicked.connect(self.save_file_as)
        self.cancel_btn = QtWidgets.QPushButton("Abbrechen", self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.save_as_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def load_file(self):
        """Lädt den JSON-Inhalt aus der Datei."""
        if os.path.isfile(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.original_content = f.read()
                self.text_edit.setPlainText(self.original_content)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler beim Laden der Datei:\n{e}")
        else:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Datei nicht gefunden:\n{self.file_path}")

    def save_file(self):
        """Speichert den aktuellen Inhalt in dieselbe Datei."""
        content = self.text_edit.toPlainText()
        try:
            # Prüfe, ob gültiges JSON vorliegt
            json.loads(content)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)
            QtWidgets.QMessageBox.information(self, "Erfolg", "Datei erfolgreich gespeichert.")
            self.accept()
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Ungültiges JSON:\n{e}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler beim Speichern der Datei:\n{e}")

    def save_file_as(self):
        """Speichert den aktuellen Inhalt unter einem neuen Dateinamen."""
        content = self.text_edit.toPlainText()
        options = QtWidgets.QFileDialog.Options()
        new_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Speichern unter", self.file_path, "JSON Files (*.json)", options=options)
        if new_file:
            try:
                # Prüfe, ob gültiges JSON vorliegt
                json.loads(content)
                with open(new_file, "w", encoding="utf-8") as f:
                    f.write(content)
                QtWidgets.QMessageBox.information(self, "Erfolg", "Datei erfolgreich gespeichert unter:\n" + new_file)
                self.file_path = new_file  # Aktualisiere den Dateipfad
                self.accept()
            except json.JSONDecodeError as e:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Ungültiges JSON:\n{e}")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler beim Speichern der Datei:\n{e}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Beispiel: Öffne den JSON Editor für eine Testdatei (hier ggf. anpassen)
    test_file = os.path.join(os.path.dirname(__file__), "test.json")
    dialog = JSONEditorDialog(test_file)
    if dialog.exec_():
        print("Gespeichert!")
    else:
        print("Abgebrochen!")