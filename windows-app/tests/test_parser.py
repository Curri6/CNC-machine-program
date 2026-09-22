"""Quick sanity tests for gcode.parser -- run with: python -m tests.test_parser"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
G90
G00 X0 Y0
G01 X1 Y1 F10
T1 M06
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
    assert "G90" in joined
    assert "M06" in joined
    assert "G28" in joined
    print("test_unsupported_codes_are_flagged: PASS")


def test_arc_flattens_to_polyline():
    result = parse_gcode(SAMPLE_SUPPORTED)
    arc_segments = [s for s in result.segments if len(s.points) > 2]
    assert len(arc_segments) == 1, "expected exactly one arc segment"
    assert len(arc_segments[0].points) > 10, "arc should flatten to many points"
    print("test_arc_flattens_to_polyline: PASS")


if __name__ == "__main__":
    test_supported_job_has_no_warnings()
    test_unsupported_codes_are_flagged()
    test_arc_flattens_to_polyline()
    print("\nAll parser tests passed.")
