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
        self.smtp_use_ssl_check = None     # NEU: SSL (Port 465)

        # Buttons
        self.smtp_test_btn = None
        self.smtp_delete_pw_btn = None     # NEU: Passwort löschen

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

        # NEU: SSL (Port 465)
        self.smtp_use_ssl_check = QtWidgets.QCheckBox("SSL (Port 465)")
        self.smtp_use_ssl_check.setToolTip("Aktiviert SMTPS über Port 465. Deaktiviert: SMTP/STARTTLS.")
        smtp_layout.addRow(self.smtp_use_ssl_check)

        self.smtp_user_edit = QtWidgets.QLineEdit()
        smtp_layout.addRow("SMTP User:", self.smtp_user_edit)

        self.smtp_pass_edit = QtWidgets.QLineEdit()
        self.smtp_pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.smtp_pass_edit.setPlaceholderText("•••••• (im Schlüsselbund)")
        smtp_layout.addRow("SMTP Pass:", self.smtp_pass_edit)

        self.smtp_notify_edit = QtWidgets.QLineEdit()
        smtp_layout.addRow("Notify E-Mail:", self.smtp_notify_edit)

        # Test & Passwort löschen
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.smtp_delete_pw_btn = QtWidgets.QPushButton("Passwort löschen")
        self.smtp_delete_pw_btn.setToolTip("Löscht das SMTP-Passwort aus dem Schlüsselbund.")
        self.smtp_delete_pw_btn.clicked.connect(self.on_delete_smtp_password)
        btn_row.addWidget(self.smtp_delete_pw_btn)

        self.smtp_test_btn = QtWidgets.QPushButton("Testmail senden")
        self.smtp_test_btn.clicked.connect(self.on_send_testmail)
        btn_row.addWidget(self.smtp_test_btn)

        smtp_layout.addRow("", btn_row)

        # Unten ein Button zum Speichern (speichert ALLE Tabs)
        btn_hlay = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Einstellungen speichern")
        btn_hlay.addStretch()
        btn_hlay.addWidget(self.save_btn)

        # Connect
        self.save_btn.clicked.connect(self.on_save)

        # Gesamtlayout abschließen
        main_layout.addLayout(btn_hlay)

        # kleine UX-Hilfe: SSL-Checkbox setzt Standard-Port 465, sonst 587 (ohne Zwang)
        self.smtp_use_ssl_check.stateChanged.connect(self._maybe_adjust_port_for_ssl)

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
        self.smtp_use_ssl_check.setChecked(bool(s.get("use_ssl", False)))

        # Passwort zeigen wir aus Sicherheitsgründen nicht an;
        # leeres Feld bedeutet: Schlüsselbund-Belegung bleibt unberührt.

    def _collect_smtp_from_ui(self) -> dict:
        return {
            "enabled": self.smtp_enabled_check.isChecked(),
            "host": self.smtp_host_edit.text().strip(),
            "port": self.smtp_port_spin.value(),
            "user": self.smtp_user_edit.text().strip(),
            "notify_email": self.smtp_notify_edit.text().strip(),
            "use_ssl": self.smtp_use_ssl_check.isChecked(),  # NEU
        }

    def _maybe_adjust_port_for_ssl(self, state: int):
        """
        UX: Wenn SSL aktiviert wird und Port ist 587 → auf 465 umstellen.
            Wenn SSL deaktiviert wird und Port ist 465 → auf 587 umstellen.
        Der User kann danach natürlich weiterhin manuell anpassen.
        """
        try:
            cur = int(self.smtp_port_spin.value())
        except Exception:
            cur = 0
        if state == QtCore.Qt.Checked and cur == 587:
            self.smtp_port_spin.setValue(465)
        elif state != QtCore.Qt.Checked and cur == 465:
            self.smtp_port_spin.setValue(587)

    # ---------------------- Testmail ----------------------
    def on_send_testmail(self):
        try:
            # Speichere aktuelle SMTP-Eingaben temporär (inkl. Keyring falls PW angegeben)
            smtp_cfg = self._collect_smtp_from_ui()
            save_smtp_settings(smtp_cfg)

            pw = self.smtp_pass_edit.text().strip()
            if pw:
                # Nur wenn explizit eingetragen → Keyring aktualisieren
                Mailer.set_password(smtp_cfg.get("user", ""), pw)

            m = Mailer()
            to = smtp_cfg.get("notify_email", "")
            m.send_mail("PRisM – SMTP Test", "Das ist eine Testmail aus den Einstellungen.", to=to)
            QtWidgets.QMessageBox.information(self, "Erfolg", "Testmail wurde gesendet.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Testmail fehlgeschlagen:\n{e}")

    # ---------------------- Passwort löschen ----------------------
    def on_delete_smtp_password(self):
        user = self.smtp_user_edit.text().strip()
        if not user:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte zuerst einen SMTP-Benutzer eintragen.")
            return
        Mailer.delete_password(user)
        self.smtp_pass_edit.clear()
        QtWidgets.QMessageBox.information(self, "Info", "SMTP-Passwort wurde (falls vorhanden) aus dem Schlüsselbund entfernt.")

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

        pw = self.smtp_pass_edit.text().strip()
        if pw:
            try:
                Mailer.set_password(smtp_cfg.get("user", ""), pw)
            except Exception as e:
                debug_print(f"[SettingsWidget] Keyring-Update fehlgeschlagen: {e}")

        QtWidgets.QMessageBox.information(self, "Info", "Einstellungen wurden gespeichert.")