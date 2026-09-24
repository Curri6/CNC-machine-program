"""Main window: open a G-code file, see warnings for anything MPS2003
won't understand, preview the toolpath, and export a copy ready to
carry over to the CNC machine.

No networking: the machine lives in a teacher's classroom, so every
job already has to be carried over there in person regardless. Export
just makes it easy to save a copy onto a USB drive or floppy. A job is
never auto-run -- someone always has to be physically at the old
machine to load and start it in MPS2003. See JOURNAL.md's standing
safety requirement.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
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
from ui.toolpath_view import ToolpathView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A-Tech CNC Job Sender (beta)")
        self.resize(1000, 650)

        self._current_path: Path | None = None
        self._current_result: ParseResult | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        open_button = QPushButton("Open G-Code File...")
        open_button.clicked.connect(self._on_open_file)

        self._file_label = QLabel("No file loaded.")

        self._warnings_list = QListWidget()
        self._warnings_list.setStyleSheet("color: #b00;")

        self._toolpath_view = ToolpathView()

        self._export_button = QPushButton("Export Copy for CNC Machine...")
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(self._on_export)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(open_button)
        left_layout.addWidget(self._file_label)
        left_layout.addWidget(QLabel("Warnings (unsupported commands):"))
        left_layout.addWidget(self._warnings_list, stretch=1)
        left_layout.addWidget(
            QLabel(
                "Save a copy onto a USB drive or floppy, then carry it to\n"
                "the CNC machine and load it into C:\\MPSPRO yourself."
            )
        )
        left_layout.addWidget(self._export_button)

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
                f"{len(result.warnings)} warning(s) — review before exporting.", 8000
            )
        else:
            self._warnings_list.addItem("None — all commands are supported by MPS2003.")
            self.statusBar().showMessage("File looks fully compatible.", 5000)

        self._toolpath_view.show_result(result)
        self._export_button.setEnabled(True)

    def _on_export(self) -> None:
        if self._current_path is None or self._current_result is None:
            return

        if self._current_result.warnings:
            proceed = QMessageBox.question(
                self,
                "Unsupported commands present",
                (
                    f"This file has {len(self._current_result.warnings)} command(s) "
                    "MPS2003 doesn't understand. Exporting it anyway may cause the "
                    "machine to behave unexpectedly.\n\nExport anyway?"
                ),
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        dest_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Copy for CNC Machine",
            self._current_path.name,
            "G-Code files (*.tap *.nc *.gcode *.txt);;All files (*)",
        )
        if not dest_str:
            return

        try:
            shutil.copyfile(self._current_path, dest_str)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        self.statusBar().showMessage(f"Exported to {dest_str}", 8000)
        QMessageBox.information(
            self,
            "Exported",
            f"Saved a copy to:\n{dest_str}\n\n"
            "Carry this to the CNC machine and load it into C:\\MPSPRO "
            "yourself — someone still needs to be physically at the "
            "machine to load and start the job in MPS2003.",
        )
