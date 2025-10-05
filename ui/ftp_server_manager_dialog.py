#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import keyring
import copy
from PySide6 import QtWidgets, QtCore
from utils.config_manager import (
    load_settings,     # Nur falls du self.settings brauchst
    debug_print,
    load_ftp_servers,  # NEU: Zum Laden aus ftp_servers.json
    save_ftp_servers   # NEU: Zum Speichern in ftp_servers.json
)

class FtpServerManagerDialog(QtWidgets.QDialog):
    """
    Verwalten mehrerer FTP-Server (Name, Host, Port, User, Protocol).
    Passwörter liegen im Keyring, Key=User.
    Daten werden NICHT in settings.json gespeichert, sondern in ftp_servers.json.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server-Verwaltung")
        self.resize(600, 300)

        # self.settings ist nur ein Verweis auf das Haupt-Settings-Objekt,
        # in das wir bei "Übernehmen" den aktuell ausgewählten Server
        # für das Hauptprogramm übernehmen (Host, Port, User, etc.).
        self.settings = settings

        # Statt self.settings.get("ftp_servers", []) nutzen wir load_ftp_servers().
        self.servers = load_ftp_servers()  # => Liste von Dicts

        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Host", "Port", "User", "Protocol"])
        layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Neu")
        self.add_btn.clicked.connect(self.add_server)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QtWidgets.QPushButton("Bearbeiten")
        self.edit_btn.clicked.connect(self.edit_server)
        btn_layout.addWidget(self.edit_btn)

        self.del_btn = QtWidgets.QPushButton("Löschen")
        self.del_btn.clicked.connect(self.delete_server)
        btn_layout.addWidget(self.del_btn)

        btn_layout.addStretch()

        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QtWidgets.QPushButton("Übernehmen")
        self.ok_btn.clicked.connect(self.accept_dialog)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)

        self.load_table()

    def load_table(self):
        self.table.setRowCount(len(self.servers))
        for row, srv in enumerate(self.servers):
            name_item = QtWidgets.QTableWidgetItem(srv.get("name", ""))
            host_item = QtWidgets.QTableWidgetItem(srv.get("host", ""))
            port_item = QtWidgets.QTableWidgetItem(str(srv.get("port", 21)))
            user_item = QtWidgets.QTableWidgetItem(srv.get("user", ""))
            proto_item = QtWidgets.QTableWidgetItem(srv.get("protocol", "ftp"))

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, host_item)
            self.table.setItem(row, 2, port_item)
            self.table.setItem(row, 3, user_item)
            self.table.setItem(row, 4, proto_item)

        self.table.resizeColumnsToContents()

    def add_server(self):
        srv = self.edit_server_dialog({})
        if srv:
            self.servers.append(srv)
            self.load_table()

    def edit_server(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.servers):
            QtWidgets.QMessageBox.information(self, "Info", "Bitte einen Server auswählen.")
            return
        existing = self.servers[row]
        new_srv = self.edit_server_dialog(existing)
        if new_srv:
            self.servers[row] = new_srv
            self.load_table()

    def delete_server(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.servers):
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Löschen?",
            f"Soll der Eintrag '{self.servers[row].get('name')}' wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            del self.servers[row]
            self.load_table()

    def edit_server_dialog(self, srv):
        """
        Öffnet einen kleinen Dialog zum Bearbeiten oder Anlegen eines Servers.
        srv = {} für neu, oder existierender Eintrag.
        Gibt dict oder None zurück.
        """
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Server-Eintrag bearbeiten" if srv else "Neuer Server")
        dlg.resize(400, 200)

        v = QtWidgets.QVBoxLayout(dlg)

        # Name
        name_label = QtWidgets.QLabel("Name:")
        name_edit = QtWidgets.QLineEdit(srv.get("name", ""))
        # Host
        host_label = QtWidgets.QLabel("Host:")
        host_edit = QtWidgets.QLineEdit(srv.get("host", ""))
        # Port
        port_label = QtWidgets.QLabel("Port:")
        port_edit = QtWidgets.QLineEdit(str(srv.get("port", 21)))
        # User
        user_label = QtWidgets.QLabel("User:")
        user_edit = QtWidgets.QLineEdit(srv.get("user", ""))
        # Protocol
        proto_label = QtWidgets.QLabel("Protocol:")
        proto_combo = QtWidgets.QComboBox()
        proto_combo.addItems(["ftp", "sftp"])
        proto_combo.setCurrentText(srv.get("protocol", "ftp"))

        # Passwort
        pass_label = QtWidgets.QLabel("Passwort (optional):")
        pass_edit = QtWidgets.QLineEdit()
        pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        # Falls wir ein existierendes user haben, laden wir das PW aus Keyring
        existing_user = srv.get("user", "")
        if existing_user:
            pw = keyring.get_password("PRisM-FTP", existing_user)
            if pw:
                pass_edit.setText(pw)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow(name_label, name_edit)
        form_layout.addRow(host_label, host_edit)
        form_layout.addRow(port_label, port_edit)
        form_layout.addRow(user_label, user_edit)
        form_layout.addRow(proto_label, proto_combo)
        form_layout.addRow(pass_label, pass_edit)

        v.addLayout(form_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Abbrechen")
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("OK")
        def ok_clicked():
            # Validierung
            name_val = name_edit.text().strip()
            host_val = host_edit.text().strip()
            user_val = user_edit.text().strip()
            try:
                port_val = int(port_edit.text().strip())
            except ValueError:
                port_val = 21
            proto_val = proto_combo.currentText()
            pw_val = pass_edit.text().strip()

            if not host_val:
                QtWidgets.QMessageBox.information(dlg, "Info", "Host darf nicht leer sein.")
                return

            new_srv = {
                "name": name_val,
                "host": host_val,
                "port": port_val,
                "user": user_val,
                "protocol": proto_val
            }
            # Passwort in Keyring speichern
            if user_val and pw_val:
                keyring.set_password("PRisM-FTP", user_val, pw_val)

            dlg.done(QtWidgets.QDialog.Accepted)
            dlg.new_srv = new_srv

        ok_btn.clicked.connect(ok_clicked)
        btn_layout.addWidget(ok_btn)

        v.addLayout(btn_layout)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            return dlg.new_srv
        else:
            return None

    def accept_dialog(self):
        """
        Speichert self.servers in ftp_servers.json,
        überträgt ggf. den aktuell ausgewählten Server in self.settings
        (damit das Hauptwidget ihn sofort nutzen kann),
        aber OHNE save_settings(self.settings) aufzurufen.
        """
        debug_print("accept_dialog: saving ftp_servers.json")
        try:
            save_ftp_servers(self.servers)
            debug_print(f"Servers saved: {self.servers}")
        except Exception as e:
            debug_print(f"Error saving ftp servers: {e}")

        # Wähle den aktuell markierten Server aus => schreibe ihn in self.settings
        row = self.table.currentRow()
        if row >= 0 and row < len(self.servers):
            srv = self.servers[row]
            self.settings["ftp_host"] = srv["host"]
            self.settings["ftp_port"] = srv["port"]
            self.settings["ftp_user"] = srv["user"]
            self.settings["ftp_protocol"] = srv["protocol"]
            debug_print(f"Selected server => {srv}")
        # Wir rufen NICHT save_settings(self.settings) auf, um es NICHT in settings.json zu speichern.

        self.accept()