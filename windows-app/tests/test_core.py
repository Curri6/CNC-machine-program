"""Tests for app_config, gcode.dosfile and gcode.analysis.
Run with: python -m tests.test_core"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["CNC_APP_HOME"] = tempfile.mkdtemp()

from app_config import Settings, load_settings, jobs_dir, outbox_dir, received_dir, settings_path  # noqa: E402
from gcode.analysis import WARN, analyze  # noqa: E402
from gcode.dosfile import dos_name, is_dos_name, to_dos_text  # noqa: E402
from gcode.parser import parse_gcode  # noqa: E402


def test_folders_and_settings_round_trip():
    for d in (jobs_dir(), outbox_dir(), received_dir()):
        assert d.is_dir()
    s = load_settings()
    assert s.rapid_in_per_min == 13.5 and s.laptop_ip == "192.168.50.1"
    s.max_depth_in = 0.25
    s.work_x_in = 8
    s.save()
    t = load_settings()
    assert t.max_depth_in == 0.25 and t.work_x_in == 8.0
    settings_path().write_text("not json")
    assert load_settings().max_depth_in == 0.5   # broken file -> defaults
    print("test_folders_and_settings_round_trip: PASS")


def test_dos_names():
    cases = {
        "KNIGHT.TAP": "KNIGHT.TAP",
        "gear.tap": "GEAR.TAP",
        "my gear (v2).nc": "MYGEARV2.TAP",
        "Very Long Job Name.gcode": "VERYLONG.TAP",
        "job": "JOB.TAP",
        "...": "JOB.TAP",
        "con.tap": "JCON.TAP",
        "photo.jpeg": "PHOTO.JPE",
    }
    for src, want in cases.items():
        got = dos_name(src)
        assert got == want, (src, got, want)
        assert is_dos_name(got), got
    assert dos_name("gear.nc", {"GEAR.TAP"}) == "GEAR~1.TAP"
    assert dos_name("verylongname.nc", {"VERYLONG.TAP", "VERYLO~1.TAP"}) == "VERYLO~2.TAP"
    assert not is_dos_name("my gear.tap".upper())
    print("test_dos_names: PASS")


def test_dos_text():
    assert to_dos_text(b"G0 X1\nG1 Y2\n") == b"G0 X1\r\nG1 Y2\r\n"
    assert to_dos_text(b"G0 X1\r\nG1 Y2") == b"G0 X1\r\nG1 Y2\r\n"
    assert to_dos_text(b"A\rB\r\n\r\n\x1a") == b"A\r\nB\r\n"
    assert to_dos_text("°".encode("latin-1")) == b"\xb0\r\n"
    print("test_dos_text: PASS")


def test_analysis_numbers():
    job = "G0 X0 Y0 Z0.1\nG1 Z-0.1 F5\nG1 X1 F10\nG1 Y1\nG0 Z0.5\nM02\n"
    st = analyze(parse_gcode(job), Settings(), "SQUARE.TAP")
    assert st.x_range == (0.0, 1.0) and st.y_range == (0.0, 1.0)
    assert st.z_range == (-0.1, 0.5)
    assert abs(st.cut_length - 2.2) < 1e-9, st.cut_length
    assert abs(st.rapid_length - (0.1 + 0.6)) < 1e-9, st.rapid_length
    # 0.2 in at F5 + 2 in at F10 + 0.7 in at 13.5 in/min
    want = (0.2 / 5 + 2 / 10 + 0.7 / 13.5) * 60
    assert abs(st.est_seconds - want) < 1e-6, (st.est_seconds, want)
    assert st.feeds == [5.0, 10.0]
    assert st.warning_count == 0, [c.text for c in st.checks]
    assert st.size_text == "1.000 × 1.000 in"
    print("test_analysis_numbers: PASS")


def test_analysis_warnings():
    s = Settings(max_depth_in=0.5, work_x_in=1.0, work_y_in=1.0)
    job = "G1 X2 Y0 Z-0.6\nM03\nT1M6\nM0\n"
    st = analyze(parse_gcode(job), s, "my job.nc")
    texts = " | ".join(c.text for c in st.checks)
    warns = [c.text for c in st.checks if c.level == WARN]
    assert any("M03" in w for w in warns), texts
    assert any("deeper" in w for w in warns), texts
    assert any("bigger than" in w for w in warns), texts
    assert any("before any feed rate" in w for w in warns), texts
    assert "tool change" in texts and "program stop" in texts and "8.3" in texts, texts
    print("test_analysis_warnings: PASS")


def test_feed_faster_than_machine():
    st = analyze(parse_gcode("G1 X10 F60\n"), Settings())
    assert any("faster than the machine" in c.text for c in st.checks)
    assert abs(st.est_seconds - 10 / 13.5 * 60) < 1e-6   # capped at top speed
    print("test_feed_faster_than_machine: PASS")


def test_air_only_and_time_text():
    st = analyze(parse_gcode("G0 Z0.5\nG1 X1 Z0.25 F1\n"), Settings())
    assert any("only moves in the air" in c.text for c in st.checks)
    assert st.time_text.endswith("s")
    st.est_seconds = 3725
    assert st.time_text == "1 h 02 min"
    st.est_seconds = 125
    assert st.time_text == "2 min 05 s"
    print("test_air_only_and_time_text: PASS")


def test_library_and_outbox():
    import tempfile as _t
    from library import JobLibrary, old_pc_names, put_in_outbox, suggest_old_pc_name
    root = Path(_t.mkdtemp())
    src = root / "src"; src.mkdir()
    (src / "gear.tap").write_bytes(b"G0 X0 Y0\nG1 X1 F10\n")
    (src / "photo.jpg").write_bytes(b"x")
    lib = JobLibrary(root / "Jobs")
    res = lib.add([src / "gear.tap", src / "photo.jpg", src / "nope.tap"])
    assert res[0][1] == "" and "not a job" in res[1][1] and res[2][1] == "not a file", res
    assert lib.add([src / "gear.tap"])[0][1] == "already there"
    (src / "gear.tap").write_bytes(b"G0 X5\n")
    r = lib.add([src / "gear.tap"])
    assert r[0][1] == "renamed" and r[0][0].name == "gear (2).tap", r
    assert [p.name for p in lib.jobs()] == ["gear (2).tap", "gear.tap"]
    job = lib.load(lib.jobs()[1], Settings())
    assert job.stats.cut_moves == 1 and lib.load(lib.jobs()[1], Settings()) is job   # cached
    lib.remove(lib.jobs()[0])
    assert [p.name for p in lib.jobs()] == ["gear.tap"]
    try:
        lib.remove(src / "gear.tap"); assert False
    except ValueError:
        pass
    assert (src / "gear.tap").exists()                       # original untouched
    assert suggest_old_pc_name("gear.tap", root) == "GEAR.TAP"
    assert suggest_old_pc_name("My Gear v2.nc", root) == "MYGEARV2.TAP"
    out = root / "out"; out.mkdir()
    dest = put_in_outbox(lib.jobs()[0], "gear.tap", out)
    assert dest.name == "GEAR.TAP" and dest.read_bytes() == b"G0 X0 Y0\r\nG1 X1 F10\r\n"
    try:
        put_in_outbox(lib.jobs()[0], "my gear.tap", out); assert False
    except ValueError:
        pass
    rec = root / "Received" / "received_20261014_145353"; rec.mkdir(parents=True)
    (rec / "MANIFEST.TXT").write_bytes(b"MPSPRO/GEAR.TAP 17765\r\nMPSPRO/PARAM3.DAT 232\r\n")
    assert old_pc_names(root / "Received") == {"GEAR.TAP", "PARAM3.DAT"}
    print("test_library_and_outbox: PASS")


if __name__ == "__main__":
    test_folders_and_settings_round_trip()
    test_dos_names()
    test_dos_text()
    test_analysis_numbers()
    test_analysis_warnings()
    test_feed_faster_than_machine()
    test_air_only_and_time_text()
    test_library_and_outbox()
    print("\nAll core tests passed.")
