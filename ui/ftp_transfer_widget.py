#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import traceback
import keyring
from datetime import datetime
from PySide6 import QtWidgets, QtCore, QtGui

from utils.config_manager import (
    debug_print,
    load_settings,
    save_settings,
    load_ftp_servers,
)
from utils.ftp_manager import FTPManager
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
        self.setFilterWildcard(f"*{text}*")


# ---- Remote-Dateiliste mit Drop-Unterstützung ----
class RemoteFilesWidget(QtWidgets.QTreeWidget):
    filesDropped = QtCore.Signal(list)   # absolute Pfade (Finder)
    namesDropped = QtCore.Signal(list)   # Dateinamen (interner Drag von local_files)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        md = event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-qabstractitemmodeldatalist"):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        md = event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-qabstractitemmodeldatalist"):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        md = event.mimeData()
        # 1) Finder-URLs
        if md.hasUrls():
            paths = []
            for u in md.urls():
                p = u.toLocalFile()
                if p and os.path.isfile(p):
                    paths.append(p)
            if paths:
                self.filesDropped.emit(paths)
                event.acceptProposedAction()
                return
        # 2) Interner Drag aus QTreeWidget (local_files)
        if md.hasFormat("application/x-qabstractitemmodeldatalist"):
            try:
                data = bytes(md.data("application/x-qabstractitemmodeldatalist"))
                text = data.decode("utf-8", errors="ignore")
                candidates = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p for p in line.split("\x00") if p] if "\x00" in line else [line]
                    for p in parts:
                        p = p.strip()
                        if not p or "/" in p or ":" in p or "Qt" in p:
                            continue
                        if 0 < len(p) <= 255:
                            candidates.append(p)
                names = []
                seen = set()
                for c in candidates:
                    if c not in seen:
                        seen.add(c)
                        names.append(c)
                if names:
                    self.namesDropped.emit(names)
                    event.acceptProposedAction()
                    return
            except Exception:
                pass
        super().dropEvent(event)


class FtpTransferWidget(QtWidgets.QWidget):
    """
    FileZilla-ähnliche Oberfläche:
      - Local & Remote: Ordnerbaum + Inhalt
      - Remote-Ordnerbaum Finder-like (ohne sichtbare Dummy-Zeilen), Lazy-Load per Expand
      - Remote-Dateiliste akzeptiert Drag&Drop → Auto-Upload inkl. Queue/Status/Progress
      - Status-Log + Warteschlange
    """

    # UserRole Keys
    ROLE_PATH = QtCore.Qt.UserRole
    ROLE_NEEDS_LOAD = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.ftp = None

        self.current_remote_path = "/"
        self.remote_items_all = []
        self.current_local_path = "/Volumes"

        self.local_history = []
        self.remote_history = []

        self.queue_items = []  # list of QTreeWidgetItem

        debug_print("FtpTransferWidget: __init__()")
        self.init_ui()

    # ----------------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------------
    def init_ui(self):
        root_vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(root_vsplit)

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

        self.disconnect_btn = QtWidgets.QPushButton("Trennen")
        self.disconnect_btn.clicked.connect(self.disconnect_ftp)
        ftp_layout.addWidget(self.disconnect_btn)

        # ---------- Mittelteil (Local/Remote) ----------
        middle_hsplit = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # ===== LINKES PANEL (LOKAL) =====
        left = QtWidgets.QWidget()
        left_v = QtWidgets.QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)

        local_top = QtWidgets.QHBoxLayout()
        self.local_path_combo = QtWidgets.QComboBox()
        self.local_path_combo.setEditable(True)
        self.local_path_combo.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.local_path_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.local_path_combo.setEditText("/Volumes")
        self.local_path_combo.lineEdit().returnPressed.connect(self.local_path_entered)
        local_top.addWidget(QtWidgets.QLabel("Local Path:"))
        local_top.addWidget(self.local_path_combo)

        local_top.addWidget(QtWidgets.QLabel("Search:"))
        self.local_search_edit = QtWidgets.QLineEdit()
        self.local_search_edit.textChanged.connect(self.apply_local_filter)
        local_top.addWidget(self.local_search_edit)

        self.local_refresh_btn = QtWidgets.QPushButton("Refresh")
        self.local_refresh_btn.clicked.connect(self.refresh_local_views)
        local_top.addWidget(self.local_refresh_btn)

        self.local_auto_refresh = QtWidgets.QCheckBox("Auto-Refresh")
        local_top.addWidget(self.local_auto_refresh)

        self.local_up_btn = QtWidgets.QPushButton("Up")
        self.local_up_btn.clicked.connect(self.local_up)
        local_top.addWidget(self.local_up_btn)

        left_v.addLayout(local_top)

        left_vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.local_model = QtWidgets.QFileSystemModel()
        self.local_model.setRootPath(self.current_local_path)
        self.local_model.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot)

        self.local_proxy = LocalFilterProxyModel()
        self.local_proxy.setRecursiveFilteringEnabled(True)
        self.local_proxy.setSourceModel(self.local_model)

        self.local_tree = QtWidgets.QTreeView()
        self.local_tree.setModel(self.local_proxy)
        self.local_tree.setRootIndex(self.local_proxy.mapFromSource(self.local_model.index(self.current_local_path)))
        self.local_tree.setHeaderHidden(False)
        self.local_tree.setSortingEnabled(True)
        self.local_tree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        for col in range(4):
            self.local_tree.setColumnWidth(col, 220 if col == 0 else 140)
        self.local_tree.clicked.connect(self.on_local_tree_clicked)

        left_vsplit.addWidget(self.local_tree)

        self.local_files = QtWidgets.QTreeWidget()
        self.local_files.setColumnCount(4)
        self.local_files.setHeaderLabels(["Name", "Size", "Kind", "Modified"])
        self.local_files.setSortingEnabled(True)
        self.local_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.local_files.setUniformRowHeights(True)
        self.local_files.setColumnWidth(0, 320)
        self.local_files.itemDoubleClicked.connect(self.local_item_double_clicked)
        self.local_files.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.local_files.customContextMenuRequested.connect(self.on_local_context_menu)
        # interner Drag (für Drop auf Remote)
        self.local_files.setDragEnabled(True)

        left_vsplit.addWidget(self.local_files)
        left_vsplit.setSizes([300, 300])
        left_v.addWidget(left_vsplit)
        middle_hsplit.addWidget(left)

        # ===== RECHTES PANEL (REMOTE) =====
        right = QtWidgets.QWidget()
        right_v = QtWidgets.QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)

        remote_top = QtWidgets.QHBoxLayout()
        self.remote_path_combo = QtWidgets.QComboBox()
        self.remote_path_combo.setEditable(True)
        self.remote_path_combo.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.remote_path_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.remote_path_combo.setEditText(self.current_remote_path)
        self.remote_path_combo.lineEdit().returnPressed.connect(self.remote_path_entered)
        remote_top.addWidget(QtWidgets.QLabel("Remote Path:"))
        remote_top.addWidget(self.remote_path_combo)

        remote_top.addWidget(QtWidgets.QLabel("Search:"))
        self.remote_search_edit = QtWidgets.QLineEdit()
        self.remote_search_edit.textChanged.connect(self.apply_remote_filter)
        remote_top.addWidget(self.remote_search_edit)

        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_remote)
        remote_top.addWidget(self.refresh_btn)

        self.auto_refresh = QtWidgets.QCheckBox("Auto-Refresh")
        remote_top.addWidget(self.auto_refresh)

        self.up_btn = QtWidgets.QPushButton("Up")
        self.up_btn.clicked.connect(self.remote_up)
        remote_top.addWidget(self.up_btn)

        right_v.addLayout(remote_top)

        right_vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Ordnerbaum (Finder-like, Lazy-Load per Expand)
        self.remote_folders = QtWidgets.QTreeWidget()
        self.remote_folders.setColumnCount(5)
        self.remote_folders.setHeaderLabels(["Name", "Owner", "Size", "Kind", "Modified"])
        self.remote_folders.setSortingEnabled(True)
        self.remote_folders.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.remote_folders.setUniformRowHeights(True)
        self.remote_folders.setColumnWidth(0, 320)
        self.remote_folders.itemDoubleClicked.connect(self.enter_remote_dir)
        self.remote_folders.itemExpanded.connect(self.on_remote_folder_expanded)
        # Optional: Bei einfachem Klick nur Dateien-Panel aktualisieren (ohne Pfadwechsel)
        self.remote_folders.itemClicked.connect(self.preview_remote_dir)

        right_vsplit.addWidget(self.remote_folders)

        # Dateien/Unterordner – mit Drop
        self.remote_files = RemoteFilesWidget()
        self.remote_files.setColumnCount(5)
        self.remote_files.setHeaderLabels(["Name", "Owner", "Size", "Kind", "Modified"])
        self.remote_files.setSortingEnabled(True)
        self.remote_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.remote_files.setUniformRowHeights(True)
        self.remote_files.setColumnWidth(0, 320)
        self.remote_files.itemDoubleClicked.connect(self.remote_item_double_clicked)
        self.remote_files.filesDropped.connect(self.handle_drop_upload_files)
        self.remote_files.namesDropped.connect(self.handle_drop_upload_names)

        right_vsplit.addWidget(self.remote_files)
        right_vsplit.setSizes([300, 300])
        right_v.addWidget(right_vsplit)
        middle_hsplit.addWidget(right)

        # ===== Buttons =====
        button_row = QtWidgets.QHBoxLayout()
        self.upload_btn = QtWidgets.QPushButton("Upload Selected")
        self.upload_btn.clicked.connect(self.upload_selected)
        button_row.addWidget(self.upload_btn)

        self.download_btn = QtWidgets.QPushButton("Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        button_row.addWidget(self.download_btn)

        button_row.addStretch()

        self.new_folder_btn = QtWidgets.QPushButton("Neuer Ordner")
        self.new_folder_btn.clicked.connect(self.create_remote_folder)
        button_row.addWidget(self.new_folder_btn)

        self.rename_btn = QtWidgets.QPushButton("Umbenennen")
        self.rename_btn.clicked.connect(self.rename_remote_item)
        button_row.addWidget(self.rename_btn)

        self.delete_btn = QtWidgets.QPushButton("Löschen")
        self.delete_btn.clicked.connect(self.delete_remote_item)
        button_row.addWidget(self.delete_btn)

        middle_container = QtWidgets.QWidget()
        middle_vbox = QtWidgets.QVBoxLayout(middle_container)
        middle_vbox.setContentsMargins(0, 0, 0, 0)
        middle_vbox.addWidget(middle_hsplit, stretch=1)
        middle_vbox.addLayout(button_row)

        # ---------- Unten ----------
        bottom_vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        status_group = QtWidgets.QGroupBox("Status")
        sg_layout = QtWidgets.QVBoxLayout(status_group)
        self.status_edit = QtWidgets.QPlainTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMaximumBlockCount(500)
        sg_layout.addWidget(self.status_edit)

        queue_group = QtWidgets.QGroupBox("Warteschlange")
        qg_layout = QtWidgets.QVBoxLayout(queue_group)
        self.queue = QtWidgets.QTreeWidget()
        self.queue.setColumnCount(8)
        self.queue.setHeaderLabels([
            "Direction", "File", "Destination", "Status", "Progress",
            "Started", "Finished", "Error"
        ])
        self.queue.setSortingEnabled(True)
        self.queue.setColumnWidth(1, 320)
        qg_layout.addWidget(self.queue)

        bottom_vsplit.addWidget(status_group)
        bottom_vsplit.addWidget(queue_group)
        bottom_vsplit.setSizes([220, 120])

        top_mid_bottom = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top_mid_bottom.addWidget(ftp_group)
        top_mid_bottom.addWidget(middle_container)
        top_mid_bottom.addWidget(bottom_vsplit)
        top_mid_bottom.setSizes([160, 600, 180])

        root_vsplit.addWidget(top_mid_bottom)

        # Icons
        style = QtWidgets.QApplication.style()
        self.folder_icon = style.standardIcon(QtWidgets.QStyle.SP_DirIcon)
        self.file_icon = style.standardIcon(QtWidgets.QStyle.SP_FileIcon)

        # Init
        self.load_server_combo()
        self.populate_local_files(self.current_local_path)

        # Timer Auto-Refresh
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.on_timer_tick)
        self.timer.start()

        self.append_status("Bereit.")

    # ----------------------------------------------------------------------
    # Status + Queue
    # ----------------------------------------------------------------------
    def append_status(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        debug_print(line)
        self.status_edit.appendPlainText(line)

    def queue_add(self, direction, file_path, destination):
        item = QtWidgets.QTreeWidgetItem([
            direction, os.path.basename(file_path), destination, "Queued",
            "0%", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", ""
        ])
        self.queue.addTopLevelItem(item)
        self.queue_items.append(item)
        return item

    def queue_update(self, item, *, status=None, progress=None, finished=False, error=None):
        if status is not None:
            item.setText(3, status)
        if progress is not None:
            item.setText(4, f"{progress}%" if isinstance(progress, int) else "–")
        if finished and not item.text(6):
            item.setText(6, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if error:
            item.setText(7, error)

    # ----------------------------------------------------------------------
    # Timer
    # ----------------------------------------------------------------------
    def on_timer_tick(self):
        if self.local_auto_refresh.isChecked():
            self.refresh_local_views()
        if self.auto_refresh.isChecked() and self.ftp and self.ftp.conn:
            self.refresh_remote()

    # ---- Local side ----
    def local_path_entered(self):
        path = self.local_path_combo.currentText().strip()
        if os.path.isdir(path):
            if path not in self.local_history:
                self.local_history.insert(0, path)
                self.local_path_combo.insertItem(0, path)
            self.current_local_path = path
            src_index = self.local_model.index(self.current_local_path)
            self.local_tree.setRootIndex(self.local_proxy.mapFromSource(src_index))
            self.populate_local_files(self.current_local_path)
        else:
            QtWidgets.QMessageBox.warning(self, "Pfad", "Pfad existiert nicht.")

    def on_local_tree_clicked(self, index):
        source_index = self.local_proxy.mapToSource(index)
        path = self.local_model.filePath(source_index)
        if os.path.isdir(path):
            self.current_local_path = path
            self.local_path_combo.setEditText(path)
            self.populate_local_files(path)

    def local_up(self):
        if not self.current_local_path or self.current_local_path == "/":
            return
        new_path = os.path.dirname(self.current_local_path.rstrip("/")) or "/"
        if os.path.isdir(new_path):
            self.current_local_path = new_path
            self.local_path_combo.setEditText(new_path)
            self.local_tree.setRootIndex(self.local_proxy.mapFromSource(self.local_model.index(new_path)))
            self.populate_local_files(new_path)

    def refresh_local_views(self):
        self.populate_local_files(self.current_local_path)

    def populate_local_files(self, folder):
        self.local_files.clear()
        if not os.path.isdir(folder):
            return
        try:
            # Ordner
            for name in sorted(os.listdir(folder)):
                full = os.path.join(folder, name)
                if os.path.isdir(full):
                    mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
                    it = QtWidgets.QTreeWidgetItem([name, "", "Folder", mtime])
                    it.setIcon(0, self.folder_icon)
                    self.local_files.addTopLevelItem(it)
            # Dateien
            for name in sorted(os.listdir(folder)):
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    size = os.path.getsize(full)
                    kind = QtCore.QFileInfo(full).suffix() or "File"
                    mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
                    it = QtWidgets.QTreeWidgetItem([name, str(size), kind, mtime])
                    it.setIcon(0, self.file_icon)
                    self.local_files.addTopLevelItem(it)
        except Exception as e:
            self.append_status(f"Lokale Dateiliste Fehler: {e}")

    def local_item_double_clicked(self, item, _column):
        name = item.text(0)
        is_folder = (item.text(2) == "Folder")
        target = os.path.join(self.current_local_path, name)
        if is_folder and os.path.isdir(target):
            self.current_local_path = target
            self.local_path_combo.setEditText(target)
            self.populate_local_files(target)

    def on_local_context_menu(self, pos: QtCore.QPoint):
        item = self.local_files.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("Öffnen")
        act_reveal = menu.addAction("Im Finder anzeigen")
        chosen = menu.exec(self.local_files.viewport().mapToGlobal(pos))
        if not chosen:
            return
        name = item.text(0)
        path = os.path.join(self.current_local_path, name)
        try:
            if chosen == act_open:
                subprocess.Popen(["open", path])
            elif chosen == act_reveal:
                subprocess.Popen(["open", "-R", path])
        except Exception as e:
            self.append_status(f"Kontextmenü-Fehler: {e}")

    # ---- Remote side ----
    def remote_path_entered(self):
        path = self.remote_path_combo.currentText().strip() or "/"
        self.current_remote_path = path if path.startswith("/") else "/" + path
        if path not in self.remote_history:
            self.remote_history.insert(0, self.current_remote_path)
            self.remote_path_combo.insertItem(0, self.current_remote_path)
        self.refresh_remote()

    # SERVER COMBO
    def load_server_combo(self):
        self.server_combo.blockSignals(True)
        self.server_combo.clear()
        servers = load_ftp_servers()
        for srv in servers:
            self.server_combo.addItem(srv.get("name", "Unnamed"))
        self.server_combo.blockSignals(False)

    def server_combo_changed(self, index):
        servers = load_ftp_servers()
        if 0 <= index < len(servers):
            srv = servers[index]
            self.host_edit.setText(srv.get("host", ""))
            self.user_edit.setText(srv.get("user", ""))
            self.port_edit.setText(str(srv.get("port", 21)))
            self.protocol_combo.setCurrentText(srv.get("protocol", "ftp"))

    def open_server_manager(self):
        dlg = FtpServerManagerDialog(self.settings, parent=self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.load_server_combo()

    # Suche/Filter
    def apply_local_filter(self, text):
        self.local_proxy.setFilterString(text)

    def apply_remote_filter(self):
        filter_text = self.remote_search_edit.text().lower().strip()
        self.populate_remote_views(self.remote_items_all, filter_text)

    # CONNECT/DISCONNECT
    def connect_ftp(self):
        if self.ftp:
            self.ftp.disconnect()
        self.ftp = FTPManager()
        self.ftp.ftp_protocol = self.protocol_combo.currentText()
        self.ftp.host = self.host_edit.text().strip()
        self.ftp.user = self.user_edit.text().strip()

        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            port = 21
        if self.ftp.ftp_protocol == "sftp":
            port = 22
        self.ftp.port = port

        self.ftp.keep_timestamp = self.keep_ts_check.isChecked()
        self.ftp.versioning_mode = self.version_combo.currentText()

        user = self.user_edit.text().strip()
        pw = self.pass_edit.text().strip()
        if pw and user:
            keyring.set_password("PRisM-FTP", user, pw)

        try:
            self.ftp.connect()
            QtWidgets.QMessageBox.information(self, "Verbunden", "FTP-Verbindung erfolgreich.")
            self.append_status(f"Verbunden: {self.ftp.user}@{self.ftp.host}:{self.ftp.port} ({self.ftp.ftp_protocol})")
            self.refresh_remote()
        except Exception as e:
            self.append_status(f"Verbindungsfehler: {e}")
            QtWidgets.QMessageBox.critical(self, "Cannot connect", f"{e}")

    def disconnect_ftp(self):
        if self.ftp:
            self.ftp.disconnect()
            self.append_status("Verbindung getrennt.")
            QtWidgets.QMessageBox.information(self, "Getrennt", "FTP-Verbindung beendet.")

    # Remote-Ansichten
    def refresh_remote(self):
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte erst verbinden.")
            return
        try:
            raw = self.ftp.list_directory(self.current_remote_path)
            normalized = []
            for entry in raw:
                if len(entry) == 4:
                    name, is_dir, size, mod = entry
                    owner = ""
                else:
                    name, is_dir, size, mod, owner = entry
                normalized.append((name, is_dir, size, mod, owner))
            self.remote_items_all = normalized
            self.remote_path_combo.setEditText(self.current_remote_path)

            # ▸ Ordnerbaum entlang des aktuellen Pfades erstellen/zeigen
            self.populate_remote_folder_tree_breadcrumb()
            # ▸ Inhalte unten
            self.populate_remote_views(self.remote_items_all, self.remote_search_edit.text().lower().strip())

            self.append_status(f"Remote aktualisiert: {self.current_remote_path}")
        except Exception as e:
            self.append_status(f"Remote-Listing Fehler: {e}")
            QtWidgets.QMessageBox.critical(self, "FTP Error", f"Cannot list directory: {e}")

    def populate_remote_views(self, items, filter_text=""):
        self.remote_files.clear()
        for (name, is_dir, size, mod_time, owner) in items:
            if filter_text and (filter_text not in name.lower()):
                continue
            if is_dir:
                it = QtWidgets.QTreeWidgetItem([name, owner or "", "", "Folder", str(mod_time)])
                it.setIcon(0, self.folder_icon)
            else:
                it = QtWidgets.QTreeWidgetItem([name, owner or "", str(size), "File", str(mod_time)])
                it.setIcon(0, self.file_icon)
            self.remote_files.addTopLevelItem(it)

    # --- Ordnerbaum (Finder-like Lazy-Load, ohne sichtbares Dummy) ---
    def populate_remote_folder_tree_breadcrumb(self):
        """Zeigt die Kette '/', 'foo', 'bar' … bis zum aktuellen Pfad.
        Unter JEDEM Knoten kann per Expand die nächste Ebene lazy geladen werden.
        Keine sichtbaren Dummy-Zeilen.
        """
        self.remote_folders.clear()

        # 1) Pfadkette bauen
        parts = [p for p in self.current_remote_path.split("/") if p]
        full_paths = []
        cur = "/"
        full_paths.append(cur)  # Root zuerst
        for p in parts:
            cur = cur.rstrip("/") + "/" + p
            full_paths.append(cur)

        # 2) Kette in Tree legen
        parent_item = None
        for fp in full_paths:
            name = fp if fp == "/" else fp.split("/")[-1]
            it = QtWidgets.QTreeWidgetItem([name, "", "", "Folder", ""])
            it.setIcon(0, self.folder_icon)
            it.setData(0, self.ROLE_PATH, fp)
            # Indikator anzeigen, obwohl (noch) keine Kinder gesetzt sind
            it.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            it.setData(0, self.ROLE_NEEDS_LOAD, True)
            if parent_item is None:
                self.remote_folders.addTopLevelItem(it)
            else:
                parent_item.addChild(it)
            parent_item = it

        # 3) automatisch entlang des Pfads expandieren und Kinder laden
        root = self.remote_folders.topLevelItem(0)
        if root:
            self._ensure_children_loaded(root)
            self.remote_folders.expandItem(root)
            node = root
            # gehe die Kette runter und expandiere/fülle jedes Element
            for i in range(1, len(full_paths)):
                if node and node.childCount() > 0:
                    # finde das Kind mit passendem Namen/Vollpfad
                    want_full = full_paths[i].rstrip("/")
                    next_node = None
                    for c in range(node.childCount()):
                        ch = node.child(c)
                        ch_full = (ch.data(0, self.ROLE_PATH) or "").rstrip("/")
                        if ch_full == want_full:
                            next_node = ch
                            break
                    if next_node:
                        self._ensure_children_loaded(next_node)
                        self.remote_folders.expandItem(next_node)
                        node = next_node

    def _ensure_children_loaded(self, item: QtWidgets.QTreeWidgetItem):
        """Lädt Unterordner für 'item', wenn noch nicht geladen."""
        needs = item.data(0, self.ROLE_NEEDS_LOAD)
        if not needs:
            return
        base = item.data(0, self.ROLE_PATH) or "/"
        try:
            entries = self.ftp.list_directory(base)
        except Exception as e:
            self.append_status(f"Ordnerbaum-Load Fehler: {e}")
            return
        # bestehende Kinder entfernen, wir bauen frisch auf
        while item.childCount() > 0:
            item.takeChild(0)
        for e in entries:
            if len(e) == 4:
                name, is_dir, size, mod = e
                owner = ""
            else:
                name, is_dir, size, mod, owner = e
            if not is_dir:
                continue
            full = self._join_remote(base, name)
            ch = QtWidgets.QTreeWidgetItem([name, owner or "", "", "Folder", str(mod)])
            ch.setIcon(0, self.folder_icon)
            ch.setData(0, self.ROLE_PATH, full)
            ch.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            ch.setData(0, self.ROLE_NEEDS_LOAD, True)
            item.addChild(ch)
        # markiere als geladen
        item.setData(0, self.ROLE_NEEDS_LOAD, False)

    def on_remote_folder_expanded(self, item: QtWidgets.QTreeWidgetItem):
        # lazy load, wenn noch nicht geladen
        self._ensure_children_loaded(item)

    def preview_remote_dir(self, item: QtWidgets.QTreeWidgetItem, _column: int):
        """
        Einfache Vorschau: Klick auf Ordner im Tree aktualisiert nur die Dateienliste unten,
        ohne self.current_remote_path zu ändern oder die Breadcrumbs neu zu bauen.
        """
        path = item.data(0, self.ROLE_PATH) or "/"
        # Inhalt dieses Pfads listen, aber nicht den "aktuellen" Pfad ändern
        try:
            raw = self.ftp.list_directory(path)
            normalized = []
            for entry in raw:
                if len(entry) == 4:
                    name, is_dir, size, mod = entry
                    owner = ""
                else:
                    name, is_dir, size, mod, owner = entry
                normalized.append((name, is_dir, size, mod, owner))
            self.populate_remote_views(normalized, self.remote_search_edit.text().lower().strip())
        except Exception as e:
            self.append_status(f"Vorschau-Listing Fehler: {e}")

    def _join_remote(self, base: str, name: str) -> str:
        if not base or base == "/":
            return "/" + name
        return base.rstrip("/") + "/" + name

    def remote_item_double_clicked(self, item, _column):
        if item.text(3) == "Folder":
            dir_name = item.text(0)
            new_path = self._join_remote(self.current_remote_path, dir_name)
            self.current_remote_path = new_path
            self.refresh_remote()

    def remote_up(self):
        if self.current_remote_path == "/" or not self.current_remote_path:
            return
        new_path = os.path.dirname(self.current_remote_path.rstrip("/")) or "/"
        self.current_remote_path = new_path
        self.refresh_remote()

    def enter_remote_dir(self, item, _column):
        # Tree: nimm immer den im Item gespeicherten Vollpfad
        path = item.data(0, self.ROLE_PATH)
        if not path:
            dir_name = item.text(0)
            path = self._join_remote(self.current_remote_path, dir_name)
        self.current_remote_path = path
        self.refresh_remote()

    # ---------------- Drag&Drop Upload ----------------
    def handle_drop_upload_files(self, file_paths: list[str]):
        paths = [p for p in file_paths if os.path.isfile(p)]
        if paths:
            self.append_status(f"Drop: {len(paths)} Datei(en) empfangen.")
            self._do_upload_paths(paths)

    def handle_drop_upload_names(self, names: list[str]):
        paths = []
        for n in names:
            full = os.path.join(self.current_local_path, n)
            if os.path.isfile(full):
                paths.append(full)
        if paths:
            self.append_status(f"Drop (intern): {len(paths)} Datei(en) empfangen.")
            self._do_upload_paths(paths)

    def _existing_remote_names(self) -> list:
        try:
            raw = self.ftp.list_directory(self.current_remote_path)
            return [e[0] for e in raw]
        except Exception:
            return []

    def _do_upload_paths(self, file_paths: list[str]):
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Verbindung.")
            return

        progress = TransferProgressDialog("Uploading...", self)
        progress.set_file_count(len(file_paths))
        progress.show()

        try:
            existing = set(self._existing_remote_names())
            for i, local_path in enumerate(file_paths, start=1):
                if progress.canceled:
                    break
                base_name = os.path.basename(local_path)
                remote_file_path = self._join_remote(self.current_remote_path, base_name)

                # Konfliktabfrage
                final_remote_folder = os.path.dirname(remote_file_path)
                final_name = base_name
                if base_name in existing:
                    action = self.ask_file_conflict_action(base_name, "remote")
                    if action == "cancel":
                        self.append_status(f"Upload abgebrochen (Konflikt): {local_path}")
                        continue
                    elif action == "suffix":
                        ver = 2
                        root, ext = os.path.splitext(base_name)
                        new_name = f"{root}_v{ver}{ext}"
                        while new_name in existing:
                            ver += 1
                            new_name = f"{root}_v{ver}{ext}"
                        final_name = new_name
                        remote_file_path = self._join_remote(self.current_remote_path, final_name)

                qitem = self.queue_add("UPLOAD", local_path, remote_file_path)
                self.queue_update(qitem, status="Running", progress=0)
                self.append_status(f"Upload gestartet (Drop): {local_path} → {remote_file_path}")
                progress.set_current_file(final_name, i)

                try:
                    if self.ftp.ftp_protocol == "ftp":
                        cb = (lambda p, qi=qitem: (self.queue_update(qi, progress=p),
                                                   QtWidgets.QApplication.processEvents()))
                        self.ftp.upload_file(local_path, final_remote_folder, progress_callback=cb)
                    else:
                        self.queue_update(qitem, progress=None)  # „–“
                        self.ftp.upload_file(local_path, final_remote_folder)

                    self.queue_update(qitem, status="SUCCESS", progress=100, finished=True)
                    self.append_status(f"Upload fertig: {remote_file_path}")
                    existing.add(final_name)
                except Exception as e:
                    self.queue_update(qitem, status="FAILED", error=str(e), finished=True)
                    self.append_status(f"Upload Fehler: {e}")
        finally:
            progress.close()

        self.refresh_remote()

    # ---------------- Remote Dateimanagement ----------------
    def create_remote_folder(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Neuer Ordner", "Ordnername:")
        if ok and name:
            new_path = self._join_remote(self.current_remote_path, name)
            try:
                self.ftp.mkdir_remote(new_path)
                QtWidgets.QMessageBox.information(self, "Erfolg", f"Ordner '{name}' wurde erstellt.")
                self.append_status(f"Remote-Ordner erstellt: {new_path}")
                self.refresh_remote()
            except Exception as e:
                self.append_status(f"Ordner erstellen Fehler: {e}")
                QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def rename_remote_item(self):
        items = self.remote_files.selectedItems() or self.remote_folders.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte wählen Sie einen Eintrag zum Umbenennen aus.")
            return
        item = items[0]
        old_name = item.text(0)
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Umbenennen", "Neuer Name:", text=old_name)
        if ok and new_name and new_name != old_name:
            old_path = self._join_remote(self.current_remote_path, old_name)
            new_path = self._join_remote(self.current_remote_path, new_name)
            try:
                self.ftp.rename_remote(old_path, new_path)
                QtWidgets.QMessageBox.information(self, "Erfolg", f"'{old_name}' wurde umbenannt zu '{new_name}'.")
                self.append_status(f"Umbenannt: {old_path} → {new_path}")
                self.refresh_remote()
            except Exception as e:
                self.append_status(f"Umbenennen Fehler: {e}")
                QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def delete_remote_item(self):
        items = self.remote_files.selectedItems() or self.remote_folders.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte wählen Sie einen Eintrag zum Löschen aus.")
            return
        item = items[0]
        name = item.text(0)
        is_dir = (item.text(3) == "Folder")
        if QtWidgets.QMessageBox.question(self, "Löschen?", f"Soll '{name}' wirklich gelöscht werden?",
                                          QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return
        remote_path = self._join_remote(self.current_remote_path, name)
        try:
            if is_dir:
                self.ftp.delete_remote_directory(remote_path)
            else:
                self.ftp.delete_remote_file(remote_path)
            QtWidgets.QMessageBox.information(self, "Erfolg", f"'{name}' wurde gelöscht.")
            self.append_status(f"Gelöscht: {remote_path}")
            self.refresh_remote()
        except Exception as e:
            self.append_status(f"Löschen Fehler: {e}")
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    # ----------------------------------------
    # TRANSFERS (Buttons)
    # ----------------------------------------
    def upload_selected(self):
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Verbindung.")
            return

        items = self.local_files.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien/Ordner ausgewählt.")
            return

        file_paths = []
        for it in items:
            if it.text(2) != "Folder":
                file_paths.append(os.path.join(self.current_local_path, it.text(0)))

        if not file_paths:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien ausgewählt.")
            return

        progress_dlg = TransferProgressDialog("Uploading...", parent=self)
        progress_dlg.set_file_count(len(file_paths))
        progress_dlg.show()

        try:
            for i, local_path in enumerate(file_paths, start=1):
                if progress_dlg.canceled:
                    break
                base_name = os.path.basename(local_path)
                remote_file_path = self._join_remote(self.current_remote_path, base_name)

                qitem = self.queue_add("UPLOAD", local_path, remote_file_path)
                self.queue_update(qitem, status="Running", progress=0)

                progress_dlg.set_current_file(local_path, i)
                self.append_status(f"Upload gestartet: {local_path} → {remote_file_path}")

                callback = (lambda p, qi=qitem: (self.queue_update(qi, progress=p),
                                                 QtWidgets.QApplication.processEvents()))
                try:
                    if self.ftp.ftp_protocol == "ftp":
                        self.ftp.upload_file(local_path, os.path.dirname(remote_file_path), progress_callback=callback)
                    else:
                        self.queue_update(qitem, progress=None)  # „–“
                        self.ftp.upload_file(local_path, os.path.dirname(remote_file_path))
                    self.queue_update(qitem, status="SUCCESS", progress=100, finished=True)
                    self.append_status(f"Upload fertig: {remote_file_path}")
                except Exception as e:
                    self.queue_update(qitem, status="FAILED", error=str(e), finished=True)
                    self.append_status(f"Upload Fehler: {e}")
                    traceback.print_exc()
        finally:
            progress_dlg.close()

        self.refresh_remote()

    def download_selected(self):
        if not self.ftp or not self.ftp.conn:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Verbindung.")
            return

        local_root = self.current_local_path
        if not os.path.isdir(local_root) or not os.access(local_root, os.W_OK):
            local_root = QtCore.QDir.homePath()

        items = self.remote_files.selectedItems()
        if not items:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien/Ordner ausgewählt.")
            return

        file_names = [it.text(0) for it in items if it.text(3) != "Folder"]
        if not file_names:
            QtWidgets.QMessageBox.information(self, "Info", "Keine Dateien ausgewählt.")
            return

        progress_dlg = TransferProgressDialog("Downloading...", parent=self)
        progress_dlg.set_file_count(len(file_names))
        progress_dlg.show()

        try:
            for i, fname in enumerate(file_names, start=1):
                remote_path = self._join_remote(self.current_remote_path, fname)
                local_file = os.path.join(local_root, fname)

                if os.path.exists(local_file):
                    action = self.ask_file_conflict_action(fname, "local")
                    if action == "cancel":
                        self.append_status(f"Download abgebrochen (Konflikt): {remote_path}")
                        continue
                    elif action == "suffix":
                        ver = 2
                        root, ext = os.path.splitext(fname)
                        new_name = f"{root}_v{ver}{ext}"
                        while os.path.exists(os.path.join(local_root, new_name)):
                            ver += 1
                            new_name = f"{root}_v{ver}{ext}"
                        local_file = os.path.join(local_root, new_name)

                qitem = self.queue_add("DOWNLOAD", fname, local_file)
                self.queue_update(qitem, status="Running", progress=0)

                progress_dlg.set_current_file(remote_path, i)
                self.append_status(f"Download gestartet: {remote_path} → {local_file}")

                try:
                    self.ftp.download_file(remote_path, os.path.dirname(local_file))
                    self.queue_update(qitem, status="SUCCESS", progress=100, finished=True)
                    self.append_status(f"Download fertig: {local_file}")
                except Exception as e:
                    self.queue_update(qitem, status="FAILED", error=str(e), finished=True)
                    self.append_status(f"Download Fehler: {e}")
                    traceback.print_exc()
        finally:
            progress_dlg.close()

        self.populate_local_files(self.current_local_path)

    # ----------------------------------------
    # Dateikonflikt-Dialog
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
            return "overwrite"
        elif msg.clickedButton() == suffix_btn:
            return "suffix"
        else:
            return "cancel"

    # ----------------------------------------
    # SAVE SETTINGS (nur FTP)
    # ----------------------------------------
    def save_settings_slot(self):
        self.settings["ftp_protocol"] = self.protocol_combo.currentText()
        self.settings["ftp_host"] = self.host_edit.text().strip()
        self.settings["ftp_user"] = self.user_edit.text().strip()
        try:
            self.settings["ftp_port"] = int(self.port_edit.text().strip())
        except ValueError:
            self.settings["ftp_port"] = 21
        self.settings["keep_timestamp"] = self.keep_ts_check.isChecked()
        self.settings["versioning_mode"] = self.version_combo.currentText()
        save_settings(self.settings)

        # FTP Passwort im Keyring ablegen (SMTP liegt jetzt im Settings-Tab)
        user = self.user_edit.text().strip()
        pw = self.pass_edit.text().strip()
        if pw and user:
            keyring.set_password("PRisM-FTP", user, pw)

        QtWidgets.QMessageBox.information(self, "Saved", "FTP-Einstellungen gespeichert.")

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.ftp:
            self.ftp.disconnect()
        super().closeEvent(event)