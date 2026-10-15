"""Drive the real app screens without a display (Qt offscreen).
Run with: python -m tests.test_ui"""

import ftplib
import io
import os
import socket
import sys
import tempfile
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["CNC_APP_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):  # Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox  # noqa: E402

POPUPS = []
for _name in ("warning", "information", "critical", "question"):
    setattr(QMessageBox, _name, staticmethod(
        lambda *a, _n=_name, **k: (POPUPS.append((_n, a[2] if len(a) > 2 else "")),
                                   QMessageBox.StandardButton.Yes)[1]))

from app_config import load_settings, outbox_dir, received_dir  # noqa: E402
from ui import theme  # noqa: E402
from ui.jobs_page import SendDialog  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

fails = 0


def check(cond, name):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails += 1


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


app = QApplication(sys.argv[:1])
app.setStyleSheet(theme.STYLE)

# settings: link on a free port, "old PC" = this computer
s = load_settings()
s.ftp_port = free_port()
s.old_pc_ip = "127.0.0.2"
s.save()

src = Path(tempfile.mkdtemp())
(src / "gear job v2.nc").write_bytes(b"(test)\nG0 X0 Y0 Z0.1\nG1 Z-0.1 F5\nG1 X1 F10\nY1\nX0\nY0\nG0 Z0.5\nM02\n")
(src / "deep.tap").write_bytes(b"G1 X1 Y1 Z-0.9 F10\nM03\n")
(src / "picture.png").write_bytes(b"x")

w = MainWindow(start_link=False)
w.show()
jp = w.jobs

jp.add_files([src / "gear job v2.nc", src / "deep.tap", src / "picture.png"])
app.processEvents()
check(jp.list.count() == 2, "two jobs added, picture refused")
check(POPUPS and POPUPS[-1][0] == "warning" and "picture.png" in POPUPS[-1][1], f"popup: {POPUPS}")
names = [jp.list.item(i).text().split("\n")[0] for i in range(jp.list.count())]
check(names == ["deep.tap", "gear job v2.nc"], f"library sorted: {names}")
deep_item = jp.list.item(0).text()
check("⚠ 2" in deep_item, f"deep.tap shows 2 warnings: {deep_item!r}")

jp.list.setCurrentRow(1)
app.processEvents()
check(jp.job is not None and jp.job.path.name == "gear job v2.nc", "job selected")
check(jp.tiles["size"].value.text() == "1.000 × 1.000 in", jp.tiles["size"].value.text())
check(jp.tiles["depth"].value.text() == "Z-0.100 in", jp.tiles["depth"].value.text())
check(jp.tiles["moves"].value.text() == "7", jp.tiles["moves"].value.text())
check(jp.tiles["feed"].value.text() == "F5–10", jp.tiles["feed"].value.text())
check(jp.code.toPlainText().startswith("(test)"), "G-code shown")
check(jp.send_btn.isEnabled() and jp.save_btn.isEnabled(), "send/save enabled")

# playback
jp.slider.setValue(3)
app.processEvents()
check(jp.view._progress == 3 and "Move 3 / 7" in jp.pos_label.text(), jp.pos_label.text())
sels = jp.code.extraSelections()
sel_cursor = sels[0].cursor if sels else None
check(sel_cursor is not None and sel_cursor.blockNumber() + 1 == jp.view.segment_line(2),
      "slider highlights the G-code line")
jp.slider.setValue(jp.slider.maximum())
app.processEvents()
check(jp.view._progress is None, "end of slider = whole job")
for v in ("front", "side", "iso", "top"):
    jp.view.set_view(v)
    app.processEvents()
check(jp.view.grab().width() > 0, "all four views paint")

# picking a line in the preview highlights it in the code
jp._on_line_picked(4)
check(jp.code.textCursor().blockNumber() == 3, "picked line shown in code")

# send dialog name rules
rec = received_dir() / "received_20261014_145353"
rec.mkdir(parents=True)
(rec / "MANIFEST.TXT").write_bytes(b"MPSPRO/GEAR.TAP 17765\r\nMPSPRO/PARAM3.DAT 232\r\n")
dlg = SendDialog("gear job v2.nc", outbox_dir(), received_dir())
ok_btn = dlg.buttons.button(QDialogButtonBox.StandardButton.Ok)
check(dlg.name() == "GEARJOV2.TAP" and ok_btn.isEnabled(), f"suggested name {dlg.name()}")
dlg.edit.setText("my gear.tap")
check(not ok_btn.isEnabled(), "space in name refused")
dlg.edit.setText("PARAM3.DAT")
check(not ok_btn.isEnabled() and ".TAP" in dlg.note.text(), "settings file name blocked")
dlg.edit.setText("gear.tap")
check(ok_btn.isEnabled() and "REPLACE" in dlg.note.text(), "warns the old PC already has GEAR.TAP")
dlg.edit.setText("GEAR2.TAP")
check(ok_btn.isEnabled() and "fine" in dlg.note.text(), "new name fine")

# put the job in the outbox the way Send does, and fetch it over the link
from library import put_in_outbox  # noqa: E402
put_in_outbox(jp.job.path, "GEAR2.TAP", outbox_dir())
w.link.refresh_lists()
check(w.link.out_list.item(0).text().startswith("GEAR2.TAP"), "waiting list shows GEAR2.TAP")
check("1 file" in w.link.out_count.text(), w.link.out_count.text())
check(w.link.back_list.item(0).text().endswith("problem(s) — send again"),
      f"backup with missing files flagged: {w.link.back_list.item(0).text()!r}")

check(w.link.start_link(quiet=True), "link turns on")
app.processEvents()
check(w.link.link_btn.text() == "Turn link off", "button says turn off")
f = ftplib.FTP()
f.connect("127.0.0.1", s.ftp_port, timeout=10)
f.set_pasv(False)
f.login("anonymous", "x")
got = io.BytesIO()
f.retrbinary("RETR GEAR2.TAP", got.write)
gb = io.BytesIO()
f.retrbinary("RETR GET.BAT", gb.write)
f.quit()
deadline = time.time() + 5
while time.time() < deadline and "Sent to old PC: GET.BAT" not in w.link.log.toPlainText():
    app.processEvents()
    time.sleep(0.05)
check(got.getvalue().startswith(b"(test)\r\nG0 X0 Y0 Z0.1\r\n"), "fetched job has CRLF")
check(gb.getvalue().startswith(b"@echo off\r\n"), "GET.BAT served")
log = w.link.log.toPlainText()
check("Sent to old PC: GEAR2.TAP" in log and "Old PC connected" in log, "activity log")
w.link.stop_link()
check(w.link.link_btn.text() == "Turn link on", "link off")

# help renders every section
for i in range(w.help.nav.count()):
    w.help.nav.setCurrentRow(i)
    app.processEvents()
    check(len(w.help.text.toPlainText()) > 200, f"help: {w.help.nav.item(i).text()}")

# --- Make G-code tab
from app_config import jobs_dir, tools_path  # noqa: E402
from ui.tools_dialog import ToolsDialog  # noqa: E402

mk = w.make
tab_names = [w.tabs.tabText(i) for i in range(w.tabs.count())]
check(tab_names == ["Jobs", "Make G-code", "Machine Link", "Help"], f"tabs {tab_names}")
check(tools_path().exists() and len(w.tools.tools) == 5, "starting tool list saved")
check(mk.output.ok and len(mk.output.files) == 3, f"example project makes 3 files: {mk.output.messages}")
check(mk.view.segment_count() > 50 and mk.part.count() == 4, "preview + part picker")
mk.part.setCurrentIndex(2)
app.processEvents()
check(mk.code.toPlainText().startswith("(A-TECH CNC: NAME PLATE)") and "BIT T4" in mk.code.toPlainText(),
      "part picker shows one bit's file")
n0 = len(mk.project.steps)
mk.add_step("holes")
app.processEvents()
new = mk.project.steps[-1]
check(new.tool == 4, f"holes step picks the drill (T{new.tool})")
check(mk.steps.currentRow() == n0 and "Holes" in mk.step_card.title.text(), "new step selected")
mk._form_widgets["hole_d"].setText("1/4")
mk.regenerate()
app.processEvents()
check(not mk.save_btn.isEnabled() and "✗" in mk.steps.item(n0).text(), "too-big hole for the drill: blocked")
check("1/4 in drill" in mk.plan.text(), "plan says what to use instead")
mk.bit.setCurrentIndex(mk.bit.findData(1))          # switch to the 1/8 end mill
app.processEvents()
check(mk.save_btn.isEnabled() and "milled round" in mk.plan.text(), "end mill mills the 1/4 holes")
mk._form_widgets["pattern"].setCurrentIndex(1)     # grid shows the grid fields
app.processEvents()
check(not mk._form_widgets["gx"].isHidden() and mk._form_widgets["points"].isHidden(), "fields follow pattern")
mk._delete()
check(len(mk.project.steps) == n0, "step deleted")
mk.p_name.setText("Plate")
mk.regenerate()
written = mk.save_to_jobs()
app.processEvents()
check([p.name for p in written] == ["Plate T5.tap", "Plate T4.tap", "Plate T1.tap"], f"saved {written}")
check(all((jobs_dir() / p.name).exists() for p in written), "files in the Jobs folder")
check(w.tabs.currentWidget() is w.jobs and jp.job and jp.job.path.name == "Plate T5.tap",
      "Jobs tab shows the new job")
check(SendDialog("Plate T5.tap", outbox_dir(), received_dir()).name() == "PLATET5.TAP", "DOS name keeps T5")
again = mk.save_to_jobs()
check(len(again) == 3 and any(p[0] == "question" for p in POPUPS), "saving again asks before replacing")
check((Path(os.environ["CNC_APP_HOME"]) / "current.cncproj").exists(), "project kept for next time")

dlg = ToolsDialog(w.tools, w.settings, "acrylic", w)
dlg._add(__import__("cam.tools", fromlist=["Tool"]).Tool(0, "drill", 0.25, 2, 1.0, angle=118))
check(dlg.work[-1].number == 6 and "Holes of its own size" in dlg.explain.text(), "tools dialog explains a bit")
dlg.size.setText("abc")
check("Diameter" in dlg.err.text(), "bad size flagged")
dlg.size.setText("1/4")
dlg._save()
check(len(w.tools.tools) == 6 and '"number": 6' in tools_path().read_text(), "new bit saved")

# remove from library deletes only the app's copy
before = jp.list.count()
jp.list.setCurrentRow(0)
check(jp.job.path.name == "deep.tap", jp.job.path.name)
jp.library.remove(jp.job.path)
jp.reload_library()
check(jp.list.count() == before - 1 and (src / "deep.tap").exists(), "remove keeps the original")

w.close()
print("\nALL PASS" if fails == 0 else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
