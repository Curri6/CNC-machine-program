"""The steps a project is made of (holes, rectangles, circles, text, lines,
facing) and how each one turns into tool moves for whichever bit it uses.

Positions are in inches from the lower-left corner of the stock. Depths
are how far below the top of the stock (Z0) to cut.

The bit decides what happens:
* a drill only goes straight down (in pecks, to clear the chips); asking
  it to cut a pocket or an outline is refused, and a hole bigger than the
  drill is refused with what to use instead
* an end mill can do everything; for a hole bigger than itself it mills
  the hole round, and outlines are moved out (or in) by its radius so the
  part comes out the size you typed
* a V-bit engraves on the line, and marks hole centres
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cam import geometry as geo
from cam.builder import Builder
from cam.tools import CutData, Overrides, Tool, inch_text

ERROR, WARN, INFO = "error", "warn", "info"


# ------------------------------------------------------------------ schema
@dataclass
class Field:
    key: str
    label: str
    kind: str                     # len, num, int, choice, text, lines, bool, font
    default: object
    choices: list[tuple[str, str]] = field(default_factory=list)
    tip: str = ""
    show_if: dict[str, list] = field(default_factory=dict)
    lo: float = 0.0
    hi: float = 1000.0


def _depth_fields(default: float = 0.0625, through: bool = True) -> list[Field]:
    out = [Field("depth", "Depth", "len", default, tip="How far below the top of the stock to cut.",
                 show_if={"through": [False]} if through else {})]
    if through:
        out.insert(0, Field("through", "Cut all the way through", "bool", False,
                            tip="Depth = stock thickness + a little extra."))
    return out


MODE_CHOICES = [
    ("pocket", "Pocket (clear the inside)"),
    ("outside", "Cut out (bit outside the line)"),
    ("inside", "Cut a hole (bit inside the line)"),
    ("on", "Engrave on the line"),
]
_TAB_FIELDS = [
    Field("tabs", "Holding tabs", "bool", True,
          tip="Leaves small bridges so a cut-out part doesn't come loose. Snip them after.",
          show_if={"through": [True], "mode": ["outside", "inside"]}),
]

STEP_TYPES: dict[str, tuple[str, list[Field]]] = {
    "holes": ("Holes", [
        Field("pattern", "Where", "choice", "list", [
            ("list", "List of points"), ("grid", "Grid"), ("circle", "Bolt circle")]),
        Field("points", "Points (x, y)", "lines", "0.5, 0.5\n1.5, 0.5",
              tip="One hole per line: x, y", show_if={"pattern": ["list"]}),
        Field("gx", "First hole X", "len", 0.5, show_if={"pattern": ["grid"]}),
        Field("gy", "First hole Y", "len", 0.5, show_if={"pattern": ["grid"]}),
        Field("nx", "Holes across", "int", 3, show_if={"pattern": ["grid"]}, lo=1, hi=200),
        Field("ny", "Holes up", "int", 2, show_if={"pattern": ["grid"]}, lo=1, hi=200),
        Field("dx", "Spacing across", "len", 0.5, show_if={"pattern": ["grid"]}),
        Field("dy", "Spacing up", "len", 0.5, show_if={"pattern": ["grid"]}),
        Field("cx", "Centre X", "len", 1.0, show_if={"pattern": ["circle"]}),
        Field("cy", "Centre Y", "len", 1.0, show_if={"pattern": ["circle"]}),
        Field("bolt", "Circle diameter", "len", 1.0, show_if={"pattern": ["circle"]}),
        Field("count", "Number of holes", "int", 6, show_if={"pattern": ["circle"]}, lo=1, hi=360),
        Field("angle", "First hole angle (°)", "num", 90.0, show_if={"pattern": ["circle"]},
              lo=-360, hi=360),
        Field("hole_d", "Hole size (0 = bit size)", "len", 0.0,
              tip="Bigger than an end mill: it mills the hole round."),
    ] + _depth_fields(0.125)),
    "rect": ("Rectangle", [
        Field("mode", "Cut", "choice", "pocket", MODE_CHOICES),
        Field("x", "Left (X)", "len", 0.5),
        Field("y", "Bottom (Y)", "len", 0.5),
        Field("w", "Width", "len", 2.0),
        Field("h", "Height", "len", 1.0),
        Field("r", "Corner radius", "len", 0.0),
    ] + _depth_fields(0.0625) + _TAB_FIELDS),
    "circle": ("Circle", [
        Field("mode", "Cut", "choice", "pocket", MODE_CHOICES),
        Field("cx", "Centre X", "len", 1.5),
        Field("cy", "Centre Y", "len", 1.0),
        Field("d", "Diameter", "len", 1.0),
    ] + _depth_fields(0.0625) + _TAB_FIELDS),
    "text": ("Text", [
        Field("text", "Text", "lines", "A-TECH"),
        Field("font", "Font", "font", "Arial"),
        Field("bold", "Bold", "bool", True),
        Field("height", "Letter height", "len", 0.5, tip="Height of a capital letter."),
        Field("x", "X", "len", 0.5),
        Field("y", "Y (bottom of the letters)", "len", 0.5),
        Field("align", "X is the", "choice", "left", [("left", "Left end"), ("center", "Middle")]),
        Field("depth", "Depth", "len", 0.02),
    ]),
    "lines": ("Lines", [
        Field("points", "Points (x, y)", "lines", "0.5, 0.5\n2.5, 0.5\n2.5, 1.5",
              tip="One point per line; the bit goes from point to point."),
        Field("closed", "Join the last point to the first", "bool", False),
        Field("depth", "Depth", "len", 0.03),
    ]),
    "face": ("Face the top", [
        Field("depth", "Depth", "len", 0.01, tip="How much to take off the whole top."),
        Field("margin", "Go past the edges by", "len", 0.05),
    ]),
}


def defaults(kind: str) -> dict:
    return {f.key: f.default for f in STEP_TYPES[kind][1]}


@dataclass
class Step:
    kind: str
    tool: int = 1
    params: dict = field(default_factory=dict)
    over: Overrides = field(default_factory=Overrides)
    name: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        base = defaults(self.kind)
        base.update(self.params or {})
        self.params = base

    def p(self, key: str):
        return self.params.get(key)

    def title(self) -> str:
        return self.name.strip() or describe(self)


def describe(step: Step) -> str:
    p = step.params
    if step.kind == "holes":
        pts = hole_points(step)
        n = len(pts) if isinstance(pts, list) else 0
        size = f" {inch_text(p['hole_d'])}" if p.get("hole_d") else ""
        return f"{n} hole{'s' if n != 1 else ''}{size}"
    if step.kind == "rect":
        mode = dict(MODE_CHOICES)[p["mode"]].split(" (")[0]
        return f"{mode}: rectangle {p['w']:g} × {p['h']:g}"
    if step.kind == "circle":
        mode = dict(MODE_CHOICES)[p["mode"]].split(" (")[0]
        return f"{mode}: circle {p['d']:g} dia"
    if step.kind == "text":
        t = str(p["text"]).replace("\n", " ")
        return f"Text “{t[:18]}{'…' if len(t) > 18 else ''}”"
    if step.kind == "lines":
        return f"Lines ({len(parse_points(p['points']))} points)"
    return STEP_TYPES[step.kind][0]


# ------------------------------------------------------------------ helpers
def parse_points(text: str) -> list[geo.Pt]:
    pts = []
    for raw in str(text).replace(";", "\n").splitlines():
        raw = raw.strip().strip("()")
        if not raw:
            continue
        parts = [s for s in raw.replace(",", " ").split() if s]
        if len(parts) != 2:
            raise ValueError(f"'{raw}' should be two numbers: x, y")
        try:
            pts.append((float(parts[0]), float(parts[1])))
        except ValueError:
            raise ValueError(f"'{raw}' should be two numbers: x, y") from None
    return pts


def hole_points(step: Step) -> list[geo.Pt] | str:
    p = step.params
    try:
        if p["pattern"] == "grid":
            return [(p["gx"] + i * p["dx"], p["gy"] + j * p["dy"])
                    for j in range(int(p["ny"])) for i in range(int(p["nx"]))]
        if p["pattern"] == "circle":
            n = max(int(p["count"]), 1)
            r = p["bolt"] / 2
            a0 = math.radians(p["angle"])
            return [(p["cx"] + r * math.cos(a0 + 2 * math.pi * k / n),
                     p["cy"] + r * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]
        return parse_points(p["points"])
    except ValueError as exc:
        return str(exc)


def levels(depth: float, per_pass: float) -> list[float]:
    """Z for each pass, getting deeper, ending at -depth."""
    n = max(1, math.ceil(depth / max(per_pass, 1e-4) - 1e-9))
    return [-depth * i / n for i in range(1, n + 1)]


@dataclass
class Ctx:
    stock_x: float
    stock_y: float
    stock_t: float
    tool: Tool
    cut: CutData
    max_depth: float            # Settings: warn deeper than
    climb: bool
    tab_height: float
    msgs: list[tuple[str, str]] = field(default_factory=list)

    def error(self, t: str) -> None:
        self.msgs.append((ERROR, t))

    def warn(self, t: str) -> None:
        self.msgs.append((WARN, t))

    def info(self, t: str) -> None:
        self.msgs.append((INFO, t))

    @property
    def has_error(self) -> bool:
        return any(level == ERROR for level, _ in self.msgs)


BREAKTHROUGH = 0.01


def step_depth(step: Step, ctx: Ctx) -> float:
    p = step.params
    if p.get("through"):
        d = ctx.stock_t + BREAKTHROUGH
        if ctx.tool.kind == "drill" and step.kind == "holes":
            # the cone at a drill's tip has to clear the bottom too
            half = math.radians(max(min(ctx.tool.angle, 179), 1) / 2)
            d += ctx.tool.radius / math.tan(half)
        return d
    return float(p.get("depth") or 0.0)


def _check_depth(step: Step, ctx: Ctx, depth: float) -> None:
    t = ctx.tool
    if depth <= 0:
        ctx.error("Depth must be more than 0.")
        return
    if t.kind == "vbit":
        deepest = t.max_vbit_depth()
        if depth > deepest + 1e-6:
            ctx.error(f"T{t.number} is a {t.describe()}; its cone is only {deepest:.3f} in deep. "
                      f"Make this step {deepest:.3f} in or less.")
    elif t.cut_length > 0 and depth > t.cut_length + 1e-6:
        ctx.error(f"T{t.number}'s cutting part is {inch_text(t.cut_length)} long, but this step "
                  f"goes {depth:.3f} in deep. Use a longer bit or a shallower cut.")
    if not step.params.get("through") and depth > ctx.stock_t + 1e-6 and step.kind != "face":
        ctx.warn(f"{depth:.3f} in is deeper than the stock ({ctx.stock_t:g} in): it will cut "
                 "into what's underneath. Tick “Cut all the way through” if that's meant.")
    if depth > ctx.max_depth + 1e-6:
        ctx.warn(f"Goes {depth:.3f} in deep, more than your {ctx.max_depth:g} in limit (Settings).")
    if step.params.get("through"):
        ctx.info("Goes all the way through: put a scrap board under the stock.")


def _check_inside_stock(ctx: Ctx, x0: float, y0: float, x1: float, y1: float) -> None:
    e = 1e-4
    if x0 < -e or y0 < -e or x1 > ctx.stock_x + e or y1 > ctx.stock_y + e:
        ctx.warn(f"Part of this step is outside the stock ({ctx.stock_x:g} × {ctx.stock_y:g} in).")


def _passes_note(ctx: Ctx, depth: float, zs: list[float]) -> None:
    n = len(zs)
    ctx.info(f"{n} pass{'es' if n != 1 else ''} of {depth / n:.4f} in "
             f"({ctx.cut.rpm:,} RPM, feed F{ctx.cut.feed:g}, plunge F{ctx.cut.plunge:g}).")


def _dir_outside(ctx: Ctx) -> bool:
    """Counter-clockwise outside = conventional milling (spindle turning
    clockwise); climb milling is the other way round."""
    return not ctx.climb


def _tabs_for(loop: list[geo.Pt], centres: list[geo.Pt], ctx: Ctx) -> list[tuple[float, float]]:
    total = geo.length(loop, closed=True)
    tab_len = 0.15 + ctx.tool.diameter
    n = len(centres)
    while n and total < n * tab_len * 3:
        n -= 2 if n > 2 else n
    if n == 2 and len(centres) == 4:
        centres = [centres[0], centres[2]]
    out = []
    for c in centres[:n]:
        s = geo.nearest_param(loop, c)
        a, b = s - tab_len / 2, s + tab_len / 2
        if a < 0.01:
            a, b = 0.01, 0.01 + tab_len
        if b > total - 0.01:
            a, b = total - 0.01 - tab_len, total - 0.01
        out.append((a, b))
    if not out and centres:
        ctx.warn("This part is too small for holding tabs; it will come loose at the end.")
    return sorted(out)


def _cut_loop(b: Builder, loop: list[geo.Pt], ctx: Ctx, zs: list[float],
              tabs: list[tuple[float, float]] | None = None) -> None:
    cut = ctx.cut
    tab_z = -ctx.stock_t + ctx.tab_height
    above = 0.02
    for z in zs:
        if tabs:
            b.loop_with_tabs(loop, z, cut.feed, cut.plunge, tabs, tab_z, above)
        else:
            b.path(loop, z, cut.feed, cut.plunge, closed=True, start_above=above)
        above = z + 0.01


def _rings_pocket(b: Builder, rings: list[list[geo.Pt]], ctx: Ctx, zs: list[float]) -> None:
    """Cut nested loops from the inside out at each depth, staying down
    between rings (the bit moves only through material it's clearing)."""
    cut = ctx.cut
    above = 0.02
    for z in zs:
        first = True
        for ring in rings:
            x0, y0 = ring[0]
            if first:
                if b.z is not None and b.z <= 0:
                    b.feed(x0, y0, f=cut.feed)          # back to the middle, at the last depth
                b.path(ring, z, cut.feed, cut.plunge, closed=True, start_above=above)
                first = False
            else:
                b.feed(x0, y0, f=cut.feed)
                b.path(ring, z, cut.feed, cut.plunge, closed=True)
        above = z + 0.01
    b.up()


def _peck(b: Builder, x: float, y: float, depth: float, peck: float, f: float) -> None:
    b.go(x, y)
    z = 0.0
    while z > -depth + 1e-9:
        nz = max(z - peck, -depth)
        b.rapid(z=(z + 0.01) if z < 0 else 0.02)
        b.feed(z=nz, f=f)
        b.rapid(z=0.05)                 # out of the hole to clear the chips
        z = nz
    b.up()


# ------------------------------------------------------------------ steps
def gen_holes(step: Step, ctx: Ctx, b: Builder) -> None:
    t, cut = ctx.tool, ctx.cut
    pts = hole_points(step)
    if isinstance(pts, str):
        ctx.error(pts)
        return
    if not pts:
        ctx.error("No holes: add at least one point.")
        return
    depth = step_depth(step, ctx)
    want = float(step.params.get("hole_d") or 0.0)
    D = t.diameter
    if want and abs(want - D) <= 0.004:
        want = 0.0
    if t.kind == "drill":
        if want > D:
            ctx.error(f"T{t.number} is a {inch_text(D)} drill, so it makes {inch_text(D)} holes. "
                      f"For {inch_text(want)} holes, pick a {inch_text(want)} drill — or an end "
                      "mill smaller than the hole, and the app will mill the holes round.")
            return
        if want and want < D:
            ctx.error(f"T{t.number} ({inch_text(D)}) is bigger than the {inch_text(want)} holes.")
            return
    elif t.kind == "vbit":
        if step.params.get("through"):
            ctx.error("A V-bit can't drill through. It can only mark the hole centres (spot); "
                      "untick “Cut all the way through”.")
            return
        ctx.info("A V-bit only marks the hole centres (spot). Drill them afterwards.")
    else:
        if want and want < D:
            ctx.error(f"The holes ({inch_text(want)}) are smaller than T{t.number} "
                      f"({inch_text(D)}). Use a smaller bit or a drill.")
            return
    _check_depth(step, ctx, depth)
    r = (want or D) / 2
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    _check_inside_stock(ctx, min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)
    if ctx.has_error:
        return
    order = geo.nearest_order(pts)
    if t.kind == "drill" or (t.kind != "vbit" and not want):
        f = cut.feed if t.kind == "drill" else cut.plunge
        n_pecks = max(1, math.ceil(depth / cut.peck - 1e-9))
        what = "drills" if t.kind == "drill" else "plunges (end mill: must be centre-cutting)"
        ctx.info(f"{len(pts)} hole(s), {inch_text(D)}: {what} {depth:.3f} in deep in "
                 f"{n_pecks} peck(s) of up to {cut.peck:.3f} in ({cut.rpm:,} RPM, F{f:g}).")
        for x, y in order:
            _peck(b, x, y, depth, cut.peck, f)
        return
    if t.kind == "vbit":
        for x, y in order:
            b.go(x, y)
            b.plunge(-depth, cut.plunge)
            b.up()
        return
    # an end mill making bigger holes: mill each one round
    zs = levels(depth, cut.depth_per_pass)
    ctx.info(f"{len(pts)} hole(s) {inch_text(want)} milled round with the {inch_text(D)} bit.")
    _passes_note(ctx, depth, zs)
    for x, y in order:
        rings = _circle_rings(x, y, want / 2 - t.radius, cut.stepover, ccw=ctx.climb)
        _rings_pocket(b, rings, ctx, zs)


def _circle_rings(cx: float, cy: float, r_out: float, step: float, ccw: bool) -> list[list[geo.Pt]]:
    radii = []
    r = r_out
    while r > 1e-4:
        radii.append(r)
        r -= step
    if not radii:
        return [[(cx, cy)]]
    return [geo.circle(cx, cy, rr, ccw=ccw) for rr in reversed(radii)]


def gen_shape(step: Step, ctx: Ctx, b: Builder) -> None:
    """Rectangles and circles."""
    t, cut = ctx.tool, ctx.cut
    p = step.params
    mode = p["mode"]
    R = t.radius
    if t.kind == "drill":
        ctx.error(f"T{t.number} is a drill: it can only go straight down, not cut sideways. "
                  "Pick an end mill for this step (or a V-bit to engrave the line).")
        return
    if t.kind == "vbit" and mode != "on":
        ctx.error(f"T{t.number} is a V-bit: it can only engrave on the line. Set “Cut” to "
                  "“Engrave on the line”, or pick an end mill.")
        return
    depth = step_depth(step, ctx)
    if step.kind == "rect":
        x, y, w, h, cr = p["x"], p["y"], p["w"], p["h"], p["r"]
        if w <= 0 or h <= 0:
            ctx.error("Width and height must be more than 0.")
            return
        _check_inside_stock(ctx, x, y, x + w, y + h)
    else:
        cx, cy, d = p["cx"], p["cy"], p["d"]
        if d <= 0:
            ctx.error("The diameter must be more than 0.")
            return
        _check_inside_stock(ctx, cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2)
    _check_depth(step, ctx, depth)
    if t.kind == "ball" and mode == "pocket":
        ctx.info("A ball end mill leaves a rounded edge and small ridges on the pocket floor.")
    small = (min(p["w"], p["h"]) if step.kind == "rect" else p["d"])
    if mode in ("pocket", "inside") and small < t.diameter - 1e-6:
        ctx.error(f"The {'pocket' if mode == 'pocket' else 'hole'} ({small:g} in) is narrower than "
                  f"T{t.number} ({inch_text(t.diameter)}). Use a smaller bit.")
        return
    if ctx.has_error:
        return
    width = t.width_at(depth)
    if mode == "on" and t.kind == "vbit":
        ctx.info(f"The V-bit cuts a groove {width:.3f} in wide at this depth.")
    if step.kind == "rect" and mode in ("pocket", "inside") and p["r"] < R - 1e-6:
        ctx.info(f"Inside corners come out rounded ({inch_text(R)} radius, from the bit).")
    zs = levels(depth, cut.depth_per_pass)
    _passes_note(ctx, depth, zs)
    out_dir = _dir_outside(ctx)
    tab_on = bool(p.get("through") and p.get("tabs") and mode in ("outside", "inside"))
    if tab_on and ctx.stock_t - ctx.tab_height <= 0:
        tab_on = False

    if step.kind == "rect":
        x, y, w, h, cr = p["x"], p["y"], p["w"], p["h"], p["r"]
        if mode == "pocket":
            ix0, iy0, ix1, iy1 = x + R, y + R, x + w - R, y + h - R
            rings, j = [], 0
            while True:
                dd = j * cut.stepover
                a0, b0, a1, b1 = ix0 + dd, iy0 + dd, ix1 - dd, iy1 - dd
                if a1 < a0 - 1e-9 or b1 < b0 - 1e-9:
                    break
                rings.append(geo.rounded_rect(a0, b0, a1, b1, max(cr - R - dd, 0), ccw=not out_dir))
                j += 1
            _rings_pocket(b, list(reversed(rings)), ctx, zs)
            return
        if mode == "outside":
            loop = geo.rounded_rect(x - R, y - R, x + w + R, y + h + R, cr + R, ccw=out_dir)
        elif mode == "inside":
            loop = geo.rounded_rect(x + R, y + R, x + w - R, y + h - R, max(cr - R, 0),
                                    ccw=not out_dir)
        else:
            loop = geo.rounded_rect(x, y, x + w, y + h, cr, ccw=out_dir)
        off = R if mode == "outside" else (-R if mode == "inside" else 0)
        centres = [(x + w / 2, y - off), (x + w + off, y + h / 2), (x + w / 2, y + h + off),
                   (x - off, y + h / 2)]
    else:
        cx, cy, d = p["cx"], p["cy"], p["d"]
        r = d / 2
        if mode == "pocket":
            if r - R < 0.002:
                ctx.info("The circle is the size of the bit: it plunges straight down.")
                _peck(b, cx, cy, depth, max(cut.depth_per_pass, 0.02), cut.plunge)
                return
            _rings_pocket(b, _circle_rings(cx, cy, r - R, cut.stepover, ccw=ctx.climb), ctx, zs)
            return
        if mode == "outside":
            rr, ccw = r + R, out_dir
        elif mode == "inside":
            rr, ccw = r - R, not out_dir
            if rr < 0.002:
                ctx.info("The hole is the size of the bit: it plunges straight down.")
                _peck(b, cx, cy, depth, max(cut.depth_per_pass, 0.02), cut.plunge)
                return
        else:
            rr, ccw = r, out_dir
        loop = geo.circle(cx, cy, rr, ccw=ccw)
        centres = [(cx + rr * math.cos(a), cy + rr * math.sin(a))
                   for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)]
    tabs = _tabs_for(loop, centres, ctx) if tab_on else None
    if tabs:
        ctx.info(f"{len(tabs)} holding tabs, {ctx.tab_height:g} in thick (Settings).")
    _cut_loop(b, loop, ctx, zs, tabs)
    b.up()


def text_loops(text: str, family: str, bold: bool, height: float, x: float, y: float,
               align: str = "left") -> list[list[geo.Pt]]:
    """Outlines of the letters, in inches. Needs Qt's font engine."""
    from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication, QPainterPath
    if QGuiApplication.instance() is None:
        raise RuntimeError("Text needs the app window to be open.")
    font = QFont(family or "Arial")
    font.setPointSizeF(72)
    font.setBold(bool(bold))
    fm = QFontMetricsF(font)
    cap = fm.capHeight() or fm.ascent() * 0.7
    scale = height / cap
    out: list[list[geo.Pt]] = []
    rows = [r for r in str(text).splitlines()] or [""]
    for i, row in enumerate(rows):
        if not row.strip():
            continue
        path = QPainterPath()
        path.addText(0, 0, font, row)
        br = path.boundingRect()
        dx = -(br.left() + br.width() / 2) if align == "center" else -br.left()
        base = y + (len(rows) - 1 - i) * height * 1.6
        for poly in path.toSubpathPolygons():
            pts = [(x + (q.x() + dx) * scale, base - q.y() * scale) for q in poly]
            pts = geo.simplify(geo.dedupe(pts, closed=True), 0.0005, closed=True)
            if len(pts) >= 3 and geo.length(pts, True) > 0.005:
                out.append(pts)
    return out


def gen_text(step: Step, ctx: Ctx, b: Builder) -> None:
    t, cut = ctx.tool, ctx.cut
    p = step.params
    if t.kind == "drill":
        ctx.error(f"T{t.number} is a drill: it can't engrave letters. Pick a V-bit or a small end mill.")
        return
    if not str(p["text"]).strip():
        ctx.error("Type some text.")
        return
    if p["height"] <= 0:
        ctx.error("Letter height must be more than 0.")
        return
    depth = step_depth(step, ctx)
    _check_depth(step, ctx, depth)
    if ctx.has_error:
        return
    try:
        loops = text_loops(p["text"], p["font"], p["bold"], p["height"], p["x"], p["y"], p["align"])
    except RuntimeError as exc:
        ctx.error(str(exc))
        return
    if not loops:
        ctx.error("That font has no outlines for this text.")
        return
    allp = [q for lp in loops for q in lp]
    x0, y0, x1, y1 = geo.bounds(allp)
    _check_inside_stock(ctx, x0, y0, x1, y1)
    width = t.width_at(depth)
    if width > p["height"] * 0.18:
        ctx.warn(f"The bit cuts {width:.3f} in wide: letters {p['height']:g} in tall will run "
                 "together. Use a smaller (or sharper) bit, cut shallower, or make the text taller.")
    ctx.info(f"Engraves the outline of the letters, {width:.3f} in wide.")
    zs = levels(depth, cut.depth_per_pass)
    _passes_note(ctx, depth, zs)
    for lp in sorted(loops, key=lambda L: (round(geo.bounds(L)[0], 2), geo.bounds(L)[1])):
        _cut_loop(b, lp, ctx, zs)
        b.up()


def gen_lines(step: Step, ctx: Ctx, b: Builder) -> None:
    t, cut = ctx.tool, ctx.cut
    if t.kind == "drill":
        ctx.error(f"T{t.number} is a drill: it can't cut along lines. Pick an end mill or a V-bit.")
        return
    try:
        pts = parse_points(step.params["points"])
    except ValueError as exc:
        ctx.error(str(exc))
        return
    if len(pts) < 2:
        ctx.error("Lines need at least two points.")
        return
    depth = step_depth(step, ctx)
    _check_depth(step, ctx, depth)
    x0, y0, x1, y1 = geo.bounds(pts)
    _check_inside_stock(ctx, x0, y0, x1, y1)
    if ctx.has_error:
        return
    zs = levels(depth, cut.depth_per_pass)
    _passes_note(ctx, depth, zs)
    closed = bool(step.params.get("closed"))
    if closed:
        _cut_loop(b, pts, ctx, zs)
    else:
        fwd = True
        above = 0.02
        for z in zs:
            seq = pts if fwd else pts[::-1]
            b.path(seq, z, cut.feed, cut.plunge, start_above=above)
            above = z + 0.01
            fwd = not fwd           # come back the other way: no trip up and over
    b.up()


def gen_face(step: Step, ctx: Ctx, b: Builder) -> None:
    t, cut = ctx.tool, ctx.cut
    if t.kind in ("drill", "vbit"):
        ctx.error(f"T{t.number} ({t.describe()}) can't face. Use a flat end mill — the bigger the better.")
        return
    if t.kind == "ball":
        ctx.warn("A ball end mill leaves ridges when facing. A flat end mill is better.")
    depth = step_depth(step, ctx)
    _check_depth(step, ctx, depth)
    if ctx.has_error:
        return
    m = float(step.params.get("margin") or 0.0)
    R = t.radius
    s = cut.stepover
    ylo, yhi = -m + R * 0.5, ctx.stock_y + m - R * 0.5
    rows = [ylo]
    while rows[-1] + s < yhi - 1e-9:
        rows.append(rows[-1] + s)
    if rows[-1] < yhi - 1e-9:
        rows.append(yhi)
    xa, xb = -m - R - 0.02, ctx.stock_x + m + R + 0.02       # start and end off the stock
    zs = levels(depth, cut.depth_per_pass)
    _passes_note(ctx, depth, zs)
    ctx.info(f"{len(rows)} rows, {s:.4f} in apart.")
    for z in zs:
        b.go(xa, rows[0])
        b.plunge(z, cut.plunge)
        fwd = True
        for k, yy in enumerate(rows):
            if k:
                b.feed(y=yy, f=cut.feed)
            b.feed(x=xb if fwd else xa, f=cut.feed)
            fwd = not fwd
        b.up()


GENERATORS = {"holes": gen_holes, "rect": gen_shape, "circle": gen_shape, "text": gen_text,
              "lines": gen_lines, "face": gen_face}
