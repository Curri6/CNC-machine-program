"""Bits (tools), materials, and how fast / deep to cut with each.

The tool list lives in Documents\\A-Tech CNC\\tools.json. Each bit has a
kind (flat end mill, ball end mill, drill, V-bit), a size and a few
details. When a bit is used in the Make tab, `cutting_data` works out
the spindle speed, feed, plunge feed, depth per pass, stepover and peck
depth for that bit in the chosen material, kept inside what this mill
can do (its top speed and the spindle speeds it can be set to).

The numbers are cautious starting points for a small, light mill, not
the fastest possible. Every one can be changed per step in the Make tab.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

KINDS = {
    "flat": "Flat end mill",
    "ball": "Ball end mill",
    "drill": "Drill bit",
    "vbit": "V-bit / engraver",
}


@dataclass
class Material:
    key: str
    name: str
    sfm_hss: float          # surface speed, ft/min, high-speed steel bits
    sfm_carbide: float      # surface speed, ft/min, carbide bits
    chip: float             # chip per tooth (in) for a 1/8 in bit; scaled with size
    doc: float              # depth per pass, as a fraction of the bit's diameter
    stepover: float         # pocket stepover, fraction of diameter (flat bits)
    drill_ipr: float        # drill feed per turn, fraction of the drill's diameter
    peck: float             # peck depth, multiples of the drill's diameter
    plunge: float           # plunge feed, fraction of the side-cutting feed
    note: str = ""


MATERIALS: dict[str, Material] = {m.key: m for m in (
    Material("acrylic", "Acrylic (Plexiglas)", 250, 500, 0.002, 0.5, 0.40, 0.020, 1.0, 0.30,
             "Acrylic melts if the bit rubs: keep the chips thick, blow the chips away."),
    Material("wax", "Machinable wax", 600, 1000, 0.004, 1.0, 0.45, 0.040, 3.0, 0.50),
    Material("wood", "Wood / MDF", 500, 800, 0.003, 0.75, 0.40, 0.030, 2.0, 0.40),
    Material("hdpe", "HDPE / soft plastic", 400, 700, 0.003, 0.75, 0.40, 0.030, 1.5, 0.40),
    Material("foam", "Foam / balsa", 800, 1200, 0.005, 2.0, 0.50, 0.050, 4.0, 0.50),
    Material("aluminum", "Aluminum", 200, 500, 0.0007, 0.20, 0.30, 0.012, 0.5, 0.25,
             "Aluminum: light cuts, use cutting fluid, watch for chips welding to the bit."),
    Material("brass", "Brass", 150, 350, 0.0006, 0.20, 0.30, 0.012, 0.75, 0.25),
)}
DEFAULT_MATERIAL = "acrylic"


@dataclass
class Tool:
    number: int
    kind: str = "flat"
    diameter: float = 0.125      # in (V-bit: widest part)
    flutes: int = 2
    cut_length: float = 0.5      # how deep the cutting part goes (in)
    angle: float = 60.0          # V-bit: included angle; drill: point angle
    tip: float = 0.0             # V-bit: flat at the tip (in)
    carbide: bool = False
    name: str = ""               # blank = made from the size and kind
    notes: str = ""

    @property
    def radius(self) -> float:
        return self.diameter / 2

    def kind_name(self) -> str:
        return KINDS.get(self.kind, self.kind)

    def size_text(self) -> str:
        return inch_text(self.diameter)

    def describe(self) -> str:
        """e.g. '1/8 in flat end mill, 2 flutes' or '60° V-bit, 1/4 in'."""
        if self.name.strip():
            return self.name.strip()
        if self.kind == "vbit":
            return f"{self.angle:g}° V-bit, {self.size_text()}"
        kind = self.kind_name().lower()
        if self.kind == "drill":
            return f"{self.size_text()} drill bit"
        return f"{self.size_text()} {kind}, {self.flutes} flute{'s' if self.flutes != 1 else ''}"

    def label(self) -> str:
        return f"T{self.number}  ·  {self.describe()}"

    def width_at(self, depth: float) -> float:
        """How wide a groove the bit cuts at this depth (V-bits get wider)."""
        if self.kind != "vbit":
            return self.diameter
        half = math.radians(max(min(self.angle, 179.0), 1.0) / 2)
        return min(self.diameter, self.tip + 2 * max(depth, 0.0) * math.tan(half))

    def max_vbit_depth(self) -> float:
        half = math.radians(max(min(self.angle, 179.0), 1.0) / 2)
        return max((self.diameter - self.tip) / 2 / math.tan(half), 0.0)


@dataclass
class CutData:
    rpm: int
    feed: float              # in/min, side cutting
    plunge: float            # in/min, going down
    depth_per_pass: float    # in
    stepover: float          # in (pockets / facing)
    peck: float              # in (drilling)
    chip: float              # in per tooth (or per turn for a drill) at these numbers
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"{self.rpm:,} RPM · feed F{self.feed:g} · plunge F{self.plunge:g} · "
                f"{self.depth_per_pass:.4f} in per pass")


@dataclass
class Overrides:
    """Numbers the person typed for one step (0 = let the app decide)."""
    rpm: int = 0
    feed: float = 0.0
    plunge: float = 0.0
    depth_per_pass: float = 0.0
    stepover_pct: float = 0.0

    def any(self) -> bool:
        return any((self.rpm, self.feed, self.plunge, self.depth_per_pass, self.stepover_pct))


def _pick_rpm(wanted: float, choices: list[int], ceiling: float) -> int:
    """The spindle speed to use: the available speed closest to `wanted`
    without going over `ceiling` (the best speed for the bit) if possible."""
    under = [c for c in choices if c <= ceiling * 1.05]
    pool = under or [min(choices)]
    return min(pool, key=lambda c: abs(c - wanted))


def cutting_data(tool: Tool, material: Material | str, max_feed: float, rpms: list[int],
                 depth: float = 0.0, overrides: Overrides | None = None) -> CutData:
    """Speeds and feeds for this bit in this material on this machine.

    max_feed: the machine's top speed (in/min). rpms: speeds the spindle
    can be set to. depth: how deep the step cuts (V-bits get wider)."""
    mat = MATERIALS.get(material, MATERIALS[DEFAULT_MATERIAL]) if isinstance(material, str) \
        else material
    notes: list[str] = []
    rpms = sorted(rpms) or [10000]
    d = tool.diameter
    if tool.kind == "vbit":
        d = max(tool.width_at(depth or 0.02), 0.02)
    d = max(d, 0.005)

    sfm = mat.sfm_carbide if tool.carbide else mat.sfm_hss
    best_rpm = sfm * 12 / (math.pi * d)

    if tool.kind == "drill":
        per_rev = max(mat.drill_ipr * d, 0.0004)
        teeth = 1.0
    else:
        scale = min(max(d / 0.125, 0.4), 2.5)
        per_rev = mat.chip * scale
        teeth = max(tool.flutes, 1)

    ideal_feed = best_rpm * teeth * per_rev
    limit = max_feed
    if tool.kind == "drill":
        limit = max_feed * 0.6     # a light mill: drill gently
    if ideal_feed > limit:
        # The mill can't feed that fast. Slow the spindle so each tooth
        # still takes a proper chip (rubbing melts plastic and dulls bits).
        feed = limit
        needed = feed / (teeth * per_rev)
        # a little faster than needed is safer than slower (slower = each
        # tooth bites more than planned, which can snap a small bit)
        ok = [c for c in rpms if needed <= c <= best_rpm * 1.05]
        rpm = min(ok) if ok else _pick_rpm(needed, rpms, best_rpm)
        if rpm > feed / (teeth * per_rev) * 1.6:
            notes.append(f"The spindle's slowest usable speed ({rpm:,} RPM) is fast for this feed: "
                         "chips will be thin. Watch for melting or a squeal.")
        if tool.kind == "drill":
            notes.append(f"Drilling held to F{limit:g}; spindle set to {rpm:,} RPM to match.")
        else:
            notes.append(f"Feed held to the machine's top speed (F{max_feed:g}); "
                         f"spindle set to {rpm:,} RPM to match.")
    else:
        rpm = _pick_rpm(best_rpm, rpms, best_rpm)
        feed = rpm * teeth * per_rev
    feed = max(round(feed, 1), 0.5)
    chip = feed / (rpm * teeth)

    if tool.kind == "drill":
        plunge = feed
    else:
        plunge = max(round(feed * mat.plunge, 1), 0.5)

    if tool.kind == "vbit":
        doc = max(mat.doc * 0.06, 0.005)
    else:
        doc = mat.doc * tool.diameter
    if tool.cut_length > 0:
        doc = min(doc, tool.cut_length)
    doc = max(round(doc, 4), 0.002)

    step = mat.stepover * tool.diameter
    if tool.kind == "ball":
        step *= 0.5          # smaller steps so the floor isn't ridged
    step = max(step, 0.002)
    peck = max(mat.peck * tool.diameter, 0.02)

    o = overrides or Overrides()
    if o.rpm:
        rpm = int(o.rpm)
    if o.feed:
        feed = min(o.feed, max_feed)
        if o.feed > max_feed:
            notes.append(f"Your feed F{o.feed:g} is over the machine's top speed; using F{max_feed:g}.")
    if o.plunge:
        plunge = min(o.plunge, max_feed)
    if o.depth_per_pass:
        doc = o.depth_per_pass
    if o.stepover_pct:
        step = tool.diameter * o.stepover_pct / 100
    if o.any():
        notes.append("Using your own numbers for this step.")
    if mat.note and tool.kind != "drill":
        notes.append(mat.note)
    return CutData(rpm=rpm, feed=feed, plunge=plunge, depth_per_pass=doc, stepover=step,
                   peck=peck, chip=chip, notes=notes)


# ------------------------------------------------------------------ sizes
_FRACTION_RE = re.compile(r"^\s*(?:(\d+)\s+)?(\d+)\s*/\s*(\d+)\s*$")


def parse_length(text: str) -> float:
    """'1/8', '1 1/4', '.125', '0.125 in', '1/8"', '3mm', '3.175 mm' -> inches."""
    t = str(text).strip().lower().replace("inches", "").replace("inch", "").replace('"', "")
    mm = False
    if t.endswith("mm"):
        mm, t = True, t[:-2]
    elif t.endswith("in"):
        t = t[:-2]
    t = t.strip()
    m = _FRACTION_RE.match(t)
    if m:
        whole = int(m.group(1) or 0)
        den = int(m.group(3))
        if den == 0:
            raise ValueError("can't divide by zero")
        v = whole + int(m.group(2)) / den
    else:
        try:
            v = float(t)
        except ValueError:
            raise ValueError(f"'{text}' is not a size (try 1/8, 0.125 or 3mm)") from None
    if v < 0:
        raise ValueError("size can't be negative")
    return v / 25.4 if mm else v


def inch_text(v: float) -> str:
    """0.125 -> '1/8 in'; 0.118 -> '0.118 in'."""
    for den in (2, 4, 8, 16, 32, 64):
        n = v * den
        if abs(n - round(n)) < 1e-4 and round(n) > 0:
            n = int(round(n))
            g = math.gcd(n, den)
            n, dd = n // g, den // g
            if dd == 1:
                return f"{n} in"
            whole, rest = divmod(n, dd)
            return f"{whole} {rest}/{dd} in" if whole else f"{rest}/{dd} in"
    return f"{v:.3f} in"


# ------------------------------------------------------------------ library
def default_tools() -> list[Tool]:
    return [
        Tool(1, "flat", 0.125, 2, 0.5),
        Tool(2, "flat", 0.0625, 2, 0.1875),
        Tool(3, "ball", 0.125, 2, 0.375),
        Tool(4, "drill", 0.125, 2, 0.75, angle=118),
        Tool(5, "vbit", 0.25, 2, 0.25, angle=60, tip=0.005),
    ]


COMMON_TOOLS: list[tuple[str, Tool]] = [
    ("1/32 in flat end mill", Tool(0, "flat", 1 / 32, 2, 0.0938)),
    ("1/16 in flat end mill", Tool(0, "flat", 1 / 16, 2, 0.1875)),
    ("1/8 in flat end mill", Tool(0, "flat", 1 / 8, 2, 0.5)),
    ("3/16 in flat end mill", Tool(0, "flat", 3 / 16, 2, 0.5)),
    ("1/4 in flat end mill", Tool(0, "flat", 1 / 4, 2, 0.75)),
    ("1/16 in ball end mill", Tool(0, "ball", 1 / 16, 2, 0.1875)),
    ("1/8 in ball end mill", Tool(0, "ball", 1 / 8, 2, 0.375)),
    ("1/4 in ball end mill", Tool(0, "ball", 1 / 4, 2, 0.75)),
    ("1/16 in drill", Tool(0, "drill", 1 / 16, 2, 0.5, angle=118)),
    ("3/32 in drill", Tool(0, "drill", 3 / 32, 2, 0.625, angle=118)),
    ("1/8 in drill", Tool(0, "drill", 1 / 8, 2, 0.75, angle=118)),
    ("3/16 in drill", Tool(0, "drill", 3 / 16, 2, 1.0, angle=118)),
    ("1/4 in drill", Tool(0, "drill", 1 / 4, 2, 1.25, angle=118)),
    ("30° V-bit, 1/8 in", Tool(0, "vbit", 1 / 8, 1, 0.125, angle=30, tip=0.004)),
    ("60° V-bit, 1/4 in", Tool(0, "vbit", 1 / 4, 2, 0.25, angle=60, tip=0.005)),
    ("90° V-bit, 1/4 in", Tool(0, "vbit", 1 / 4, 2, 0.25, angle=90, tip=0.005)),
]


class ToolLibrary:
    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        self.tools: list[Tool] = []
        self.load()

    def load(self) -> None:
        self.tools = []
        if self.path is not None:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                names = {f.name for f in fields(Tool)}
                for d in data.get("tools", []):
                    t = Tool(**{k: v for k, v in d.items() if k in names})
                    t.number = int(t.number)
                    if t.kind not in KINDS or t.diameter <= 0:
                        continue
                    self.tools.append(t)
            except (OSError, ValueError, TypeError):
                self.tools = []
        if not self.tools:
            self.tools = default_tools()
        self.tools.sort(key=lambda t: t.number)

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"tools": [asdict(t) for t in self.tools]}, indent=2),
                             encoding="utf-8")

    def get(self, number: int) -> Tool | None:
        for t in self.tools:
            if t.number == number:
                return t
        return None

    def next_number(self) -> int:
        return max((t.number for t in self.tools), default=0) + 1

    def put(self, tool: Tool, old_number: int | None = None) -> None:
        """Add or replace a tool. Numbers must be unique."""
        if tool.number < 1:
            raise ValueError("Tool numbers start at 1.")
        if tool.diameter <= 0:
            raise ValueError("The size must be more than 0.")
        if tool.kind not in KINDS:
            raise ValueError(f"Unknown kind of bit: {tool.kind}")
        other = self.get(tool.number)
        if other is not None and tool.number != old_number:
            raise ValueError(f"T{tool.number} is already {other.describe()}.")
        if old_number is not None:
            self.tools = [t for t in self.tools if t.number != old_number]
        self.tools.append(tool)
        self.tools.sort(key=lambda t: t.number)

    def remove(self, number: int) -> None:
        self.tools = [t for t in self.tools if t.number != number]
