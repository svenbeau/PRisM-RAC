#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6 import QtWidgets, QtCore


class PathSelectionWidget(QtWidgets.QWidget):
    """
    Ein Widget, das ein Dropdown (QComboBox) und einen Browse-Button kombiniert.
    Das Dropdown zeigt zuletzt verwendete Pfade; der Browse-Button ermöglicht es,
    über einen QFileDialog einen neuen Pfad (Ordner oder Datei) auszuwählen.

    Der Typ (self.type) kann "folder", "file", "script" oder "csv" sein – je nachdem,
    welcher Filter beim Dateidialog angewendet werden soll.
    """

    def __init__(self, label, recent_list=None, type="folder", parent=None):
        super().__init__(parent)
        self.type = type  # "folder", "file", "script" oder "csv"
        self.recent_list = recent_list if recent_list is not None else []
        self.init_ui(label)

    def init_ui(self, label_text):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.combo = QtWidgets.QComboBox(self)
        self.combo.setEditable(True)
        self.combo.addItems(self.recent_list)
        layout.addWidget(self.combo)

        self.browse_btn = QtWidgets.QPushButton("Browse", self)
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self.browse)
        layout.addWidget(self.browse_btn)

        self.setLayout(layout)

    def browse(self):
        if self.type in ["folder", "file"]:
            if self.type == "folder":
                selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", self.combo.currentText())
            else:
                selected, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", self.combo.currentText(),
                                                                    "All Files (*)")
        elif self.type == "script":
            selected, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Script", self.combo.currentText(),
                                                                "JSX Files (*.jsx)")
        elif self.type == "csv":
            selected, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV File", self.combo.currentText(),
                                                                "CSV Files (*.csv)")
        else:
            selected = ""
        if selected:
            if self.combo.findText(selected) == -1:
                self.combo.insertItem(0, selected)
            self.combo.setCurrentText(selected)

    def get_path(self):
        return self.combo.currentText()

    def set_path(self, path):
        index = self.combo.findText(path)
        if index == -1:
            self.combo.insertItem(0, path)
            self.combo.setCurrentIndex(0)
        else:
            self.combo.setCurrentIndex(index)