#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from PySide6 import QtWidgets, QtGui
from utils.config_manager import save_settings, debug_print


class JSONEditorDialog(QtWidgets.QDialog):
    """
    Ein einfacher JSON-Editor.
    Neben der normalen Bearbeitung gibt es zwei zusätzliche Buttons:
      - "Speichern unter": Öffnet einen Dateiauswahldialog, um die aktuelle Datei unter neuem Namen zu speichern.
      - "Cancel": Bricht die Bearbeitung ab.
    """

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Editor")
        self.file_path = file_path
        self.init_ui()
        self.load_file()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Text-Editor (PlainTextEdit) für JSON-Inhalt
        self.text_edit = QtWidgets.QPlainTextEdit(self)
        font = QtGui.QFont("Courier", 10)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit)

        # Buttons-Leiste
        btn_layout = QtWidgets.QHBoxLayout()

        self.save_as_btn = QtWidgets.QPushButton("Speichern unter", self)
        self.save_as_btn.clicked.connect(self.save_as)
        btn_layout.addWidget(self.save_as_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel", self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.resize(600, 400)

    def load_file(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_edit.setPlainText(content)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler beim Laden der Datei:\n{e}")

    def save_as(self):
        options = QtWidgets.QFileDialog.Options()
        new_file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Speichern unter",
            self.file_path,
            "JSON Files (*.json);;Alle Dateien (*)",
            options=options
        )
        if new_file:
            try:
                content = self.text_edit.toPlainText()
                # Validierung: Versuche, den Text als JSON zu parsen
                json.loads(content)
                with open(new_file, "w", encoding="utf-8") as f:
                    f.write(content)
                QtWidgets.QMessageBox.information(self, "Erfolg", "Datei erfolgreich gespeichert.")
                self.accept()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler beim Speichern:\n{e}")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # Testweise: Öffne einen Editor für eine Test-Datei
    dlg = JSONEditorDialog("test.json")
    dlg.exec_()