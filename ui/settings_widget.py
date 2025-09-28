#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide6 import QtWidgets, QtCore, QtGui

from utils.config_manager import save_settings, load_smtp_settings, save_smtp_settings, debug_print
from utils.mailer import Mailer  # zentraler Mailversand


class SettingsWidget(QtWidgets.QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Stelle sicher, dass resource_paths existiert
        if "resource_paths" not in self.settings:
            self.settings["resource_paths"] = {}

        # interne SMTP-Felder
        self.smtp_enabled_check = None
        self.smtp_host_edit = None
        self.smtp_port_spin = None
        self.smtp_user_edit = None
        self.smtp_pass_edit = None
        self.smtp_notify_edit = None

        self.init_ui()
        self._load_smtp_into_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # 1) Allgemein
        self.general_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.general_tab, "Allgemein")
        gen_layout = QtWidgets.QVBoxLayout(self.general_tab)
        gen_layout.setContentsMargins(5, 5, 5, 5)
        gen_layout.setSpacing(5)

        # --- (A) Gruppe für allgemeine Einstellungen ---
        self.general_group = QtWidgets.QGroupBox("Allgemeine Einstellungen")
        self.general_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
            }
        """)
        group_layout = QtWidgets.QFormLayout(self.general_group)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(5)

        # (A1) Pfad für JSX-Templates
        self.jsx_templates_edit = QtWidgets.QLineEdit()
        self.jsx_templates_edit.setFixedWidth(500)  # feste Breite von 500 Pixeln
        current_jsx_path = self.settings["resource_paths"].get("jsx_templates", "")
        self.jsx_templates_edit.setText(current_jsx_path)

        self.jsx_browse_btn = QtWidgets.QPushButton("Browse")
        self.jsx_browse_btn.clicked.connect(self.browse_jsx_folder)

        # Layout für das Label, QLineEdit und den Button
        jsx_layout = QtWidgets.QHBoxLayout()
        jsx_layout.addWidget(self.jsx_templates_edit, stretch=1)
        jsx_layout.addWidget(self.jsx_browse_btn, stretch=0)

        group_layout.addRow("JSX Templates:", jsx_layout)

        gen_layout.addWidget(self.general_group)
        gen_layout.addStretch()

        # 2) SMTP (neuer Tab)
        self.smtp_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.smtp_tab, "SMTP")
        smtp_layout = QtWidgets.QFormLayout(self.smtp_tab)
        smtp_layout.setContentsMargins(5, 5, 5, 5)
        smtp_layout.setSpacing(5)

        self.smtp_enabled_check = QtWidgets.QCheckBox("SMTP aktiviert")
        smtp_layout.addRow(self.smtp_enabled_check)

        self.smtp_host_edit = QtWidgets.QLineEdit()
        smtp_layout.addRow("SMTP Host:", self.smtp_host_edit)

        self.smtp_port_spin = QtWidgets.QSpinBox()
        self.smtp_port_spin.setMaximum(65535)
        self.smtp_port_spin.setValue(587)
        smtp_layout.addRow("Port:", self.smtp_port_spin)

        self.smtp_user_edit = QtWidgets.QLineEdit()
        smtp_layout.addRow("SMTP User:", self.smtp_user_edit)

        self.smtp_pass_edit = QtWidgets.QLineEdit()
        self.smtp_pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.smtp_pass_edit.setPlaceholderText("•••••• (im Schlüsselbund)")
        smtp_layout.addRow("SMTP Pass:", self.smtp_pass_edit)

        self.smtp_notify_edit = QtWidgets.QLineEdit()
        smtp_layout.addRow("Notify E-Mail:", self.smtp_notify_edit)

        test_row = QtWidgets.QHBoxLayout()
        self.smtp_test_btn = QtWidgets.QPushButton("Testmail senden")
        self.smtp_test_btn.clicked.connect(self.on_send_testmail)
        test_row.addStretch()
        test_row.addWidget(self.smtp_test_btn)
        smtp_layout.addRow("", test_row)

        # Unten ein Button zum Speichern (speichert ALLE Tabs)
        btn_hlay = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")
        btn_hlay.addStretch()
        btn_hlay.addWidget(self.save_btn)

        # Connect
        self.save_btn.clicked.connect(self.on_save)

        # Gesamtlayout abschließen
        main_layout.addLayout(btn_hlay)

    # ---------------------- Allgemein ----------------------
    def browse_jsx_folder(self):
        """
        Öffnet einen QFileDialog, damit der Benutzer einen Ordner für die JSX-Templates auswählen kann.
        """
        start_dir = self.jsx_templates_edit.text() or QtCore.QDir.homePath()
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "JSX-Templates-Ordner auswählen", start_dir)
        if folder:
            self.jsx_templates_edit.setText(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Info", "Kein gültiger Ordner ausgewählt.")

    # ---------------------- SMTP Laden/Speichern ----------------------
    def _load_smtp_into_ui(self):
        s = load_smtp_settings() or {}
        self.smtp_enabled_check.setChecked(bool(s.get("enabled", False)))
        self.smtp_host_edit.setText(s.get("host", ""))
        self.smtp_port_spin.setValue(int(s.get("port", 587) or 587))
        self.smtp_user_edit.setText(s.get("user", ""))
        self.smtp_notify_edit.setText(s.get("notify_email", ""))

        # Passwort zeigen wir aus Sicherheitsgründen nicht an;
        # leeres Feld bedeutet: Schlüsselbund-Belegung bleibt unberührt.

    def _collect_smtp_from_ui(self) -> dict:
        return {
            "enabled": self.smtp_enabled_check.isChecked(),
            "host": self.smtp_host_edit.text().strip(),
            "port": self.smtp_port_spin.value(),
            "user": self.smtp_user_edit.text().strip(),
            "notify_email": self.smtp_notify_edit.text().strip(),
        }

    # ---------------------- Testmail ----------------------
    def on_send_testmail(self):
        try:
            # Speichere aktuelle SMTP-Eingaben temporär (inkl. Keyring falls PW angegeben)
            smtp_cfg = self._collect_smtp_from_ui()
            save_smtp_settings(smtp_cfg)
            pw = self.smtp_pass_edit.text()
            if pw:
                # Nur wenn explizit eingetragen → Keyring aktualisieren
                Mailer.set_password(smtp_cfg.get("user", ""), pw)

            m = Mailer()
            to = smtp_cfg.get("notify_email", "")
            m.send_mail("PRisM – SMTP Test", "Das ist eine Testmail aus den Einstellungen.", to=to)
            QtWidgets.QMessageBox.information(self, "Erfolg", "Testmail wurde gesendet.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Testmail fehlgeschlagen:\n{e}")

    # ---------------------- Speichern ----------------------
    def on_save(self):
        """
        Speichert:
          - Allgemeine Einstellungen (JSX-Pfad) in self.settings via save_settings
          - SMTP-Einstellungen via save_smtp_settings (+ optional Keyring)
        """
        # Allgemein
        new_jsx_path = self.jsx_templates_edit.text().strip()
        if new_jsx_path:
            self.settings["resource_paths"]["jsx_templates"] = new_jsx_path
        else:
            if "jsx_templates" in self.settings["resource_paths"]:
                del self.settings["resource_paths"]["jsx_templates"]

        save_settings(self.settings)

        # SMTP
        smtp_cfg = self._collect_smtp_from_ui()
        save_smtp_settings(smtp_cfg)

        pw = self.smtp_pass_edit.text()
        if pw:
            try:
                Mailer.set_password(smtp_cfg.get("user", ""), pw)
            except Exception as e:
                debug_print(f"[SettingsWidget] Keyring-Update fehlgeschlagen: {e}")

        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")