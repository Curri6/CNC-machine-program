"""Writes G-code in the plain style MPS2003's own sample jobs use:
G00 / G01 moves in inches, absolute (G90), four decimals, comments on
their own line in ( ), M00 to pause, M02 at the end. No canned cycles,
no cutter compensation and no spindle M-codes: those aren't in the
MicroMill manual, so the app works the offsets and pecks out itself."""

from __future__ import annotations

import math
import re

from cam import geometry as geo

_COMMENT_OK = re.compile(r"[^A-Z0-9 .,:;/=+\-#%*]")


def comment_text(text: str) -> str:
    t = text.upper().replace("°", " DEG").replace("×", "X").replace("(", " ").replace(")", " ")
    t = _COMMENT_OK.sub(" ", t)
    t = re.sub(r"\s+", " ", t).replace(" ,", ",").replace(" :", ":")
    return t.strip()[:70]


def num(v: float) -> str:
    s = f"{v:.4f}"
    return "0.0000" if s in ("-0.0000", "0.0000") else s


class Builder:
    """Keeps track of where the tool is so it only writes what changes."""

    def __init__(self, safe_z: float, offset: tuple[float, float] = (0.0, 0.0)):
        self.safe_z = safe_z
        self.ox, self.oy = offset           # design coords -> job coords
        self.lines: list[str] = []
        self.x: float | None = None
        self.y: float | None = None
        self.z: float | None = None
        self.f: float | None = None
        self.min_xy = [math.inf, math.inf]
        self.max_xy = [-math.inf, -math.inf]
        self.cut_points = 0

    # ------------------------------------------------------------ raw
    def comment(self, text: str) -> None:
        t = comment_text(text)
        if t:
            self.lines.append(f"({t})")

    def raw(self, line: str) -> None:
        self.lines.append(line)

    def _move(self, code: str, x=None, y=None, z=None, f=None) -> None:
        words = []
        if x is not None:
            jx = x - self.ox
            if self.x is None or abs(jx - self.x) > 5e-5:
                words.append("X" + num(jx))
                self.x = jx
        if y is not None:
            jy = y - self.oy
            if self.y is None or abs(jy - self.y) > 5e-5:
                words.append("Y" + num(jy))
                self.y = jy
        if z is not None and (self.z is None or abs(z - self.z) > 5e-5):
            words.append("Z" + num(z))
            self.z = z
        if not words:
            return
        if code == "G01":
            if f is not None and (self.f is None or abs(f - self.f) > 1e-6):
                words.append(f"F{f:g}")
                self.f = f
            if self.z is not None and self.z < 0:
                self.cut_points += 1
            if x is not None or y is not None:
                for i, v in enumerate((x, y)):
                    if v is not None:
                        self.min_xy[i] = min(self.min_xy[i], v)
                        self.max_xy[i] = max(self.max_xy[i], v)
        self.lines.append(code + " " + " ".join(words))

    # ------------------------------------------------------------ moves
    def rapid(self, x=None, y=None, z=None) -> None:
        self._move("G00", x, y, z)

    def feed(self, x=None, y=None, z=None, f: float = 1.0) -> None:
        self._move("G01", x, y, z, f)

    def up(self) -> None:
        """Lift to the safe height (only if lower)."""
        if self.z is None or self.z < self.safe_z - 1e-6:
            self.rapid(z=self.safe_z)

    def at(self, x: float, y: float) -> bool:
        return (self.x is not None and self.y is not None and
                abs(x - self.ox - self.x) < 1e-4 and abs(y - self.oy - self.y) < 1e-4)

    def go(self, x: float, y: float) -> None:
        """Travel to (x, y) above the work."""
        if self.at(x, y) and self.z is not None and self.z >= 0:
            return
        self.up()
        self.rapid(x, y)

    def plunge(self, z: float, f: float, start_above: float = 0.02) -> None:
        """Go down to depth z here: quickly to just above where the material
        starts (start_above), then at the plunge feed."""
        if self.z is None or self.z > start_above + 1e-6:
            self.rapid(z=start_above)
        self.feed(z=z, f=f)

    # ------------------------------------------------------------ shapes
    def path(self, pts: list[geo.Pt], z: float, feed: float, plunge: float,
             closed: bool = False, start_above: float = 0.02) -> None:
        """Cut along a point list at depth z."""
        if not pts:
            return
        x0, y0 = pts[0]
        if not self.at(x0, y0) or self.z is None or self.z > 0:
            self.go(x0, y0)
            self.plunge(z, plunge, start_above)
        elif self.z > z + 1e-6:
            self.feed(z=z, f=plunge)
        for x, y in pts[1:]:
            self.feed(x, y, f=feed)
        if closed:
            self.feed(x0, y0, f=feed)

    def loop_with_tabs(self, loop: list[geo.Pt], z: float, feed: float, plunge: float,
                       tabs: list[tuple[float, float]], tab_z: float,
                       start_above: float = 0.02) -> None:
        """Cut once round a closed loop at depth z, riding up to tab_z over
        each tab (start, end distances along the loop)."""
        if not tabs or z >= tab_z:
            self.path(loop, z, feed, plunge, closed=True, start_above=start_above)
            return
        marks = [e for t in tabs for e in t]
        walk = geo.walk_loop(loop, marks)

        def in_tab(s: float) -> bool:
            return any(a < s < b for a, b in tabs)

        (x0, y0), _ = walk[0]
        if not self.at(x0, y0) or self.z is None or self.z > 0:
            self.go(x0, y0)
        cur = tab_z if in_tab(1e-6) else z
        if self.z is None or self.z > cur:
            self.plunge(cur, plunge, start_above)
        for k in range(1, len(walk)):
            (x, y), s = walk[k]
            mid = (walk[k - 1][1] + s) / 2
            want = tab_z if in_tab(mid) else z
            if abs(want - (self.z if self.z is not None else want)) > 1e-6:
                self.feed(z=want, f=plunge if want < (self.z or 0) else feed)
            self.feed(x, y, f=feed)
