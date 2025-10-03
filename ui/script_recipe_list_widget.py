#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from PySide6 import QtWidgets
from utils.script_config_manager import debug_print, ScriptConfigManager
from ui.script_recipe_widget import ScriptRecipeWidget

class ScriptRecipeListWidget(QtWidgets.QWidget):
    """
    Entspricht dem HotfolderListWidget, nur für Script-Configs:
      - Oben Buttons: "Script-Config hinzufügen" / "Script-Config entfernen"
      - ScrollArea mit collapsiblen Widgets (ScriptRecipeWidget)
      - Lädt und speichert über ScriptConfigManager (~/Library/Application Support/PRisM-CC/config/script_config.json)
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = ScriptConfigManager()  # Schreibt/liest script_config.json
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Buttons zum Hinzufügen/Entfernen
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Script-Config hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Script-Config entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # ScrollArea
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_widget = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(10)
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Connect
        self.add_btn.clicked.connect(self.add_script_config)
        self.del_btn.clicked.connect(self.remove_script_config)

        self.load_scripts()

    def load_scripts(self):
        """
        Lädt alle Skript-Konfigurationen und erzeugt ein ScriptRecipeWidget je Eintrag.
        """
        debug_print("ScriptRecipeListWidget.load_scripts() aufgerufen.")
        # Alte Widgets entfernen
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        scripts = self.manager.get_scripts()
        debug_print(f"Scripts={scripts}")
        for sdata in scripts:
            widget = ScriptRecipeWidget(sdata, parent=self.container_widget)
            self.container_layout.addWidget(widget)

        self.container_layout.addStretch()

    def add_script_config(self):
        """
        Legt einen neuen Eintrag an.
        """
        new_id = str(uuid.uuid4())
        new_script = {
            "id": new_id,
            "name": "Neues Skript",
            "script_path": "",
            "json_folder": "",
            "actionFolderName": "",
            "basicWandFiles": "",
            "csvWandFile": "",
            "wandFileSavePath": "",
            "body_visible": True
        }
        self.manager.add_script(new_script)
        self.load_scripts()

    def remove_script_config(self):
        scripts = self.manager.get_scripts()
        if not scripts:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Script-Configs vorhanden.")
            return
        idx, ok = QtWidgets.QInputDialog.getInt(
            self, "Script entfernen",
            "Index (1-basiert):", 1, 1, len(scripts)
        )
        if ok:
            real_idx = idx - 1
            if 0 <= real_idx < len(scripts):
                sid = scripts[real_idx].get("id")
                self.manager.remove_script(sid)
                self.load_scripts()