#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import traceback
from PySide6 import QtWidgets, QtCore, QtGui

from utils.config_manager import (
    debug_print,
    load_all_backup_plans,
    save_all_backup_plans
)

class FtpScheduleWidget(QtWidgets.QWidget):
    """
    Zeigt eine Liste aller Backup-Pläne (backup_plans.json).
    Pro Plan:
      - Pause/Resume
      - "Jetzt ausführen" => ruft prism_scheduled_transfer.py auf
      - NEU: "Neuen Plan hinzufügen"
      - NEU: "Ausgewählten Plan löschen"
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # Tabelle
        self.plan_table = QtWidgets.QTableWidget()
        self.plan_table.setColumnCount(5)
        self.plan_table.setHorizontalHeaderLabels(
            ["Plan-Name", "Quelle", "Ziel (remote)", "Status", "Aktionen"]
        )
        layout.addWidget(self.plan_table)

        # Button-Leiste unten
        btn_layout = QtWidgets.QHBoxLayout()

        self.refresh_btn = QtWidgets.QPushButton("Refresh Pläne")
        self.refresh_btn.clicked.connect(self.load_plans)
        btn_layout.addWidget(self.refresh_btn)

        # NEU: Plan hinzufügen
        self.add_btn = QtWidgets.QPushButton("Neuen Plan hinzufügen")
        self.add_btn.clicked.connect(self.add_plan)
        btn_layout.addWidget(self.add_btn)

        # NEU: Plan löschen
        self.delete_btn = QtWidgets.QPushButton("Ausgewählten Plan löschen")
        self.delete_btn.clicked.connect(self.delete_plan)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Liste der Pläne im Speicher
        self.plans = []
        self.load_plans()

    def load_plans(self):
        """
        Lädt die Pläne aus backup_plans.json und zeigt sie in der Tabelle an.
        """
        self.plans = load_all_backup_plans()
        self.plan_table.setRowCount(len(self.plans))

        for row, plan in enumerate(self.plans):
            name = plan.get("name", "")
            source = plan.get("source_path", "")
            remote = plan.get("remote_path", "")
            paused = plan.get("paused", False)

            # Spalte 0: Name
            item_name = QtWidgets.QTableWidgetItem(name)
            item_name.setFlags(QtCore.Qt.ItemIsEnabled)
            self.plan_table.setItem(row, 0, item_name)

            # Spalte 1: Quelle
            item_source = QtWidgets.QTableWidgetItem(source)
            item_source.setFlags(QtCore.Qt.ItemIsEnabled)
            self.plan_table.setItem(row, 1, item_source)

            # Spalte 2: Ziel
            item_remote = QtWidgets.QTableWidgetItem(remote)
            item_remote.setFlags(QtCore.Qt.ItemIsEnabled)
            self.plan_table.setItem(row, 2, item_remote)

            # Spalte 3: Status
            status_text = "Pausiert" if paused else "Aktiv"
            item_status = QtWidgets.QTableWidgetItem(status_text)
            item_status.setFlags(QtCore.Qt.ItemIsEnabled)
            self.plan_table.setItem(row, 3, item_status)

            # Spalte 4: Aktionen (Pause/Resume, Jetzt ausführen)
            action_widget = QtWidgets.QWidget()
            action_layout = QtWidgets.QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)

            pause_btn = QtWidgets.QPushButton("Resume" if paused else "Pause")
            pause_btn.clicked.connect(lambda checked, r=row: self.toggle_pause(r))
            action_layout.addWidget(pause_btn)

            run_btn = QtWidgets.QPushButton("Jetzt ausführen")
            run_btn.clicked.connect(lambda checked, r=row: self.run_now(r))
            action_layout.addWidget(run_btn)

            action_layout.addStretch()
            self.plan_table.setCellWidget(row, 4, action_widget)

        self.plan_table.resizeColumnsToContents()

    def toggle_pause(self, row):
        """Wechselt zwischen paused=True und paused=False für den Plan in row."""
        plan = self.plans[row]
        old_paused = plan.get("paused", False)
        plan["paused"] = not old_paused
        save_all_backup_plans(self.plans)
        self.load_plans()

    def run_now(self, row):
        """Startet prism_scheduled_transfer.py --plan <Name> als Subprozess."""
        plan = self.plans[row]
        plan_name = plan.get("name", "")
        if not plan_name:
            return

        if plan.get("paused", False):
            msg = QtWidgets.QMessageBox.question(
                self,
                "Plan pausiert",
                f"Plan '{plan_name}' ist pausiert. Trotzdem jetzt ausführen?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if msg == QtWidgets.QMessageBox.No:
                return

        script_path = os.path.join(os.path.dirname(__file__), "..", "utils", "prism_scheduled_transfer.py")
        script_path = os.path.abspath(script_path)

        python_exe = "python3"  # ggf. Pfad anpassen
        try:
            proc = subprocess.Popen([python_exe, script_path, "--plan", plan_name],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            if out:
                debug_print("OUT:", out)
            if err:
                debug_print("ERR:", err)

            if proc.returncode == 0:
                QtWidgets.QMessageBox.information(self, "Fertig", f"Plan '{plan_name}' ausgeführt.")
            else:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Fehler:\n{err or out}")
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    # ---------------------------------------------------
    # NEU: Plan hinzufügen
    # ---------------------------------------------------
    def add_plan(self):
        """
        Fügt einen neuen Plan hinzu (Name, Quelle, Ziel(remote)).
        Speichert in backup_plans.json und aktualisiert die Tabelle.
        """
        # Name
        plan_name, ok = QtWidgets.QInputDialog.getText(self, "Neuer Plan", "Name des Plans eingeben:")
        if not ok or not plan_name:
            return

        # Quellordner
        source_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Quellordner wählen")
        if not source_dir:
            return

        # Remote-Ziel
        remote, ok2 = QtWidgets.QInputDialog.getText(self, "Remote-Pfad", "Remote-Zielverzeichnis eingeben:")
        if not ok2 or not remote:
            return

        new_plan = {
            "name": plan_name,
            "source_path": source_dir,
            "remote_path": remote,
            "paused": False
        }
        self.plans.append(new_plan)
        save_all_backup_plans(self.plans)
        self.load_plans()

    # ---------------------------------------------------
    # NEU: Plan löschen
    # ---------------------------------------------------
    def delete_plan(self):
        """
        Löscht den aktuell markierten Plan aus backup_plans.json.
        """
        row = self.plan_table.currentRow()
        if row < 0 or row >= len(self.plans):
            QtWidgets.QMessageBox.information(self, "Info", "Bitte einen Plan in der Liste auswählen.")
            return

        plan_name = self.plans[row].get("name", "Unbenannt")
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Plan löschen?",
            f"Soll der Plan '{plan_name}' wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.No:
            return

        # Lösche den Plan aus der Liste
        del self.plans[row]
        save_all_backup_plans(self.plans)
        self.load_plans()