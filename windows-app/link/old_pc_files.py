"""Small helper files the old PC can fetch from the app (not listed in
the To Old PC folder, always available).

GET.BAT: after a one-time fetch into C:\\NETUP, the old PC gets a job
with a single command:  C:\\NETUP\\GET JOB1.TAP
It writes a tiny FTP script and runs Windows 95's own FTP.EXE, which
saves the job into C:\\MPSPRO. Same file as tools/win95/netdisc/kit/GET.BAT.
"""

from __future__ import annotations

from pathlib import Path

_KIT_GET = Path(__file__).resolve().parents[2] / "tools" / "win95" / "netdisc" / "kit" / "GET.BAT"

GET_BAT = (
    "@echo off\r\n"
    "rem GET.BAT - fetch a job from the laptop (A-Tech CNC app) into C:\\MPSPRO.\r\n"
    "rem Use it in an MS-DOS Prompt window inside Windows:  C:\\NETUP\\GET JOB1.TAP\r\n"
    "if \"%1\"==\"\" goto usage\r\n"
    "if not exist C:\\MPSPRO\\NUL goto nompspro\r\n"
    "echo user anonymous x> C:\\NETUP\\GET.FTP\r\n"
    "echo binary>> C:\\NETUP\\GET.FTP\r\n"
    "echo lcd C:\\MPSPRO>> C:\\NETUP\\GET.FTP\r\n"
    "echo get %1>> C:\\NETUP\\GET.FTP\r\n"
    "echo quit>> C:\\NETUP\\GET.FTP\r\n"
    "ftp -n -s:C:\\NETUP\\GET.FTP 192.168.50.1\r\n"
    "echo.\r\n"
    "if exist C:\\MPSPRO\\%1 echo Done: C:\\MPSPRO\\%1 is ready. Load it in MPS2003 (option 2).\r\n"
    "if not exist C:\\MPSPRO\\%1 echo NOT RECEIVED. Is the app's link on? Is the name right?\r\n"
    "goto end\r\n"
    ":usage\r\n"
    "echo Type the job name after GET, for example:  C:\\NETUP\\GET JOB1.TAP\r\n"
    "goto end\r\n"
    ":nompspro\r\n"
    "echo C:\\MPSPRO is missing.\r\n"
    ":end\r\n"
)


def helper_files() -> dict[str, bytes]:
    return {"GET.BAT": GET_BAT.encode("latin-1")}
