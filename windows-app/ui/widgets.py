"""Small shared widgets: cards, stat tiles, status lights."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui import theme


class Card(QFrame):
    """White rounded panel with an optional title row."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, 12, 14, 14)
        self.body.setSpacing(8)
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        self.header.addWidget(self.title)
        self.header.addStretch(1)
        if title:
            self.body.addLayout(self.header)


class Tile(QFrame):
    """A small number + label, e.g. '26 min' / 'Estimated time'."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Tile")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(1)
        self.value = QLabel("–")
        self.value.setObjectName("TileValue")
        self.label = QLabel(label)
        self.label.setObjectName("TileLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)

    def set(self, value: str, tip: str = "") -> None:
        self.value.setText(value)
        self.setToolTip(tip)


def dot_icon(color: str, size: int = 12) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return QIcon(pm)


class StatusLight(QWidget):
    """Colored dot + bold title + muted detail line."""

    COLORS = {"ok": theme.OK, "warn": theme.WARN, "bad": theme.BAD, "off": "#9ca3af",
              "info": theme.INFO}

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.dot = QLabel()
        self.dot.setFixedSize(14, 14)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight: 600;")
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        col.addWidget(self.title)
        col.addWidget(self.detail)
        lay.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(col, 1)
        self.set("off", "")

    def set(self, state: str, detail: str, title: str | None = None) -> None:
        self.dot.setPixmap(dot_icon(self.COLORS.get(state, "#9ca3af"), 14).pixmap(14, 14))
        self.detail.setText(detail)
        if title is not None:
            self.title.setText(title)
        self.state = state


def check_symbol(level: str) -> tuple[str, str]:
    return {"ok": ("✓", theme.OK), "warn": ("⚠", theme.WARN), "info": ("ℹ", theme.INFO)}.get(
        level, ("•", theme.MUTED))
