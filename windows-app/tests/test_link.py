"""Tests for link.ftp_server, talking to it the way Windows 95 FTP.EXE
does (active-mode PORT, XMKD/XPWD). Run with: python -m tests.test_link"""

import ftplib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):  # Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from link.ftp_server import LinkServer, resolve_remote  # noqa: E402

fails = 0


def check(cond, name):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails += 1


def make_server():
    root = Path(tempfile.mkdtemp())
    events = []
    srv = LinkServer(root / "Received", root / "To Old PC", bind_ip="127.0.0.1", port=0,
                     allowed_prefix="127.", on_event=events.append)
    (root / "Received").mkdir()
    (root / "To Old PC").mkdir()
    srv.start()
    return srv, root, events


def client(srv):
    f = ftplib.FTP()
    f.connect("127.0.0.1", srv.port, timeout=10)
    f.set_pasv(False)
    f.login("anonymous", "guest")
    f.voidcmd("TYPE I")
    return f


def wait_for(events, kind, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        for e in events:
            if e.kind == kind:
                return e
        time.sleep(0.05)
    return None


def test_resolve_remote():
    check(resolve_remote([], "../../x") == ["x"], "'..' cannot climb out")
    check(resolve_remote(["A"], "B/C") == ["A", "B", "C"], "relative path")
    check(resolve_remote([], "C:\\MPSPRO\\X.TAP") == ["MPSPRO", "X.TAP"], "drive letter dropped")
    for bad in ["A/B:C", "CON", "aux.txt", "X|Y", "TRAIL."]:
        check(resolve_remote([], bad) is None, f"refused {bad!r}")


def test_backup_session():
    srv, root, ev = make_server()
    blobs = {"MPSPRO/A.TAP": os.urandom(1234), "MPSPRO/SUB/B.EXE": os.urandom(70000),
             "MPSPRO/EMPTY.DAT": b"", "MPSPRO/ALL.DAT": bytes(range(256)) * 4}
    man = "".join(f"{k} {len(v)}\r\n" for k, v in blobs.items())
    f = client(srv)
    f.storbinary("STOR MANIFEST.TXT", io.BytesIO(man.encode()))
    f.sendcmd("XMKD MPSPRO")
    for k, v in blobs.items():
        f.storbinary("STOR " + k, io.BytesIO(v))
    check(f.sendcmd("XPWD") == '257 "/"', "XPWD")
    for bad in ["../../ESC.TXT", "CON"]:
        try:
            f.storbinary("STOR " + bad, io.BytesIO(b"x"))
        except ftplib.error_perm:
            pass
    try:
        f.sendcmd("PORT 10,0,0,9,200,1")
        r = "ok"
    except ftplib.error_perm as e:
        r = str(e)[:3]
    check(r == "504", "PORT to another computer refused")
    f.quit()
    e = wait_for(ev, "check")
    check(e is not None and e.data["ok"], "CHECK PASSED event")
    folder = Path(e.data["folder"])
    for k, v in blobs.items():
        check((folder / k).read_bytes() == v, "identical: " + k)
    check(not (root / "ESC.TXT").exists() and (folder / "ESC.TXT").exists(), "'..' upload stays inside")
    with zipfile.ZipFile(e.data["zip"]) as z:
        check(z.read("MPSPRO/SUB/B.EXE") == blobs["MPSPRO/SUB/B.EXE"], "zip has the right content")
    files = [x for x in ev if x.kind == "file"]
    check(len(files) == 5 and files[0].data["total_files"] == 4, "file events with totals")
    srv.stop()


def test_failed_check():
    srv, root, ev = make_server()
    f = client(srv)
    f.storbinary("STOR MANIFEST.TXT", io.BytesIO(b"MPSPRO/A.TAP 10\r\nMPSPRO/B.TAP 5\r\n"))
    f.storbinary("STOR MPSPRO/A.TAP", io.BytesIO(b"short"))
    f.quit()
    e = wait_for(ev, "check")
    check(e is not None and not e.data["ok"], "CHECK FAILED event")
    check(any("MISSING: MPSPRO/B.TAP" in p for p in e.data["problems"]), "missing reported")
    check(any("WRONG SIZE: MPSPRO/A.TAP" in p for p in e.data["problems"]), "wrong size reported")
    check(not list(Path(root / "Received").glob("*.zip")), "no zip on failure")
    srv.stop()


def test_fetch_from_outbox():
    srv, root, ev = make_server()
    box = root / "To Old PC"
    (box / "JOB1.TAP").write_bytes(b"G00 Z0.25\nG01 X0.5 F10\nM02\n")
    blob = os.urandom(3000)
    (box / "DATA.BIN").write_bytes(blob)
    (root / "SECRET.TXT").write_bytes(b"no")
    f = client(srv)
    got = io.BytesIO()
    f.retrbinary("RETR job1.tap", got.write)
    check(got.getvalue() == b"G00 Z0.25\r\nG01 X0.5 F10\r\nM02\r\n", "job sent with CRLF")
    got = io.BytesIO()
    f.retrbinary("RETR DATA.BIN", got.write)
    check(got.getvalue() == blob, "other file byte-for-byte")
    check(sorted(f.nlst()) == ["DATA.BIN", "JOB1.TAP"], "NLST")
    rows = []
    f.retrlines("LIST", rows.append)
    check(len(rows) == 2 and rows[1].endswith("JOB1.TAP") and " 30 " in rows[1], f"LIST {rows}")
    for bad in ["SECRET.TXT", "../SECRET.TXT", "C:\\SECRET.TXT", "NOPE.TAP", ".."]:
        try:
            f.retrbinary("RETR " + bad, io.BytesIO().write)
            r = "sent"
        except ftplib.error_perm as e:
            r = str(e)[:3]
        check(r == "550", f"refused {bad!r}")
    f.quit()
    time.sleep(0.3)
    check(any(e.kind == "sent" and e.data["name"] == "JOB1.TAP" for e in ev), "sent event")
    check(not list((root / "Received").iterdir()), "fetch-only session makes no backup folder")
    srv.stop()


def test_helper_get_bat():
    from link.old_pc_files import helper_files
    root = Path(tempfile.mkdtemp())
    (root / "R").mkdir(); (root / "O").mkdir()
    ev = []
    srv = LinkServer(root / "R", root / "O", bind_ip="127.0.0.1", port=0, allowed_prefix="127.",
                     on_event=ev.append, helper_files=helper_files())
    srv.start()
    f = client(srv)
    got = io.BytesIO()
    f.retrbinary("RETR get.bat", got.write)
    data = got.getvalue()
    check(data.startswith(b"@echo off\r\n") and b"get %1" in data and b"\n" not in data.replace(b"\r\n", b""),
          "GET.BAT served, CRLF only")
    check(f.nlst() == [], "helper not listed")
    f.quit()
    srv.stop()


def test_refuses_other_networks():
    root = Path(tempfile.mkdtemp())
    ev = []
    srv = LinkServer(root, root, bind_ip="127.0.0.1", port=0, allowed_prefix="192.168.50.",
                     on_event=ev.append)
    srv.start()
    try:
        f = ftplib.FTP()
        f.connect("127.0.0.1", srv.port, timeout=5)
        r = "connected"
    except (EOFError, OSError, ftplib.Error):
        r = "refused"
    time.sleep(0.3)
    check(any(e.kind == "error" and "Refused" in e.text for e in ev), f"other address refused ({r})")
    srv.stop()
    check(not srv.running, "server stops")


def test_real_ftp_client_send_and_get():
    # The Linux/BSD ftp client takes a port; Windows' ftp.exe doesn't (it is
    # tested for real against the old PC instead).
    if sys.platform.startswith("win") or not shutil.which("ftp"):
        print("SKIP real ftp client (needs the Linux/BSD ftp command)")
        return
    srv, root, ev = make_server()
    src = Path(tempfile.mkdtemp())
    (src / "A.TAP").write_bytes(b"G0 X1\r\n")
    (src / "B.DAT").write_bytes(os.urandom(5000))
    (src / "MANIFEST.TXT").write_bytes(b"MPSPRO/A.TAP 7\r\nMPSPRO/B.DAT 5000\r\n")
    (root / "To Old PC" / "SQUARE1.TAP").write_bytes(b"G00 Z0.25\nM02\n")
    script = (f"user anonymous guest\nbinary\nput {src}/MANIFEST.TXT MANIFEST.TXT\nmkdir MPSPRO\n"
              f"put {src}/A.TAP MPSPRO/A.TAP\nput {src}/B.DAT MPSPRO/B.DAT\nget SQUARE1.TAP\nquit\n")
    r = subprocess.run(["ftp", "-n", "-v", "127.0.0.1", str(srv.port)], input=script, text=True,
                       capture_output=True, cwd=src, timeout=60)
    e = wait_for(ev, "check")
    check(e is not None and e.data["ok"], "real ftp client: CHECK PASSED")
    check((src / "SQUARE1.TAP").read_bytes() == b"G00 Z0.25\r\nM02\r\n", "real ftp client: get works")
    if fails:
        print(r.stdout[-800:])
    srv.stop()


if __name__ == "__main__":
    test_resolve_remote()
    test_backup_session()
    test_failed_check()
    test_fetch_from_outbox()
    test_helper_get_bat()
    test_refuses_other_networks()
    test_real_ftp_client_send_and_get()
    print("\nALL PASS" if fails == 0 else f"\n{fails} FAILED")
    sys.exit(1 if fails else 0)
