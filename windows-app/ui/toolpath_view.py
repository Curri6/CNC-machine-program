"""Toolpath preview: top / front / side / 3D views of a job.

* cutting moves below Z0 are colored by depth (light = shallow, purple = deepest)
* feed moves above Z0 ("air") are slate; rapid G0 moves are dashed grey
* a playback position dims the moves not reached yet and shows the tool
* wheel = zoom, drag = pan, double-click = fit, click = find that line
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QWidget

from gcode.parser import ParseResult
from ui import theme

VIEWS = ("top", "front", "side", "iso")
VIEW_NAMES = {"top": "Top (X / Y)", "front": "Front (X / Z)", "side": "Side (Y / Z)", "iso": "3D"}
_DEPTH_COLORS = ["#7dd3fc", "#38bdf8", "#3b82f6", "#6366f1", "#8b5cf6", "#c026d3"]
_AIR_COLOR = "#64748b"
_C30, _S30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def _project(view: str, p) -> tuple[float, float]:
    x, y, z = p
    if view == "top":
        return x, y
    if view == "front":
        return x, z
    if view == "side":
        return y, z
    return (x - y) * _C30, (x + y) * _S30 + z


def _nice_step(target: float) -> float:
    if target <= 0:
        return 1.0
    e = math.floor(math.log10(target))
    for m in (1, 2, 5, 10):
        if m * 10 ** e >= target:
            return m * 10 ** e
    return 10 ** (e + 1)


class ToolpathView(QWidget):
    linePicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 260)
        self.setMouseTracking(True)
        self._segs: list[tuple[list, bool, int, int]] = []   # points, rapid, line, color bucket
        self._units = "in"
        self._view = "top"
        self._show_rapids = True
        self._progress: int | None = None
        self._hilite: int | None = None
        self._proj: list[list[tuple[float, float]]] = []
        self._full_paths: dict = {}
        self._done_paths: dict = {}
        self._scale = 100.0
        self._off = QPointF(0, 0)
        self._drag_from: QPointF | None = None
        self._dragged = False
        self._user_moved = False
        self._empty_text = "Add a job file to see its preview."
        self._stock: tuple[float, float, float, float, float] | None = None
        self._widths: list[tuple[int, int, float]] = []   # (first line, last line, bit diameter)
        self._wide: dict[float, QPainterPath] = {}
        self._holes = QPainterPath()

    # ------------------------------------------------------------ public
    def show_result(self, result: ParseResult | None) -> None:
        self._segs = []
        if result is not None:
            self._units = result.units
            cut_z = [min(p[2] for p in s.points) for s in result.segments if not s.rapid]
            deep = min([z for z in cut_z if z < 0], default=0.0)
            for s in result.segments:
                zmin = min(p[2] for p in s.points)
                if s.rapid:
                    bucket = -2
                elif zmin >= 0 or deep >= 0:
                    bucket = -1
                else:
                    t = min(max(zmin / deep, 0.0), 1.0)
                    bucket = min(int(t * len(_DEPTH_COLORS)), len(_DEPTH_COLORS) - 1)
                self._segs.append((s.points, s.rapid, s.source_line, bucket))
        self._progress = None
        self._hilite = None
        self._rebuild()
        self.fit()

    def set_stock(self, box: tuple[float, float, float, float, float] | None) -> None:
        """Draw the stock: (x0, y0, x1, y1, thickness), top at Z0."""
        self._stock = box
        self._rebuild()

    def set_cut_widths(self, widths: list[tuple[int, int, float]]) -> None:
        """Shade the cuts as wide as the bit in the top view: a list of
        (first line, last line, diameter) ranges of G-code lines."""
        self._widths = list(widths)
        self._rebuild()

    def set_empty_text(self, text: str) -> None:
        self._empty_text = text
        self.update()

    def set_view(self, view: str) -> None:
        if view in VIEWS and view != self._view:
            self._view = view
            self._rebuild()
            self.fit()

    def set_show_rapids(self, on: bool) -> None:
        self._show_rapids = on
        self.update()

    def set_progress(self, k: int | None) -> None:
        """Show moves 0..k-1 as done (None = show the whole job normally)."""
        self._progress = k
        self._done_paths = self._build_paths(k) if k is not None else {}
        self.update()

    def set_highlight_line(self, line: int | None) -> None:
        self._hilite = line
        self.update()

    def segment_count(self) -> int:
        return len(self._segs)

    def segment_line(self, k: int) -> int | None:
        return self._segs[k][2] if 0 <= k < len(self._segs) else None

    def first_segment_for_line(self, line: int) -> int | None:
        for i, s in enumerate(self._segs):
            if s[2] >= line:
                return i
        return None

    def fit(self) -> None:
        pts = [p for seg in self._proj for p in seg] or [(0.0, 0.0)]
        pts.append((0.0, 0.0))
        pts += [p for edge in self._stock_edges() for p in edge]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = max(max(xs) - min(xs), 1e-3)
        h = max(max(ys) - min(ys), 1e-3)
        avail_w = max(self.width() - 60, 50)
        avail_h = max(self.height() - 70, 50)
        self._scale = min(avail_w / w, avail_h / h)
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        self._off = QPointF(self.width() / 2 - cx * self._scale,
                            self.height() / 2 + cy * self._scale)
        self._user_moved = False
        self.update()

    # ------------------------------------------------------------ building
    def _rebuild(self) -> None:
        self._proj = [[_project(self._view, p) for p in s[0]] for s in self._segs]
        self._full_paths = self._build_paths(None)
        self._done_paths = self._build_paths(self._progress) if self._progress is not None else {}
        self._wide = {}
        self._holes = QPainterPath()
        if self._widths and self._view == "top":
            for i, (pts3, rapid, line, _b) in enumerate(self._segs):
                if rapid or min(p[2] for p in pts3) >= 0:
                    continue
                d = next((w for a, b, w in self._widths if a <= line <= b), None)
                if not d:
                    continue
                path = self._wide.setdefault(d, QPainterPath())
                pts = self._proj[i]
                if all(abs(u - pts[0][0]) < 1e-6 and abs(v - pts[0][1]) < 1e-6 for u, v in pts):
                    if pts3[0][2] < -1e-6:
                        continue        # a step down inside a cut (pecks, tabs): already shaded
                    self._holes.addEllipse(QPointF(pts[0][0], -pts[0][1]), d / 2, d / 2)  # drilled
                    continue
                path.moveTo(pts[0][0], -pts[0][1])
                for u, v in pts[1:]:
                    path.lineTo(u, -v)
        self.update()

    def _stock_edges(self) -> list[list[tuple[float, float]]]:
        if not self._stock:
            return []
        x0, y0, x1, y1, th = self._stock
        z0, z1 = -th, 0.0
        if self._view == "top":
            return [[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]
        if self._view == "front":
            return [[(x0, z0), (x1, z0), (x1, z1), (x0, z1), (x0, z0)]]
        if self._view == "side":
            return [[(y0, z0), (y1, z0), (y1, z1), (y0, z1), (y0, z0)]]
        c = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        edges = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
        return [[_project("iso", c[a]), _project("iso", c[b])] for a, b in edges]

    def _build_paths(self, upto: int | None) -> dict:
        paths: dict[int, QPainterPath] = {}
        n = len(self._segs) if upto is None else min(upto, len(self._segs))
        for i in range(n):
            bucket = self._segs[i][3]
            path = paths.get(bucket)
            if path is None:
                path = paths[bucket] = QPainterPath()
            pts = self._proj[i]
            path.moveTo(pts[0][0], -pts[0][1])
            for u, v in pts[1:]:
                path.lineTo(u, -v)
        return paths

    # ------------------------------------------------------------ painting
    def _xform(self) -> QTransform:
        return QTransform(self._scale, 0, 0, self._scale, self._off.x(), self._off.y())

    @staticmethod
    def _pen(color: str, width: float = 1.4, dash: bool = False, alpha: int = 255) -> QPen:
        c = QColor(color)
        c.setAlpha(alpha)
        pen = QPen(c, width)
        pen.setCosmetic(True)
        if dash:
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def paintEvent(self, event) -> None:  # noqa: D102
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.VIEW_BG))
        if not self._segs and not self._stock:
            p.setPen(QColor("#8a94a6"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._empty_text)
            return
        if self._view != "iso":
            self._draw_grid(p)
        p.setTransform(self._xform())
        edges = self._stock_edges()
        if edges:
            sp = QPainterPath()
            for e in edges:
                sp.moveTo(e[0][0], -e[0][1])
                for u, v in e[1:]:
                    sp.lineTo(u, -v)
            if self._view != "iso":
                p.fillPath(sp, QColor(theme.VIEW_STOCK))
            p.setPen(self._pen(theme.VIEW_STOCK_EDGE, 1.2))
            p.drawPath(sp)
        for d, path in self._wide.items():
            c = QColor(theme.VIEW_CUT_WIDE)
            c.setAlpha(70)
            pen = QPen(c, d)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
        if not self._holes.isEmpty():
            c = QColor(theme.VIEW_CUT_WIDE)
            c.setAlpha(110)
            p.fillPath(self._holes, c)

        dim = self._progress is not None
        for bucket, path in self._full_paths.items():
            if bucket == -2 and not self._show_rapids:
                continue
            p.setPen(self._pen_for(bucket, alpha=55 if dim else 255))
            p.drawPath(path)
        if dim:
            for bucket, path in self._done_paths.items():
                if bucket == -2 and not self._show_rapids:
                    continue
                p.setPen(self._pen_for(bucket, width_boost=0.6))
                p.drawPath(path)

        if self._hilite is not None:
            hp = QPainterPath()
            for i, s in enumerate(self._segs):
                if s[2] == self._hilite:
                    pts = self._proj[i]
                    hp.moveTo(pts[0][0], -pts[0][1])
                    for u, v in pts[1:]:
                        hp.lineTo(u, -v)
            p.setPen(self._pen(theme.VIEW_HILITE, 3.2))
            p.drawPath(hp)

        p.resetTransform()
        self._draw_origin(p)
        if dim and self._progress:
            k = min(self._progress, len(self._proj)) - 1
            u, v = self._proj[k][-1]
            pt = self._xform().map(QPointF(u, -v))
            p.setPen(QPen(QColor("white"), 1.5))
            p.setBrush(QColor(theme.VIEW_TOOL))
            p.drawEllipse(pt, 6, 6)
        self._draw_overlay(p)

    def _pen_for(self, bucket: int, alpha: int = 255, width_boost: float = 0.0) -> QPen:
        if bucket == -2:
            return self._pen(theme.VIEW_RAPID, 1.0, dash=True, alpha=min(alpha, 170))
        if bucket == -1:
            return self._pen(_AIR_COLOR, 1.3 + width_boost, alpha=alpha)
        return self._pen(_DEPTH_COLORS[bucket], 1.5 + width_boost, alpha=alpha)

    def _draw_grid(self, p: QPainter) -> None:
        inv, _ = self._xform().inverted()
        r = inv.mapRect(QRectF(self.rect()))
        step = _nice_step(26 / self._scale)
        major = step * 5
        for s, color in ((step, theme.VIEW_GRID), (major, theme.VIEW_GRID_MAJOR)):
            p.setPen(QPen(QColor(color), 1))
            x = math.floor(r.left() / s) * s
            while x <= r.right():
                sx = self._scale * x + self._off.x()
                p.drawLine(QPointF(sx, 0), QPointF(sx, self.height()))
                x += s
            y = math.floor(r.top() / s) * s
            while y <= r.bottom():
                sy = self._scale * y + self._off.y()
                p.drawLine(QPointF(0, sy), QPointF(self.width(), sy))
                y += s
        self._grid_major = major

    def _draw_origin(self, p: QPainter) -> None:
        o = self._xform().map(QPointF(0, 0))
        p.setPen(QPen(QColor(theme.VIEW_ORIGIN), 1.5))
        p.drawLine(QPointF(o.x() - 9, o.y()), QPointF(o.x() + 9, o.y()))
        p.drawLine(QPointF(o.x(), o.y() - 9), QPointF(o.x(), o.y() + 9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(o, 4, 4)

    def _draw_overlay(self, p: QPainter) -> None:
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor("#cbd5e1"))
        p.drawText(QPointF(12, 20), VIEW_NAMES[self._view] + "   ·   0 = red cross")
        # scale bar
        if self._view != "iso":
            target = 110 / self._scale
            bar = _nice_step(target)
            px = bar * self._scale
            y = self.height() - 16
            p.setPen(QPen(QColor("#cbd5e1"), 2))
            p.drawLine(QPointF(14, y), QPointF(14 + px, y))
            p.drawLine(QPointF(14, y - 4), QPointF(14, y + 4))
            p.drawLine(QPointF(14 + px, y - 4), QPointF(14 + px, y + 4))
            p.drawText(QPointF(20 + px, y + 4), f"{bar:g} {self._units}")
        # legend
        items = [("cut (deeper = purple)", _DEPTH_COLORS[3], False),
                 ("feed above Z0", _AIR_COLOR, False)]
        if self._show_rapids:
            items.append(("rapid G0", theme.VIEW_RAPID, True))
        x = self.width() - 170
        y = self.height() - 14 - 16 * (len(items) - 1)
        for label, color, dash in items:
            p.setPen(self._pen(color, 2.2, dash))
            p.drawLine(QPointF(x, y - 4), QPointF(x + 22, y - 4))
            p.setPen(QColor("#cbd5e1"))
            p.drawText(QPointF(x + 30, y), label)
            y += 16

    # ------------------------------------------------------------ mouse
    def wheelEvent(self, event) -> None:  # noqa: D102
        f = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        pos = event.position()
        self._off = QPointF(pos.x() - (pos.x() - self._off.x()) * f,
                            pos.y() - (pos.y() - self._off.y()) * f)
        self._scale *= f
        self._user_moved = True
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: D102
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = event.position()
            self._dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: D102
        if self._drag_from is not None:
            d = event.position() - self._drag_from
            if abs(d.x()) + abs(d.y()) > 3:
                self._dragged = True
            self._off += d
            self._user_moved = True
            self._drag_from = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102
        self.setCursor(Qt.CursorShape.ArrowCursor)
        was_drag = self._dragged
        self._drag_from = None
        if not was_drag and event.button() == Qt.MouseButton.LeftButton:
            line = self._pick(event.position())
            if line is not None:
                self.linePicked.emit(line)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: D102
        self.fit()

    def resizeEvent(self, event) -> None:  # noqa: D102
        super().resizeEvent(event)
        if not self._user_moved:
            self.fit()

    def _pick(self, pos: QPointF) -> int | None:
        best, best_d = None, 10.0
        x0, y0, s = self._off.x(), self._off.y(), self._scale
        for i, pts in enumerate(self._proj):
            if self._segs[i][1] and not self._show_rapids:
                continue
            for u, v in pts:
                d = abs(u * s + x0 - pos.x()) + abs(-v * s + y0 - pos.y())
                if d < best_d:
                    best, best_d = self._segs[i][2], d
        return best
