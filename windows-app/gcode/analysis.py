"""Job summary and safety checks for the preview screen.

Works on a ParseResult from gcode.parser. Nothing here talks to the
machine; it only describes the job so a person can decide whether it
looks right before carrying it over.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app_config import Settings
from gcode.dosfile import is_dos_name
from gcode.parser import ParseResult

OK, INFO, WARN = "ok", "info", "warn"


@dataclass
class Check:
    level: str   # OK / INFO / WARN
    text: str


@dataclass
class JobStats:
    units: str
    line_count: int
    move_count: int
    cut_moves: int
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    z_range: tuple[float, float]
    cut_length: float
    rapid_length: float
    est_seconds: float
    feeds: list[float]
    tool_changes: int
    program_stops: int
    checks: list[Check] = field(default_factory=list)

    @property
    def size_text(self) -> str:
        w = self.x_range[1] - self.x_range[0]
        h = self.y_range[1] - self.y_range[0]
        return f"{w:.3f} × {h:.3f} {self.units}"

    @property
    def time_text(self) -> str:
        return time_text(self.est_seconds)

    @property
    def short_time(self) -> str:
        s = int(round(self.est_seconds))
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}h {m:02d}m"
        return f"{m}m {sec:02d}s" if m else f"{sec}s"

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.level == WARN)


def time_text(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min {sec:02d} s"


def _length(points) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def analyze(result: ParseResult, settings: Settings, file_name: str = "") -> JobStats:
    mm = result.units == "mm"
    scale = 25.4 if mm else 1.0          # settings are in inches
    rapid_speed = settings.rapid_in_per_min * scale
    default_feed = settings.default_feed_in_per_min * scale

    pts = [p for s in result.segments for p in s.points]
    xs = [p[0] for p in pts] or [0.0]
    ys = [p[1] for p in pts] or [0.0]
    zs = [p[2] for p in pts] or [0.0]

    cut_len = rapid_len = 0.0
    minutes = 0.0
    feeds: set[float] = set()
    no_feed_cut = False
    for seg in result.segments:
        length = _length(seg.points)
        if seg.rapid:
            rapid_len += length
            minutes += length / rapid_speed
        else:
            cut_len += length
            if seg.feed is None:
                no_feed_cut = True
                f = default_feed
            else:
                f = seg.feed
                feeds.add(f)
            minutes += length / min(f, rapid_speed)

    stats = JobStats(
        units=result.units,
        line_count=len(result.lines),
        move_count=len(result.segments),
        cut_moves=sum(1 for s in result.segments if not s.rapid),
        x_range=(min(xs), max(xs)),
        y_range=(min(ys), max(ys)),
        z_range=(min(zs), max(zs)),
        cut_length=cut_len,
        rapid_length=rapid_len,
        est_seconds=minutes * 60.0,
        feeds=sorted(feeds),
        tool_changes=result.tool_changes,
        program_stops=result.program_stops,
    )
    checks = stats.checks

    # --- commands MPS2003 doesn't know
    unsupported = sorted({c for line in result.lines for c in line.unsupported})
    if unsupported:
        checks.append(Check(WARN, (
            f"Commands MPS2003's manual doesn't list: {', '.join(unsupported)}. "
            "Check the job in MPS2003's Plot Preview (P) before cutting.")))
    else:
        checks.append(Check(OK, "Every command is one MPS2003 understands."))

    if not result.segments:
        checks.append(Check(WARN, "No moves found — is this really a G-code job?"))
        return stats

    # --- depth
    deepest = stats.z_range[0]
    limit = settings.max_depth_in * scale
    if deepest < -limit:
        checks.append(Check(WARN, (
            f"Deepest cut is Z{deepest:.3f} {result.units}, deeper than your "
            f"{limit:g} {result.units} limit (Settings).")))
    elif deepest < 0:
        checks.append(Check(OK, f"Deepest cut: Z{deepest:.3f} {result.units}."))
    else:
        checks.append(Check(INFO, "Nothing goes below Z0 — this job only moves in the air. "
                                  "(MPS2003's Plot Preview only draws moves at or below Z0, "
                                  "so its preview screen will stay blank.)"))

    # --- work area
    if settings.work_x_in > 0 and settings.work_y_in > 0:
        wx, wy = settings.work_x_in * scale, settings.work_y_in * scale
        w = stats.x_range[1] - stats.x_range[0]
        h = stats.y_range[1] - stats.y_range[0]
        if w > wx or h > wy:
            checks.append(Check(WARN, (
                f"Job is {stats.size_text}, bigger than the {wx:g} × {wy:g} "
                f"{result.units} work area (Settings).")))
        else:
            checks.append(Check(OK, f"Fits the {wx:g} × {wy:g} {result.units} work area."))

    # --- feeds
    if no_feed_cut:
        checks.append(Check(WARN, (
            "A cutting move comes before any feed rate (F). MPS2003 will use "
            "whatever feed it last had.")))
    fast = [f for f in feeds if f > rapid_speed]
    if fast:
        checks.append(Check(INFO, (
            f"Feed F{max(fast):g} is faster than the machine's top speed "
            f"(about {rapid_speed:.1f} {result.units}/min); it will run slower.")))

    # --- pauses
    if result.tool_changes:
        checks.append(Check(INFO, (
            f"{result.tool_changes} tool change(s) (M6): MPS2003 stops and waits "
            "for you to press C each time.")))
    if result.program_stops:
        checks.append(Check(INFO, (
            f"{result.program_stops} program stop(s) (M0): MPS2003 stops and "
            "waits for you to press C each time.")))

    if mm:
        checks.append(Check(INFO, "Job is in millimetres (G21). The machine is set to INCH."))

    if file_name and not is_dos_name(file_name.upper()):
        checks.append(Check(INFO, (
            f"'{file_name}' is not a DOS 8.3 name; it gets a short name when "
            "sent to the old PC.")))
    return stats
