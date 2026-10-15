"""2D shapes as point lists, in inches. Loops are closed (the last point
joins back to the first, which is not repeated)."""

from __future__ import annotations

import math

Pt = tuple[float, float]
TOL = 0.0005          # how far a straight piece may stray from a true curve (in)


def _steps_for(r: float, sweep: float) -> int:
    if r <= TOL:
        return 1
    a = 2 * math.acos(max(1 - TOL / r, -1.0))
    return max(int(math.ceil(abs(sweep) / max(a, 1e-3))), 4 if abs(sweep) >= math.pi else 1)


def circle(cx: float, cy: float, r: float, ccw: bool = True, start: float = 0.0) -> list[Pt]:
    """Loop around a circle, starting at angle `start` (radians, 0 = +X)."""
    n = max(_steps_for(r, 2 * math.pi), 8)
    sgn = 1 if ccw else -1
    return [(cx + r * math.cos(start + sgn * 2 * math.pi * i / n),
             cy + r * math.sin(start + sgn * 2 * math.pi * i / n)) for i in range(n)]


def rounded_rect(x0: float, y0: float, x1: float, y1: float, r: float = 0.0,
                 ccw: bool = True) -> list[Pt]:
    """Loop around a rectangle with rounded corners. Starts at the left end
    of the bottom edge. A rectangle with no width or height comes out as
    a line (there and back)."""
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    w, h = x1 - x0, y1 - y0
    r = max(min(r, w / 2, h / 2), 0.0)
    pts: list[Pt] = []
    corners = ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0.0),
               (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi))
    pts.append((x0 + r, y0))
    for cx, cy, a0 in corners:
        if r > 1e-9:
            n = _steps_for(r, math.pi / 2)
            for i in range(n + 1):
                a = a0 + (math.pi / 2) * i / n
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        else:
            pts.append((cx, cy))
    out = dedupe(pts, closed=True)
    if not ccw:
        out = [out[0]] + out[1:][::-1]
    return out


def dedupe(pts: list[Pt], closed: bool = False, eps: float = 1e-7) -> list[Pt]:
    out: list[Pt] = []
    for p in pts:
        if not out or math.dist(out[-1], p) > eps:
            out.append(p)
    if closed and len(out) > 1 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    return out


def simplify(pts: list[Pt], tol: float = TOL, closed: bool = False) -> list[Pt]:
    """Drop points that sit (nearly) on the line between their neighbours."""
    if len(pts) < 3:
        return list(pts)
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = keep[-1], pts[i], pts[i + 1]
        if _dist_to_seg(b, a, c) > tol:
            keep.append(b)
    keep.append(pts[-1])
    return dedupe(keep, closed=closed)


def _dist_to_seg(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    if L < 1e-18:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def signed_area(loop: list[Pt]) -> float:
    """> 0 for counter-clockwise loops."""
    s = 0.0
    for i, (x0, y0) in enumerate(loop):
        x1, y1 = loop[(i + 1) % len(loop)]
        s += x0 * y1 - x1 * y0
    return s / 2


def length(pts: list[Pt], closed: bool = False) -> float:
    n = len(pts)
    total = sum(math.dist(pts[i], pts[i + 1]) for i in range(n - 1))
    if closed and n > 1:
        total += math.dist(pts[-1], pts[0])
    return total


def nearest_param(loop: list[Pt], p: Pt) -> float:
    """Distance along the closed loop to the point nearest p."""
    best, best_d, run = 0.0, float("inf"), 0.0
    n = len(loop)
    for i in range(n):
        a, b = loop[i], loop[(i + 1) % n]
        seg = math.dist(a, b)
        if seg > 1e-12:
            t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1]))
                             / (seg * seg)))
            q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            d = math.dist(p, q)
            if d < best_d:
                best, best_d = run + t * seg, d
        run += seg
    return best


def walk_loop(loop: list[Pt], marks: list[float]) -> list[tuple[Pt, float]]:
    """Points once round a closed loop and back to its start, each with its
    distance along the loop, with extra points added at each distance in
    `marks` (e.g. where a holding tab starts and ends)."""
    n = len(loop)
    marks = sorted(m for m in marks if m > 1e-9)
    out: list[tuple[Pt, float]] = [(loop[0], 0.0)]
    run = 0.0
    for i in range(n):
        a, b = loop[i], loop[(i + 1) % n]
        seg = math.dist(a, b)
        if seg < 1e-12:
            continue
        for m in marks:
            if run + 1e-9 < m < run + seg - 1e-9:
                t = (m - run) / seg
                out.append(((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), m))
        run += seg
        out.append((b, run))
    return out


def bounds(pts) -> tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def nearest_order(points: list[Pt], start: Pt = (0.0, 0.0)) -> list[Pt]:
    """Visit points in a short order (closest next)."""
    left = list(points)
    out = []
    cur = start
    while left:
        i = min(range(len(left)), key=lambda k: math.dist(cur, left[k]))
        cur = left.pop(i)
        out.append(cur)
    return out
