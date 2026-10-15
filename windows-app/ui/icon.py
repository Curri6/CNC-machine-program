"""The app icon, drawn in code (a blue tile with an end mill over a toolpath)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def icon_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256.0
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2563eb"))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 52 * s, 52 * s)
    # toolpath zig-zag
    path = QPainterPath(QPointF(40 * s, 200 * s))
    for i, x in enumerate(range(40, 220, 30)):
        path.lineTo(QPointF(x * s, (200 if i % 2 == 0 else 170) * s))
    pen = QPen(QColor("#93c5fd"), 12 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    # end mill
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(104 * s, 36 * s, 48 * s, 46 * s), 8 * s, 8 * s)
    flute = QPainterPath(QPointF(112 * s, 82 * s))
    flute.lineTo(QPointF(144 * s, 82 * s))
    flute.lineTo(QPointF(144 * s, 140 * s))
    flute.lineTo(QPointF(128 * s, 158 * s))
    flute.lineTo(QPointF(112 * s, 140 * s))
    flute.closeSubpath()
    p.drawPath(flute)
    p.setPen(QPen(QColor("#2563eb"), 6 * s))
    p.drawLine(QPointF(114 * s, 100 * s), QPointF(142 * s, 116 * s))
    p.drawLine(QPointF(114 * s, 122 * s), QPointF(142 * s, 138 * s))
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for n in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(icon_pixmap(n))
    return icon
