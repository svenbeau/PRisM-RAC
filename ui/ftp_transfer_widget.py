#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import traceback
import keyring
import json
import smtplib
from datetime import datetime
from PySide6 import QtWidgets, QtCore, QtGui

from utils.config_manager import (
    debug_print,
    load_settings,
    save_settings,
    load_ftp_servers,
    load_smtp_settings,
    save_smtp_settings,
    get_mail_transfer_info_path
)
from utils.ftp_manager import FTPManager, TransferError
from ui.ftp_server_manager_dialog import FtpServerManagerDialog


class TransferProgressDialog(QtWidgets.QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 100)
        self.canceled = False

        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel("Starting...")
        layout.addWidget(self.label)
        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)

        btn = QtWidgets.QPushButton("Abbrechen")
        btn.clicked.connect(self.on_cancel)
        layout.addWidget(btn)

        self.file_count = 1

    def set_file_count(self, count):
        self.file_count = count
        self.progress.setRange(0, count)

    def set_current_file(self, filename, index):
        self.label.setText(f"{index}/{self.file_count}: {filename}")
        self.progress.setValue(index)
        QtWidgets.QApplication.processEvents()

    def on_cancel(self):
        self.canceled = True


class LocalFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setFilterKeyColumn(0)

    def setFilterString(self, text: str):
        pattern = f"*{text}*"
        self.setFilterWildcard(pattern)


class FtpTransferWidget(QtWidgets.QWidget):
    """
    Haupt-Widget mit:
      - Lokaler Pane (mit Suchfeld und dynamischer Aktualisierung des lokalen Zielpfads)
      - Remote Pane (mit Suchfeld, Remote-Verwaltungsbuttons)
      - "Saved Servers"-Dropdown (aus ftp_servers.json)
      - Buttons: Refresh, Up, Neuer Ordner, Umbenennen, Löschen, Upload, Download
      - Lokaler RootPath "/Volumes" (auf macOS) als Ausgangspunkt – der aktuelle lokale Zielpfad wird über Klick in der TreeView aktualisiert.
      - Interaktive Abfrage bei Dateikonflikt (Überschreiben, Suffix oder Abbrechen)

      **Hinweis:** Es werden nur Dateien transferiert.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # FTP-Einstellungen aus settings.json
        self.settings = load_settings()
        # SMTP-Einstellungen aus smtp_settings.json
        self.smtp_settings = load_smtp_settings()
        self.ftp = None
        self.current_remote_path = "/"
        self.remote_items_all = []
        self.current_local_path = "/Volumes"  # Standardmäßig /Volumes
        debug_print("FtpTransferWidget: __init__() aufgerufen, current_local_path=" + self.current_local_path)
        self.init_ui()

    def init_ui(self):
        debug_print("FtpTransferWidget: init_ui() aufgerufen")
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # ---------- FTP-Einstellungen ----------
        ftp_group = QtWidgets.QGroupBox("FTP-Einstellungen")
        ftp_layout = QtWidgets.QHBoxLayout(ftp_group)

        self.server_combo = QtWidgets.QComboBox()
        ftp_layout.addWidget(QtWidgets.QLabel("Saved Servers:"))
        ftp_layout.addWidget(self.server_combo)
        self.server_combo.currentIndexChanged.connect(self.server_combo_changed)

        self.manage_btn = QtWidgets.QPushButton("Manage")
        self.manage_btn.clicked.connect(self.open_server_manager)
        ftp_layout.addWidget(self.manage_btn)

        self.protocol_combo = QtWidgets.QComboBox()
        self.protocol_combo.addItems(["ftp", "sftp"])
        self.protocol_combo.setCurrentText(self.settings.get("ftp_protocol", "ftp"))
        ftp_layout.addWidget(QtWidgets.QLabel("Protocol:"))
        ftp_layout.addWidget(self.protocol_combo)

        self.host_edit = QtWidgets.QLineEdit(self.settings.get("ftp_host", ""))
        ftp_layout.addWidget(QtWidgets.QLabel("Host:"))
        ftp_layout.addWidget(self.host_edit)

        self.port_edit = QtWidgets.QLineEdit(str(self.settings.get("ftp_port", 21)))
        ftp_layout.addWidget(QtWidgets.QLabel("Port:"))
        ftp_layout.addWidget(self.port_edit)

        self.user_edit = QtWidgets.QLineEdit(self.settings.get("ftp_user", ""))
        ftp_layout.addWidget(QtWidgets.QLabel("User:"))
        ftp_layout.addWidget(self.user_edit)

        self.pass_edit = QtWidgets.QLineEdit()
        self.pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        ftp_layout.addWidget(QtWidgets.QLabel("Pass:"))
        ftp_layout.addWidget(self.pass_edit)

        self.keep_ts_check = QtWidgets.QCheckBox("Keep Timestamp")
        self.keep_ts_check.setChecked(self.settings.get("keep_timestamp", False))
        ftp_layout.addWidget(self.keep_ts_check)

        self.version_combo = QtWidgets.QComboBox()
        self.version_combo.addItems(["mirror", "suffix"])
        self.version_combo.setCurrentText(self.settings.get("versioning_mode", "mirror"))
        ftp_layout.addWidget(QtWidgets.QLabel("Versioning:"))
        ftp_layout.addWidget(self.version_combo)

        self.save_btn = QtWidgets.QPushButton("Save FTP Settings")
        self.save_btn.clicked.connect(self.save_settings_slot)
        ftp_layout.addWidget(self.save_btn)

        self.connect_btn = QtWidgets.QPushButton("Verbinden")
        self.connect_btn.clicked.connect(self.connect_ftp)
        ftp_layout.addWidget(self.connect_btn)

        main_layout.addWidget(ftp_group)

        # ---------- SMTP-Einstellungen ----------
        smtp_group = QtWidgets.QGroupBox("SMTP-Einstellungen (Fehlermeldungen)")
        smtp_layout = QtWidgets.QHBoxLayout(smtp_group)

        self.smtp_enabled_check = QtWidgets.QCheckBox("SMTP aktiviert")
        smtp_layout.addWidget(self.smtp_enabled_check)

        self.smtp_host_edit = QtWidgets.QLineEdit()
        smtp_layout.addWidget(QtWidgets.QLabel("SMTP Host:"))
        smtp_layout.addWidget(self.smtp_host_edit)

        self.smtp_port_spin = QtWidgets.QSpinBox()
        self.smtp_port_spin.setMaximum(65535)
        self.smtp_port_spin.setValue(587)
        smtp_layout.addWidget(QtWidgets.QLabel("Port:"))
        smtp_layout.addWidget(self.smtp_port_spin)

        self.smtp_user_edit = QtWidgets.QLineEdit()
        smtp_layout.addWidget(QtWidgets.QLabel("SMTP User:"))
        smtp_layout.addWidget(self.smtp_user_edit)

        self.smtp_pass_edit = QtWidgets.QLineEdit()
        self.smtp_pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        smtp_layout.addWidget(QtWidgets.QLabel("SMTP Pass:"))
        smtp_layout.addWidget(self.smtp_pass_edit)

        self.notify_email_edit = QtWidgets.QLineEdit()
        smtp_layout.addWidget(QtWidgets.QLabel("Notify Email:"))
        smtp_layout.addWidget(self.notify_email_edit)

        main_layout.addWidget(smtp_group)

        # SMTP-Werte aus smtp_settings.json
        self.smtp_enabled_check.setChecked(self.smtp_settings.get("enabled", False))
        self.smtp_host_edit.setText(self.smtp_settings.get("host", ""))
        self.smtp_port_spin.setValue(self.smtp_settings.get("port", 587))
        self.smtp_user_edit.setText(self.smtp_settings.get("user", ""))
        self.notify_email_edit.setText(self.smtp_settings.get("notify_email", ""))

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(line)

        # ---------- Split (lokal / remote) ----------
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(split, stretch=1)

        # LINKES PANE: Lokaler Dateibaum
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.local_path_label = QtWidgets.QLabel("Local Path:")
        left_layout.addWidget(self.local_path_label)

        local_search_layout = QtWidgets.QHBoxLayout()
        local_search_layout.addWidget(QtWidgets.QLabel("Search:"))
        self.local_search_edit = QtWidgets.QLineEdit()
        self.local_search_edit.textChanged.connect(self.apply_local_filter)
        local_search_layout.addWidget(self.local_search_edit)
        left_layout.addLayout(local_search_layout)

        self.local_model = QtWidgets.QFileSystemModel()
        self.local_model.setRootPath("/Volumes")
        self.local_model.setFilter(QtCore.QDir.AllEntries | QtCore.QDir.NoDotAndDotDot)

        self.local_proxy = LocalFilterProxyModel()
        self.local_proxy.setRecursiveFilteringEnabled(True)
        self.local_proxy.setSourceModel(self.local_model)

        self.local_view = QtWidgets.QTreeView()
        self.local_view.setModel(self.local_proxy)
        index_volumes = self.local_model.index("/Volumes")
        self.local_view.setRootIndex(self.local_proxy.mapFromSource(index_volumes))
        self.local_view.setColumnWidth(0, 250)
        self.local_view.setSortingEnabled(True)
        self.local_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.local_view.clicked.connect(self.on_local_item_clicked)

        left_layout.addWidget(self.local_view, stretch=1)
        split.addWidget(left_widget)

        # RECHTES PANE: Remote Ansicht
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.remote_path_label = QtWidgets.QLabel("Remote Path: /")
        right_layout.addWidget(self.remote_path_label)

        remote_search_layout = QtWidgets.QHBoxLayout()
        remote_search_layout.addWidget(QtWidgets.QLabel("Search:"))
        self.remote_search_edit = QtWidgets.QLineEdit()
        self.remote_search_edit.textChanged.connect(self.apply_remote_filter)
        remote_search_layout.addWidget(self.remote_search_edit)
        right_layout.addLayout(remote_search_layout)

        self.remote_list = QtWidgets.QTreeWidget()
        self.remote_list.setColumnCount(4)
        self.remote_list.setHeaderLabels(["Name", "Size", "Kind", "Modified"])
        self.remote_list.setSortingEnabled(True)
        self.remote_list.setColumnWidth(0, 400)
        self.remote_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.remote_list.itemDoubleClicked.connect(self.enter_remote_dir)
        right_layout.addWidget(self.remote_list, stretch=1)

        rm_btn_layout = QtWidgets.QHBoxLayout()
        self.new_folder_btn = QtWidgets.QPushButton("Neuer Ordner")
        self.new_folder_btn.clicked.connect(self.create_remote_folder)
        rm_btn_layout.addWidget(self.new_folder_btn)
        self.rename_btn = QtWidgets.QPushButton("Umbenennen")
        self.rename_btn.clicked.connect(self.rename_remote_item)
        rm_btn_layout.addWidget(self.rename_btn)
        self.delete_btn = QtWidgets.QPushButton("Löschen")
        self.delete_btn.clicked.connect(self.delete_remote_item)
        rm_btn_layout.addWidget(self.delete_btn)
        rm_btn_layout.addStretch()
        right_layout.addLayout(rm_btn_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_remote)
        btn_layout.addWidget(self.refresh_btn)
        self.up_btn = QtWidgets.QPushButton("Up")
        self.up_btn.clicked.connect(self.remote_up)
        btn_layout.addWidget(self.up_btn)
        right_layout.addLayout(btn_layout)
        split.addWidget(right_widget)

        bottom_layout = QtWidgets.QHBoxLayout()
        self.upload_btn = QtWidgets.QPushButton("Upload Selected")
        self.upload_btn.clicked.connect(self.upload_selected)
        bottom_layout.addWidget(self.upload_btn)
        self.download_btn = QtWidgets.QPushButton("Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        bottom_layout.addWidget(self.download_btn)
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

        style = QtWidgets.QApplication.style()
        self.folder_icon = style.standardIcon(QtWidgets.QStyle.SP_DirIcon)
        self.file_icon = style.standardIcon(QtWidgets.QStyle.SP_FileIcon)

        self.load_server_combo()

    # ----------------------------------------
    # Lokaler Pfad aktualisieren bei Klick in der TreeView
    # ----------------------------------------
    def on_local_item_clicked(self, index):
        source_index = self.local_proxy.mapToSource(index)
        path = self.local_model.filePath(source_index)
        debug_print(f"on_local_item_clicked(): path={path}")
        if os.path.isdir(path):
            self.current_local_path = path
            self.local_path_label.setText("Local Path: " + path)
            debug_print("Local path updated: " + path)
        else:
            debug_print("Geklickt wurde kein Verzeichnis: " + path)

    # ----------------------------------------
    # SERVER COMBO
    # ----------------------------------------
    def load_server_combo(self):
        debug_print("load_server_combo() aufgerufen")
        self.server_combo.blockSignals(True)
        self.server_combo.clear()

        servers = load_ftp_servers()
        debug_print(f"Gefundene Server in ftp_servers.json: {servers}")

        for srv in servers:
            self.server_combo.addItem(srv.get("name", "Unnamed"))

        self.server_combo.blockSignals(False)

    def server_combo_changed(self, index):
        debug_print(f"server_combo_changed({index})")
        servers = load_ftp_servers()
        if index < 0 or index >= len(servers):
            debug_print("Index außerhalb der Serverliste. Abbruch.")
            return
        srv = servers[index]
        debug_print(f"Ausgewählter Server: {srv}")
        self.host_edit.setText(srv.get("host", ""))
        self.user_edit.setText(srv.get("user", ""))
        self.port_edit.setText(str(srv.get("port", 21)))
        self.protocol_combo.setCurrentText(srv.get("protocol", "ftp"))

    def open_server_manager(self):
        debug_print("open_server_manager() aufgerufen")
        dlg = FtpServerManagerDialog(self.settings, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            debug_print("Server-Manager accepted => load_server_combo()")
            self.load_server_combo()

    # ----------------------------------------
    # LOKALES SUCHEN
    # ----------------------------------------
    def apply_local_filter(self, text):
        debug_print(f"apply_local_filter('{text}')")
        self.local_proxy.setFilterString(text)

    # ----------------------------------------
    # REMOTE SUCHEN
    # ----------------------------------------
    def apply_remote_filter(self):
        filter_text = self.remote_search_edit.text().lower().strip()
        debug_print(f"apply_remote_filter('{filter_text}')")
        self.remote_list.clear()
        for (name, is_dir, size, mod_time) in self.remote_items_all:
            if filter_text and (filter_text not in name.lower()):
                continue
            item = QtWidgets.QTreeWidgetItem(self.remote_list)
            item.setText(0, name)
            item.setText(1, str(size))
            item.setText(2, "Folder" if is_dir else "File")
            item.setText(3, str(mod_time))
            item.setData(0, QtCore.Qt.UserRole, is_dir)
            if is_dir:
                item.setIcon(0, self.folder_icon)
            else:
                item.setIcon(0, self.file_icon)

    # ----------------------------------------
    # CONNECT
    # ----------------------------------------
    def connect_ftp(self):
        debug_print("connect_ftp() aufgerufen")
        if self.ftp:
            self.ftp.disconnect()

        self.ftp = FTPManager()
        self.ftp.ftp_protocol = self.protocol_combo.currentText()
        self.ftp.host = self.host_edit.text().strip()
        self.ftp.user = self.user_edit.text().strip()

        debug_print(f"connect_ftp(): host={self.ftp.host}, user={self.ftp.user}, proto={self.ftp.ftp_protocol}")

        try:
            custom_port = int(self.port_edit.text().strip())
        except ValueError:
            custom_port = 21
        if self.ftp.ftp_protocol == "sftp":
            custom_port = 22
        self.ftp.port = custom_port

        self.ftp.keep_timestamp = self.keep_ts_check.isChecked()
        self.ftp.versioning_mode = self.version_combo.currentText()

        current_user = self.user_edit.text().strip()
        new_pass = self.pass_edit.text().strip()
        if new_pass and current_user:
            debug_print(f"connect_ftp(): set_password('PRisM-FTP', {current_user}, (PASSWORT))")
            keyring.set_password("PRisM-FTP", current_user, new_pass)

        try:
            self.ftp.connect()
            QtWidgets.QMessageBox.information(self, "Verbunden", "FTP-Verbindung erfolgreich.")
            debug_print("connect_ftp() => refresh_remote()")
            self.refresh_remote()
        except Exception as e:
            debug_print(f"Fehler beim Verbinden: {e}")
            QtWidgets.QMessageBox.critical(self, "Cannot connect", f"{e}")

    def refresh_remote(self):
        debug_print(f"refresh_remote() => current_remote_path={self.current_remote_path}")
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte erst verbinden.")
            return
        try:
            self.remote_items_all = self.ftp.list_directory(self.current_remote_path)
            debug_print(f"refresh_remote(): remote_items_all={self.remote_items_all}")
            self.remote_path_label.setText(f"Remote Path: {self.current_remote_path}")
            self.apply_remote_filter()
        except Exception as e:
            debug_print(f"Fehler bei refresh_remote: {e}")
            QtWidgets.QMessageBox.critical(self, "FTP Error", f"Cannot list directory: {e}")

    # ----------------------------------------
    # NAVIGATION REMOTE
    # ----------------------------------------
    def remote_up(self):
        debug_print("remote_up() aufgerufen")
        if self.current_remote_path == "/" or not self.current_remote_path:
            debug_print("remote_up(): root, kein Up möglich.")
            return
        new_path = os.path.dirname(self.current_remote_path.rstrip("/"))
        if not new_path:
            new_path = "/"
        debug_print(f"remote_up(): new_path={new_path}")
        self.current_remote_path = new_path
        self.refresh_remote()

    def enter_remote_dir(self, item, column):
        debug_print("enter_remote_dir() aufgerufen")
        is_dir = item.data(0, QtCore.Qt.UserRole)
        dir_name = item.text(0)
        debug_print(f"enter_remote_dir(): is_dir={is_dir}, dir_name={dir_name}")
        if is_dir:
            if self.current_remote_path == "/":
                new_path = "/" + dir_name
            else:
                new_path = self.current_remote_path.rstrip("/") + "/" + dir_name
            debug_print(f"enter_remote_dir(): new_path={new_path}")
            self.current_remote_path = new_path
            self.refresh_remote()

    # ----------------------------------------
    # Neue Funktionen: Remote Folder Management
    # ----------------------------------------
    def create_remote_folder(self):
        debug_print("create_remote_folder() aufgerufen")
        folder_name, ok = QtWidgets.QInputDialog.getText(self, "Neuer Ordner", "Ordnername:")
        if ok and folder_name:
            new_path = self.current_remote_path.rstrip("/") + "/" + folder_name
            debug_print(f"create_remote_folder(): new_path={new_path}")
            try:
                self.ftp.mkdir_remote(new_path)
                QtWidgets.QMessageBox.information(self, "Erfolg", f"Ordner '{folder_name}' wurde erstellt.")
                self.refresh_remote()
            except Exception as e:
                debug_print(f"Fehler beim Erstellen des Ordners: {e}")
                QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def rename_remote_item(self):
        debug_print("rename_remote_item() aufgerufen")
        items = self.remote_list.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte wählen Sie einen Eintrag zum Umbenennen aus.")
            return
        item = items[0]
        old_name = item.text(0)
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Umbenennen", "Neuer Name:", text=old_name)
        if ok and new_name and new_name != old_name:
            old_path = self.current_remote_path.rstrip("/") + "/" + old_name
            new_path = self.current_remote_path.rstrip("/") + "/" + new_name
            debug_print(f"rename_remote_item(): old_path={old_path}, new_path={new_path}")
            try:
                self.ftp.rename_remote(old_path, new_path)
                QtWidgets.QMessageBox.information(self, "Erfolg", f"'{old_name}' wurde umbenannt zu '{new_name}'.")
                self.refresh_remote()
            except Exception as e:
                debug_print(f"Fehler beim Umbenennen: {e}")
                QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def delete_remote_item(self):
        debug_print("delete_remote_item() aufgerufen")
        items = self.remote_list.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte wählen Sie einen Eintrag zum Löschen aus.")
            return
        item = items[0]
        name = item.text(0)
        is_dir = item.data(0, QtCore.Qt.UserRole)
        confirm = QtWidgets.QMessageBox.question(
            self, "Löschen?", f"Soll '{name}' wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return
        remote_path = self.current_remote_path.rstrip("/") + "/" + name
        debug_print(f"delete_remote_item(): remote_path={remote_path}, is_dir={is_dir}")
        try:
            if is_dir:
                self.ftp.delete_remote_directory(remote_path)
            else:
                self.ftp.delete_remote_file(remote_path)
            QtWidgets.QMessageBox.information(self, "Erfolg", f"'{name}' wurde gelöscht.")
            self.refresh_remote()
        except Exception as e:
            debug_print(f"Fehler beim Löschen: {e}")
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    # ----------------------------------------
    # UPLOAD: Interaktive Abfrage bei Dateikonflikt und Transfer-Info sammeln
    # ----------------------------------------
    def upload_selected(self):
        debug_print("upload_selected() aufgerufen")
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Verbindung.")
            return

        indexes = self.local_view.selectionModel().selectedIndexes()
        debug_print(f"upload_selected(): selectedIndexes={indexes}")
        if not indexes:
            debug_print("upload_selected(): keine Auswahl.")
            return
        file_paths = set()
        for ix in indexes:
            if ix.column() == 0:
                src_idx = self.local_proxy.mapToSource(ix)
                fp = self.local_model.filePath(src_idx)
                debug_print(f"upload_selected(): local filePath={fp}")
                if os.path.isfile(fp):
                    file_paths.add(fp)

        if not file_paths:
            debug_print("upload_selected(): keine Dateien ausgewählt.")
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien ausgewählt.")
            return

        debug_print(f"upload_selected(): file_paths={file_paths}")
        progress_dlg = TransferProgressDialog("Uploading...", parent=self)
        progress_dlg.set_file_count(len(file_paths))
        progress_dlg.show()

        transfer_results = []  # Sammle Ergebnisse

        try:
            for i, local_path in enumerate(file_paths, start=1):
                if progress_dlg.canceled:
                    debug_print("upload_selected(): Abbruch vom Benutzer.")
                    break
                progress_dlg.set_current_file(local_path, i)
                debug_print(f"upload_selected(): Uploading '{local_path}' to '{self.current_remote_path}'")
                base_name = os.path.basename(local_path)
                # Prüfe, ob die Datei remote bereits existiert
                existing_files = []
                try:
                    existing_files = [x[0] for x in self.ftp.list_directory(self.current_remote_path)]
                except Exception as ex:
                    debug_print(f"upload_selected(): Fehler beim Abrufen der Remote-Liste: {ex}")

                remote_file_path = self.current_remote_path.rstrip("/") + "/" + base_name
                if base_name in existing_files:
                    action = self.ask_file_conflict_action(base_name, "remote")
                    if action == "cancel":
                        debug_print(f"upload_selected(): user canceled => skip {local_path}")
                        transfer_results.append({
                            "file": local_path,
                            "direction": "UPLOAD",
                            "destination": remote_file_path,
                            "status": "SKIPPED",
                            "error": "User canceled"
                        })
                        continue
                    elif action == "suffix":
                        ver = 2
                        root, ext = os.path.splitext(base_name)
                        new_name = f"{root}_v{ver}{ext}"
                        while new_name in existing_files:
                            ver += 1
                            new_name = f"{root}_v{ver}{ext}"
                        remote_file_path = self.current_remote_path.rstrip("/") + "/" + new_name
                debug_print(f"upload_selected(): final remote_file_path={remote_file_path}")
                try:
                    self.ftp.upload_file(local_path, os.path.dirname(remote_file_path))
                    transfer_results.append({
                        "file": local_path,
                        "direction": "UPLOAD",
                        "destination": remote_file_path,
                        "status": "SUCCESS"
                    })
                except Exception as e:
                    debug_print(f"Fehler beim Upload: {e}")
                    transfer_results.append({
                        "file": local_path,
                        "direction": "UPLOAD",
                        "destination": remote_file_path,
                        "status": "FAILED",
                        "error": str(e)
                    })
                    self.ftp.send_failure_notification(str(e))
                    traceback.print_exc()
        finally:
            progress_dlg.close()
        self.refresh_remote()
        # Sende Transfer Summary Mail
        self.ftp.send_transfer_summary_email(transfer_results)

    # ----------------------------------------
    # DOWNLOAD: Interaktive Abfrage bei Dateikonflikt und Transfer-Info sammeln
    # ----------------------------------------
    def download_selected(self):
        debug_print("download_selected() aufgerufen")
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Verbindung.")
            return

        local_root = self.current_local_path
        debug_print(f"download_selected(): current_local_path={local_root}")
        if not os.path.isdir(local_root) or not os.access(local_root, os.W_OK):
            debug_print(f"download_selected(): '{local_root}' ist nicht schreibbar, fallback auf Home")
            local_root = QtCore.QDir.homePath()

        items = self.remote_list.selectedItems()
        if not items:
            debug_print("download_selected(): keine Auswahl im Remote-Tree.")
            return

        file_names = []
        for it in items:
            name = it.text(0)
            is_dir = it.data(0, QtCore.Qt.UserRole)
            debug_print(f"download_selected(): selected item => name={name}, is_dir={is_dir}")
            if not is_dir:
                file_names.append(name)

        if not file_names:
            debug_print("download_selected(): keine Dateien ausgewählt.")
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien ausgewählt.")
            return

        debug_print(f"download_selected(): file_names={file_names}, local_root={local_root}")
        progress_dlg = TransferProgressDialog("Downloading...", parent=self)
        progress_dlg.set_file_count(len(file_names))
        progress_dlg.show()

        transfer_results = []  # Liste für Download-Ergebnisse

        try:
            for i, fname in enumerate(file_names, start=1):
                if progress_dlg.canceled:
                    debug_print("download_selected(): Abbruch vom Benutzer.")
                    break
                remote_path = self.current_remote_path.rstrip("/") + "/" + fname
                local_file = os.path.join(local_root, fname)
                if os.path.exists(local_file):
                    action = self.ask_file_conflict_action(fname, "local")
                    if action == "cancel":
                        debug_print(f"download_selected(): user canceled => skip {remote_path}")
                        transfer_results.append({
                            "file": fname,
                            "direction": "DOWNLOAD",
                            "destination": local_file,
                            "status": "SKIPPED",
                            "error": "User canceled"
                        })
                        continue
                    elif action == "suffix":
                        ver = 2
                        root, ext = os.path.splitext(fname)
                        new_name = f"{root}_v{ver}{ext}"
                        while os.path.exists(os.path.join(local_root, new_name)):
                            ver += 1
                            new_name = f"{root}_v{ver}{ext}"
                        local_file = os.path.join(local_root, new_name)
                debug_print(f"download_selected(): final local_file={local_file}")
                progress_dlg.set_current_file(remote_path, i)
                try:
                    self.ftp.download_file(remote_path, os.path.dirname(local_file))
                    transfer_results.append({
                        "file": fname,
                        "direction": "DOWNLOAD",
                        "destination": local_file,
                        "status": "SUCCESS"
                    })
                except Exception as e:
                    debug_print(f"Fehler beim Download: {e}")
                    transfer_results.append({
                        "file": fname,
                        "direction": "DOWNLOAD",
                        "destination": local_file,
                        "status": "FAILED",
                        "error": str(e)
                    })
                    self.ftp.send_failure_notification(str(e))
                    traceback.print_exc()
        finally:
            progress_dlg.close()

        # Sende Transfer Summary Mail
        self.ftp.send_transfer_summary_email(transfer_results)

    # ----------------------------------------
    # Fragt den Nutzer bei Dateikonflikt ab
    # ----------------------------------------
    def ask_file_conflict_action(self, filename, location="local"):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Datei existiert")
        msg.setText(f"Die Datei '{filename}' existiert bereits auf {location}.\nWie möchten Sie fortfahren?")
        overwrite_btn = msg.addButton("Überschreiben", QtWidgets.QMessageBox.YesRole)
        suffix_btn = msg.addButton("Behalten (Suffix)", QtWidgets.QMessageBox.NoRole)
        cancel_btn = msg.addButton("Abbrechen", QtWidgets.QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == overwrite_btn:
            debug_print("ask_file_conflict_action: user chose OVERWRITE")
            return "overwrite"
        elif msg.clickedButton() == suffix_btn:
            debug_print("ask_file_conflict_action: user chose SUFFIX")
            return "suffix"
        else:
            debug_print("ask_file_conflict_action: user chose CANCEL")
            return "cancel"

    # ----------------------------------------
    # SAVE SETTINGS
    # ----------------------------------------
    def save_settings_slot(self):
        debug_print("save_settings_slot() aufgerufen")
        # FTP-Einstellungen in settings.json
        self.settings["ftp_protocol"] = self.protocol_combo.currentText()
        self.settings["ftp_host"] = self.host_edit.text().strip()
        self.settings["ftp_user"] = self.user_edit.text().strip()

        try:
            self.settings["ftp_port"] = int(self.port_edit.text().strip())
        except ValueError:
            self.settings["ftp_port"] = 21

        self.settings["keep_timestamp"] = self.keep_ts_check.isChecked()
        self.settings["versioning_mode"] = self.version_combo.currentText()

        debug_print("save_settings_slot(): Speichere FTP-Einstellungen")
        save_settings(self.settings)

        # SMTP-Einstellungen in smtp_settings.json
        self.smtp_settings["enabled"] = self.smtp_enabled_check.isChecked()
        self.smtp_settings["host"] = self.smtp_host_edit.text().strip()
        self.smtp_settings["port"] = self.smtp_port_spin.value()
        self.smtp_settings["user"] = self.smtp_user_edit.text().strip()
        self.smtp_settings["notify_email"] = self.notify_email_edit.text().strip()

        debug_print("save_settings_slot(): Speichere SMTP-Einstellungen")
        save_smtp_settings(self.smtp_settings)

        # Passwörter in den Keyring
        current_user = self.user_edit.text().strip()
        new_pass = self.pass_edit.text().strip()
        if new_pass and current_user:
            debug_print(f"save_settings_slot(): keyring.set_password('PRisM-FTP', {current_user}, (PASSWORT))")
            keyring.set_password("PRisM-FTP", current_user, new_pass)

        smtp_user = self.smtp_user_edit.text().strip()
        smtp_pass = self.smtp_pass_edit.text().strip()
        if smtp_pass and smtp_user:
            debug_print(f"save_settings_slot(): keyring.set_password('PRisM-SMTP', {smtp_user}, (PASSWORT))")
            keyring.set_password("PRisM-SMTP", smtp_user, smtp_pass)

        QtWidgets.QMessageBox.information(self, "Saved", "FTP- und SMTP-Einstellungen gespeichert.")

    def closeEvent(self, event: QtGui.QCloseEvent):
        debug_print("closeEvent() => disconnect FTP if needed")
        if self.ftp:
            self.ftp.disconnect()
        super().closeEvent(event)
