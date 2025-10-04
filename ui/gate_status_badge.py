# ui/gate_status_badge.py
from __future__ import annotations

from typing import Optional

# PySide6 bevorzugen, sonst PyQt5
try:
    from PySide6.QtCore import Qt, QSize, QTimer
    from PySide6.QtGui import QPainter, QFont, QPen, QColor
    from PySide6.QtWidgets import (
        QWidget, QLabel, QHBoxLayout, QFrame, QStatusBar
    )
    QT_LIB = "PySide6"
except Exception:  # noqa: BLE001
    from PyQt5.QtCore import Qt, QSize, QTimer
    from PyQt5.QtGui import QPainter, QFont, QPen, QColor
    from PyQt5.QtWidgets import (
        QWidget, QLabel, QHBoxLayout, QFrame, QStatusBar
    )
    QT_LIB = "PyQt5"


class _Dot(QWidget):
    """Kleiner runder Punkt, der je nach Status grün/rot ist."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self._color_on = QColor(35, 180, 85)     # grün
        self._color_off = QColor(200, 60, 60)    # rot
        self.setFixedSize(QSize(12, 12))

    def set_on(self, on: bool):
        if self._on != on:
            self._on = on
            self.update()

    def paintEvent(self, ev):  # noqa: N802
        r = min(self.width(), self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color_on if self._on else self._color_off)
        p.drawEllipse(0, 0, r, r)
        p.end()


class GateStatusBadge(QFrame):
    """
    Kompaktes Badge: •  Hotfolder-Gate: aktiv / inaktiv
    - Call set_gate_open(True/False), z.B. aus PlanCleaner.sig_gate_changed
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GateStatusBadge")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("""
            #GateStatusBadge {
                border: 1px solid rgba(120,120,120,0.35);
                border-radius: 8px;
                background: rgba(240,240,240,0.6);
            }
        """)

        self._dot = _Dot(self)
        self._label = QLabel("Hotfolder-Gate: inaktiv", self)
        f = QFont(self._label.font())
        f.setPointSize(max(9, f.pointSize()))
        self._label.setFont(f)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)
        lay.addWidget(self._dot, 0, Qt.AlignVCenter)
        lay.addWidget(self._label, 0, Qt.AlignVCenter)

        self._gate_open = False
        self.set_gate_open(False)

    def set_gate_open(self, is_open: bool):
        self._gate_open = bool(is_open)
        self._dot.set_on(self._gate_open)
        self._label.setText(
            "Hotfolder-Gate: aktiv" if self._gate_open else "Hotfolder-Gate: inaktiv"
        )

    def gate_open(self) -> bool:
        return self._gate_open


def attach_gate_badge(container_widget) -> GateStatusBadge:
    """
    Versucht, das Badge sinnvoll im UI unterzubringen:
    - Wenn das Fenster eine QStatusBar hat → dort rechts hinzufügen.
    - Sonst: falls ein Layout existiert → Badge ans Ende setzen.
    - Sonst: einfach als Child zurückgeben (Caller fügt es selbst ein).
    """
    badge = GateStatusBadge(container_widget)

    # 1) Statusbar?
    main_win = container_widget
    status_bar: Optional[QStatusBar] = None
    try:
        # QMainWindow.statusBar()
        status_bar = getattr(main_win, "statusBar", None)() if hasattr(main_win, "statusBar") else None
    except Exception:  # noqa: BLE001
        status_bar = None

    if isinstance(status_bar, QStatusBar):
        status_bar.addPermanentWidget(badge, 0)
        return badge

    # 2) Direktes Layout am Container?
    try:
        lay = container_widget.layout()
        if lay is not None:
            lay.addWidget(badge, 0, Qt.AlignRight)
            return badge
    except Exception:  # noqa: BLE001
        pass

    # 3) Fallback – Caller muss selbst positionieren
    badge.setParent(container_widget)
    badge.show()
    return badge