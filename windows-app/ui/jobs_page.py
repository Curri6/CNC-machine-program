"""Jobs tab: the job library, the preview, the checks, and sending a job
to the old PC (or saving a copy to a USB stick).

A job is never started from here. "Send to old PC" only puts a copy in
the To Old PC folder; a person at the machine fetches it, loads it, and
runs it in MPS2003.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QSlider, QSplitter, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from app_config import Settings, jobs_dir, outbox_dir, received_dir
from gcode.dosfile import is_dos_name
from library import Job, JobLibrary, old_pc_names, put_in_outbox, suggest_old_pc_name
from ui import theme
from ui.toolpath_view import VIEW_NAMES, ToolpathView
from ui.widgets import Card, Tile, check_symbol, dot_icon

JOB_FILTER = "Job files (*.tap *.nc *.gcode *.gco *.ngc *.cnc *.txt);;All files (*)"


class JobsPage(QWidget):
    sentToOutbox = Signal(str)       # file name put in To Old PC
    message = Signal(str)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self.settings = settings
        self.library = JobLibrary(jobs_dir())
        self.job: Job | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        self._build()
        self.reload_library()

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)
        root.addWidget(split, 1)

        # --- left: library
        lib = Card("Job library")
        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        lib.header.addWidget(self.count_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search jobs…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        lib.body.addWidget(self.search)
        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list.currentItemChanged.connect(self._on_pick)
        lib.body.addWidget(self.list, 1)
        row = QHBoxLayout()
        add = QPushButton("＋  Add jobs…")
        add.setObjectName("Primary")
        add.clicked.connect(self._on_add)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._on_remove)
        row.addWidget(add, 1)
        row.addWidget(self.remove_btn)
        lib.body.addLayout(row)
        hint = QLabel("Tip: drag job files from File Explorer onto this window.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        lib.body.addWidget(hint)
        lib.setMinimumWidth(250)

        # --- middle: preview
        prev = Card("")
        top = QHBoxLayout()
        self.job_title = QLabel("No job selected")
        self.job_title.setObjectName("Big")
        top.addWidget(self.job_title, 1)
        self.view_group = QButtonGroup(self)
        for i, (key, label) in enumerate(VIEW_NAMES.items()):
            b = QToolButton()
            b.setText(label.split(" (")[0])
            b.setToolTip(label)
            b.setCheckable(True)
            b.setObjectName("Seg")
            b.setChecked(key == "top")
            b.clicked.connect(lambda _=False, k=key: self.view.set_view(k))
            self.view_group.addButton(b, i)
            top.addWidget(b)
        self.rapids = QCheckBox("Rapids")
        self.rapids.setChecked(True)
        self.rapids.setToolTip("Show G0 rapid (non-cutting) moves as dashed lines")
        self.rapids.toggled.connect(lambda on: self.view.set_show_rapids(on))
        top.addSpacing(8)
        top.addWidget(self.rapids)
        fit = QPushButton("Fit")
        fit.setObjectName("Flat")
        fit.setToolTip("Zoom to the whole job (or double-click the preview)")
        fit.clicked.connect(lambda: self.view.fit())
        top.addWidget(fit)
        prev.body.addLayout(top)
        self.view = ToolpathView()
        self.view.linePicked.connect(self._on_line_picked)
        prev.body.addWidget(self.view, 1)
        play = QHBoxLayout()
        self.play_btn = QPushButton("▶  Play")
        self.play_btn.setToolTip("Watch the tool go through the job, move by move")
        self.play_btn.clicked.connect(self._toggle_play)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self._on_slider)
        self.speed = QComboBox()
        for label, n in (("1×", 1), ("4×", 4), ("16×", 16), ("64×", 64), ("256×", 256)):
            self.speed.addItem(label, n)
        self.speed.setCurrentIndex(2)
        self.speed.setToolTip("Moves per step while playing")
        self.speed.setMinimumWidth(78)
        self.pos_label = QLabel("")
        self.pos_label.setObjectName("Muted")
        self.pos_label.setMinimumWidth(170)
        play.addWidget(self.play_btn)
        play.addWidget(self.slider, 1)
        play.addWidget(self.speed)
        play.addWidget(self.pos_label)
        prev.body.addLayout(play)

        # --- right: summary, checks, code
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        summ = Card("Summary")
        grid = QGridLayout()
        grid.setSpacing(8)
        self.tiles = {k: Tile(lbl) for k, lbl in (
            ("size", "Size (X × Y)"), ("depth", "Deepest cut"), ("time", "Estimated time"),
            ("moves", "Moves"), ("feed", "Feed rates"), ("lines", "Lines"))}
        for i, t in enumerate(self.tiles.values()):
            grid.addWidget(t, i // 2, i % 2)
        summ.body.addLayout(grid)
        rl.addWidget(summ)
        checks = Card("Checks")
        self.checks = QListWidget()
        self.checks.setWordWrap(True)
        self.checks.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.checks.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.checks.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.checks.setMinimumHeight(120)
        checks.body.addWidget(self.checks)
        rl.addWidget(checks, 1)
        code = Card("G-code")
        self.code = QPlainTextEdit()
        self.code.setObjectName("Code")
        self.code.setReadOnly(True)
        self.code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code.cursorPositionChanged.connect(self._on_code_cursor)
        code.body.addWidget(self.code)
        rl.addWidget(code, 2)
        right.setMinimumWidth(300)

        split.addWidget(lib)
        split.addWidget(prev)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([275, 700, 340])

        # --- action bar
        bar = QHBoxLayout()
        safety = QLabel("The app never starts a job. Someone at the machine loads and runs it "
                        "in MPS2003 — check it with Plot Preview (P) first.")
        safety.setObjectName("Muted")
        safety.setWordWrap(True)
        bar.addWidget(safety, 1)
        self.save_btn = QPushButton("Save copy to USB…")
        self.save_btn.clicked.connect(self._on_save_copy)
        self.send_btn = QPushButton("Send to old PC  ➜")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self._on_send)
        bar.addWidget(self.save_btn)
        bar.addWidget(self.send_btn)
        root.addLayout(bar)
        self._set_job(None)

    # ------------------------------------------------------------ library
    def reload_library(self, select: Path | None = None) -> None:
        cur = select or (self.job.path if self.job else None)
        self.list.blockSignals(True)
        self.list.clear()
        for path in self.library.jobs():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            try:
                job = self.library.load(path, self.settings)
                st = job.stats
                warn = f"  ⚠ {st.warning_count}" if st.warning_count else "  ✓"
                w = st.x_range[1] - st.x_range[0]
                h = st.y_range[1] - st.y_range[0]
                item.setText(f"{path.name}\n{w:.2f}×{h:.2f} {st.units} · {st.short_time}{warn}")
                item.setIcon(dot_icon(theme.WARN if st.warning_count else theme.OK))
                item.setToolTip(f"{path}\n{st.move_count} moves, {st.line_count} lines")
            except OSError as exc:
                item.setText(f"{path.name}\ncould not read: {exc}")
                item.setIcon(dot_icon(theme.BAD))
            self.list.addItem(item)
        self.list.blockSignals(False)
        n = self.list.count()
        self.count_label.setText(f"{n} job{'s' if n != 1 else ''}")
        self._filter(self.search.text())
        target = None
        for i in range(self.list.count()):
            if cur and self.list.item(i).data(Qt.ItemDataRole.UserRole) == str(cur):
                target = i
        if target is None and self.list.count():
            target = 0
        if target is not None:
            self.list.setCurrentRow(target)
        else:
            self._set_job(None)

    def _filter(self, text: str) -> None:
        t = text.strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def add_files(self, paths: list[Path]) -> None:
        results = self.library.add(paths)
        added = [p for p, note in results if note in ("", "renamed")]
        problems = [f"{p.name}: {note}" for p, note in results
                    if note not in ("", "renamed", "already there")]
        self.reload_library(select=added[-1] if added else None)
        msg = f"Added {len(added)} job(s) to the library."
        if problems:
            QMessageBox.warning(self, "Some files were not added", "\n".join(problems))
        self.message.emit(msg)

    def _on_add(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Add jobs to the library", str(Path.home()),
                                                JOB_FILTER)
        if files:
            self.add_files([Path(f) for f in files])

    def _on_remove(self) -> None:
        if not self.job:
            return
        ans = QMessageBox.question(
            self, "Remove job",
            f"Remove {self.job.path.name} from the job library?\n\n"
            "This deletes the app's copy in Documents\\A-Tech CNC\\Jobs. "
            "The file you added it from is not touched.")
        if ans == QMessageBox.StandardButton.Yes:
            name = self.job.path.name
            self.library.remove(self.job.path)
            self.job = None
            self.reload_library()
            self.message.emit(f"Removed {name} from the library.")

    def _on_pick(self, item: QListWidgetItem | None, _prev=None) -> None:
        if item is None:
            self._set_job(None)
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            self._set_job(self.library.load(path, self.settings))
        except OSError as exc:
            QMessageBox.critical(self, "Could not open job", str(exc))
            self._set_job(None)

    # ------------------------------------------------------------ show a job
    def _set_job(self, job: Job | None) -> None:
        self._stop_play()
        self.job = job
        has = job is not None
        for w in (self.send_btn, self.save_btn, self.remove_btn, self.play_btn, self.slider):
            w.setEnabled(has)
        self.checks.clear()
        if not has:
            self.job_title.setText("No job selected")
            self.view.show_result(None)
            self.code.setPlainText("")
            for t in self.tiles.values():
                t.set("–")
            self.slider.setRange(0, 0)
            self.pos_label.setText("")
            return
        st = job.stats
        self.job_title.setText(job.path.name)
        self.view.show_result(job.result)
        n = self.view.segment_count()
        self.slider.blockSignals(True)
        self.slider.setRange(0, n)
        self.slider.setValue(n)
        self.slider.blockSignals(False)
        self.view.set_progress(None)
        self._update_pos(n)
        u = st.units
        self.tiles["size"].set(st.size_text, f"X {st.x_range[0]:.3f} … {st.x_range[1]:.3f}\n"
                               f"Y {st.y_range[0]:.3f} … {st.y_range[1]:.3f}")
        self.tiles["depth"].set(f"Z{st.z_range[0]:.3f} {u}", f"Highest point Z{st.z_range[1]:.3f}")
        self.tiles["time"].set(st.time_text, (
            f"Cutting {st.cut_length:.1f} {u}, rapids {st.rapid_length:.1f} {u}.\n"
            f"Rapids at about {self.settings.rapid_in_per_min:g} in/min (Settings). "
            "Pauses for M0/M6 are not counted."))
        self.tiles["moves"].set(f"{st.move_count:,}", f"{st.cut_moves:,} cutting moves")
        feeds = st.feeds
        self.tiles["feed"].set("–" if not feeds else (f"F{feeds[0]:g}" if len(feeds) == 1 else
                               f"F{feeds[0]:g}–{feeds[-1]:g}"), ", ".join(f"F{f:g}" for f in feeds))
        self.tiles["lines"].set(f"{st.line_count:,}")
        for c in st.checks:
            sym, color = check_symbol(c.level)
            it = QListWidgetItem(f"{sym}  {c.text}")
            it.setForeground(QColor(color if c.level != "ok" else theme.TEXT))
            self.checks.addItem(it)
        self.code.blockSignals(True)
        self.code.setPlainText(job.text)
        self.code.blockSignals(False)

    # ------------------------------------------------------------ playback / sync
    def _update_pos(self, k: int) -> None:
        n = self.view.segment_count()
        line = self.view.segment_line(k - 1) if k else None
        self.pos_label.setText(f"Move {k:,} / {n:,}" + (f"  ·  line {line}" if line else ""))

    def _on_slider(self, k: int) -> None:
        n = self.view.segment_count()
        self.view.set_progress(None if k >= n else k)
        self._update_pos(k)
        line = self.view.segment_line(k - 1) if k else None
        if line and k < n:
            self._highlight_code_line(line)
            self.view.set_highlight_line(None)

    def _toggle_play(self) -> None:
        if self._timer.isActive():
            self._stop_play()
            return
        if self.slider.value() >= self.slider.maximum():
            self.slider.setValue(0)
        self._timer.start()
        self.play_btn.setText("❚❚  Pause")

    def _stop_play(self) -> None:
        self._timer.stop()
        self.play_btn.setText("▶  Play")

    def _tick(self) -> None:
        v = self.slider.value() + int(self.speed.currentData())
        if v >= self.slider.maximum():
            self.slider.setValue(self.slider.maximum())
            self._stop_play()
        else:
            self.slider.setValue(v)

    def _on_line_picked(self, line: int) -> None:
        self.view.set_highlight_line(line)
        self._highlight_code_line(line, move_cursor=True)

    def _highlight_code_line(self, line: int, move_cursor: bool = True) -> None:
        block = self.code.document().findBlockByNumber(line - 1)
        if not block.isValid():
            return
        sel = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#fef3c7"))
        fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.format = fmt
        cur = QTextCursor(block)
        sel.cursor = cur
        self.code.setExtraSelections([sel])
        if move_cursor:
            self.code.blockSignals(True)
            self.code.setTextCursor(cur)
            self.code.centerCursor()
            self.code.blockSignals(False)

    def _on_code_cursor(self) -> None:
        line = self.code.textCursor().blockNumber() + 1
        self.view.set_highlight_line(line)
        self._highlight_code_line(line, move_cursor=False)

    # ------------------------------------------------------------ send / save
    def _confirm_warnings(self, what: str) -> bool:
        n = self.job.stats.warning_count
        if not n:
            return True
        ans = QMessageBox.warning(
            self, "This job has warnings",
            f"{self.job.path.name} has {n} warning(s) (see Checks).\n\n{what} anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return ans == QMessageBox.StandardButton.Yes

    def _on_send(self) -> None:
        if not self.job or not self._confirm_warnings("Send it"):
            return
        dlg = SendDialog(self.job.path.name, outbox_dir(), received_dir(), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.name()
        try:
            put_in_outbox(self.job.path, name, outbox_dir())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not send", str(exc))
            return
        self.sentToOutbox.emit(name)
        self.message.emit(f"{name} is waiting for the old PC in the To Old PC folder.")
        NextStepsDialog(name, self).exec()

    def _on_save_copy(self) -> None:
        if not self.job or not self._confirm_warnings("Save a copy"):
            return
        default = suggest_old_pc_name(self.job.path.name, outbox_dir())
        dest, _ = QFileDialog.getSaveFileName(self, "Save a copy (e.g. to a USB stick)",
                                              str(Path.home() / default), JOB_FILTER)
        if not dest:
            return
        try:
            from gcode.dosfile import to_dos_text
            Path(dest).write_bytes(to_dos_text(self.job.path.read_bytes()))
        except OSError as exc:
            QMessageBox.critical(self, "Could not save", str(exc))
            return
        self.message.emit(f"Saved a copy to {dest}")

    def settings_changed(self) -> None:
        self.library.refresh_settings()
        self.reload_library()


class SendDialog(QDialog):
    """Pick the DOS name the job will have on the old PC."""

    def __init__(self, src_name: str, outbox: Path, received: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send to old PC")
        self.setMinimumWidth(460)
        self._outbox = outbox
        self._old = old_pc_names(received)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        title = QLabel(f"Send <b>{src_name}</b> to the old PC")
        lay.addWidget(title)
        lay.addWidget(QLabel("Name on the old PC (8 letters max, then .TAP):"))
        self.edit = QLineEdit(suggest_old_pc_name(src_name, outbox))
        self.edit.textChanged.connect(self._validate)
        lay.addWidget(self.edit)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        info = QLabel("The file goes into the <b>To Old PC</b> folder with DOS line endings. "
                      "Nothing happens on the machine until someone fetches it there.")
        info.setWordWrap(True)
        info.setObjectName("Muted")
        lay.addWidget(info)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                        QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Send")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("Primary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self._validate()

    def name(self) -> str:
        return self.edit.text().strip().upper()

    def _validate(self) -> None:
        n = self.name()
        ok = is_dos_name(n)
        msg, color = "", theme.MUTED
        if not ok:
            msg, color = "Use up to 8 letters/numbers, a dot, and up to 3 letters, e.g. JOB1.TAP.", theme.BAD
        elif n.rsplit(".", 1)[-1] in ("EXE", "COM", "BAT", "DAT", "PIF", "SYS"):
            ok = False
            msg, color = ("That kind of file could replace a program or setting on the old PC. "
                          "Use .TAP."), theme.BAD
        elif n in self._old:
            msg, color = (f"⚠ The old PC already has a {n} (in the last backup). Getting this one "
                          "will REPLACE it there. Pick another name to keep both."), theme.WARN
        elif (self._outbox / n).exists():
            msg, color = f"A {n} is already waiting in To Old PC; it will be replaced.", theme.WARN
        else:
            msg, color = "✓ Name is fine.", theme.OK
        self.note.setText(msg)
        self.note.setStyleSheet(f"color: {color};")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)


class NextStepsDialog(QDialog):
    """What to type on the old PC to fetch the job."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Now, on the old PC")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        head = QLabel(f"<b>{name}</b> is ready for the old PC.")
        head.setStyleSheet("font-size: 12pt;")
        lay.addWidget(head)
        lay.addWidget(QLabel("1. Make sure the link is on (Machine Link tab, green).\n"
                             "2. On the old PC, open an MS-DOS Prompt and type:"))
        cmd = QLineEdit(f"C:\\NETUP\\GET {name}")
        cmd.setReadOnly(True)
        cmd.setStyleSheet("font-family: Consolas, monospace; font-size: 12pt; padding: 6px;")
        lay.addWidget(cmd)
        more = QLabel(
            "3. In MPS2003: press 2 (Load Program), type TAP, pick the job.\n"
            "4. Press P for Plot Preview and run it once with no movement before cutting.\n\n"
            "No C:\\NETUP\\GET.BAT yet? See Help → \"First time: get GET.BAT\".")
        more.setObjectName("Muted")
        lay.addWidget(more)
        row = QHBoxLayout()
        copy = QPushButton("Copy command")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(cmd.text()))
        ok = QPushButton("OK")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        row.addStretch(1)
        row.addWidget(copy)
        row.addWidget(ok)
        lay.addLayout(row)
