#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from config.config_manager import save_settings, load_settings, debug_print
from ui.hotfolder_config import HotfolderConfigDialog
from hotfolder_monitor import HotfolderMonitor

DEBUG_OUTPUT = True

def debug_print_local(msg):
    if DEBUG_OUTPUT:
        print("[DEBUG]", msg)

class HotfolderListWidget(QtWidgets.QWidget):
    """
    Zeigt alle Hotfolder in einer Liste (ScrollArea).
    Buttons oben: "Hotfolder hinzufügen" und "Hotfolder entfernen".
    Lädt/aktualisiert die Widgets in load_hotfolders().
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
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
        """
        Lädt alle Hotfolder aus self.settings und erzeugt für jeden ein HotfolderWidget.
        """
        debug_print_local("HotfolderListWidget.load_hotfolders() aufgerufen.")
        # Zunächst alte Widgets entfernen
        for i in reversed(range(self.hf_layout.count())):
            item = self.hf_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        # Hotfolder-Liste aus den Settings holen
        hotfolders = self.settings.setdefault("hotfolders", [])
        debug_print_local(f"load_hotfolders: hotfolders={hotfolders}")
        for hf_data in hotfolders:
            widget = HotfolderWidget(hf_data, self.settings, parent=self.hf_container)
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
            # Neu: standardmäßig aufgeklappt
            "body_visible": True
        }
        self.settings.setdefault("hotfolders", []).append(new_hf)
        save_settings(self.settings)
        self.load_hotfolders()

    def delete_hotfolder(self):
        hotfolders = self.settings.setdefault("hotfolders", [])
        if not hotfolders:
            QtWidgets.QMessageBox.warning(self, "Entfernen", "Keine Hotfolder vorhanden.")
            return
        idx, ok = QtWidgets.QInputDialog.getInt(self, "Hotfolder entfernen", "Index (1-basiert):", 1, 1, len(hotfolders))
        if ok:
            real_idx = idx - 1
            if 0 <= real_idx < len(hotfolders):
                del hotfolders[real_idx]
                save_settings(self.settings)
                self.load_hotfolders()

class HotfolderWidget(QtWidgets.QFrame):
    """
    Zeigt die Konfiguration (Ordner, Bearbeitung, Contentcheck) und den Status (Start/Stop, Spinner, Edit)
    für einen einzelnen Hotfolder an.

    - Titelzeile mit Name (links) + Toggle-Button (rechts)
    - Subheader: "Ordner, Bearbeitung, Contentcheck, Status" (immer sichtbar)
    - Collapsible Body: "Ordner", "Bearbeitung", "Contentcheck"
    - Status-Bereich immer sichtbar (nicht einklappbar)
    - Der Zustand (auf- oder zugeklappt) wird in hotfolder_config["body_visible"] gespeichert
      und beim nächsten Start wiederhergestellt.
    """
    def __init__(self, hotfolder_config: dict, settings: dict, parent=None):
        super().__init__(parent)
        self.hotfolder_config = hotfolder_config
        self.settings = settings
        self.monitor = None

        # Zustand (auf-/zugeklappt) aus hotfolder_config
        self.body_visible = self.hotfolder_config.get("body_visible", True)

        # Icons
        self.icon_expand = QtGui.QIcon(os.path.join("assets", "dropdown_list.png"))   # "aufklappen"
        self.icon_collapse = QtGui.QIcon(os.path.join("assets", "close_list.png"))    # "zuklappen"

        self.setupUi()

    def setupUi(self):
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        #
        # (A) Titelzeile
        #
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setStyleSheet("background-color: #2b2b2b;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        # Hotfolder-Name (links)
        self.title_label = QtWidgets.QLabel(self.hotfolder_config.get("name", "Unbenannt"))
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(self.title_label, 1, QtCore.Qt.AlignVCenter)

        # Toggle-Button (rechts)
        self.toggle_btn = QtWidgets.QPushButton()
        self.toggle_btn.setFlat(True)
        # Setze das Icon entsprechend body_visible
        if self.body_visible:
            self.toggle_btn.setIcon(self.icon_collapse)
        else:
            self.toggle_btn.setIcon(self.icon_expand)
        self.toggle_btn.clicked.connect(self.on_toggle_body)
        title_layout.addWidget(self.toggle_btn, 0, QtCore.Qt.AlignRight)

        main_layout.addWidget(self.title_bar)

        #
        # (B) Subheader-Zeile
        #
        self.subheader_frame = QtWidgets.QFrame()
        self.subheader_frame.setStyleSheet("background-color: #b0b0b0;")
        subheader_layout = QtWidgets.QHBoxLayout(self.subheader_frame)
        subheader_layout.setContentsMargins(10, 5, 10, 5)
        subheader_layout.setSpacing(0)

        self.subheader_label = QtWidgets.QLabel("Ordner, Bearbeitung, Contentcheck, Status")
        self.subheader_label.setStyleSheet("color: #000000; font-weight: bold;")
        subheader_layout.addWidget(self.subheader_label, 1, QtCore.Qt.AlignLeft)

        main_layout.addWidget(self.subheader_frame)

        #
        # (C) Body-Widget (Collapsible): Ordner, Bearbeitung, Contentcheck
        #
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        # (C1) Ordner
        self.ordner_group = QtWidgets.QGroupBox("Ordner")
        self.ordner_group.setStyleSheet("""
            QGroupBox {
                background-color: #e5e5e5;
                color: #000000;
            }
            QGroupBox::title {
                background-color: #b0b0b0;
                color: #000000;
            }
        """)
        ordner_layout = QtWidgets.QVBoxLayout(self.ordner_group)

        self.monitor_label = QtWidgets.QLabel()
        self.success_label = QtWidgets.QLabel()
        self.fault_label   = QtWidgets.QLabel()
        self.logfiles_label= QtWidgets.QLabel()

        folder_labels = [self.monitor_label, self.success_label, self.fault_label, self.logfiles_label]
        for i, lbl in enumerate(folder_labels):
            bg_color = "#f7f7f7" if i % 2 == 0 else "#e5e5e5"
            lbl.setStyleSheet(f"background-color: {bg_color}; color: #000000; padding: 4px;")
            ordner_layout.addWidget(lbl)

        body_layout.addWidget(self.ordner_group)

        # (C2) Bearbeitung
        self.bearbeitung_group = QtWidgets.QGroupBox("Bearbeitung")
        self.bearbeitung_group.setStyleSheet("""
            QGroupBox {
                background-color: #e5e5e5;
                color: #000000;
            }
            QGroupBox::title {
                background-color: #b0b0b0;
                color: #000000;
            }
        """)
        bearbeitung_layout = QtWidgets.QVBoxLayout(self.bearbeitung_group)

        self.jsx_folder_label = QtWidgets.QLabel()
        self.selected_jsx_label = QtWidgets.QLabel()
        self.additional_jsx_label = QtWidgets.QLabel()

        self.jsx_folder_label.setStyleSheet("background-color: #f7f7f7; color: #000000; padding: 4px;")
        self.selected_jsx_label.setStyleSheet("background-color: #e5e5e5; color: #000000; padding: 4px;")
        self.additional_jsx_label.setStyleSheet("background-color: #f7f7f7; color: #000000; padding: 4px;")

        bearbeitung_layout.addWidget(self.jsx_folder_label)
        bearbeitung_layout.addWidget(self.selected_jsx_label)
        bearbeitung_layout.addWidget(self.additional_jsx_label)

        body_layout.addWidget(self.bearbeitung_group)

        # (C3) Contentcheck
        self.content_group = QtWidgets.QGroupBox("Contentcheck")
        self.content_group.setStyleSheet("""
            QGroupBox {
                background-color: #e5e5e5;
                color: #000000;
            }
            QGroupBox::title {
                background-color: #b0b0b0;
                color: #000000;
            }
        """)
        content_layout = QtWidgets.QVBoxLayout(self.content_group)

        self.std_layers_label = QtWidgets.QLabel()
        self.std_meta_label   = QtWidgets.QLabel()
        self.kw_layers_label  = QtWidgets.QLabel()
        self.kw_meta_label    = QtWidgets.QLabel()

        self.std_layers_label.setStyleSheet("background-color: #f7f7f7; color: #000000; padding: 4px;")
        self.std_meta_label.setStyleSheet("background-color: #e5e5e5; color: #000000; padding: 4px;")
        self.kw_layers_label.setStyleSheet("background-color: #f7f7f7; color: #000000; padding: 4px;")
        self.kw_meta_label.setStyleSheet("background-color: #e5e5e5; color: #000000; padding: 4px;")

        content_layout.addWidget(self.std_layers_label)
        content_layout.addWidget(self.std_meta_label)
        content_layout.addWidget(self.kw_layers_label)
        content_layout.addWidget(self.kw_meta_label)

        body_layout.addWidget(self.content_group)

        self.body_widget.setLayout(body_layout)
        main_layout.addWidget(self.body_widget)

        #
        # (D) Status-Bereich (immer sichtbar, NICHT Teil des collapsible Body)
        #
        self.status_group = QtWidgets.QGroupBox("Status")
        self.status_group.setStyleSheet("""
            QGroupBox {
                background-color: #e5e5e5;
                color: #000000;
            }
            QGroupBox::title {
                background-color: #b0b0b0;
                color: #000000;
            }
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

        # Sichtbarkeit des Body-Bereichs anhand self.body_visible
        self.body_widget.setVisible(self.body_visible)
        if self.body_visible:
            self.toggle_btn.setIcon(self.icon_collapse)
        else:
            self.toggle_btn.setIcon(self.icon_expand)

        self.update_labels()

    def on_toggle_body(self):
        """
        Ein-/Ausklappen des Body-Bereichs (Ordner, Bearbeitung, Contentcheck).
        Subheader bleibt sichtbar, Status bleibt ebenfalls immer sichtbar.
        """
        self.body_visible = not self.body_visible
        self.body_widget.setVisible(self.body_visible)
        if self.body_visible:
            self.toggle_btn.setIcon(self.icon_collapse)
        else:
            self.toggle_btn.setIcon(self.icon_expand)

        # In die Hotfolder-Konfiguration schreiben
        self.hotfolder_config["body_visible"] = self.body_visible
        save_settings(self.settings)

    def on_start_stop(self):
        if not self.monitor or not self.monitor.active:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        debug_print_local(f"Starte Monitor für: {self.hotfolder_config.get('name','?')} (ID={self.hotfolder_config.get('id','??')})")
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
            debug_print_local(f"Stoppe Monitor für: {self.hotfolder_config.get('name','?')} (ID={self.hotfolder_config.get('id','??')})")
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
        if filename:
            short_filename = os.path.basename(filename)
            if self.spinner_movie:
                self.spinner_label.setVisible(True)
                self.spinner_label.setStyleSheet("opacity: 1.0;")
            self.status_label.setText(f"Aktiv (Verarbeite: {short_filename})")
            self.status_label.setStyleSheet("color: green;")
        else:
            if self.monitor and self.monitor.active:
                if self.spinner_movie:
                    self.spinner_label.setVisible(True)
                    self.spinner_label.setStyleSheet("opacity: 0.3;")
                self.status_label.setText("Aktiv")
                self.status_label.setStyleSheet("color: green;")
            else:
                if self.spinner_movie:
                    self.spinner_label.setVisible(False)
                self.status_label.setText("Inaktiv")
                self.status_label.setStyleSheet("color: red;")

    def on_edit(self):
        dlg = HotfolderConfigDialog(self.hotfolder_config, parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            debug_print_local("Hotfolder geändert, reload.")
            save_settings(self.settings)
            self.settings = load_settings()
            self.update_labels()
            parent_widget = self.parent()
            if parent_widget and hasattr(parent_widget, "load_hotfolders"):
                debug_print_local("Rufe parent_widget.load_hotfolders() auf, um das gesamte UI zu aktualisieren.")
                parent_widget.load_hotfolders()
        else:
            debug_print_local("Hotfolder-Konfiguration Dialog abgebrochen.")

    def update_labels(self):
        debug_print_local("Aktualisiere HotfolderWidget-Labels.")
        # Titel
        self.title_label.setText(self.hotfolder_config.get("name", "Unbenannt"))
        debug_print_local("Name aktualisiert: " + self.hotfolder_config.get("name", "Unbenannt"))

        # Ordner
        self.monitor_label.setText(f"Monitor: {self.hotfolder_config.get('monitor_dir','')}")
        self.success_label.setText(f"Success: {self.hotfolder_config.get('success_dir','')}")
        self.fault_label.setText(f"Fault: {self.hotfolder_config.get('fault_dir','')}")
        self.logfiles_label.setText(f"Logfiles: {self.hotfolder_config.get('logfiles_dir','')}")

        # Bearbeitung
        folder = self.hotfolder_config.get("jsx_folder", "")
        self.jsx_folder_label.setText(f"JSX-Folder: {folder}")
        combo_name = os.path.basename(self.hotfolder_config.get("selected_jsx","")) or "(none)"
        manual_name= os.path.basename(self.hotfolder_config.get("additional_jsx","")) or "(none)"
        self.selected_jsx_label.setText(f"JSX-Script (Combo): {combo_name}")
        self.additional_jsx_label.setText(f"JSX-Script (Manual): {manual_name}")
        debug_print_local(f"Selected JSX: {self.hotfolder_config.get('selected_jsx','')}, Additional JSX: {self.hotfolder_config.get('additional_jsx','')}")

        # Contentcheck
        std_layers = ", ".join(self.hotfolder_config.get("required_layers", []))
        std_meta   = ", ".join(self.hotfolder_config.get("required_metadata", []))
        self.std_layers_label.setText(f"Standard Ebenen: {std_layers}")
        self.std_meta_label.setText(f"Standard Metadaten: {std_meta}")
        debug_print_local("Standard Contentcheck - Ebenen: " + std_layers)
        debug_print_local("Standard Contentcheck - Metadaten: " + std_meta)

        if self.hotfolder_config.get("keyword_check_enabled", False):
            kw = self.hotfolder_config.get("keyword_check_word", "Rueckseite")
            kw_layers = ", ".join(self.hotfolder_config.get("keyword_layers", []))
            kw_meta   = ", ".join(self.hotfolder_config.get("keyword_metadata", []))
            self.kw_layers_label.setText(f"Keyword '{kw}' Ebenen: {kw_layers}")
            self.kw_meta_label.setText(f"Keyword '{kw}' Metadaten: {kw_meta}")
            debug_print_local("Keyword Contentcheck - Keyword: " + kw)
            debug_print_local("Keyword Contentcheck - Ebenen: " + kw_layers)
            debug_print_local("Keyword Contentcheck - Metadaten: " + kw_meta)
        else:
            self.kw_layers_label.setText("")
            self.kw_meta_label.setText("")

        # Status zurücksetzen
        self.status_label.setText("Inaktiv")
        self.status_label.setStyleSheet("color: red;")
        self.start_stop_btn.setText("Start")
        if self.spinner_movie:
            self.spinner_label.setVisible(False)