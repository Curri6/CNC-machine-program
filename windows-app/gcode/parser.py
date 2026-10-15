"""Parse and validate G-code against the command set MPS2003 supports.

The supported command list comes from THE MICROMILL 2000 Desktop
Machining System USER'S MANUAL (MicroProto Systems) -- see
JOURNAL.md in the repo root for how this was confirmed. MPS2003 only
understands a small, classic subset of G-code; anything else in an
imported file needs to be flagged before it's sent to the machine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SUPPORTED_G_CODES = {
    "G00", "G01", "G02", "G03", "G17", "G20", "G21", "G43", "G81", "G83",
    "G90", "G91", "G92", "G98", "G99",
}
# M00 (program stop) and M06 (tool change) are both documented in the
# manual's M-Codes section, and M30 is what MPS2003's own digitizer
# appends to the files it writes.
SUPPORTED_M_CODES = {"M00", "M02", "M06", "M30", "M97", "M99"}

# G-codes that move the tool (used to build the toolpath preview).
_LINEAR_MOVES = {"G00", "G01"}
_ARC_MOVES = {"G02", "G03"}
_DRILL_CYCLES = {"G81", "G83"}
# Codes that stay in effect for following lines that only give X/Y/Z.
_MOTION_MODES = _LINEAR_MOVES | _ARC_MOVES | _DRILL_CYCLES

_COMMENT_PAREN_RE = re.compile(r"\([^)]*\)")
_COMMENT_SEMI_RE = re.compile(r";.*$")
# Numbers may have no leading digit (Z.1, Z-.070 -- common in the
# machine's own sample jobs) and may have a space after the letter.
_WORD_RE = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


@dataclass
class ParsedLine:
    line_no: int
    raw: str
    codes: list[str]
    words: dict[str, float]
    unsupported: list[str] = field(default_factory=list)


@dataclass
class ToolpathSegment:
    """One motion segment for the preview: a straight line or an arc,
    already flattened to a polyline of (x, y, z) points for easy
    drawing regardless of whether it started as G00/G01 or G02/G03."""
    points: list[tuple[float, float, float]]
    rapid: bool  # True for G00 (non-cutting) moves
    source_line: int
    feed: float | None = None  # modal F in effect (None for rapids / not set yet)


@dataclass
class ParseResult:
    lines: list[ParsedLine]
    segments: list[ToolpathSegment]
    warnings: list[str]
    units: str  # "in" or "mm"
    tool_changes: int = 0     # M06 count (MPS2003 pauses for each)
    program_stops: int = 0    # M00 count (MPS2003 pauses for each)

    @property
    def is_fully_supported(self) -> bool:
        return not self.warnings


def _normalize_code(letter: str, number: float) -> str:
    """Format a word like G1 / G01 / G1.0 all as 'G01'."""
    return f"{letter.upper()}{int(round(number)):02d}"


def _strip_comments(line: str) -> str:
    line = _COMMENT_PAREN_RE.sub(" ", line)
    line = _COMMENT_SEMI_RE.sub("", line)
    return line.strip()


def parse_line(line_no: int, raw: str) -> ParsedLine | None:
    stripped = _strip_comments(raw)
    if not stripped:
        return None

    codes: list[str] = []
    words: dict[str, float] = {}
    unsupported: list[str] = []

    for letter, number_str in _WORD_RE.findall(stripped):
        number = float(number_str)
        letter_upper = letter.upper()
        if letter_upper in ("G", "M"):
            code = _normalize_code(letter_upper, number)
            codes.append(code)
            supported = (
                SUPPORTED_G_CODES if letter_upper == "G" else SUPPORTED_M_CODES
            )
            if code not in supported:
                unsupported.append(code)
        else:
            # Parameter word (X, Y, Z, I, J, F, H, R, P, A, ...).
            # Last one wins if a letter appears twice on one line,
            # which shouldn't happen in well-formed G-code anyway.
            words[letter_upper] = number

    if not codes and not words:
        return None

    return ParsedLine(
        line_no=line_no, raw=raw, codes=codes, words=words, unsupported=unsupported
    )


def _arc_to_polyline(
    start: tuple[float, float, float],
    end_xy: tuple[float, float],
    center_offset: tuple[float, float],
    clockwise: bool,
    z: float,
    steps: int = 32,
) -> list[tuple[float, float, float]]:
    """Flatten a G02/G03 arc (XY plane, per G17) into a polyline.

    center_offset is (I, J): the arc center relative to the start
    point, which is how MPS2003's G02/G03 examples specify it.
    """
    sx, sy, _ = start
    ex, ey = end_xy
    cx, cy = sx + center_offset[0], sy + center_offset[1]

    start_angle = _angle(cx, cy, sx, sy)
    end_angle = _angle(cx, cy, ex, ey)

    # ">=" / "<=" so an arc that ends where it starts is a full circle
    if clockwise:
        while end_angle >= start_angle:
            end_angle -= 2 * 3.141592653589793
    else:
        while end_angle <= start_angle:
            end_angle += 2 * 3.141592653589793

    radius = ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5
    points = []
    for i in range(1, steps + 1):
        t = start_angle + (end_angle - start_angle) * (i / steps)
        points.append((cx + radius * _cos(t), cy + radius * _sin(t), z))
    return points


def _angle(cx: float, cy: float, x: float, y: float) -> float:
    import math

    return math.atan2(y - cy, x - cx)


def _cos(t: float) -> float:
    import math

    return math.cos(t)


def _sin(t: float) -> float:
    import math

    return math.sin(t)


def parse_gcode(text: str) -> ParseResult:
    """Parse a full G-code program and build a preview-ready toolpath.

    Tracks the modal state that real jobs rely on (checked against the
    sample jobs in the machine's own C:\\MPSPRO, 2026-10-14):

    * the motion mode (G00/G01/G02/G03/G81/G83) carries on to following
      lines that only give coordinates -- most CAM output is written
      this way, so without it a 10,000-line job previews as 3 moves;
    * G90 absolute / G91 incremental positioning (manual p. 25);
    * G92 setting a new reference position (manual p. 25);
    * G81/G83 drill cycles: each hole is drawn as rapid over the hole,
      rapid down to R, feed to the Z depth, and rapid back to R (G99)
      or to the starting height (G98).

    Preview coordinates are machine coordinates: what G92 shifts is
    the program's coordinates, not where the tool really is.
    """
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    segments: list[ToolpathSegment] = []
    units = "in"

    pos = (0.0, 0.0, 0.0)          # machine position
    offset = [0.0, 0.0, 0.0]       # machine = program + offset (G92)
    motion: str | None = None      # modal motion code
    incremental = False            # G91
    retract_to_r = False           # G99 (else G98: back to start height)
    drill_r: float | None = None   # modal R plane (program coords)
    drill_z: float | None = None   # modal drill depth (program coords)
    feed: float | None = None      # modal F
    tool_changes = 0
    program_stops = 0

    for i, raw in enumerate(text.splitlines(), start=1):
        parsed = parse_line(i, raw)
        if parsed is None:
            continue
        lines.append(parsed)

        for code in parsed.unsupported:
            warnings.append(
                f"Line {i}: unsupported code {code} — MPS2003 does not "
                f"recognize this. Job will likely fail or behave "
                f"unexpectedly if sent as-is."
            )

        codes = parsed.codes
        words = parsed.words
        if "F" in words and words["F"] > 0:
            feed = words["F"]
        tool_changes += codes.count("M06")
        program_stops += codes.count("M00")
        if "G20" in codes:
            units = "in"
        if "G21" in codes:
            units = "mm"
        if "G90" in codes:
            incremental = False
        if "G91" in codes:
            incremental = True
        if "G98" in codes:
            retract_to_r = False
        if "G99" in codes:
            retract_to_r = True

        if "G92" in codes:
            # New reference: the current machine position now reads as
            # the given program coordinates. No movement.
            for axis, letter in enumerate("XYZ"):
                if letter in words:
                    offset[axis] = pos[axis] - words[letter]
            continue

        for code in codes:
            if code in _MOTION_MODES:
                motion = code

        has_xyz = any(k in words for k in "XYZ")
        # a G02/G03 with only I/J is a full circle back to the start
        if motion in _ARC_MOVES and ("I" in words or "J" in words):
            has_xyz = True
        if motion is None or not has_xyz:
            # e.g. a lone G17/G20/M02, or a feed-only line
            if motion in _DRILL_CYCLES and "R" in words:
                drill_r = words["R"]
            continue

        def axis_target(axis: int, letter: str) -> float:
            if letter not in words:
                return pos[axis]
            if incremental:
                return pos[axis] + words[letter]
            return words[letter] + offset[axis]

        if motion in _DRILL_CYCLES:
            if "R" in words:
                drill_r = words["R"]
            if "Z" in words:
                drill_z = words["Z"]
            x = axis_target(0, "X")
            y = axis_target(1, "Y")
            start_z = pos[2]
            r_z = start_z if drill_r is None else drill_r + offset[2]
            depth = r_z if drill_z is None else drill_z + offset[2]
            end_z = r_z if retract_to_r else start_z
            path = [
                ((pos[0], pos[1], start_z), (x, y, start_z), True),
                ((x, y, start_z), (x, y, r_z), True),
                ((x, y, r_z), (x, y, depth), False),
                ((x, y, depth), (x, y, end_z), True),
            ]
            for a, b, rapid in path:
                if a != b:
                    segments.append(
                        ToolpathSegment(
                            points=[a, b], rapid=rapid, source_line=i,
                            feed=None if rapid else feed,
                        )
                    )
            pos = (x, y, end_z)
            continue

        target = (axis_target(0, "X"), axis_target(1, "Y"), axis_target(2, "Z"))

        if motion in _LINEAR_MOVES:
            segments.append(
                ToolpathSegment(
                    points=[pos, target], rapid=(motion == "G00"), source_line=i,
                    feed=None if motion == "G00" else feed,
                )
            )
        else:
            i_off = words.get("I", 0.0)
            j_off = words.get("J", 0.0)
            arc_points = _arc_to_polyline(
                start=pos,
                end_xy=(target[0], target[1]),
                center_offset=(i_off, j_off),
                clockwise=(motion == "G02"),
                z=target[2],
            )
            segments.append(
                ToolpathSegment(
                    points=[pos] + arc_points, rapid=False, source_line=i, feed=feed
                )
            )

        pos = target

    return ParseResult(
        lines=lines, segments=segments, warnings=warnings, units=units,
        tool_changes=tool_changes, program_stops=program_stops,
    )
