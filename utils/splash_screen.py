#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from PySide6 import QtWidgets, QtCore, QtGui


def resource_path(relative_path):
    """Gibt den absoluten Pfad zur Ressource zurück – funktioniert im Entwicklungsmodus und im PyInstaller-Bundle."""
    try:
        # Wenn wir per PyInstaller laufen:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class SplashScreen(QtWidgets.QSplashScreen):
    def __init__(self, app):
        """Initialisiert den Splash-Screen."""
        self.app = app
        splash_image_path = resource_path("assets/CC_PRisM_SplashScreen_600px.png")
        splash_pixmap = QtGui.QPixmap(splash_image_path)

        # Falls das Bild nicht gefunden wurde, versuche alternative Pfade
        if splash_pixmap.isNull():
            alternative_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets",
                             "CC_PRisM_SplashScreen_600px.png"),
                os.path.join(os.path.dirname(sys.executable), "assets", "CC_PRisM_SplashScreen_600px.png"),
                os.path.join(os.path.abspath("."), "assets", "CC_PRisM_SplashScreen_600px.png"),
                "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/assets/CC_PRisM_SplashScreen_600px.png"
                # Absoluter Pfad als Fallback
            ]

            for path in alternative_paths:
                if os.path.exists(path):
                    splash_pixmap = QtGui.QPixmap(path)
                    if not splash_pixmap.isNull():
                        break

            # Wenn immer noch kein Bild gefunden wurde, erstelle ein einfaches Bild
            if splash_pixmap.isNull():
                splash_pixmap = QtGui.QPixmap(600, 400)
                splash_pixmap.fill(QtGui.QColor(30, 30, 30))
                painter = QtGui.QPainter(splash_pixmap)
                painter.setPen(QtGui.QColor(255, 255, 255))
                painter.setFont(QtGui.QFont("Arial", 30))
                painter.drawText(splash_pixmap.rect(), QtCore.Qt.AlignCenter, "PRisM-RAC")
                painter.end()

        super().__init__(splash_pixmap)

        # Zentriere den Splash-Screen auf dem Bildschirm
        screen_geometry = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - splash_pixmap.width()) // 2
        y = (screen_geometry.height() - splash_pixmap.height()) // 2
        self.move(x, y)

        # Füge ein Fortschritts-Label hinzu
        self.progress_label = QtWidgets.QLabel("Starte PRisM-RAC...", self)
        self.progress_label.setStyleSheet("""
            color: white; 
            background-color: rgba(0, 0, 0, 127);
            padding: 5px;
            border-radius: 3px;
            font-size: 14px;
        """)
        self.progress_label.setGeometry(10, splash_pixmap.height() - 40, splash_pixmap.width() - 20, 30)
        self.progress_label.setAlignment(QtCore.Qt.AlignCenter)

        # Füge einen Fortschrittsbalken hinzu
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #76797C;
                border-radius: 2px;
                text-align: center;
                background-color: rgba(0, 0, 0, 127);
                color: white;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
            }
        """)
        self.progress_bar.setGeometry(10, splash_pixmap.height() - 80, splash_pixmap.width() - 20, 25)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Timer für automatisches Ausblenden nach 2 Sekunden
        self.main_window = None
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(3000)  # 2000 ms = 2 Sekunden
        self.timer.timeout.connect(self.close_splash)

    def update_progress(self, message, percent=None):
        """Aktualisiert die Fortschrittsanzeige."""
        self.progress_label.setText(message)
        if percent is not None:
            self.progress_bar.setValue(percent)
        self.app.processEvents()  # Wichtig, damit UI-Updates verarbeitet werden

    def finish(self, main_window):
        """Speichert das Hauptfenster und startet den Timer."""
        self.main_window = main_window
        self.timer.start()  # Startet den 2-Sekunden-Timer

    def close_splash(self):
        """Wird aufgerufen, wenn der Timer abläuft. Blendet den Splash-Screen aus und zeigt das Hauptfenster."""
        if self.main_window:
            super().finish(self.main_window)