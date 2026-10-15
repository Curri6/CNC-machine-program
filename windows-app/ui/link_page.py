"""Machine Link tab: the network cable to the old Windows 95 PC.

Shows whether the laptop has its address (192.168.50.1), whether the old
PC answers, and whether the link (FTP server) is on; lists the jobs
waiting in To Old PC and the backups received; keeps an activity log.
"""

from __future__ import annotations

import datetime as _dt
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from app_config import Settings, app_home, outbox_dir, received_dir
from link import netcheck
from link.ftp_server import LinkEvent, LinkServer, check_backup
from link.old_pc_files import helper_files
from ui import theme
from ui.widgets import Card, StatusLight, dot_icon


class _Bridge(QObject):
    event = Signal(object)
    ping = Signal(bool, bool)   # laptop has IP, old PC answers


class LinkPage(QWidget):
    message = Signal(str)
    backupReceived = Signal(str)   # folder

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self.settings = settings
        self.server: LinkServer | None = None
        self._bridge = _Bridge()
        self._bridge.event.connect(self._on_event)
        self._bridge.ping.connect(self._on_ping)
        self._pinging = False
        self._build()
        self._update_link_light()
        self.refresh_lists()
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(3000)
        self._ping_timer.timeout.connect(self._ping_soon)
        self._ping_timer.start()
        self._ping_soon()

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # status row
        status = Card("Connection")
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        self.light_ip = StatusLight("Laptop address")
        self.light_pc = StatusLight("Old PC")
        self.light_link = StatusLight("Link")
        grid.addWidget(self.light_ip, 0, 0)
        grid.addWidget(self.light_pc, 0, 1)
        grid.addWidget(self.light_link, 0, 2)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        status.body.addLayout(grid)
        row = QHBoxLayout()
        self.link_btn = QPushButton("Turn link on")
        self.link_btn.setObjectName("Primary")
        self.link_btn.clicked.connect(self.toggle_link)
        self.setup_btn = QPushButton("Set up network…")
        self.setup_btn.setToolTip("One time: give this laptop's cable port 192.168.50.1 and allow "
                                  "the old PC through the firewall (asks for administrator rights)")
        self.setup_btn.clicked.connect(lambda: self._run_setup("Set"))
        undo = QPushButton("Undo network setup")
        undo.setObjectName("Flat")
        undo.clicked.connect(lambda: self._run_setup("Undo"))
        folder = QPushButton("Open app folder")
        folder.setObjectName("Flat")
        folder.clicked.connect(lambda: netcheck.open_folder(app_home()))
        row.addWidget(self.link_btn)
        row.addWidget(self.setup_btn)
        row.addStretch(1)
        row.addWidget(folder)
        row.addWidget(undo)
        status.body.addLayout(row)
        root.addWidget(status)

        mid = QHBoxLayout()
        mid.setSpacing(10)
        # waiting for the old PC
        out = Card("Waiting for the old PC")
        self.out_count = QLabel("")
        self.out_count.setObjectName("Muted")
        out.header.addWidget(self.out_count)
        self.out_list = QListWidget()
        out.body.addWidget(self.out_list, 1)
        orow = QHBoxLayout()
        rm = QPushButton("Remove")
        rm.clicked.connect(self._remove_outbox)
        op = QPushButton("Open folder")
        op.setObjectName("Flat")
        op.clicked.connect(lambda: netcheck.open_folder(outbox_dir()))
        orow.addWidget(rm)
        orow.addStretch(1)
        orow.addWidget(op)
        out.body.addLayout(orow)
        mid.addWidget(out, 1)
        # backups
        back = Card("Backups from the old PC")
        self.back_list = QListWidget()
        back.body.addWidget(self.back_list, 1)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        back.body.addWidget(self.progress)
        brow = QHBoxLayout()
        ob = QPushButton("Open backup")
        ob.clicked.connect(self._open_backup)
        addj = QPushButton("Add its jobs to library")
        addj.setToolTip("Copy the .TAP jobs from this backup into the job library")
        addj.clicked.connect(self._backup_jobs_to_library)
        brow.addWidget(ob)
        brow.addWidget(addj)
        brow.addStretch(1)
        back.body.addLayout(brow)
        mid.addWidget(back, 1)
        # what to type
        how = Card("Type this on the old PC")
        how.body.addWidget(self._cmd_row("Fetch a job (after it's sent):", "C:\\NETUP\\GET JOB1.TAP"))
        how.body.addWidget(self._cmd_row("Back up all of C:\\MPSPRO:", "C:\\NETUP\\SEND"))
        how.body.addWidget(self._cmd_row("First time only, to get GET.BAT:",
                                         "ftp 192.168.50.1   (then see Help)"))
        tip = QLabel("Type these in an MS-DOS Prompt window inside Windows 95, "
                     "with the link on here.")
        tip.setObjectName("Muted")
        tip.setWordWrap(True)
        how.body.addWidget(tip)
        how.body.addStretch(1)
        mid.addWidget(how, 1)
        root.addLayout(mid, 1)

        logc = Card("Activity")
        clear = QPushButton("Clear")
        clear.setObjectName("Flat")
        logc.header.addWidget(clear)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        clear.clicked.connect(self.log.clear)
        logc.body.addWidget(self.log)
        root.addWidget(logc, 1)

    def _cmd_row(self, label: str, cmd: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(3)
        l = QLabel(label)
        l.setObjectName("Muted")
        row = QHBoxLayout()
        e = QLineEdit(cmd)
        e.setReadOnly(True)
        e.setStyleSheet("font-family: Consolas, monospace; font-size: 10.5pt;")
        b = QPushButton("Copy")
        b.setObjectName("Flat")
        b.clicked.connect(lambda: QApplication.clipboard().setText(cmd.split("   ")[0]))
        row.addWidget(e, 1)
        row.addWidget(b)
        lay.addWidget(l)
        lay.addLayout(row)
        return w

    # ------------------------------------------------------------ link on/off
    def toggle_link(self) -> None:
        if self.server and self.server.running:
            self.stop_link()
        else:
            self.start_link()

    def start_link(self, quiet: bool = False) -> bool:
        if self.server and self.server.running:
            return True
        self.server = LinkServer(received_dir(), outbox_dir(), bind_ip="0.0.0.0",
                                 port=self.settings.ftp_port,
                                 allowed_prefix=self.settings.old_pc_ip.rsplit(".", 1)[0] + ".",
                                 on_event=self._bridge.event.emit, helper_files=helper_files())
        try:
            self.server.start()
        except OSError as exc:
            self.server = None
            self._log(f"Could not turn the link on: {exc}")
            if not quiet:
                QMessageBox.warning(self, "Link could not start", (
                    f"Port {self.settings.ftp_port} is busy or blocked ({exc}).\n\n"
                    "Is another copy of this app (or receive_files.bat) still open? Close it "
                    "and try again."))
            self._update_link_light()
            return False
        self._update_link_light()
        return True

    def stop_link(self) -> None:
        if self.server:
            self.server.stop()
        self.server = None
        self._update_link_light()

    def _update_link_light(self) -> None:
        on = bool(self.server and self.server.running)
        self.light_link.set("ok" if on else "off",
                            f"On — the old PC can send and fetch (port {self.settings.ftp_port})."
                            if on else "Off — the old PC can't reach the app.")
        self.link_btn.setText("Turn link off" if on else "Turn link on")
        self.link_btn.setObjectName("" if on else "Primary")
        self.link_btn.style().unpolish(self.link_btn)
        self.link_btn.style().polish(self.link_btn)

    # ------------------------------------------------------------ ping
    def _ping_soon(self) -> None:
        if self._pinging:
            return
        self._pinging = True
        ip, pc = self.settings.laptop_ip, self.settings.old_pc_ip

        def work():
            try:
                has = netcheck.has_ip(ip)
                ans = netcheck.ping(pc) if has else False
            finally:
                self._pinging = False
            self._bridge.ping.emit(has, ans)

        threading.Thread(target=work, daemon=True).start()

    def _on_ping(self, has_ip: bool, answers: bool) -> None:
        ip, pc = self.settings.laptop_ip, self.settings.old_pc_ip
        if has_ip:
            self.light_ip.set("ok", f"{ip} is set on this laptop.")
        else:
            self.light_ip.set("bad", f"{ip} is not set. Plug in the cable, then click "
                              "“Set up network…” (one time).")
        old_state = getattr(self.light_pc, "state", "off")
        if answers:
            self.light_pc.set("ok", f"{pc} answers — the cable works.")
        else:
            self.light_pc.set("off", f"{pc} not answering. Is the old PC on, in Windows, "
                              "with the cable plugged in?")
        if answers and old_state != "ok":
            self._log(f"Old PC ({pc}) answers ping.")
        elif not answers and old_state == "ok":
            self._log(f"Old PC ({pc}) stopped answering.")

    def _run_setup(self, action: str) -> None:
        if action == "Set":
            text = ("Windows will ask for administrator rights, then a blue window sets this "
                    f"laptop's network-cable port to {self.settings.laptop_ip} and lets the old "
                    "PC through the firewall (FTP and ping from 192.168.50.x only).\n\n"
                    "Use “Undo network setup” later to put it back. Continue?")
        else:
            text = "Put the laptop's address and firewall back the way they were before Set up?"
        if QMessageBox.question(self, "Network setup", text) != QMessageBox.StandardButton.Yes:
            return
        if not netcheck.run_network_setup(action, self.settings.laptop_ip, self.settings.ftp_port,
                                          app_home()):
            QMessageBox.information(self, "Network setup", (
                "The setup window didn't start (Windows only, and you need to click Yes "
                "when Windows asks)."))
            return
        self._log(f"Network {action.lower()} started in its own window.")
        QTimer.singleShot(4000, self._ping_soon)

    # ------------------------------------------------------------ events
    def _log(self, text: str) -> None:
        t = _dt.datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"{t}  {text}")

    def _on_event(self, e: LinkEvent) -> None:
        self._log(e.text)
        d = e.data or {}
        if e.kind == "status":
            self._update_link_light()
        elif e.kind == "manifest":
            self.progress.setVisible(True)
            self.progress.setRange(0, max(d.get("total", 0), 1))
            self.progress.setValue(0)
            self.progress.setFormat("Receiving backup… %p%")
        elif e.kind == "file" and self.progress.isVisible():
            self.progress.setValue(min(d.get("got_bytes", 0), self.progress.maximum()))
        elif e.kind == "sent":
            self.message.emit(e.text)
            self.refresh_lists()
        elif e.kind == "check":
            self.progress.setVisible(False)
            for p in d.get("problems", [])[:20]:
                self._log("   " + p)
            if d.get("ok"):
                self._log(f"   Zipped: {d.get('zip')}")
            self.refresh_lists()
            self.message.emit(e.text)
            if d.get("folder"):
                self.backupReceived.emit(d["folder"])
        elif e.kind == "session_end":
            self.refresh_lists()

    # ------------------------------------------------------------ lists
    def refresh_lists(self) -> None:
        self.out_list.clear()
        files = sorted((p for p in outbox_dir().iterdir() if p.is_file()), key=lambda p: p.name)
        for p in files:
            it = QListWidgetItem(f"{p.name}\n{p.stat().st_size:,} bytes  ·  on the old PC: "
                                 f"C:\\NETUP\\GET {p.name}")
            it.setData(Qt.ItemDataRole.UserRole, str(p))
            it.setIcon(dot_icon(theme.ACCENT))
            self.out_list.addItem(it)
        self.out_count.setText(f"{len(files)} file{'s' if len(files) != 1 else ''}")
        if not files:
            it = QListWidgetItem("Nothing waiting. Use “Send to old PC” on the Jobs tab.")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.out_list.addItem(it)

        self.back_list.clear()
        folders = sorted((p for p in received_dir().glob("received_*") if p.is_dir()),
                         key=lambda p: p.name, reverse=True)
        for f in folders:
            ok, problems, manifest = check_backup(f)
            stamp = f.name.replace("received_", "")
            try:
                when = _dt.datetime.strptime(stamp[:15], "%Y%m%d_%H%M%S").strftime("%b %d %Y, %H:%M")
            except ValueError:
                when = stamp
            if ok:
                text = f"{when}\n✓ {len(manifest)} files, all checked"
                color = theme.OK
            elif manifest:
                text = f"{when}\n⚠ {len(problems)} problem(s) — send again"
                color = theme.WARN
            else:
                n = sum(1 for p in f.rglob("*") if p.is_file())
                text = f"{when}\n{n} file(s), no manifest"
                color = "#9ca3af"
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, str(f))
            it.setIcon(dot_icon(color))
            self.back_list.addItem(it)
        if not folders:
            it = QListWidgetItem("No backups yet. On the old PC: C:\\NETUP\\SEND")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.back_list.addItem(it)

    def _selected(self, lst: QListWidget) -> Path | None:
        it = lst.currentItem()
        v = it.data(Qt.ItemDataRole.UserRole) if it else None
        return Path(v) if v else None

    def _remove_outbox(self) -> None:
        p = self._selected(self.out_list)
        if p and QMessageBox.question(self, "Remove", f"Stop offering {p.name} to the old PC?\n"
                                      "(Deletes it from the To Old PC folder only.)") \
                == QMessageBox.StandardButton.Yes:
            p.unlink(missing_ok=True)
            self.refresh_lists()

    def _open_backup(self) -> None:
        p = self._selected(self.back_list)
        if p:
            netcheck.open_folder(p)

    jobsFromBackup = Signal(list)

    def _backup_jobs_to_library(self) -> None:
        p = self._selected(self.back_list)
        if not p:
            QMessageBox.information(self, "Backups", "Pick a backup first.")
            return
        jobs = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in (".tap", ".nc")]
        if not jobs:
            QMessageBox.information(self, "Backups", "That backup has no .TAP jobs.")
            return
        self.jobsFromBackup.emit(jobs)

    def shutdown(self) -> None:
        self._ping_timer.stop()
        self.stop_link()
