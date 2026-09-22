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
    "G98", "G99",
}
SUPPORTED_M_CODES = {"M02", "M97", "M99"}

# G-codes that move the tool (used to build the toolpath preview).
_LINEAR_MOVES = {"G00", "G01"}
_ARC_MOVES = {"G02", "G03"}

_COMMENT_PAREN_RE = re.compile(r"\([^)]*\)")
_COMMENT_SEMI_RE = re.compile(r";.*$")
_WORD_RE = re.compile(r"([A-Za-z])\s*(-?\d+\.?\d*)")


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


@dataclass
class ParseResult:
    lines: list[ParsedLine]
    segments: list[ToolpathSegment]
    warnings: list[str]
    units: str  # "in" or "mm"

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

    if clockwise:
        while end_angle > start_angle:
            end_angle -= 2 * 3.141592653589793
    else:
        while end_angle < start_angle:
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

    Positioning is treated as absolute throughout: the MPS2003 manual
    only documents absolute-mode examples for G02/G03 and never shows
    G90/G91, so incremental mode is out of scope for this parser.
    """
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    segments: list[ToolpathSegment] = []
    units = "in"

    pos = (0.0, 0.0, 0.0)

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

        if "G20" in parsed.codes:
            units = "in"
        if "G21" in parsed.codes:
            units = "mm"

        target = (
            parsed.words.get("X", pos[0]),
            parsed.words.get("Y", pos[1]),
            parsed.words.get("Z", pos[2]),
        )

        moved_codes = [c for c in parsed.codes if c in _LINEAR_MOVES | _ARC_MOVES]
        if not moved_codes:
            # No motion command on this line (e.g. a lone G17/G20/M02);
            # still worth tracking Z-only or XY-only moves that ride
            # along on a previous modal G-code, but for a beta preview
            # we only draw moves that explicitly carry a G-word.
            continue

        code = moved_codes[-1]
        if code in _LINEAR_MOVES:
            segments.append(
                ToolpathSegment(
                    points=[pos, target], rapid=(code == "G00"), source_line=i
                )
            )
        elif code in _ARC_MOVES:
            i_off = parsed.words.get("I", 0.0)
            j_off = parsed.words.get("J", 0.0)
            arc_points = _arc_to_polyline(
                start=pos,
                end_xy=(target[0], target[1]),
                center_offset=(i_off, j_off),
                clockwise=(code == "G02"),
                z=target[2],
            )
            segments.append(
                ToolpathSegment(points=[pos] + arc_points, rapid=False, source_line=i)
            )

        pos = target

    return ParseResult(lines=lines, segments=segments, warnings=warnings, units=units)
