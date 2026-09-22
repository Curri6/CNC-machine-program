"""2D top-down toolpath preview (X/Y), the way a small 3-axis mill's
job is most easily checked at a glance. Cutting moves are drawn solid,
rapid (non-cutting) moves dashed, matching the convention most CAM/
G-code viewers use.
"""

from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from gcode.parser import ParseResult

_RAPID_COLOR = Qt.GlobalColor.gray
_CUT_COLOR = Qt.GlobalColor.blue
_ORIGIN_COLOR = Qt.GlobalColor.red


class ToolpathView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(self.renderHints() | self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def show_result(self, result: ParseResult) -> None:
        self._scene.clear()

        rapid_pen = QPen(_RAPID_COLOR)
        rapid_pen.setStyle(Qt.PenStyle.DashLine)
        rapid_pen.setWidthF(0.0)

        cut_pen = QPen(_CUT_COLOR)
        cut_pen.setWidthF(0.0)

        for segment in result.segments:
            pen = rapid_pen if segment.rapid else cut_pen
            points = segment.points
            for a, b in zip(points, points[1:]):
                self._scene.addLine(QLineF(a[0], -a[1], b[0], -b[1]), pen)
                # Y is flipped (negated) because Qt's scene grows
                # downward but G-code's Y grows upward like normal
                # graph paper -- this keeps the preview intuitive.

        origin_pen = QPen(_ORIGIN_COLOR)
        origin_pen.setWidthF(0.0)
        r = 0.05
        self._scene.addLine(QLineF(-r, 0, r, 0), origin_pen)
        self._scene.addLine(QLineF(0, -r, 0, r), origin_pen)

        bounds = self._scene.itemsBoundingRect()
        if bounds.isEmpty():
            bounds = QRectF(-1, -1, 2, 2)
        margin = max(bounds.width(), bounds.height(), 1.0) * 0.1
        self._scene.setSceneRect(bounds.adjusted(-margin, -margin, margin, margin))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:  # noqa: D102 - Qt override
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)
