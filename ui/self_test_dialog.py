#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ui/self_test_dialog.py
Self-Test-Dialog für PRisM-RAC.

- Nimmt optional settings_override (In-Memory Settings) entgegen
- Liest ansonsten utils.config_manager.load_settings(), Fallback auf utils.self_check.load_settings()
- Liest zusätzlich ~/Library/Application Support/PRisM-CC/smtp_settings.json und merged sie in die Settings
- Robustes Mapping für SMTP/FTP (inkl. smtp_enabled, smtp_ssl/use_ssl, email.*)
- Führt Tests in Worker-Thread aus und zeigt Log/Ergebnis
"""

from __future__ import annotations
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from utils.self_check import (
    SmtpConfig, FtpConfig,
    test_https, test_smtp, test_ftp, test_sftp, test_write_access,
    APP_SUPPORT_DIR
)

# App-Settings-Loader (primär)
_APP_LOAD_SETTINGS = None
try:
    from utils.config_manager import load_settings as _APP_LOAD_SETTINGS  # type: ignore
except Exception:
    _APP_LOAD_SETTINGS = None

# Fallback
_FALLBACK_LOAD_SETTINGS = None
try:
    from utils.self_check import load_settings as _FALLBACK_LOAD_SETTINGS  # type: ignore
except Exception:
    _FALLBACK_LOAD_SETTINGS = None


# -------------------- Helpers: Settings & Mapping --------------------

def _g(obj: Dict[str, Any], *path, default=None):
    cur = obj
    try:
        for p in path:
            cur = cur[p]
        return cur
    except Exception:
        return default


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _load_smtp_settings_json() -> dict:
    """
    Liest ~/Library/Application Support/PRisM-CC/smtp_settings.json wenn vorhanden.
    Unterstützt dein Schema:
      { "enabled": bool, "host": str, "port": int, "user": str, "notify_email": str, "use_ssl": bool }
    """
    p = Path(APP_SUPPORT_DIR) / "smtp_settings.json"
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _merge_settings(base: dict, smtp_extra: dict) -> dict:
    """
    Merged smtp_settings.json in die vorhandenen Settings, ohne bestehende Strukturen zu zerstören.
    - Legt sinnvolle Defaults in base['smtp'] und base['mail'] an, falls nicht vorhanden.
    - Übernimmt host/port/user/encryption/enable-Flags.
    - Lässt Passwörter außen vor.
    """
    if not isinstance(base, dict):
        base = {}

    merged = dict(base)
    smtp_ns = dict(merged.get("smtp", {}))
    mail_ns = dict(merged.get("mail", {}))

    # enabled
    enabled = smtp_extra.get("enabled")
    if enabled is not None:
        smtp_ns.setdefault("enabled", bool(enabled))
        mail_ns.setdefault("enabled", bool(enabled))

    # host
    host = smtp_extra.get("host") or smtp_extra.get("server")
    if host:
        smtp_ns.setdefault("host", host)
        mail_ns.setdefault("smtp_host", host)

    # port
    port = smtp_extra.get("port")
    if port:
        try:
            port = int(port)
        except Exception:
            port = 587
        smtp_ns.setdefault("port", port)
        mail_ns.setdefault("smtp_port", port)

    # user
    user = smtp_extra.get("user") or smtp_extra.get("username")
    if user:
        smtp_ns.setdefault("user", user)
        mail_ns.setdefault("user", user)
        # optional notify_email ignorieren wir für den Test; es ist kein Login-Parameter

    # use_ssl → Ableitung use_starttls
    # - use_ssl True  ⇒ SSL (kein STARTTLS), default Port 465, wenn keiner explizit gesetzt wurde
    # - use_ssl False ⇒ STARTTLS
    if "use_ssl" in smtp_extra:
        use_ssl = bool(smtp_extra.get("use_ssl"))
        if use_ssl:
            smtp_ns.setdefault("use_starttls", False)
            mail_ns.setdefault("use_starttls", False)
            if not port:
                smtp_ns.setdefault("port", 465)
                mail_ns.setdefault("smtp_port", 465)
        else:
            smtp_ns.setdefault("use_starttls", True)
            mail_ns.setdefault("use_starttls", True)

    merged["smtp"] = smtp_ns
    merged["mail"] = mail_ns
    return merged


def _coerce_mail(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalisiert SMTP:
      host, port, use_starttls, user, enabled

    Erkannt werden u. a.:
      - settings['mail']['smtp_host'|'smtp_port'|'use_starttls'|'user'|'enabled']
      - settings['smtp']['host'|'port'|'use_starttls'|'user'|'enabled'|'ssl'|'use_ssl']
      - flach: smtp_host/smtp_port/smtp_user/smtp_enabled/smtp_ssl/use_ssl
      - settings['email']:{server/host, port, username, encryption: 'starttls'|'ssl'}
    """
    mail = _g(settings, 'mail', default={})
    smtp = _g(settings, 'smtp', default={})
    email = _g(settings, 'email', default={})

    enabled = (
        _g(mail, 'enabled') or _g(smtp, 'enabled') or settings.get('smtp_enabled')
    )

    host = (
        _g(mail, 'smtp_host') or _g(smtp, 'host') or
        _g(email, 'server') or _g(email, 'host') or
        settings.get('smtp_host') or ""
    )

    port = (
        _g(mail, 'smtp_port') or _g(smtp, 'port') or
        _g(email, 'port') or settings.get('smtp_port') or 587
    )

    # SSL/STARTTLS Ableitung
    ssl_flag = (
        _g(smtp, 'ssl') or _g(smtp, 'use_ssl') or
        settings.get('smtp_ssl') or settings.get('use_ssl')
    )
    enc = (_g(email, 'encryption') or "").strip().lower()
    if enc in {"ssl", "ssl/tls", "smtps"}:
        ssl_flag = True
    elif enc in {"starttls", "tls"}:
        ssl_flag = False

    use_starttls = _g(mail, 'use_starttls')
    if use_starttls is None:
        use_starttls = _g(smtp, 'use_starttls')

    # Wenn Port 465 oder ssl=True ⇒ SSL (ohne STARTTLS)
    if int(port or 0) == 465 or _truthy(ssl_flag):
        use_starttls = False
        if not port:
            port = 465

    if use_starttls is None:
        use_starttls = True

    user = (
        _g(mail, 'user') or _g(smtp, 'user') or
        _g(email, 'username') or settings.get('smtp_user') or ""
    )

    return {
        "enabled": bool(_truthy(enabled) or host),
        "host": str(host or ""),
        "port": int(port or 587),
        "use_starttls": bool(use_starttls),
        "user": str(user or ""),
    }


def _coerce_ftp(settings: Dict[str, Any]) -> Dict[str, Any]:
    ftp = _g(settings, 'ftp', default={})
    mode = (ftp.get('mode') or settings.get('ftp_mode') or 'FTP').upper()
    host = ftp.get('host') or settings.get('ftp_host') or ''
    port = ftp.get('port') or settings.get('ftp_port') or 21
    user = ftp.get('user') or settings.get('ftp_user') or ''
    passive = ftp.get('passive')
    if passive is None:
        passive = settings.get('ftp_passive')
    if passive is None:
        passive = True
    remote_base = ftp.get('remote_base') or settings.get('ftp_remote_base') or '/'

    return {
        "mode": str(mode or 'FTP').upper(),
        "host": str(host or ''),
        "port": int(port or 21),
        "user": str(user or ''),
        "passive": bool(_truthy(passive)),
        "remote_base": str(remote_base or '/'),
    }


# -------------------- Worker --------------------

class TestWorker(QtCore.QObject):
    progressed = QtCore.Signal(str)
    resultReady = QtCore.Signal(dict)
    finished = QtCore.Signal()

    def __init__(self, plan: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.plan = plan

    @QtCore.Slot()
    def run(self):
        results: Dict[str, Tuple[bool, str, Dict[str, Any]]] = {}
        try:
            if self.plan.get("do_https"):
                self.progressed.emit("▶️ HTTPS-Test startet …")
                ok, msg, det = test_https(self.plan.get("https_url") or "https://www.python.org")
                results["https"] = (ok, msg, det)
                self.progressed.emit(("✅ " if ok else "❌ ") + msg)

            if self.plan.get("do_smtp"):
                self.progressed.emit("▶️ SMTP-Test startet …")
                scfg: SmtpConfig = self.plan["smtp_cfg"]
                ok, msg, det = test_smtp(scfg, do_login=self.plan.get("smtp_login", False))
                results["smtp"] = (ok, msg, det)
                self.progressed.emit(("✅ " if ok else "❌ ") + msg)

            if self.plan.get("do_ftp"):
                self.progressed.emit("▶️ FTP/FTPS-Test startet …")
                fcfg: FtpConfig = self.plan["ftp_cfg"]
                ok, msg, det = test_ftp(fcfg, listdir=True)
                results["ftp"] = (ok, msg, det)
                self.progressed.emit(("✅ " if ok else "❌ ") + msg)

            if self.plan.get("do_sftp"):
                self.progressed.emit("▶️ SFTP-Test startet …")
                fcfg: FtpConfig = self.plan["sftp_cfg"]
                ok, msg, det = test_sftp(fcfg, listdir=True)
                results["sftp"] = (ok, msg, det)
                self.progressed.emit(("✅ " if ok else "❌ ") + msg)

            if self.plan.get("do_write"):
                self.progressed.emit("▶️ Write-Access-Test startet …")
                ok, msg, det = test_write_access(APP_SUPPORT_DIR)
                results["write"] = (ok, msg, det)
                self.progressed.emit(("✅ " if ok else "❌ ") + msg)

        except Exception as e:
            tb = traceback.format_exc()
            self.progressed.emit(f"❌ Unerwarteter Fehler: {e}\n{tb}")
        finally:
            summary = {k: {"ok": v[0], "msg": v[1], "details": v[2]} for k, v in results.items()}
            self.resultReady.emit(summary)
            self.finished.emit()


# -------------------- Dialog --------------------

class SelfTestDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, settings_override: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("PRisM-RAC – Systemcheck")
        self.setMinimumSize(720, 560)
        self._thread = None
        self._worker = None
        self.results: Dict[str, Any] = {}
        self._settings_override = settings_override

        self._build_ui()
        self._load_defaults()

    # ----- UI -----
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()

        self.chk_https = QtWidgets.QCheckBox("HTTPS/TLS")
        self.ed_https = QtWidgets.QLineEdit("https://www.python.org")

        self.chk_smtp = QtWidgets.QCheckBox("SMTP")
        smtp_row = QtWidgets.QHBoxLayout()
        self.ed_smtp_host = QtWidgets.QLineEdit()
        self.ed_smtp_port = QtWidgets.QSpinBox()
        self.ed_smtp_port.setRange(1, 65535)
        self.ed_smtp_port.setValue(587)
        self.chk_smtp_starttls = QtWidgets.QCheckBox("STARTTLS")
        self.chk_smtp_starttls.setChecked(True)
        self.ed_smtp_user = QtWidgets.QLineEdit()
        self.ed_smtp_pass = QtWidgets.QLineEdit()
        self.ed_smtp_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.chk_smtp_login = QtWidgets.QCheckBox("Login testen")
        smtp_row.addWidget(QtWidgets.QLabel("Host:"))
        smtp_row.addWidget(self.ed_smtp_host, 2)
        smtp_row.addWidget(QtWidgets.QLabel("Port:"))
        smtp_row.addWidget(self.ed_smtp_port)
        smtp_row.addWidget(self.chk_smtp_starttls)
        smtp_row.addWidget(QtWidgets.QLabel("User:"))
        smtp_row.addWidget(self.ed_smtp_user)
        smtp_row.addWidget(QtWidgets.QLabel("Passwort:"))
        smtp_row.addWidget(self.ed_smtp_pass)
        smtp_row.addWidget(self.chk_smtp_login)

        self.chk_ftp = QtWidgets.QCheckBox("FTP/FTPS")
        ftp_row = QtWidgets.QHBoxLayout()
        self.cmb_ftp_mode = QtWidgets.QComboBox()
        self.cmb_ftp_mode.addItems(["FTP", "FTPS"])
        self.ed_ftp_host = QtWidgets.QLineEdit()
        self.ed_ftp_port = QtWidgets.QSpinBox()
        self.ed_ftp_port.setRange(1, 65535)
        self.ed_ftp_port.setValue(21)
        self.ed_ftp_user = QtWidgets.QLineEdit()
        self.ed_ftp_pass = QtWidgets.QLineEdit()
        self.ed_ftp_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.chk_ftp_passive = QtWidgets.QCheckBox("passive")
        self.chk_ftp_passive.setChecked(True)
        self.ed_ftp_base = QtWidgets.QLineEdit("/")
        ftp_row.addWidget(QtWidgets.QLabel("Mode:"))
        ftp_row.addWidget(self.cmb_ftp_mode)
        ftp_row.addWidget(QtWidgets.QLabel("Host:"))
        ftp_row.addWidget(self.ed_ftp_host, 2)
        ftp_row.addWidget(QtWidgets.QLabel("Port:"))
        ftp_row.addWidget(self.ed_ftp_port)
        ftp_row.addWidget(QtWidgets.QLabel("User:"))
        ftp_row.addWidget(self.ed_ftp_user)
        ftp_row.addWidget(QtWidgets.QLabel("Passwort:"))
        ftp_row.addWidget(self.ed_ftp_pass)
        ftp_row.addWidget(self.chk_ftp_passive)
        ftp_row.addWidget(QtWidgets.QLabel("Remote-Base:"))
        ftp_row.addWidget(self.ed_ftp_base)

        self.chk_sftp = QtWidgets.QCheckBox("SFTP")
        sftp_row = QtWidgets.QHBoxLayout()
        self.ed_sftp_host = QtWidgets.QLineEdit()
        self.ed_sftp_port = QtWidgets.QSpinBox()
        self.ed_sftp_port.setRange(1, 65535)
        self.ed_sftp_port.setValue(22)
        self.ed_sftp_user = QtWidgets.QLineEdit()
        self.ed_sftp_pass = QtWidgets.QLineEdit()
        self.ed_sftp_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_sftp_base = QtWidgets.QLineEdit(".")
        sftp_row.addWidget(QtWidgets.QLabel("Host:"))
        sftp_row.addWidget(self.ed_sftp_host, 2)
        sftp_row.addWidget(QtWidgets.QLabel("Port:"))
        sftp_row.addWidget(self.ed_sftp_port)
        sftp_row.addWidget(QtWidgets.QLabel("User:"))
        sftp_row.addWidget(self.ed_sftp_user)
        sftp_row.addWidget(QtWidgets.QLabel("Passwort:"))
        sftp_row.addWidget(self.ed_sftp_pass)
        sftp_row.addWidget(QtWidgets.QLabel("Remote-Base:"))
        sftp_row.addWidget(self.ed_sftp_base)

        self.chk_write = QtWidgets.QCheckBox("Write-Access (App-Support)")

        form.addRow(self.chk_https, self.ed_https)
        form.addRow(self.chk_smtp, smtp_row)
        form.addRow(self.chk_ftp, ftp_row)
        form.addRow(self.chk_sftp, sftp_row)
        form.addRow(self.chk_write)

        layout.addLayout(form)

        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMinimumHeight(200)
        layout.addWidget(self.txt_log)

        btns = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("Tests ausführen")
        self.btn_copy = QtWidgets.QPushButton("Ergebnis kopieren")
        self.btn_save = QtWidgets.QPushButton("Als JSON speichern…")
        self.btn_close = QtWidgets.QPushButton("Schließen")
        btns.addWidget(self.btn_run)
        btns.addStretch(1)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

        self.btn_run.clicked.connect(self.on_run)
        self.btn_close.clicked.connect(self.reject)
        self.btn_copy.clicked.connect(self.on_copy)
        self.btn_save.clicked.connect(self.on_save)

    # ----- Defaults laden -----
    def _load_defaults(self):
        # 1) Basis-Settings laden (Override > App > Fallback)
        if self._settings_override is not None:
            settings = self._settings_override
        elif _APP_LOAD_SETTINGS:
            try:
                settings = _APP_LOAD_SETTINGS()
            except Exception:
                settings = {}
        elif _FALLBACK_LOAD_SETTINGS:
            settings = _FALLBACK_LOAD_SETTINGS()
        else:
            settings = {}

        # 2) smtp_settings.json einbeziehen (merge)
        smtp_extra = _load_smtp_settings_json()
        if smtp_extra:
            settings = _merge_settings(settings, smtp_extra)

        # 3) HTTPS
        self.chk_https.setChecked(True)
        if not self.ed_https.text().strip():
            self.ed_https.setText("https://www.python.org")

        # 4) SMTP aus gemergten Settings mappen
        mail = _coerce_mail(settings)
        self.chk_smtp.setChecked(bool(mail.get("enabled")))
        self.ed_smtp_host.setText(mail.get("host", ""))
        self.ed_smtp_port.setValue(int(mail.get("port", 587) or 587))
        self.chk_smtp_starttls.setChecked(bool(mail.get("use_starttls", True)))
        self.ed_smtp_user.setText(mail.get("user", ""))
        self.chk_smtp_login.setChecked(False)  # Passwort bleibt bewusst leer

        # 5) FTP/FTPS
        ftp = _coerce_ftp(settings)
        self.chk_ftp.setChecked(bool(ftp.get("host")))
        self.cmb_ftp_mode.setCurrentText((ftp.get("mode") or "FTP").upper())
        self.ed_ftp_host.setText(ftp.get("host", ""))
        self.ed_ftp_port.setValue(int(ftp.get("port", 21) or 21))
        self.ed_ftp_user.setText(ftp.get("user", ""))
        self.chk_ftp_passive.setChecked(bool(ftp.get("passive", True)))
        self.ed_ftp_base.setText(ftp.get("remote_base", "/") or "/")

        # 6) SFTP (aus FTP vorbelegen; deaktiviert)
        self.chk_sftp.setChecked(False)
        self.ed_sftp_host.setText(self.ed_ftp_host.text())
        self.ed_sftp_port.setValue(22)
        self.ed_sftp_user.setText(self.ed_ftp_user.text())
        self.ed_sftp_base.setText(".")

        # 7) Write
        self.chk_write.setChecked(True)

    # ----- Aktionen -----
    def append_log(self, line: str):
        self.txt_log.appendPlainText(line)

    def build_plan(self) -> Dict[str, Any]:
        plan: Dict[str, Any] = {
            "do_https": self.chk_https.isChecked(),
            "https_url": self.ed_https.text().strip(),

            "do_smtp": self.chk_smtp.isChecked(),
            "smtp_login": self.chk_smtp_login.isChecked(),
            "smtp_cfg": SmtpConfig(
                host=self.ed_smtp_host.text().strip(),
                port=self.ed_smtp_port.value(),
                use_starttls=self.chk_smtp_starttls.isChecked(),
                user=self.ed_smtp_user.text().strip(),
                password=self.ed_smtp_pass.text()
            ),

            "do_ftp": self.chk_ftp.isChecked(),
            "ftp_cfg": FtpConfig(
                mode=self.cmb_ftp_mode.currentText().strip().upper(),
                host=self.ed_ftp_host.text().strip(),
                port=self.ed_ftp_port.value(),
                user=self.ed_ftp_user.text().strip(),
                password=self.ed_ftp_pass.text(),
                passive=self.chk_ftp_passive.isChecked(),
                remote_base=self.ed_ftp_base.text().strip() or "/"
            ),

            "do_sftp": self.chk_sftp.isChecked(),
            "sftp_cfg": FtpConfig(
                mode="SFTP",
                host=self.ed_sftp_host.text().strip(),
                port=self.ed_sftp_port.value(),
                user=self.ed_sftp_user.text().strip(),
                password=self.ed_sftp_pass.text(),
                passive=True,
                remote_base=self.ed_sftp_base.text().strip() or "."
            ),

            "do_write": self.chk_write.isChecked(),
        }
        return plan

    @QtCore.Slot()
    def on_run(self):
        if self._thread:
            QtWidgets.QMessageBox.information(self, "Läuft", "Bitte warte – ein Testlauf ist noch aktiv.")
            return

        self.txt_log.clear()
        plan = self.build_plan()
        self.append_log("Self-Test wird gestartet …")

        self._thread = QtCore.QThread(self)
        self._worker = TestWorker(plan)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progressed.connect(self.append_log)
        self._worker.resultReady.connect(self.on_results)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.on_thread_finished)

        self.btn_run.setEnabled(False)
        self._thread.start()

    @QtCore.Slot(dict)
    def on_results(self, summary: Dict[str, Any]):
        self.results = summary
        self.append_log("\n— Zusammenfassung —")
        ok_all = True
        for key, res in summary.items():
            ok = bool(res.get("ok"))
            ok_all = ok_all and ok
            sym = "✅" if ok else "❌"
            self.append_log(f"{sym} {key}: {res.get('msg')}")
        self.append_log("\nGesamtergebnis: " + ("✅ OK" if ok_all else "❌ Probleme vorhanden"))

    @QtCore.Slot()
    def on_thread_finished(self):
        self.btn_run.setEnabled(True)
        self._thread = None
        self._worker = None

    @QtCore.Slot()
    def on_copy(self):
        if not self.results:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Noch keine Ergebnisse vorhanden.")
            return
        txt = json.dumps(self.results, ensure_ascii=False, indent=2)
        QtWidgets.QApplication.clipboard().setText(txt)
        QtWidgets.QMessageBox.information(self, "Kopiert", "Ergebnis wurde in die Zwischenablage kopiert.")

    @QtCore.Slot()
    def on_save(self):
        if not self.results:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Noch keine Ergebnisse vorhanden.")
            return
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Ergebnis speichern", str(APP_SUPPORT_DIR / "self_test_result.json"),
            "JSON (*.json)"
        )
        if not fn:
            return
        try:
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Gespeichert", f"Ergebnis gespeichert:\n{fn}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Konnte Datei nicht speichern:\n{e}")