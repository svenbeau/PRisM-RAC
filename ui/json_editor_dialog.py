#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Editor Dialog for PRisM-RAC.
Ermöglicht das Bearbeiten einer JSON-Datei mit den Optionen
"Speichern", "Speichern unter" und "Abbrechen".
"""

import os
import json
import re
from PyQt5 import QtWidgets, QtCore, QtGui


class JSONHighlighter(QtGui.QSyntaxHighlighter):
    """
    Syntax-Highlighter-Klasse für JSON mit farblicher Unterscheidung ähnlich dem
    dunklen Farbschema wie im Screenshot gezeigt.
    - Unterschiedliche Farben für Top-Level-Keys und Array-Keys
    - Unterstützung für helles und dunkles Theme
    """

    def __init__(self, document, dark_theme=True):
        super(JSONHighlighter, self).__init__(document)

        self.dark_theme = dark_theme

        # Farben basierend auf dem Farbschema im Screenshot
        if dark_theme:
            # Farbdefinitionen für dunkles Thema
            self.brace_color = QtGui.QColor("#FFFFFF")  # Weiß für geschweifte Klammern
            self.array_color = QtGui.QColor("#6B9BD2")  # Blau für Arrays
            self.punctuation_color = QtGui.QColor("#BBBBBB")  # Hellgrau für Kommas, Doppelpunkte
            self.number_color = QtGui.QColor("#B5CEA8")  # Hellgrün für Zahlen
            self.bool_null_color = QtGui.QColor("#569CD6")  # Blau für true/false/null
            self.string_color = QtGui.QColor("#CE9178")  # Orange-rot für Strings
            self.top_level_key_color = QtGui.QColor("#9CDCFE")  # Hellblau für Top-Level-Keys
            self.array_key_color = QtGui.QColor("#4EC9B0")  # Türkis für Keys in Arrays
            self.other_key_color = QtGui.QColor("#9CDCFE")  # Hellblau für alle anderen Keys
        else:
            # Farbdefinitionen für helles Thema
            self.brace_color = QtGui.QColor("#000000")  # Schwarz für geschweifte Klammern
            self.array_color = QtGui.QColor("#0000FF")  # Blau für Arrays
            self.punctuation_color = QtGui.QColor("#666666")  # Grau für Kommas, Doppelpunkte
            self.number_color = QtGui.QColor("#008000")  # Grün für Zahlen
            self.bool_null_color = QtGui.QColor("#0000FF")  # Blau für true/false/null
            self.string_color = QtGui.QColor("#A31515")  # Rot für Strings
            self.top_level_key_color = QtGui.QColor("#0451A5")  # Dunkelblau für Top-Level-Keys
            self.array_key_color = QtGui.QColor("#008080")  # Petrolblau für Keys in Arrays
            self.other_key_color = QtGui.QColor("#0451A5")  # Dunkelblau für alle anderen Keys

    def highlightBlock(self, text):
        """
        Verbesserte Highlight-Methode, die JSON-Strukturen berücksichtigt
        und zwischen Top-Level-Keys und Array-Keys unterscheidet.
        """
        # Wir müssen den gesamten Text betrachten, um die Struktur zu verstehen
        document = self.document()
        full_text = document.toPlainText()
        current_block_number = self.currentBlock().blockNumber()

        # Grundlegende Syntax-Elemente mit einfachen Regex-Regeln hervorheben
        self._highlight_basic_syntax(text)

        # Für die korrekte Einfärbung von Keys je nach Kontext benötigen wir die Struktur
        if '"' in text:  # Nur verarbeiten, wenn potenzielle Keys vorhanden sind
            self._highlight_keys_contextually(text, full_text, current_block_number)

    def _highlight_basic_syntax(self, text):
        """Hebt grundlegende JSON-Syntax-Elemente hervor"""
        # Geschweifte Klammern
        brace_format = QtGui.QTextCharFormat()
        brace_format.setForeground(self.brace_color)
        for match in re.finditer(r'[{}]', text):
            self.setFormat(match.start(), match.end() - match.start(), brace_format)

        # Array-Klammern
        array_format = QtGui.QTextCharFormat()
        array_format.setForeground(self.array_color)
        for match in re.finditer(r'[\[\]]', text):
            self.setFormat(match.start(), match.end() - match.start(), array_format)

        # Satzzeichen (Kommas, Doppelpunkte)
        punctuation_format = QtGui.QTextCharFormat()
        punctuation_format.setForeground(self.punctuation_color)
        for match in re.finditer(r'[,:]', text):
            self.setFormat(match.start(), match.end() - match.start(), punctuation_format)

        # Zahlen
        number_format = QtGui.QTextCharFormat()
        number_format.setForeground(self.number_color)
        for match in re.finditer(r'\b[-+]?(?:\d*\.\d+|\d+)\b', text):
            self.setFormat(match.start(), match.end() - match.start(), number_format)

        # Booleans und null
        bool_null_format = QtGui.QTextCharFormat()
        bool_null_format.setForeground(self.bool_null_color)
        for match in re.finditer(r'\b(true|false|null)\b', text):
            self.setFormat(match.start(), match.end() - match.start(), bool_null_format)

        # Strings (allgemein)
        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(self.string_color)
        # Für Strings verwenden wir eine etwas kompliziertere Regex, um auch Escape-Sequenzen zu berücksichtigen
        for match in re.finditer(r'"(?:\\.|[^"\\])*"', text):
            self.setFormat(match.start(), match.end() - match.start(), string_format)

    def _highlight_keys_contextually(self, text, full_text, current_block_number):
        """
        Hebt JSON-Keys basierend auf ihrem Kontext unterschiedlich hervor:
        - Top-Level-Keys ("source", "target", "outputs")
        - Array-Keys (Keys innerhalb eines Arrays)
        - Andere Keys (alle anderen)
        """
        # Erst alle Keys finden (Strings gefolgt von Doppelpunkt)
        key_matches = list(re.finditer(r'"(.*?)"(?=\s*:)', text))

        if not key_matches:
            return

        # Ermitteln der Einrückungsebene und Kontext anhand des vollständigen Textes
        lines = full_text.split('\n')
        current_line = lines[current_block_number] if current_block_number < len(lines) else ""

        # Einrückungsebene durch Analyse des Whitespaces am Zeilenanfang bestimmen
        indent_level = len(current_line) - len(current_line.lstrip())

        # Top-Level-Keys haben normalerweise die geringste Einrückung
        for match in key_matches:
            key_name = match.group(1)  # Der Name des Keys ohne Anführungszeichen
            key_start = match.start()
            key_length = match.end() - match.start()

            # Bestimme die Farbe basierend auf Einrückung und Namen
            if indent_level <= 4:  # Top-Level oder direkt darunter
                # Spezifische Keys auf der obersten Ebene
                if key_name in ["source", "target", "outputs"]:
                    key_format = QtGui.QTextCharFormat()
                    key_format.setForeground(self.top_level_key_color)
                    self.setFormat(key_start, key_length, key_format)
                else:
                    key_format = QtGui.QTextCharFormat()
                    key_format.setForeground(self.other_key_color)
                    self.setFormat(key_start, key_length, key_format)
            else:  # Keys in tieferen Ebenen (z.B. Arrays)
                # Spezifische Array-Keys
                if key_name in ["name", "photoshopAction", "outputFolder", "suffix",
                                "filetype", "backside", "backsideAction", "backsideSuffix"]:
                    key_format = QtGui.QTextCharFormat()
                    key_format.setForeground(self.array_key_color)
                    self.setFormat(key_start, key_length, key_format)
                else:
                    key_format = QtGui.QTextCharFormat()
                    key_format.setForeground(self.other_key_color)
                    self.setFormat(key_start, key_length, key_format)


class JSONEditorDialog(QtWidgets.QDialog):
    def __init__(self, file_path, parent=None, dark_theme=True):
        super(JSONEditorDialog, self).__init__(parent)
        self.setWindowTitle("JSON Editor")
        self.resize(800, 600)
        self.file_path = file_path
        self.original_content = ""
        self.dark_theme = dark_theme
        self.init_ui()
        self.load_file()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Textfeld zum Bearbeiten des JSON-Inhalts
        self.text_edit = QtWidgets.QTextEdit(self)

        # Stil für Theme anwenden
        self.apply_theme()

        layout.addWidget(self.text_edit)

        # Syntax-Highlighting für JSON aktivieren
        self.highlighter = JSONHighlighter(self.text_edit.document(), self.dark_theme)

        # Theme-Toggle-Button
        theme_btn = QtWidgets.QPushButton("Wechsel zu " + ("Hellem" if self.dark_theme else "Dunklem") + " Theme", self)
        theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_btn)

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

    def apply_theme(self):
        """Wendet das aktuelle Theme auf die UI-Elemente an"""
        if self.dark_theme:
            self.text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12pt;
                }
            """)
            self.setStyleSheet("""
                QDialog {
                    background-color: #2D2D30;
                    color: #D4D4D4;
                }
                QPushButton {
                    background-color: #3E3E42;
                    color: #D4D4D4;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
        else:
            self.text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #FFFFFF;
                    color: #000000;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12pt;
                }
            """)
            self.setStyleSheet("""
                QDialog {
                    background-color: #F0F0F0;
                    color: #000000;
                }
                QPushButton {
                    background-color: #E1E1E1;
                    color: #000000;
                    border: 1px solid #BDBDBD;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #D0D0D0;
                }
            """)

    def toggle_theme(self):
        """Wechselt zwischen dunklem und hellem Theme"""
        self.dark_theme = not self.dark_theme
        self.apply_theme()

        # Syntax-Highlighter mit neuem Theme neu erstellen
        self.highlighter = JSONHighlighter(self.text_edit.document(), self.dark_theme)
        # Text kurz neu setzen, um das Highlighting sofort zu aktualisieren
        current_text = self.text_edit.toPlainText()
        self.text_edit.setPlainText(current_text)

        # Button-Text aktualisieren
        sender = self.sender()
        if sender:
            sender.setText("Wechsel zu " + ("Hellem" if self.dark_theme else "Dunklem") + " Theme")

    def load_file(self):
        """Lädt den JSON-Inhalt aus der Datei."""
        if os.path.isfile(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.original_content = f.read()

                # Optionale Formatierung für bessere Lesbarkeit
                try:
                    json_obj = json.loads(self.original_content)
                    formatted_json = json.dumps(json_obj, indent=4)
                    self.text_edit.setPlainText(formatted_json)
                except:
                    # Bei Fehler in der Formatierung Original-Text behalten
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
        new_file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Speichern unter",
            self.file_path,
            "JSON Files (*.json)",
            options=options
        )
        if new_file:
            try:
                # Prüfe, ob gültiges JSON vorliegt
                json.loads(content)
                with open(new_file, "w", encoding="utf-8") as f:
                    f.write(content)
                QtWidgets.QMessageBox.information(
                    self, "Erfolg", "Datei erfolgreich gespeichert unter:\n" + new_file
                )
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
    # Um mit hellem Theme zu starten: dark_theme=False
    dialog = JSONEditorDialog(test_file, dark_theme=True)
    if dialog.exec_():
        print("Gespeichert!")
    else:
        print("Abgebrochen!")