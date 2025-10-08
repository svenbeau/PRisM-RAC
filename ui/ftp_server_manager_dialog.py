#!/usr/bin/env python3
#ftp_server_manager_dialog.py
# -*- coding: utf-8 -*-

import copy
import keyring
from keyring.errors import KeyringError
from PySide6 import QtWidgets, QtCore

from utils.config_manager import (
    load_settings,     # nur falls self.settings gebraucht wird
    debug_print,
    load_ftp_servers,  # Lesen aus ftp_servers.json
    save_ftp_servers   # Schreiben in ftp_servers.json
)


class FtpServerManagerDialog(QtWidgets.QDialog):
    """
    Verwalten mehrerer FTP-Server (Name, Host, Port, User, Protocol).
    Passwörter liegen im Keyring, Key = User (Service: "PRisM-FTP").
    Die Serverliste wird in ftp_servers.json gehalten (nicht settings.json).
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server-Verwaltung")
        self.resize(700, 360)

        # Referenz auf Haupt-Settings, um den ausgewählten Server ins UI zu übernehmen
        self.settings = settings

        # Serverliste laden
        self.servers = load_ftp_servers() or []

        # UI
        main = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Host", "Port", "User", "Protocol"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        main.addWidget(self.table)

        btn_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Neu")
        self.add_btn.clicked.connect(self.add_server)
        btn_row.addWidget(self.add_btn)

        self.edit_btn = QtWidgets.QPushButton("Bearbeiten")
        self.edit_btn.clicked.connect(self.edit_server)
        btn_row.addWidget(self.edit_btn)

        self.del_btn = QtWidgets.QPushButton("Löschen")
        self.del_btn.clicked.connect(self.delete_server)
        btn_row.addWidget(self.del_btn)

        btn_row.addStretch()

        self.cancel_btn = QtWidgets.QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.ok_btn = QtWidgets.QPushButton("Übernehmen")
        self.ok_btn.clicked.connect(self.accept_dialog)
        btn_row.addWidget(self.ok_btn)

        main.addLayout(btn_row)

        self.load_table()

    # -------------------------
    # Tabellen-Handling
    # -------------------------
    def load_table(self):
        self.table.setRowCount(len(self.servers))
        for row, srv in enumerate(self.servers):
            name_item = QtWidgets.QTableWidgetItem(srv.get("name", ""))
            host_item = QtWidgets.QTableWidgetItem(srv.get("host", ""))
            port_item = QtWidgets.QTableWidgetItem(str(srv.get("port", 21)))
            user_item = QtWidgets.QTableWidgetItem(srv.get("user", ""))
            proto_item = QtWidgets.QTableWidgetItem(srv.get("protocol", "ftp"))

            # read-only
            for it in (name_item, host_item, port_item, user_item, proto_item):
                it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, host_item)
            self.table.setItem(row, 2, port_item)
            self.table.setItem(row, 3, user_item)
            self.table.setItem(row, 4, proto_item)

        self.table.resizeColumnsToContents()

    # -------------------------
    # CRUD
    # -------------------------
    def add_server(self):
        srv = self.edit_server_dialog({})
        if srv:
            self.servers.append(srv)
            self.load_table()
            # neueste Zeile auswählen
            last_row = self.table.rowCount() - 1
            if last_row >= 0:
                self.table.selectRow(last_row)

    def edit_server(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.servers):
            QtWidgets.QMessageBox.information(self, "Info", "Bitte einen Server auswählen.")
            return
        existing = copy.deepcopy(self.servers[row])
        new_srv = self.edit_server_dialog(existing)
        if new_srv:
            self.servers[row] = new_srv
            self.load_table()
            self.table.selectRow(row)

    def delete_server(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.servers):
            return
        name = self.servers[row].get("name") or self.servers[row].get("host", "(ohne Name)")
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Löschen?",
            f"Soll der Eintrag „{name}“ wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            del self.servers[row]
            self.load_table()

    # -------------------------
    # Editor-Dialog
    # -------------------------
    def edit_server_dialog(self, srv: dict):
        """
        Kleiner Editor-Dialog.
        srv = {} -> Neu
        srv = {...} -> Bearbeiten
        Rückgabe: dict oder None
        """
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Server-Eintrag bearbeiten" if srv else "Neuer Server")
        dlg.resize(420, 260)
        vbox = QtWidgets.QVBoxLayout(dlg)

        name_edit = QtWidgets.QLineEdit(srv.get("name", ""))
        host_edit = QtWidgets.QLineEdit(srv.get("host", ""))
        port_edit = QtWidgets.QLineEdit(str(srv.get("port", 21)))
        user_edit = QtWidgets.QLineEdit(srv.get("user", ""))

        proto_combo = QtWidgets.QComboBox()
        proto_combo.addItems(["ftp", "sftp"])
        proto_combo.setCurrentText(srv.get("protocol", "ftp"))

        pass_edit = QtWidgets.QLineEdit()
        pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        # Passwort (falls vorhanden) aus Keyring lesbar machen — nie hart erzwingen
        existing_user = srv.get("user", "")
        if existing_user:
            try:
                pw = keyring.get_password("PRisM-FTP", existing_user)
            except KeyringError as e:
                debug_print(f"[ftp_server_manager] Keyring get_password() Fehler: {e}")
                pw = None
            except Exception as e:
                debug_print(f"[ftp_server_manager] Keyring get_password() unerwartet: {e}")
                pw = None
            if pw:
                pass_edit.setText(pw)

        form = QtWidgets.QFormLayout()
        form.addRow("Name:", name_edit)
        form.addRow("Host:", host_edit)
        form.addRow("Port:", port_edit)
        form.addRow("User:", user_edit)
        form.addRow("Protocol:", proto_combo)
        form.addRow("Passwort (optional):", pass_edit)
        vbox.addLayout(form)

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            dlg
        )
        buttons.accepted.connect(lambda: self._on_editor_ok(dlg, name_edit, host_edit, port_edit,
                                                            user_edit, proto_combo, pass_edit))
        buttons.rejected.connect(dlg.reject)
        vbox.addWidget(buttons)

        # Enter soll OK auslösen
        ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        ok_button.setDefault(True)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            return dlg.new_srv
        return None

    def _on_editor_ok(self, dlg, name_edit, host_edit, port_edit, user_edit, proto_combo, pass_edit):
        # Validierung
        name_val = name_edit.text().strip()
        host_val = host_edit.text().strip()
        user_val = user_edit.text().strip()
        proto_val = proto_combo.currentText().strip()

        try:
            port_val = int((port_edit.text() or "").strip())
        except ValueError:
            port_val = 21

        if not host_val:
            QtWidgets.QMessageBox.information(dlg, "Info", "Host darf nicht leer sein.")
            return
        if port_val <= 0 or port_val > 65535:
            QtWidgets.QMessageBox.information(dlg, "Info", "Port ist ungültig (1–65535).")
            return

        pw_val = pass_edit.text()

        new_srv = {
            "name": name_val,
            "host": host_val,
            "port": port_val,
            "user": user_val,
            "protocol": proto_val or "ftp",
        }

        # Passwort optional in Keyring speichern — Fehler fangen, Dialog trotzdem schließen
        if user_val and pw_val:
            try:
                keyring.set_password("PRisM-FTP", user_val, pw_val)
            except KeyringError as e:
                debug_print(f"[ftp_server_manager] Keyring set_password() Fehler: {e}")
                QtWidgets.QMessageBox.warning(
                    dlg,
                    "Passwort nicht gespeichert",
                    "Das Passwort konnte nicht im Schlüsselbund gespeichert werden.\n"
                    "Du kannst den Server trotzdem verwenden, musst das Passwort ggf. später eingeben."
                )
            except Exception as e:
                debug_print(f"[ftp_server_manager] Keyring set_password() unerwartet: {e}")
                QtWidgets.QMessageBox.warning(
                    dlg,
                    "Passwort nicht gespeichert",
                    "Unerwarteter Fehler beim Speichern im Schlüsselbund.\n"
                    "Der Servereintrag wurde erstellt; Passwort bitte später erneut hinterlegen."
                )

        dlg.new_srv = new_srv
        dlg.accept()

    # -------------------------
    # Übernehmen (Speichern & Auswahl in Settings)
    # -------------------------
    def accept_dialog(self):
        debug_print("[ftp_server_manager] accept_dialog: saving ftp_servers.json")
        try:
            save_ftp_servers(self.servers)
            debug_print(f"[ftp_server_manager] Servers saved: {self.servers}")
        except Exception as e:
            debug_print(f"[ftp_server_manager] Error saving ftp servers: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Speichern fehlgeschlagen",
                f"Die Serverliste konnte nicht gespeichert werden.\n\n{e}"
            )
            # trotzdem nicht schließen – Benutzer kann reagieren
            return

        # markierten Server in self.settings übernehmen (ohne settings.json zu schreiben)
        row = self.table.currentRow()
        if 0 <= row < len(self.servers):
            srv = self.servers[row]
            self.settings["ftp_host"] = srv.get("host", "")
            self.settings["ftp_port"] = srv.get("port", 21)
            self.settings["ftp_user"] = srv.get("user", "")
            self.settings["ftp_protocol"] = srv.get("protocol", "ftp")
            debug_print(f"[ftp_server_manager] Selected server => {srv}")

        self.accept()