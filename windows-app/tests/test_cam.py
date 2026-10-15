"""Tests for the G-code maker (cam/): bits, speeds and feeds, every kind
of step, and that what comes out is G-code MPS2003 understands.
Run with: python -m tests.test_cam"""

import math
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CNC_APP_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):  # Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PySide6.QtGui import QGuiApplication  # noqa: E402

APP = QGuiApplication(sys.argv[:1])

from app_config import Settings  # noqa: E402
from cam import geometry as geo  # noqa: E402
from cam.operations import ERROR, WARN, Step  # noqa: E402
from cam.program import Project, generate  # noqa: E402
from cam.tools import Overrides, Tool, ToolLibrary, cutting_data, inch_text, parse_length  # noqa: E402
from gcode.analysis import analyze  # noqa: E402
from gcode.parser import parse_gcode  # noqa: E402

RPMS = [1100, 1800, 2700, 4000, 6000, 10000]
S = Settings()


def lib(*tools: Tool) -> ToolLibrary:
    t = ToolLibrary(None)
    if tools:
        t.tools = list(tools)
    return t


def run(steps, tools=None, **proj):
    p = Project(name=proj.pop("name", "Test"), **proj)
    p.steps = steps
    return generate(p, tools or lib(), proj.get("settings", S))


def errors(out, i=0):
    return [m.text for m in out.messages if m.step == i and m.level == ERROR]


def warns(out, i=0):
    return [m.text for m in out.messages if m.step == i and m.level == WARN]


def cut_points(text):
    """(x, y, z) at the end of every G01 move below the top."""
    r = parse_gcode(text)
    return [s.points[-1] for s in r.segments if not s.rapid and s.points[-1][2] < -1e-9]


def check_mps2003(text):
    r = parse_gcode(text)
    bad = sorted({c for ln in r.lines for c in ln.unsupported})
    assert not bad, bad
    assert "G20" in text and "G90" in text and text.rstrip().endswith("M02")
    for ln in text.splitlines():
        assert ln.startswith(("G00", "G01", "(", "M00", "M02", "G20", "G90")), ln
        if ln.startswith("("):
            assert ln.endswith(")") and ln.count("(") == 1, ln
    return r


# ------------------------------------------------------------------ bits
def test_sizes():
    assert parse_length("1/8") == 0.125
    assert parse_length("1 1/4") == 1.25
    assert parse_length('1/4"') == 0.25
    assert abs(parse_length("3mm") - 3 / 25.4) < 1e-12
    assert parse_length(".0625 in") == 0.0625
    for bad in ("abc", "1/0", "-1"):
        try:
            parse_length(bad)
            assert False, bad
        except ValueError:
            pass
    assert inch_text(0.125) == "1/8 in" and inch_text(1.5) == "1 1/2 in"
    assert inch_text(1.0) == "1 in" and inch_text(0.118) == "0.118 in"
    print("test_sizes: PASS")


def test_speeds_and_feeds():
    flat = Tool(1, "flat", 0.125, 2, 0.5)
    c = cutting_data(flat, "acrylic", 13.5, RPMS)
    # the mill tops out at 13.5 in/min, so the spindle is slowed to keep a real chip
    assert c.feed == 13.5 and c.rpm == 4000, c
    assert 0.0012 < c.chip < 0.0025
    assert c.depth_per_pass == 0.0625 and abs(c.stepover - 0.05) < 1e-9
    assert c.plunge < c.feed
    al = cutting_data(flat, "aluminum", 13.5, RPMS)
    assert al.feed < c.feed and al.depth_per_pass < c.depth_per_pass
    small = cutting_data(Tool(2, "flat", 1 / 32, 2, 0.09), "acrylic", 13.5, RPMS)
    assert small.depth_per_pass < c.depth_per_pass and small.rpm >= c.rpm
    drill = cutting_data(Tool(3, "drill", 0.125, 2, 0.75), "acrylic", 13.5, RPMS)
    assert drill.feed <= 13.5 * 0.6 + 1e-9 and drill.plunge == drill.feed and drill.peck == 0.125
    ball = cutting_data(Tool(4, "ball", 0.125, 2, 0.4), "acrylic", 13.5, RPMS)
    assert ball.stepover < c.stepover
    v = Tool(5, "vbit", 0.25, 2, 0.25, angle=60, tip=0.0)
    assert abs(v.width_at(0.1) - 2 * 0.1 * math.tan(math.radians(30))) < 1e-9
    assert abs(v.max_vbit_depth() - 0.125 / math.tan(math.radians(30))) < 1e-9
    # cutting length limits depth per pass
    stub = cutting_data(Tool(6, "flat", 0.25, 2, 0.05), "wax", 13.5, RPMS)
    assert stub.depth_per_pass == 0.05
    # one-speed spindle
    one = cutting_data(flat, "acrylic", 13.5, [10000])
    assert one.rpm == 10000 and any("thin" in n for n in one.notes)
    # your own numbers win (but not past the machine's top speed)
    mine = cutting_data(flat, "acrylic", 13.5, RPMS, overrides=Overrides(rpm=2500, feed=40,
                                                                         depth_per_pass=0.02))
    assert mine.rpm == 2500 and mine.feed == 13.5 and mine.depth_per_pass == 0.02
    print("test_speeds_and_feeds: PASS")


def test_tool_library_file():
    path = Path(tempfile.mkdtemp()) / "tools.json"
    t = ToolLibrary(path)
    assert [x.number for x in t.tools] == [1, 2, 3, 4, 5]
    t.put(Tool(9, "drill", 0.25, 2, 1.0))
    try:
        t.put(Tool(9, "flat", 0.1))
        assert False
    except ValueError:
        pass
    t.save()
    u = ToolLibrary(path)
    assert u.get(9).kind == "drill" and u.get(9).diameter == 0.25
    path.write_text("not json")
    assert len(ToolLibrary(path).tools) == 5          # broken file -> the starting set
    print("test_tool_library_file: PASS")


# ------------------------------------------------------------------ steps
def test_rect_pocket_stays_inside():
    out = run([Step("rect", 1, {"mode": "pocket", "x": 1, "y": 0.5, "w": 1.5, "h": 1, "depth": 0.1})])
    assert out.ok, out.messages
    text = out.files[0].text
    r = check_mps2003(text)
    pts = cut_points(text)
    R = 0.0625
    xs, ys, zs = [p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts]
    assert min(xs) >= 1 + R - 1e-6 and max(xs) <= 2.5 - R + 1e-6
    assert min(ys) >= 0.5 + R - 1e-6 and max(ys) <= 1.5 - R + 1e-6
    assert abs(min(xs) - (1 + R)) < 1e-4 and abs(max(ys) - (1.5 - R)) < 1e-4   # reaches the walls
    assert sorted(set(round(z, 4) for z in zs)) == [-0.1, -0.05]               # 2 passes of 0.05
    st = analyze(r, S, "X.TAP")
    assert st.warning_count == 0, [c.text for c in st.checks]
    print("test_rect_pocket_stays_inside: PASS")


def test_outside_cut_size_and_direction():
    out = run([Step("rect", 1, {"mode": "outside", "x": 0.5, "y": 0.5, "w": 2, "h": 1,
                                "depth": 0.05})])
    pts = cut_points(out.files[0].text)
    R = 0.0625
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    # the bit runs outside the line by its radius, so the part comes out 2 x 1
    assert abs(min(xs) - (0.5 - R)) < 1e-4 and abs(max(xs) - (2.5 + R)) < 1e-4
    assert abs(min(ys) - (0.5 - R)) < 1e-4 and abs(max(ys) - (1.5 + R)) < 1e-4
    loop = [(p[0], p[1]) for p in pts]
    assert geo.signed_area(loop) > 0          # counter-clockwise = conventional milling outside
    climb = Settings(climb_milling=True)
    p = Project(name="c")
    p.steps = [Step("rect", 1, {"mode": "outside", "x": 0.5, "y": 0.5, "w": 2, "h": 1, "depth": 0.05})]
    loop2 = [(q[0], q[1]) for q in cut_points(generate(p, lib(), climb).files[0].text)]
    assert geo.signed_area(loop2) < 0
    # a hole cut from inside: bit inside the line, clockwise
    out = run([Step("circle", 1, {"mode": "inside", "cx": 2, "cy": 1, "d": 1, "depth": 0.05})])
    pts = cut_points(out.files[0].text)
    rs = [math.dist((p[0], p[1]), (2, 1)) for p in pts]
    assert all(abs(r - 0.4375) < 0.001 for r in rs), (min(rs), max(rs))
    assert geo.signed_area([(p[0], p[1]) for p in pts]) < 0
    print("test_outside_cut_size_and_direction: PASS")


def test_through_cut_with_tabs():
    out = run([Step("circle", 1, {"mode": "outside", "cx": 1.5, "cy": 1.5, "d": 2,
                                  "through": True})], stock_t=0.25)
    assert out.ok
    text = out.files[0].text
    zs = [p[2] for p in cut_points(text)]
    assert abs(min(zs) - (-0.26)) < 1e-6                      # through + 0.01
    tab_top = -0.25 + 0.03
    assert any(abs(z - tab_top) < 1e-6 for z in zs), "tabs on the last passes"
    assert any("tabs" in m.text for m in out.messages)
    # no tabs when switched off
    out = run([Step("circle", 1, {"mode": "outside", "cx": 1.5, "cy": 1.5, "d": 2,
                                  "through": True, "tabs": False})], stock_t=0.25)
    zs = [p[2] for p in cut_points(out.files[0].text)]
    assert not any(abs(z - tab_top) < 1e-6 for z in zs)
    print("test_through_cut_with_tabs: PASS")


def test_holes_know_the_bit():
    drill = Tool(4, "drill", 0.125, 2, 0.75, angle=118)
    flat = Tool(1, "flat", 0.125, 2, 0.5)
    v = Tool(5, "vbit", 0.25, 2, 0.25, angle=90)
    tools = lib(flat, drill, v)
    pts = {"points": "0.5, 0.5\n1.5, 0.5\n1.0, 1.0", "depth": 0.2}
    # a drill pecks straight down at each point
    out = run([Step("holes", 4, dict(pts))], tools)
    assert out.ok
    r = check_mps2003(out.files[0].text)
    xy_moves = [s for s in r.segments if not s.rapid and
                (abs(s.points[0][0] - s.points[-1][0]) > 1e-9 or abs(s.points[0][1] - s.points[-1][1]) > 1e-9)]
    assert not xy_moves, "a drill never moves sideways while cutting"
    deep = [s.points[-1] for s in r.segments if not s.rapid and abs(s.points[-1][2] + 0.2) < 1e-6]
    assert len(deep) == 3
    # through holes: the drill's point has to clear the bottom too
    out = run([Step("holes", 4, {"points": "1, 1", "through": True})], tools, stock_t=0.25)
    zmin = min(p[2] for p in cut_points(out.files[0].text))
    assert abs(zmin - (-0.26 - 0.0625 / math.tan(math.radians(59)))) < 1e-4, zmin
    # hole bigger than the drill: refused, with what to do instead
    out = run([Step("holes", 4, dict(pts, hole_d=0.25))], tools)
    e = errors(out)
    assert not out.ok and e and "1/4 in drill" in e[0] and "end mill" in e[0], e
    # the same holes with an end mill: milled round to the right size
    out = run([Step("holes", 1, dict(pts, hole_d=0.25))], tools)
    assert out.ok, out.messages
    p3 = cut_points(out.files[0].text)
    near = [math.dist((q[0], q[1]), (0.5, 0.5)) for q in p3 if math.dist((q[0], q[1]), (0.5, 0.5)) < 0.3]
    assert abs(max(near) - (0.125 - 0.0625)) < 0.001, max(near)
    # an end mill too big for the holes
    out = run([Step("holes", 1, dict(pts, hole_d=0.0625))], tools)
    assert errors(out)
    # a V-bit only spots the centres
    out = run([Step("holes", 5, dict(pts, depth=0.03))], tools)
    assert out.ok and any("centres" in m.text for m in out.messages)
    out = run([Step("holes", 5, {"points": "1,1", "through": True})], tools)
    assert errors(out)
    # patterns
    grid = Step("holes", 4, {"pattern": "grid", "gx": 0.5, "gy": 0.5, "nx": 4, "ny": 3,
                             "dx": 0.25, "dy": 0.25, "depth": 0.1})
    circle = Step("holes", 4, {"pattern": "circle", "cx": 1.5, "cy": 1.5, "bolt": 1.0, "count": 6,
                               "angle": 0, "depth": 0.1})
    for st, n in ((grid, 12), (circle, 6)):
        r = parse_gcode(run([st], tools, stock_x=4, stock_y=3).files[0].text)
        bottoms = [s.points[-1] for s in r.segments if not s.rapid and abs(s.points[-1][2] + 0.1) < 1e-6]
        assert len(bottoms) == n, (st.params["pattern"], len(bottoms))
    print("test_holes_know_the_bit: PASS")


def test_wrong_bit_for_the_job():
    drill = Tool(4, "drill", 0.125, 2, 0.75)
    v = Tool(5, "vbit", 0.25, 2, 0.25, angle=60)
    flat = Tool(1, "flat", 0.25, 2, 0.75)
    tools = lib(flat, drill, v)
    assert "straight down" in errors(run([Step("rect", 4, {"mode": "pocket"})], tools))[0]
    assert "engrave on the line" in errors(run([Step("rect", 5, {"mode": "pocket"})], tools))[0]
    assert run([Step("rect", 5, {"mode": "on", "depth": 0.02})], tools).ok
    assert errors(run([Step("text", 4, {})], tools))
    assert errors(run([Step("lines", 4, {})], tools))
    assert errors(run([Step("face", 5, {})], tools))
    # pocket narrower than the bit
    e = errors(run([Step("rect", 1, {"mode": "pocket", "w": 0.2, "h": 1})], tools))
    assert e and "narrower" in e[0]
    # deeper than the bit's cutting part
    e = errors(run([Step("rect", 1, {"mode": "pocket", "depth": 0.9})], tools, stock_t=1.0))
    assert e and "cutting part" in e[0]
    # V-bit deeper than its cone
    e = errors(run([Step("lines", 5, {"depth": 0.3})], tools))
    assert e and "cone" in e[0]
    # missing bit
    out = run([Step("rect", 7, {})], tools)
    assert not out.ok and "isn't in the tool list" in errors(out)[0]
    # outside the stock / deeper than the stock -> warnings, still makes code
    out = run([Step("rect", 1, {"mode": "pocket", "x": 3, "w": 2, "depth": 0.05})], tools)
    assert out.ok and any("outside the stock" in w for w in warns(out))
    out = run([Step("rect", 1, {"mode": "pocket", "depth": 0.3})], tools, stock_t=0.25)
    assert any("deeper than the stock" in w for w in warns(out))
    print("test_wrong_bit_for_the_job: PASS")


def test_text_lines_face():
    v = Tool(5, "vbit", 0.25, 2, 0.25, angle=60, tip=0.005)
    flat = Tool(1, "flat", 0.125, 2, 0.5)
    tools = lib(flat, v)
    out = run([Step("text", 5, {"text": "HI", "height": 0.5, "x": 1, "y": 1, "depth": 0.02})], tools)
    assert out.ok, out.messages
    pts = cut_points(out.files[0].text)
    ys = [p[1] for p in pts]
    assert abs(min(ys) - 1.0) < 0.01 and abs(max(ys) - 1.5) < 0.01, (min(ys), max(ys))
    assert min(p[0] for p in pts) >= 0.99
    # letters too small for the bit
    out = run([Step("text", 1, {"text": "HI", "height": 0.25, "depth": 0.02})], tools)
    assert any("run together" in w for w in warns(out))
    # lines go back and forth, no trip up between passes
    out = run([Step("lines", 1, {"points": "0.5,0.5\n2.5,0.5", "depth": 0.1})], tools)
    r = parse_gcode(out.files[0].text)
    ups = [s for s in r.segments if s.rapid and s.points[-1][2] > 0 and s.points[0][2] < 0]
    assert len(ups) == 1, len(ups)        # only the final lift
    # facing covers the whole top, starting and ending off the stock
    out = run([Step("face", 1, {"depth": 0.01, "margin": 0.05})], tools, stock_x=2, stock_y=1)
    pts = cut_points(out.files[0].text)
    assert min(p[0] for p in pts) < -0.05 and max(p[0] for p in pts) > 2.05
    ys = sorted({round(p[1], 4) for p in pts})
    assert ys[0] <= 0.0 and ys[-1] >= 1.0 and max(b - a for a, b in zip(ys, ys[1:])) <= 0.0502
    print("test_text_lines_face: PASS")


def test_project_files_one_per_bit():
    tools = lib()
    p = Project(name="Name plate", stock_x=4, stock_y=1.5, stock_t=0.25)
    p.steps = [Step("text", 5, {"text": "A", "x": 2, "y": 0.5, "align": "center", "depth": 0.02}),
               Step("holes", 4, {"points": "0.3,0.75\n3.7,0.75", "through": True}),
               Step("rect", 1, {"mode": "outside", "x": 0.1, "y": 0.1, "w": 3.8, "h": 1.3,
                                "through": True}),
               Step("rect", 1, {"mode": "pocket", "depth": 0.02}, enabled=False)]
    out = generate(p, tools, S)
    assert out.ok, [m.text for m in out.messages]
    assert [f.name for f in out.files] == ["Name plate T5.tap", "Name plate T4.tap", "Name plate T1.tap"]
    assert [f.steps for f in out.files] == [[0], [1], [2]]           # step 4 is switched off
    for f in out.files:
        r = check_mps2003(f.text)
        assert f"(BIT T{f.tool.number}:" in f.text and "M00" in f.text
        st = analyze(r, S, "A.TAP")
        assert st.warning_count == 0, (f.name, [c.text for c in st.checks])
        assert st.z_range[1] <= S.safe_z_in + 1e-9
    assert any("one per bit" in m.text for m in out.messages)
    # zero at the centre shifts every move
    p.origin = "center"
    out2 = generate(p, tools, S)
    a = parse_gcode(out.files[2].text).segments
    b = parse_gcode(out2.files[2].text).segments
    pa = [q for s in a if not s.rapid for q in s.points]
    pb = [q for s in b if not s.rapid for q in s.points]
    assert abs(min(x for x, _, _ in pa) - 2 - min(x for x, _, _ in pb)) < 1e-6
    assert abs(min(y for _, y, _ in pa) - 0.75 - min(y for _, y, _ in pb)) < 1e-6
    # save and load the project
    path = Path(tempfile.mkdtemp()) / "p.cncproj"
    p.save(path)
    q = Project.load(path)
    assert q.name == p.name and len(q.steps) == 4 and q.steps[3].enabled is False
    assert q.steps[1].params["points"] == "0.3,0.75\n3.7,0.75"
    assert generate(q, tools, S).files[0].text == out2.files[0].text
    print("test_project_files_one_per_bit: PASS")


def test_builder_text():
    from cam.builder import comment_text, num
    assert comment_text("Nameplate (v2): 1/8° bit × 2") == "NAMEPLATE V2: 1/8 DEG BIT X 2"
    assert num(-0.00001) == "0.0000" and num(1.23456) == "1.2346"
    print("test_builder_text: PASS")


if __name__ == "__main__":
    test_sizes()
    test_speeds_and_feeds()
    test_tool_library_file()
    test_rect_pocket_stays_inside()
    test_outside_cut_size_and_direction()
    test_through_cut_with_tabs()
    test_holes_know_the_bit()
    test_wrong_bit_for_the_job()
    test_text_lines_face()
    test_project_files_one_per_bit()
    test_builder_text()
    print("\nAll G-code maker tests passed.")
