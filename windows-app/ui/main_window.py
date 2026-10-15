"""Main window: header, the Jobs / Make G-code / Machine Link / Help tabs,
status bar."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from app_config import load_settings, tools_path
from cam.tools import ToolLibrary
from library import JOB_EXTS
from ui.help_page import HelpPage
from ui.icon import icon_pixmap
from ui.jobs_page import JobsPage
from ui.link_page import LinkPage
from ui.make_page import MakePage
from ui.settings_dialog import SettingsDialog
from ui.tools_dialog import ToolsDialog

VERSION = "1.1"


class MainWindow(QMainWindow):
    def __init__(self, start_link: bool = True):
        super().__init__()
        self.setWindowTitle("A-Tech CNC")
        self.resize(1360, 860)
        self.setMinimumSize(1000, 640)
        self.setAcceptDrops(True)
        self.settings = load_settings()

        central = QWidget()
        central.setObjectName("Page")
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        header = QWidget()
        header.setObjectName("Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 8, 12, 8)
        logo = QLabel()
        logo.setPixmap(icon_pixmap(40))
        h.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("A-Tech CNC")
        t.setObjectName("AppTitle")
        sub = QLabel("Make, preview and send G-code for the MicroMill (MPS2003)")
        sub.setObjectName("AppSub")
        titles.addWidget(t)
        titles.addWidget(sub)
        h.addLayout(titles)
        h.addSpacing(24)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        h.addStretch(1)
        gear = QPushButton("⚙  Settings")
        gear.setObjectName("Flat")
        gear.clicked.connect(self._settings)
        helpb = QPushButton("?  Help")
        helpb.setObjectName("Flat")
        helpb.clicked.connect(lambda: self.tabs.setCurrentWidget(self.help))
        bits = QPushButton("⛏  Bits")
        bits.setObjectName("Flat")
        bits.setToolTip("The tool list: end mills, drills and V-bits")
        bits.clicked.connect(self._bits)
        h.addWidget(helpb)
        h.addWidget(bits)
        h.addWidget(gear)
        v.addWidget(header)

        self.tools = ToolLibrary(tools_path())
        if not tools_path().exists():
            self.tools.save()
        self.jobs = JobsPage(self.settings)
        self.make = MakePage(self.settings, self.tools)
        self.link = LinkPage(self.settings)
        self.help = HelpPage()
        self.tabs.addTab(self.jobs, "Jobs")
        self.tabs.addTab(self.make, "Make G-code")
        self.tabs.addTab(self.link, "Machine Link")
        self.tabs.addTab(self.help, "Help")
        v.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.link_status = QLabel("")
        self.statusBar().addPermanentWidget(self.link_status)

        self.jobs.message.connect(self._msg)
        self.link.message.connect(self._msg)
        self.make.message.connect(self._msg)
        self.make.savedJobs.connect(self._jobs_made)
        self.jobs.sentToOutbox.connect(lambda _n: self.link.refresh_lists())
        self.link.jobsFromBackup.connect(self._jobs_from_backup)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)
        if start_link:
            QTimer.singleShot(300, lambda: self.link.start_link(quiet=True))
        self._update_status()

    def _msg(self, text: str) -> None:
        self.statusBar().showMessage(text, 10000)

    def _update_status(self) -> None:
        on = bool(self.link.server and self.link.server.running)
        pc = getattr(self.link.light_pc, "state", "off") == "ok"
        self.link_status.setText(("● Link on" if on else "○ Link off") +
                                 ("   ·   Old PC connected" if pc else "   ·   Old PC not found") +
                                 f"   ·   v{VERSION}  ")

    def _settings(self) -> None:
        if SettingsDialog(self.settings, self).exec():
            self.jobs.settings_changed()
            self.make.settings_changed()
            self._msg("Settings saved.")

    def _bits(self) -> None:
        if ToolsDialog(self.tools, self.settings, self.make.project.material, self).exec():
            self.make.tools_changed()
            self._msg("Tool list saved.")

    def _jobs_made(self, paths: list) -> None:
        self.jobs.library.refresh_settings()
        self.jobs.reload_library(select=Path(paths[0]) if paths else None)
        self.tabs.setCurrentWidget(self.jobs)

    def _jobs_from_backup(self, paths: list) -> None:
        self.jobs.add_files([Path(p) for p in paths])
        self.tabs.setCurrentWidget(self.jobs)

    # drag and drop job files anywhere on the window
    def dragEnterEvent(self, e) -> None:  # noqa: D102
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:  # noqa: D102
        paths = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        files = []
        for p in paths:
            if p.is_dir():
                files += [f for f in p.iterdir() if f.suffix.lower() in JOB_EXTS]
            else:
                files.append(p)
        if files:
            self.jobs.add_files(files)
            self.tabs.setCurrentWidget(self.jobs)

    def closeEvent(self, e) -> None:  # noqa: D102
        self.link.shutdown()
        super().closeEvent(e)
