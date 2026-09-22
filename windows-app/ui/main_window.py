"""Main window: open a G-code file, see warnings for anything MPS2003
won't understand, preview the toolpath, and send it to the old PC.

A job is never sent automatically and the receiver never auto-runs it
-- someone always has to be physically at the old machine to load and
start it in MPS2003. See JOURNAL.md's standing safety requirement.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gcode.parser import ParseResult, parse_gcode
from network.sender import DEFAULT_PORT, send_job
from ui.toolpath_view import ToolpathView


class _SendWorker(QThread):
    finished_send = Signal(bool, str)

    def __init__(self, host: str, port: int, filename: str, data: bytes):
        super().__init__()
        self._host = host
        self._port = port
        self._filename = filename
        self._data = data

    def run(self) -> None:
        result = send_job(self._host, self._filename, self._data, self._port)
        self.finished_send.emit(result.ok, result.message)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A-Tech CNC Job Sender (beta)")
        self.resize(1000, 650)

        self._current_path: Path | None = None
        self._current_result: ParseResult | None = None
        self._send_worker: _SendWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        open_button = QPushButton("Open G-Code File...")
        open_button.clicked.connect(self._on_open_file)

        self._file_label = QLabel("No file loaded.")

        self._warnings_list = QListWidget()
        self._warnings_list.setStyleSheet("color: #b00;")

        self._toolpath_view = ToolpathView()

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("Old PC's IP address, e.g. 192.168.1.50")
        self._port_edit = QLineEdit(str(DEFAULT_PORT))
        self._port_edit.setFixedWidth(70)

        self._send_button = QPushButton("Send to CNC Receiver")
        self._send_button.setEnabled(False)
        self._send_button.clicked.connect(self._on_send)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(open_button)
        left_layout.addWidget(self._file_label)
        left_layout.addWidget(QLabel("Warnings (unsupported commands):"))
        left_layout.addWidget(self._warnings_list, stretch=1)

        network_row = QHBoxLayout()
        network_row.addWidget(QLabel("Host:"))
        network_row.addWidget(self._host_edit, stretch=1)
        network_row.addWidget(QLabel("Port:"))
        network_row.addWidget(self._port_edit)
        left_layout.addLayout(network_row)
        left_layout.addWidget(self._send_button)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self._toolpath_view)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

    def _on_open_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open G-Code File",
            "",
            "G-Code files (*.tap *.nc *.gcode *.txt);;All files (*)",
        )
        if not path_str:
            return
        self._load_file(Path(path_str))

    def _load_file(self, path: Path) -> None:
        try:
            text = path.read_text(errors="replace")
        except OSError as exc:
            QMessageBox.critical(self, "Could not open file", str(exc))
            return

        result = parse_gcode(text)
        self._current_path = path
        self._current_result = result

        self._file_label.setText(
            f"{path.name} — {len(result.lines)} line(s), units: {result.units}"
        )

        self._warnings_list.clear()
        if result.warnings:
            self._warnings_list.addItems(result.warnings)
            self.statusBar().showMessage(
                f"{len(result.warnings)} warning(s) — review before sending.", 8000
            )
        else:
            self._warnings_list.addItem("None — all commands are supported by MPS2003.")
            self.statusBar().showMessage("File looks fully compatible.", 5000)

        self._toolpath_view.show_result(result)
        self._send_button.setEnabled(True)

    def _on_send(self) -> None:
        if self._current_path is None or self._current_result is None:
            return

        host = self._host_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "Missing host", "Enter the old PC's IP address first.")
            return
        try:
            port = int(self._port_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid port", "Port must be a number.")
            return

        if self._current_result.warnings:
            proceed = QMessageBox.question(
                self,
                "Unsupported commands present",
                (
                    f"This file has {len(self._current_result.warnings)} command(s) "
                    "MPS2003 doesn't understand. Sending it anyway may cause the "
                    "machine to behave unexpectedly.\n\nSend anyway?"
                ),
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        data = self._current_path.read_bytes()
        self._send_button.setEnabled(False)
        self.statusBar().showMessage(f"Sending to {host}:{port}...")

        self._send_worker = _SendWorker(host, port, self._current_path.name, data)
        self._send_worker.finished_send.connect(self._on_send_finished)
        self._send_worker.start()

    def _on_send_finished(self, ok: bool, message: str) -> None:
        self._send_button.setEnabled(True)
        self.statusBar().showMessage(message, 8000)
        if ok:
            QMessageBox.information(
                self,
                "Sent",
                message
                + "\n\nRemember: someone still needs to be physically at the "
                "old computer to load and run this job in MPS2003.",
            )
        else:
            QMessageBox.critical(self, "Send failed", message)
