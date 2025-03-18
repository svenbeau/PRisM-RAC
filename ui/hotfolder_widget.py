#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from PySide6 import QtWidgets, QtCore, QtGui
from utils.hotfolder_config_manager import HotfolderConfigManager, debug_print
from ui.hotfolder_config_dialog import HotfolderConfigDialog
from hotfolder_monitor import HotfolderMonitor  # bleibt unverändert


def resource_path(relative_path):
    """Gibt den absoluten Pfad zur Ressource zurück – funktioniert im Entwicklungsmodus und im PyInstaller-Bundle."""
    try:
        # Wenn wir per PyInstaller laufen:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class HotfolderListWidget(QtWidgets.QWidget):
    """
    Zeigt alle Hotfolder in einer Liste (ScrollArea).
    Oben befinden sich Buttons zum Hinzufügen und Entfernen.
    Die Hotfolder-Daten werden über den HotfolderConfigManager geladen.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings  # Dieser Parameter wird jetzt nur noch für Kompatibilität beibehalten
        self.hf_manager = HotfolderConfigManager()
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Buttons zum Hinzufügen/Entfernen
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Hotfolder hinzufügen")
        self.del_btn = QtWidgets.QPushButton("Hotfolder entfernen")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.hf_container = QtWidgets.QWidget()
        self.hf_layout = QtWidgets.QVBoxLayout(self.hf_container)
        self.hf_layout.setContentsMargins(5, 5, 5, 5)
        self.hf_layout.setSpacing(10)
        self.scroll_area.setWidget(self.hf_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.add_btn.clicked.connect(self.add_hotfolder)
        self.del_btn.clicked.connect(self.delete_hotfolder)

        self.load_hotfolders()

    def load_hotfolders(self):
        debug_print("HotfolderListWidget.load_hotfolders() aufgerufen.")
        # Alte Widgets entfernen
        for i in reversed(range(self.hf_layout.count())):
            item = self.hf_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        hotfolders = self.hf_manager.get_hotfolders()
        debug_print(f"load_hotfolders: hotfolders={hotfolders}")
        for hf_data in hotfolders:
            widget = HotfolderWidget(hf_data, parent=self.hf_container)
            self.hf_layout.addWidget(widget)

        self.hf_layout.addStretch()

    def add_hotfolder(self):
        import uuid
        new_id = str(uuid.uuid4())
        new_hf = {
            "id": new_id,
            "name": "Neuer Hotfolder",
            "path": "",
            "monitor_dir": "",
            "success_dir": "",
            "fault_dir": "",
            "logfiles_dir": "",
            "contentcheck_enabled": True,
            "required_layers": [],
            "required_metadata": [],
            "keyword_check_enabled": False,
            "keyword_check_word": "Rueckseite",
            "keyword_layers": [],
            "keyword_metadata": [],
            "jsx_folder": "",
            "selected_jsx": "",
            "additional_jsx": "",
            "body_visible": True
        }
        self.hf_manager.add_hotfolder(new_hf)
        self.load_hotfolders()

    def delete_hotfolder(self):
        hotfolders = self.hf_manager.get_hotfolders()
        if not hotfolders:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Hotfolder vorhanden.")
            return
        idx, ok = QtWidgets.QInputDialog.getInt(self, "Hotfolder entfernen", "Index (1-basiert):", 1, 1,
                                                len(hotfolders))
        if ok:
            real_idx = idx - 1
            if 0 <= real_idx < len(hotfolders):
                hf_id = hotfolders[real_idx].get("id")
                self.hf_manager.remove_hotfolder(hf_id)
                self.load_hotfolders()


class HotfolderWidget(QtWidgets.QFrame):
    """
    Zeigt die Konfiguration (Ordner, Bearbeitung, Contentcheck) und den Status
    (Start/Stop, Spinner, Edit) für einen einzelnen Hotfolder an.
    """

    def __init__(self, hotfolder_config: dict, parent=None):
        super().__init__(parent)
        self.hotfolder_config = hotfolder_config
        self.monitor = None
        self.body_visible = self.hotfolder_config.get("body_visible", True)

        # Hartkodierte relative Pfade für die Assets, um sicherzustellen, dass sie direkt gefunden werden
        expand_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "dropdown_list.png")
        collapse_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "close_list.png")

        # Fallback zu resource_path wenn die direkten Pfade nicht funktionieren
        if not os.path.exists(expand_icon_path):
            expand_icon_path = resource_path("assets/dropdown_list.png")
        if not os.path.exists(collapse_icon_path):
            collapse_icon_path = resource_path("assets/close_list.png")

        debug_print(f"Expand icon path: {expand_icon_path}, exists: {os.path.exists(expand_icon_path)}")
        debug_print(f"Collapse icon path: {collapse_icon_path}, exists: {os.path.exists(collapse_icon_path)}")

        self.icon_expand = QtGui.QIcon(expand_icon_path)
        self.icon_collapse = QtGui.QIcon(collapse_icon_path)

        self.setupUi()

    def setupUi(self):
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # (A) Titelzeile
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setStyleSheet("background-color: #2b2b2b;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)
        self.title_label = QtWidgets.QLabel(self.hotfolder_config.get("name", "Unbenannt"))
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(self.title_label, 1, QtCore.Qt.AlignVCenter)

        # Erstelle einen Button mit einem Text statt eines Icons für den Togglebutton (als Fallback)
        self.toggle_btn = QtWidgets.QPushButton()
        self.toggle_btn.setFlat(True)

        # Überprüfe, ob die Icons richtig geladen wurden
        if self.icon_expand.isNull() or self.icon_collapse.isNull():
            debug_print("Icons konnten nicht geladen werden, verwende Text stattdessen")
            self.toggle_btn.setText("↕")  # Ein Unicode-Symbol als Ersatz
        else:
            if self.body_visible:
                self.toggle_btn.setIcon(self.icon_collapse)
            else:
                self.toggle_btn.setIcon(self.icon_expand)

        self.toggle_btn.clicked.connect(self.on_toggle_body)
        title_layout.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.title_bar)

        # (B) Subheader-Zeile
        self.subheader_frame = QtWidgets.QFrame()
        self.subheader_frame.setStyleSheet("background-color: #b0b0b0;")
        subheader_layout = QtWidgets.QHBoxLayout(self.subheader_frame)
        subheader_layout.setContentsMargins(10, 5, 10, 5)
        subheader_layout.setSpacing(0)
        self.subheader_label = QtWidgets.QLabel("Ordner, Bearbeitung, Contentcheck, Status")
        self.subheader_label.setStyleSheet("color: #000000; font-weight: bold;")
        subheader_layout.addWidget(self.subheader_label, 1, QtCore.Qt.AlignLeft)
        main_layout.addWidget(self.subheader_frame)

        # (C) Body-Widget (Collapsible)
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        self.ordner_group = QtWidgets.QGroupBox("Ordner")
        self.ordner_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        ordner_layout = QtWidgets.QVBoxLayout(self.ordner_group)
        self.monitor_label = QtWidgets.QLabel(f"Monitor: {self.hotfolder_config.get('monitor_dir', '')}")
        self.success_label = QtWidgets.QLabel(f"Success: {self.hotfolder_config.get('success_dir', '')}")
        self.fault_label = QtWidgets.QLabel(f"Fault: {self.hotfolder_config.get('fault_dir', '')}")
        self.logfiles_label = QtWidgets.QLabel(f"Logfiles: {self.hotfolder_config.get('logfiles_dir', '')}")
        for i, lbl in enumerate([self.monitor_label, self.success_label, self.fault_label, self.logfiles_label]):
            bg_color = "#f7f7f7" if i % 2 == 0 else "#e5e5e5"
            lbl.setStyleSheet(f"background-color: {bg_color}; color: #000000; padding: 4px;")
            ordner_layout.addWidget(lbl)
        body_layout.addWidget(self.ordner_group)

        self.bearbeitung_group = QtWidgets.QGroupBox("Bearbeitung")
        self.bearbeitung_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        bearbeitung_layout = QtWidgets.QVBoxLayout(self.bearbeitung_group)
        self.jsx_folder_label = QtWidgets.QLabel(f"JSX-Folder: {self.hotfolder_config.get('jsx_folder', '')}")
        self.selected_jsx_label = QtWidgets.QLabel(
            f"JSX-Script (Combo): {os.path.basename(self.hotfolder_config.get('selected_jsx', '')) or '(none)'}")
        self.additional_jsx_label = QtWidgets.QLabel(
            f"JSX-Script (Manual): {os.path.basename(self.hotfolder_config.get('additional_jsx', '')) or '(none)'}")
        for lbl in [self.jsx_folder_label, self.selected_jsx_label, self.additional_jsx_label]:
            lbl.setStyleSheet("background-color: #f7f7f7; color: #000000; padding: 4px;")
            bearbeitung_layout.addWidget(lbl)
        body_layout.addWidget(self.bearbeitung_group)

        self.content_group = QtWidgets.QGroupBox("Contentcheck")
        self.content_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        content_layout = QtWidgets.QVBoxLayout(self.content_group)
        self.std_layers_label = QtWidgets.QLabel()
        self.std_meta_label = QtWidgets.QLabel()
        self.kw_layers_label = QtWidgets.QLabel()
        self.kw_meta_label = QtWidgets.QLabel()
        for i, lbl in enumerate([self.std_layers_label, self.std_meta_label, self.kw_layers_label, self.kw_meta_label]):
            bg_color = "#f7f7f7" if i % 2 == 0 else "#e5e5e5"
            lbl.setStyleSheet(f"background-color: {bg_color}; color: #000000; padding: 4px;")
            content_layout.addWidget(lbl)
        body_layout.addWidget(self.content_group)

        self.body_widget.setLayout(body_layout)
        main_layout.addWidget(self.body_widget)

        # (D) Status-Bereich (immer sichtbar)
        self.status_group = QtWidgets.QGroupBox("Status")
        self.status_group.setStyleSheet("""
            QGroupBox { background-color: #e5e5e5; color: #000000; }
            QGroupBox::title { background-color: #b0b0b0; color: #000000; }
        """)
        status_layout = QtWidgets.QHBoxLayout(self.status_group)
        self.status_label = QtWidgets.QLabel("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        status_layout.addWidget(QtWidgets.QLabel("Aktuell:"))
        status_layout.addWidget(self.status_label)
        self.spinner_label = QtWidgets.QLabel()
        self.spinner_label.setFixedSize(20, 20)
        self.spinner_label.setScaledContents(True)
        spinner_path = os.path.join("assets", "spinner.gif")
        self.spinner_movie = None
        if os.path.exists(spinner_path):
            self.spinner_movie = QtGui.QMovie(spinner_path)
            self.spinner_movie.setScaledSize(QtCore.QSize(20, 20))
            self.spinner_label.setMovie(self.spinner_movie)
            self.spinner_movie.start()
            self.spinner_label.setVisible(False)
        else:
            self.spinner_label.setText("Spinner?")
        status_layout.addWidget(self.spinner_label)
        self.start_stop_btn = QtWidgets.QPushButton("Start")
        self.start_stop_btn.clicked.connect(self.on_start_stop)
        status_layout.addWidget(self.start_stop_btn)
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit)
        status_layout.addWidget(self.edit_btn)
        main_layout.addWidget(self.status_group)

        self.body_widget.setVisible(self.body_visible)
        self.update_labels()

    def on_toggle_body(self):
        self.body_visible = not self.body_visible
        self.body_widget.setVisible(self.body_visible)

        # Überprüfe, ob die Icons richtig geladen wurden
        if self.icon_expand.isNull() or self.icon_collapse.isNull():
            self.toggle_btn.setText("↕")  # Fallback Text
        else:
            if self.body_visible:
                self.toggle_btn.setIcon(self.icon_collapse)
            else:
                self.toggle_btn.setIcon(self.icon_expand)

        # body_visible in den Hotfolder-Daten aktualisieren
        self.hotfolder_config["body_visible"] = self.body_visible

        # ÄNDERUNG: Sofort in hotfolder_config.json speichern
        manager = HotfolderConfigManager()
        manager.update_hotfolder(self.hotfolder_config["id"], self.hotfolder_config)

    def on_start_stop(self):
        if not self.monitor or not self.monitor.active:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        debug_print(
            f"Starte Monitor für: {self.hotfolder_config.get('name', '?')} (ID={self.hotfolder_config.get('id', '??')})")
        self.monitor = HotfolderMonitor(
            hf_config=self.hotfolder_config,
            on_status_update=self.on_status_update,
            on_file_processing=self.on_file_processing
        )
        self.monitor.start()
        self.start_stop_btn.setText("Stop")
        self.status_label.setText("Aktiv")
        self.status_label.setStyleSheet("color: green;")
        if self.spinner_movie:
            self.spinner_label.setVisible(True)
            self.spinner_label.setStyleSheet("opacity: 0.3;")

    def stop_monitor(self):
        if self.monitor:
            debug_print(
                f"Stoppe Monitor für: {self.hotfolder_config.get('name', '?')} (ID={self.hotfolder_config.get('id', '??')})")
            self.monitor.stop()
            self.monitor = None
        self.start_stop_btn.setText("Start")
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)

    def on_status_update(self, status_text: str, is_active: bool):
        if is_active:
            self.status_label.setText("Aktiv")
            self.status_label.setStyleSheet("color: green;")
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 0.3;")
        else:
            self.status_label.setText("Inaktiv")
            self.status_label.setStyleSheet("color: red;")
            if self.spinner_movie:
                self.spinner_label.setVisible(False)

    def on_file_processing(self, filename: str):
        from datetime import datetime
        import os, json
        from utils.log_manager import add_log_entry
        debug_print(f"Verarbeite Datei: {filename}")

        logfiles_dir = self.hotfolder_config.get("logfiles_dir", "")
        basename = os.path.splitext(os.path.basename(filename))[0]
        # Korrektur: Entferne das zusätzliche führende "_" vor dem Dateinamen.
        contentcheck_filename = os.path.join(logfiles_dir, f"{basename}_01_log_contentcheck.json")
        if os.path.exists(contentcheck_filename):
            try:
                with open(contentcheck_filename, "r", encoding="utf-8") as f:
                    contentcheck_data = json.load(f)
                metadata = contentcheck_data.get("metadata")
                details = contentcheck_data.get("details")
                debug_print(f"ContentCheck-Daten geladen aus {contentcheck_filename}")
            except Exception as e:
                debug_print(f"Fehler beim Laden des ContentCheck-Logs: {e}")
                metadata = None
                details = None
        else:
            debug_print(f"ContentCheck-Logdatei nicht gefunden: {contentcheck_filename}")
            metadata = None
            details = None

        if metadata is None:
            metadata = {
                "documentTitle": "undefined",
                "author": "RecomArt-Cruse-Color",
                "authorPosition": "undefined",
                "description": "OnlineOnly",
                "descriptionWriter": "undefined",
                "keywords": "751",
                "copyrightNotice": "Copyright (C) reserved",
                "copyrightURL": "undefined",
                "city": "undefined",
                "stateProvince": "undefined",
                "country": "undefined",
                "creditLine": "undefined",
                "source": "undefined",
                "headline": "undefined",
                "instructions": "undefined",
                "transmissionRef": "undefined"
            }
        if details is None:
            details = {
                "layers": {},
                "missingLayers": [],
                "missingMetadata": [],
                "layerStatus": "OK",
                "metaStatus": "OK",
                "checkType": "Standard",
                "keywordCheck": {
                    "enabled": True,
                    "keyword": self.hotfolder_config.get("keyword_check_word", "Rueckseite")
                }
            }
        if "layers" not in details:
            details["layers"] = {"Freisteller": "yes", "Messwerte": "no", "Korrektur": "no"}
        if "missingLayers" not in details:
            details["missingLayers"] = ["Messwerte", "Korrektur"]

        status = "OK"
        applied_script = os.path.basename(self.hotfolder_config.get("selected_jsx", "(none)"))
        checkType = "Standard"
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "filename": os.path.basename(filename),
            "metadata": metadata,
            "checkType": checkType,
            "status": status,
            "applied_script": applied_script,
            "details": details
        }
        add_log_entry(log_entry)
        debug_print(f"Logeintrag erstellt für Datei: {filename}")

    def on_edit(self):
        dlg = HotfolderConfigDialog(self.hotfolder_config, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            debug_print("Hotfolder geändert, reload.")
            hf_manager = HotfolderConfigManager()
            hf_manager.update_hotfolder(self.hotfolder_config.get("id"), self.hotfolder_config)
            self.update_labels()
            parent_widget = self.parent()
            if parent_widget and hasattr(parent_widget, "load_hotfolders"):
                debug_print("Rufe parent_widget.load_hotfolders() auf, um das gesamte UI zu aktualisieren.")
                parent_widget.load_hotfolders()
        else:
            debug_print("Hotfolder-Konfiguration Dialog abgebrochen.")

    def update_labels(self):
        debug_print("Aktualisiere HotfolderWidget-Labels.")
        self.title_label.setText(self.hotfolder_config.get("name", "Unbenannt"))
        self.monitor_label.setText(f"Monitor: {self.hotfolder_config.get('monitor_dir', '')}")
        self.success_label.setText(f"Success: {self.hotfolder_config.get('success_dir', '')}")
        self.fault_label.setText(f"Fault: {self.hotfolder_config.get('fault_dir', '')}")
        self.logfiles_label.setText(f"Logfiles: {self.hotfolder_config.get('logfiles_dir', '')}")
        folder = self.hotfolder_config.get("jsx_folder", "")
        self.jsx_folder_label.setText(f"JSX-Folder: {folder}")
        combo_name = os.path.basename(self.hotfolder_config.get("selected_jsx", "")) or "(none)"
        manual_name = os.path.basename(self.hotfolder_config.get("additional_jsx", "")) or "(none)"
        self.selected_jsx_label.setText(f"JSX-Script (Combo): {combo_name}")
        self.additional_jsx_label.setText(f"JSX-Script (Manual): {manual_name}")
        std_layers = ", ".join(self.hotfolder_config.get("required_layers", []))
        std_meta = ", ".join(self.hotfolder_config.get("required_metadata", []))
        self.std_layers_label.setText(f"Standard Ebenen: {std_layers}")
        self.std_meta_label.setText(f"Standard Metadaten: {std_meta}")
        if self.hotfolder_config.get("keyword_check_enabled", False):
            kw = self.hotfolder_config.get("keyword_check_word", "Rueckseite")
            kw_layers = ", ".join(self.hotfolder_config.get("keyword_layers", []))
            kw_meta = ", ".join(self.hotfolder_config.get("keyword_metadata", []))
            self.kw_layers_label.setText(f"Keyword '{kw}' Ebenen: {kw_layers}")
            self.kw_meta_label.setText(f"Keyword '{kw}' Metadaten: {kw_meta}")
        else:
            self.kw_layers_label.setText("")
            self.kw_meta_label.setText("")
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        self.start_stop_btn.setText("Start")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = HotfolderWidget({
        "id": "1234",
        "name": "TestHotfolder",
        "monitor_dir": "/Pfad/Monitor",
        "success_dir": "/Pfad/Success",
        "fault_dir": "/Pfad/Fault",
        "logfiles_dir": "/Pfad/Logfiles",
        "contentcheck_enabled": True,
        "required_layers": [],
        "required_metadata": [],
        "keyword_check_enabled": False,
        "keyword_check_word": "",
        "keyword_layers": [],
        "keyword_metadata": [],
        "jsx_folder": "",
        "selected_jsx": "",
        "additional_jsx": "",
        "body_visible": True
    })
    widget.show()
    sys.exit(app.exec())