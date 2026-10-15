"""Quick sanity tests for gcode.parser -- run with: python -m tests.test_parser"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):  # Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from gcode.parser import parse_gcode

SAMPLE_SUPPORTED = """
(simple supported test job)
G20
G17
G00 X0.0 Y0.0 Z0.5
G01 Z-0.1 F5.0
G01 X1.0 Y0.0 F10.0
G02 X2.0 Y0.0 I0.5 J0.0 F5.0
G01 X2.0 Y1.0
M02
"""

SAMPLE_UNSUPPORTED = """
G00 X0 Y0
G41 D1
G01 X1 Y1 F10
M03 S10000
G28
"""


def test_supported_job_has_no_warnings():
    result = parse_gcode(SAMPLE_SUPPORTED)
    assert result.warnings == [], f"unexpected warnings: {result.warnings}"
    assert result.units == "in"
    assert result.is_fully_supported
    # 4 motion lines -> 4 segments (G00, G01, G01, G02, G01 = 5 actually)
    assert len(result.segments) == 5, result.segments
    print("test_supported_job_has_no_warnings: PASS")


def test_unsupported_codes_are_flagged():
    result = parse_gcode(SAMPLE_UNSUPPORTED)
    assert not result.is_fully_supported
    joined = "\n".join(result.warnings)
    assert "G41" in joined
    assert "M03" in joined
    assert "G28" in joined
    print("test_unsupported_codes_are_flagged: PASS")


def test_arc_flattens_to_polyline():
    result = parse_gcode(SAMPLE_SUPPORTED)
    arc_segments = [s for s in result.segments if len(s.points) > 2]
    assert len(arc_segments) == 1, "expected exactly one arc segment"
    assert len(arc_segments[0].points) > 10, "arc should flatten to many points"
    print("test_arc_flattens_to_polyline: PASS")


# The tests below copy patterns from the sample jobs in the machine's own
# C:\\MPSPRO (backed up 2026-10-14; see JOURNAL.md).


def test_manual_codes_are_supported():
    # G90/G91/G92, M0, M6 are in the MPS2000 manual; M30 is written by
    # MPS2003's own digitizer.
    result = parse_gcode("G90\nG91\nG92 X0 Y0\nM0\nT1M6\nM30\n")
    assert result.warnings == [], result.warnings
    print("test_manual_codes_are_supported: PASS")


def test_modal_motion_continues():
    # KNIGHT.TAP / FACEF.TAP style: one G1, then thousands of bare moves
    result = parse_gcode("G0 X0 Y0 Z0.15\nG1 Z-0.068 F10\nX0.5\nY0.5\nX0\nG0 Z0.15\nX1\n")
    assert len(result.segments) == 7, len(result.segments)
    assert [s.rapid for s in result.segments] == [True, False, False, False, False, True, True]
    assert result.segments[2].points[-1] == (0.5, 0.0, -0.068)
    assert result.segments[-1].points[-1] == (1.0, 0.5, 0.15)
    print("test_modal_motion_continues: PASS")


def test_numbers_without_leading_zero():
    # GEAR.TAP: "G00Z.1", "G01Z-.070F10.", "G00X -0.0656Y  0.4146"
    result = parse_gcode("G00X -0.0656Y  0.4146\nG00Z.1\nG01Z-.070F10.\n")
    end = result.segments[-1].points[-1]
    assert end == (-0.0656, 0.4146, -0.07), end
    assert result.segments[1].points[-1][2] == 0.1
    print("test_numbers_without_leading_zero: PASS")


def test_incremental_and_absolute():
    result = parse_gcode("G0 X1 Y1\nG91\nG1 X0.5 Y-0.25\nX0.5\nG90\nG1 X0 Y0\n")
    ends = [s.points[-1][:2] for s in result.segments]
    assert ends == [(1.0, 1.0), (1.5, 0.75), (2.0, 0.75), (0.0, 0.0)], ends
    print("test_incremental_and_absolute: PASS")


def test_g92_shifts_program_coordinates():
    # manual p. 26: G92 then repeat a part at a new place
    result = parse_gcode("G0 X1 Y0\nG92 X0 Y0\nG1 X0.5 Y0.5\n")
    assert result.segments[-1].points[-1][:2] == (1.5, 0.5)
    print("test_g92_shifts_program_coordinates: PASS")


def test_drill_cycle_draws_each_hole():
    # BOLTHOLE.TAP: G83 on one line, then the other holes as bare X/Y
    job = "G00X0Y0Z1\nG00 Z0.2\nG83 X1 Y0 Z-0.2 R0.1 F5. Q0.1\nX0 Y1\nX-1 Y0\nG00 Z1\n"
    result = parse_gcode(job)
    assert result.warnings == []
    feeds = [s for s in result.segments if not s.rapid]
    assert len(feeds) == 3, len(feeds)   # one plunge per hole
    for f, xy in zip(feeds, [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]):
        assert f.points[0] == (xy[0], xy[1], 0.1), f.points
        assert f.points[-1] == (xy[0], xy[1], -0.2), f.points
    print("test_drill_cycle_draws_each_hole: PASS")


def test_full_circle_with_only_ij():
    result = parse_gcode("G0 X1 Y0\nG02 I-1 J0 F10\n")
    arc = result.segments[-1]
    xs = [p[0] for p in arc.points]
    assert min(xs) < -0.99 and max(xs) > 0.99, (min(xs), max(xs))
    print("test_full_circle_with_only_ij: PASS")


if __name__ == "__main__":
    test_supported_job_has_no_warnings()
    test_unsupported_codes_are_flagged()
    test_arc_flattens_to_polyline()
    test_manual_codes_are_supported()
    test_modal_motion_continues()
    test_numbers_without_leading_zero()
    test_incremental_and_absolute()
    test_g92_shifts_program_coordinates()
    test_drill_cycle_draws_each_hole()
    test_full_circle_with_only_ij()
    print("\nAll parser tests passed.")
