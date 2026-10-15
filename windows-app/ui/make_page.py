"""Make G-code tab: design a job from simple steps (holes, rectangles,
circles, text, lines, facing), pick a bit for each, and the app writes
the G-code — speeds, feeds, passes, offsets and pecks worked out for
whichever bit each step uses. Saved jobs go into the Jobs library, from
where they're checked and sent like any other job."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFontComboBox, QFormLayout, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from app_config import Settings, app_home, jobs_dir, projects_dir
from cam.operations import ERROR, INFO, STEP_TYPES, WARN, Step, describe
from cam.program import PROJECT_EXT, Output, Project, dry_run, file_stem, generate
from cam.tools import MATERIALS, Overrides, ToolLibrary, parse_length
from gcode.analysis import analyze, time_text
from gcode.parser import parse_gcode
from ui import theme
from ui.toolpath_view import VIEW_NAMES, ToolpathView
from ui.tools_dialog import ToolsDialog, tool_icon_text
from ui.widgets import Card, Tile

STEP_ICONS = {"holes": "⦿", "rect": "▭", "circle": "◯", "text": "A", "lines": "╱", "face": "▤"}
LEVEL_COLORS = {ERROR: theme.BAD, WARN: theme.WARN, INFO: theme.MUTED}
LEVEL_SYMBOLS = {ERROR: "✗", WARN: "⚠", INFO: "ℹ"}


def _fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, (int, float)) else str(v)


class LengthEdit(QLineEdit):
    """Text box for a length in inches; takes 1/8, 0.125, 3mm."""

    def __init__(self, value: float = 0.0, parent=None):
        super().__init__(_fmt(value), parent)
        self.setPlaceholderText("in")
        self.textChanged.connect(self._check)
        self._ok = True

    def value(self) -> float | None:
        try:
            return parse_length(self.text() or "0")
        except ValueError:
            return None

    def _check(self) -> None:
        ok = self.value() is not None
        if ok != self._ok:
            self._ok = ok
            self.setStyleSheet("" if ok else f"border: 1px solid {theme.BAD};")
        self.setToolTip("" if ok else "Type a size like 1/8, 0.125 or 3mm")


class MakePage(QWidget):
    message = Signal(str)
    savedJobs = Signal(list)          # paths written into the Jobs folder
    toolsChanged = Signal()

    def __init__(self, settings: Settings, tools: ToolLibrary, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self.settings = settings
        self.tools = tools
        self.project = self._load_current()
        self.project_path: Path | None = None
        self.output: Output | None = None
        self._form_widgets: dict[str, QWidget] = {}
        self._loading = False
        self._regen = QTimer(self)
        self._regen.setSingleShot(True)
        self._regen.setInterval(250)
        self._regen.timeout.connect(self.regenerate)
        self._build()
        self._load_project_fields()
        self._fill_steps(select=0)
        self.regenerate()

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)
        root.addWidget(split, 1)

        # --- left: project + steps
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        proj = Card("Project")
        files = QHBoxLayout()
        for text, fn in (("New", self._new), ("Open…", self._open), ("Save…", self._save_project)):
            b = QPushButton(text)
            b.setObjectName("Flat")
            b.clicked.connect(fn)
            files.addWidget(b)
        proj.header.addLayout(files)
        pf = QFormLayout()
        pf.setVerticalSpacing(6)
        self.p_name = QLineEdit()
        self.p_material = QComboBox()
        for k, m in MATERIALS.items():
            self.p_material.addItem(m.name, k)
        size = QHBoxLayout()
        self.p_x, self.p_y, self.p_t = LengthEdit(), LengthEdit(), LengthEdit()
        for w, tip in ((self.p_x, "X"), (self.p_y, "Y"), (self.p_t, "thick")):
            w.setToolTip({"X": "Stock width (X)", "Y": "Stock height (Y)",
                          "thick": "Stock thickness"}[tip])
            w.setPlaceholderText(tip)
            w.setMinimumWidth(50)
        size.addWidget(self.p_x)
        size.addWidget(QLabel("×"))
        size.addWidget(self.p_y)
        size.addWidget(QLabel("×"))
        size.addWidget(self.p_t)
        size.addWidget(QLabel("in"))
        self.p_origin = QComboBox()
        self.p_origin.addItem("Lower-left corner", "corner")
        self.p_origin.addItem("Centre of the stock", "center")
        self.p_origin.setToolTip("Where you zero X and Y on the machine (MPS2003 option 4)")
        pf.addRow("Name", self.p_name)
        pf.addRow("Material", self.p_material)
        pf.addRow("Stock", size)
        pf.addRow("Zero at", self.p_origin)
        proj.body.addLayout(pf)
        for w in (self.p_name, self.p_x, self.p_y, self.p_t):
            w.textChanged.connect(self._project_edited)
        self.p_material.currentIndexChanged.connect(self._project_edited)
        self.p_origin.currentIndexChanged.connect(self._project_edited)
        ll.addWidget(proj)

        steps = Card("Steps")
        self.steps_count = QLabel("")
        self.steps_count.setObjectName("Muted")
        steps.header.addWidget(self.steps_count)
        self.steps = QListWidget()
        self.steps.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.steps.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.steps.currentRowChanged.connect(self._on_step_pick)
        self.steps.itemChanged.connect(self._on_step_check)
        steps.body.addWidget(self.steps, 1)
        row = QHBoxLayout()
        add = QToolButton()
        add.setText("＋  Add step")
        add.setObjectName("PrimaryTool")
        add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(add)
        for kind, (title, _f) in STEP_TYPES.items():
            menu.addAction(f"{STEP_ICONS[kind]}   {title}", lambda k=kind: self.add_step(k))
        add.setMenu(menu)
        row.addWidget(add)
        row.addStretch(1)
        for text, tip, fn in (("↑", "Move up", lambda: self._move(-1)),
                              ("↓", "Move down", lambda: self._move(1)),
                              ("⧉", "Duplicate", self._duplicate),
                              ("✕", "Delete", self._delete)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setObjectName("Flat")
            b.clicked.connect(fn)
            row.addWidget(b)
        steps.body.addLayout(row)
        hint = QLabel("Positions are inches from the lower-left corner of the stock. "
                      "Depths are below the top (Z0). Untick a step to leave it out.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        steps.body.addWidget(hint)
        ll.addWidget(steps, 1)
        left.setMinimumWidth(320)

        # --- middle: preview / G-code
        mid = Card("")
        top = QHBoxLayout()
        self.title = QLabel("")
        self.title.setObjectName("Big")
        top.addWidget(self.title, 1)
        self.part = QComboBox()
        self.part.setToolTip("Which bit's file to show")
        self.part.currentIndexChanged.connect(self._show_part)
        self.part.setMinimumWidth(220)
        top.addWidget(self.part)
        mid.body.addLayout(top)
        self.mid_tabs = QTabWidget()
        self.mid_tabs.setDocumentMode(True)
        pv = QWidget()
        pvl = QVBoxLayout(pv)
        pvl.setContentsMargins(0, 6, 0, 0)
        vb = QHBoxLayout()
        self.view_group = QButtonGroup(self)
        for i, (key, label) in enumerate(VIEW_NAMES.items()):
            b = QToolButton()
            b.setText(label.split(" (")[0])
            b.setCheckable(True)
            b.setObjectName("Seg")
            b.setChecked(key == "top")
            b.clicked.connect(lambda _=False, k=key: self.view.set_view(k))
            self.view_group.addButton(b, i)
            vb.addWidget(b)
        vb.addStretch(1)
        self.width_box = QCheckBox("Show bit width")
        self.width_box.setChecked(True)
        self.width_box.setToolTip("Shade each cut as wide as the bit (top view)")
        self.width_box.toggled.connect(lambda _on: self._show_part())
        vb.addWidget(self.width_box)
        self.rapids = QCheckBox("Rapids")
        self.rapids.setChecked(True)
        self.rapids.toggled.connect(lambda on: self.view.set_show_rapids(on))
        vb.addWidget(self.rapids)
        fit = QPushButton("Fit")
        fit.setObjectName("Flat")
        fit.clicked.connect(lambda: self.view.fit())
        vb.addWidget(fit)
        pvl.addLayout(vb)
        self.view = ToolpathView()
        self.view.set_empty_text("Add a step to see the toolpath.")
        self.view.linePicked.connect(self._on_line_picked)
        pvl.addWidget(self.view, 1)
        self.mid_tabs.addTab(pv, "Preview")
        self.code = QPlainTextEdit()
        self.code.setObjectName("Code")
        self.code.setReadOnly(True)
        self.code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.mid_tabs.addTab(self.code, "G-code")
        mid.body.addWidget(self.mid_tabs, 1)
        tiles = QGridLayout()
        tiles.setSpacing(8)
        self.tiles = {k: Tile(lbl) for k, lbl in (
            ("files", "Job files (one per bit)"), ("time", "Estimated time"),
            ("depth", "Deepest cut"), ("lines", "Lines of G-code"))}
        for i, t in enumerate(self.tiles.values()):
            tiles.addWidget(t, 0, i)
        mid.body.addLayout(tiles)

        # --- right: step settings + messages
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        self.step_card = Card("Step")
        bitrow = QHBoxLayout()
        self.bit = QComboBox()
        self.bit.currentIndexChanged.connect(self._bit_changed)
        bitrow.addWidget(self.bit, 1)
        tb = QPushButton("Bits…")
        tb.setToolTip("Add or change the bits in the tool list")
        tb.clicked.connect(self.open_tools)
        bitrow.addWidget(tb)
        self.step_card.body.addWidget(QLabel("<b>Bit</b>"))
        self.step_card.body.addLayout(bitrow)
        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.form.setContentsMargins(0, 4, 0, 0)
        self.form.setVerticalSpacing(6)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background: {theme.CARD}; border: none; }}")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("StepInner")
        inner.setStyleSheet(f"QWidget#StepInner {{ background: {theme.CARD}; }}")
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 6, 0)
        il.setSpacing(8)
        il.addWidget(self.form_host)
        self.plan = QLabel("")
        self.plan.setWordWrap(True)
        self.plan.setTextFormat(Qt.TextFormat.RichText)
        self.plan.setStyleSheet(f"background: {theme.BG}; border-radius: 8px; padding: 8px;")
        il.addWidget(self.plan)
        self.own = QCheckBox("Use my own speeds and feeds for this step")
        self.own.toggled.connect(self._own_toggled)
        il.addWidget(self.own)
        scroll.setWidget(inner)
        scroll.setMinimumHeight(260)
        self.step_card.body.addWidget(scroll, 1)
        self.own_box = QWidget()
        og = QGridLayout(self.own_box)
        og.setContentsMargins(0, 0, 0, 0)
        self.o_rpm = QSpinBox()
        self.o_rpm.setRange(0, 60000)
        self.o_rpm.setSingleStep(100)
        self.o_rpm.setSuffix(" RPM")
        self.o_feed, self.o_plunge, self.o_doc = QLineEdit(), QLineEdit(), LengthEdit()
        self.o_step = QSpinBox()
        self.o_step.setRange(0, 95)
        self.o_step.setSuffix(" %")
        for i, (lbl, w) in enumerate((("Spindle", self.o_rpm), ("Feed (in/min)", self.o_feed),
                                      ("Plunge (in/min)", self.o_plunge),
                                      ("Depth per pass", self.o_doc),
                                      ("Stepover (% of bit)", self.o_step))):
            og.addWidget(QLabel(lbl), i // 2, (i % 2) * 2)
            og.addWidget(w, i // 2, (i % 2) * 2 + 1)
        note = QLabel("0 or blank = let the app decide.")
        note.setObjectName("Muted")
        og.addWidget(note, 3, 0, 1, 4)
        for w in (self.o_feed, self.o_plunge, self.o_doc):
            w.textChanged.connect(self._own_edited)
        for w in (self.o_rpm, self.o_step):
            w.valueChanged.connect(self._own_edited)
        il.addWidget(self.own_box)
        il.addStretch(1)
        rl.addWidget(self.step_card, 3)
        msgs = Card("Checks")
        self.msgs = QListWidget()
        self.msgs.setWordWrap(True)
        self.msgs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msgs.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.msgs.itemClicked.connect(self._on_msg_click)
        msgs.body.addWidget(self.msgs)
        rl.addWidget(msgs, 1)
        right.setMinimumWidth(380)

        split.addWidget(left)
        split.addWidget(mid)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([310, 640, 410])

        bar = QHBoxLayout()
        safety = QLabel("Check every job in the Jobs tab and in MPS2003's Plot Preview (P) before "
                        "cutting. Someone stays at the machine the whole time.")
        safety.setObjectName("Muted")
        safety.setWordWrap(True)
        bar.addWidget(safety, 1)
        self.dry_btn = QPushButton("Save a dry run")
        self.dry_btn.setToolTip("The same job raised above the stock, so it runs in the air: "
                                "watch every move (and the pauses) before cutting for real")
        self.dry_btn.clicked.connect(self.save_dry_run)
        bar.addWidget(self.dry_btn)
        self.save_btn = QPushButton("Save to Jobs  ➜")
        self.save_btn.setObjectName("Primary")
        self.save_btn.setToolTip("Put the job file(s) in the Jobs library, ready to check and send")
        self.save_btn.clicked.connect(self.save_to_jobs)
        bar.addWidget(self.save_btn)
        root.addLayout(bar)

    # ------------------------------------------------------------ project
    @staticmethod
    def _current_path() -> Path:
        return app_home() / ("current" + PROJECT_EXT)

    def _load_current(self) -> Project:
        try:
            return Project.load(self._current_path())
        except (OSError, ValueError, KeyError, TypeError):
            return example_project()

    def _autosave(self) -> None:
        try:
            self._current_path().parent.mkdir(parents=True, exist_ok=True)
            self.project.save(self._current_path())
        except OSError:
            pass

    def _load_project_fields(self) -> None:
        self._loading = True
        p = self.project
        self.p_name.setText(p.name)
        self.p_material.setCurrentIndex(max(self.p_material.findData(p.material), 0))
        self.p_x.setText(_fmt(p.stock_x))
        self.p_y.setText(_fmt(p.stock_y))
        self.p_t.setText(_fmt(p.stock_t))
        self.p_origin.setCurrentIndex(max(self.p_origin.findData(p.origin), 0))
        self._loading = False

    def _project_edited(self) -> None:
        if self._loading:
            return
        p = self.project
        p.name = self.p_name.text().strip() or "My project"
        p.material = self.p_material.currentData()
        for attr, w in (("stock_x", self.p_x), ("stock_y", self.p_y), ("stock_t", self.p_t)):
            v = w.value()
            if v is not None:
                setattr(p, attr, v)
        p.origin = self.p_origin.currentData()
        self.changed()

    def _new(self) -> None:
        ans = QMessageBox.question(self, "New project",
                                   "Start a new, empty project? (Save this one first if you want "
                                   "to keep it.)")
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.set_project(Project(), None)

    def set_project(self, project: Project, path: Path | None) -> None:
        self.project = project
        self.project_path = path
        self._load_project_fields()
        self._fill_steps(select=0)
        self.changed(now=True)

    def _open(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Open a project", str(projects_dir()),
                                           f"A-Tech CNC projects (*{PROJECT_EXT});;All files (*)")
        if not f:
            return
        try:
            self.set_project(Project.load(Path(f)), Path(f))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.critical(self, "Could not open", str(exc))
            return
        self.message.emit(f"Opened {Path(f).name}")

    def _save_project(self) -> None:
        start = self.project_path or projects_dir() / (file_stem(self.project.name) + PROJECT_EXT)
        f, _ = QFileDialog.getSaveFileName(self, "Save the project", str(start),
                                           f"A-Tech CNC projects (*{PROJECT_EXT})")
        if not f:
            return
        path = Path(f)
        if path.suffix.lower() != PROJECT_EXT:
            path = path.with_suffix(PROJECT_EXT)
        try:
            self.project.save(path)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save", str(exc))
            return
        self.project_path = path
        self.message.emit(f"Saved the project to {path}")

    # ------------------------------------------------------------ steps list
    def _fill_steps(self, select: int | None = None) -> None:
        cur = self.steps.currentRow() if select is None else select
        self.steps.blockSignals(True)
        self.steps.clear()
        for i, s in enumerate(self.project.steps):
            it = QListWidgetItem()
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if s.enabled else Qt.CheckState.Unchecked)
            self.steps.addItem(it)
            self._step_text(i)
        self.steps.blockSignals(False)
        n = len(self.project.steps)
        self.steps_count.setText(f"{n} step{'s' if n != 1 else ''}")
        if n:
            self.steps.setCurrentRow(min(max(cur, 0), n - 1))
            self._on_step_pick(self.steps.currentRow())
        else:
            self._on_step_pick(-1)

    def _step_text(self, i: int) -> None:
        it = self.steps.item(i)
        if it is None:
            return
        s = self.project.steps[i]
        t = self.tools.get(s.tool)
        bit = f"T{s.tool} {t.describe()}" if t else f"T{s.tool} (not in the tool list)"
        level = None
        if self.output is not None and s.enabled:
            lv = {m.level for m in self.output.step_messages(i)}
            level = ERROR if ERROR in lv else (WARN if WARN in lv else "ok")
        sym = {ERROR: "  ✗", WARN: "  ⚠", "ok": "  ✓", None: ""}[level]
        self.steps.blockSignals(True)
        it.setText(f"{i + 1}.  {STEP_ICONS[s.kind]}  {s.title()}{sym}\n      {bit}")
        color = {ERROR: theme.BAD, WARN: theme.WARN}.get(level, theme.TEXT)
        it.setForeground(QColor(color if s.enabled else theme.MUTED))
        self.steps.blockSignals(False)

    def add_step(self, kind: str) -> None:
        cur = self.current_step()
        tool = cur.tool if cur else (self.tools.tools[0].number if self.tools.tools else 1)
        if kind == "holes":
            drill = next((t for t in self.tools.tools if t.kind == "drill"), None)
            tool = drill.number if drill else tool
        elif kind == "text":
            v = next((t for t in self.tools.tools if t.kind == "vbit"), None)
            tool = v.number if v else tool
        else:
            t = self.tools.get(tool)
            if t is None or t.kind in ("drill", "vbit"):
                flat = next((t for t in self.tools.tools if t.kind == "flat"), None)
                tool = flat.number if flat else tool
        params = {}
        if kind in ("rect", "circle"):
            # start in the middle of the stock
            p = self.project
            if kind == "rect":
                w, h = round(p.stock_x / 2, 3), round(p.stock_y / 2, 3)
                params = {"x": round((p.stock_x - w) / 2, 3), "y": round((p.stock_y - h) / 2, 3),
                          "w": w, "h": h}
            else:
                params = {"cx": round(p.stock_x / 2, 3), "cy": round(p.stock_y / 2, 3),
                          "d": round(min(p.stock_x, p.stock_y) / 2, 3)}
        self.project.steps.append(Step(kind, tool, params))
        self._fill_steps(select=len(self.project.steps) - 1)
        self.changed(now=True)

    def current_index(self) -> int:
        i = self.steps.currentRow()
        return i if 0 <= i < len(self.project.steps) else -1

    def current_step(self) -> Step | None:
        i = self.current_index()
        return self.project.steps[i] if i >= 0 else None

    def _move(self, d: int) -> None:
        i = self.current_index()
        j = i + d
        if i < 0 or not (0 <= j < len(self.project.steps)):
            return
        st = self.project.steps
        st[i], st[j] = st[j], st[i]
        self._fill_steps(select=j)
        self.changed(now=True)

    def _duplicate(self) -> None:
        s = self.current_step()
        if s is None:
            return
        i = self.current_index()
        self.project.steps.insert(i + 1, copy.deepcopy(s))
        self._fill_steps(select=i + 1)
        self.changed(now=True)

    def _delete(self) -> None:
        i = self.current_index()
        if i < 0:
            return
        del self.project.steps[i]
        self._fill_steps(select=max(i - 1, 0))
        self.changed(now=True)

    def _on_step_check(self, it: QListWidgetItem) -> None:
        i = self.steps.row(it)
        if 0 <= i < len(self.project.steps):
            self.project.steps[i].enabled = it.checkState() == Qt.CheckState.Checked
            self.changed()

    # ------------------------------------------------------------ step form
    def _fill_bits(self, step: Step | None) -> None:
        self.bit.blockSignals(True)
        self.bit.clear()
        for t in self.tools.tools:
            self.bit.addItem(f"{tool_icon_text(t.kind)}  {t.label()}", t.number)
        if step is not None:
            k = self.bit.findData(step.tool)
            if k < 0:
                self.bit.addItem(f"T{step.tool} — not in the tool list", step.tool)
                k = self.bit.count() - 1
            self.bit.setCurrentIndex(k)
        self.bit.blockSignals(False)

    def _on_step_pick(self, i: int) -> None:
        step = self.project.steps[i] if 0 <= i < len(self.project.steps) else None
        self.step_card.setEnabled(step is not None)
        self._fill_bits(step)
        # rebuild the form for this kind of step
        while self.form.rowCount():
            self.form.removeRow(0)
        self._form_widgets = {}
        if step is None:
            self.step_card.title.setText("Step")
            self.plan.setText("")
            self.own.setChecked(False)
            self.own_box.setVisible(False)
            return
        self.step_card.title.setText(f"Step {i + 1}: {STEP_TYPES[step.kind][0]}")
        self._loading = True
        name = QLineEdit(step.name)
        name.setPlaceholderText(describe(step))
        name.textChanged.connect(lambda t: self._set_name(t))
        self.form.addRow("Name", name)
        for f in STEP_TYPES[step.kind][1]:
            v = step.params.get(f.key, f.default)
            if f.kind == "len":
                w = LengthEdit(float(v or 0))
                w.textChanged.connect(lambda _t, k=f.key, w=w: self._set_len(k, w))
            elif f.kind == "num":
                w = QLineEdit(_fmt(v))
                w.textChanged.connect(lambda t, k=f.key, w=w: self._set_num(k, t, w))
            elif f.kind == "int":
                w = QSpinBox()
                w.setRange(int(f.lo), int(f.hi))
                w.setValue(int(v))
                w.valueChanged.connect(lambda val, k=f.key: self._set(k, int(val)))
            elif f.kind == "choice":
                w = QComboBox()
                for val, label in f.choices:
                    w.addItem(label, val)
                w.setCurrentIndex(max(w.findData(v), 0))
                w.currentIndexChanged.connect(lambda _i, k=f.key, w=w: self._set(k, w.currentData()))
            elif f.kind == "bool":
                w = QCheckBox()
                w.setChecked(bool(v))
                w.toggled.connect(lambda on, k=f.key: self._set(k, bool(on)))
            elif f.kind == "lines":
                w = QPlainTextEdit(str(v))
                w.setFixedHeight(84 if f.key == "points" else 56)
                w.textChanged.connect(lambda k=f.key, w=w: self._set(k, w.toPlainText()))
            elif f.kind == "font":
                w = QFontComboBox()
                w.setCurrentFont(QFont(str(v)))
                w.currentFontChanged.connect(lambda fnt, k=f.key: self._set(k, fnt.family()))
            else:
                w = QLineEdit(str(v))
                w.textChanged.connect(lambda t, k=f.key: self._set(k, t))
            if f.tip:
                w.setToolTip(f.tip)
            self.form.addRow(f.label, w)
            self._form_widgets[f.key] = w
        o = step.over
        self.own.blockSignals(True)
        self.own.setChecked(o.any())
        self.own.blockSignals(False)
        self.own_box.setVisible(o.any())
        self.o_rpm.setValue(int(o.rpm))
        self.o_feed.setText(_fmt(o.feed) if o.feed else "")
        self.o_plunge.setText(_fmt(o.plunge) if o.plunge else "")
        self.o_doc.setText(_fmt(o.depth_per_pass) if o.depth_per_pass else "")
        self.o_step.setValue(int(o.stepover_pct))
        self._loading = False
        self._update_visibility()
        self._update_plan()

    def _update_visibility(self) -> None:
        step = self.current_step()
        if step is None:
            return
        for f in STEP_TYPES[step.kind][1]:
            w = self._form_widgets.get(f.key)
            if w is None:
                continue
            show = all(step.params.get(k) in vals for k, vals in f.show_if.items())
            self.form.setRowVisible(w, show)

    def _set(self, key: str, value) -> None:
        if self._loading:
            return
        s = self.current_step()
        if s is None:
            return
        s.params[key] = value
        self._update_visibility()
        self._step_text(self.current_index())
        self.changed()

    def _set_len(self, key: str, w: LengthEdit) -> None:
        v = w.value()
        if v is not None:
            self._set(key, v)

    def _set_num(self, key: str, text: str, w: QLineEdit) -> None:
        try:
            v = float(text)
        except ValueError:
            w.setStyleSheet(f"border: 1px solid {theme.BAD};")
            return
        w.setStyleSheet("")
        self._set(key, v)

    def _set_name(self, text: str) -> None:
        if self._loading:
            return
        s = self.current_step()
        if s is not None:
            s.name = text
            self._step_text(self.current_index())
            self.changed()

    def _bit_changed(self) -> None:
        s = self.current_step()
        if s is None or self.bit.currentData() is None:
            return
        s.tool = int(self.bit.currentData())
        self._step_text(self.current_index())
        self.changed(now=True)

    def _own_toggled(self, on: bool) -> None:
        self.own_box.setVisible(on)
        s = self.current_step()
        if s is not None and not on:
            s.over = Overrides()
            self._loading = True
            self.o_rpm.setValue(0)
            for w in (self.o_feed, self.o_plunge, self.o_doc):
                w.setText("")
            self.o_step.setValue(0)
            self._loading = False
            self.changed(now=True)

    def _own_edited(self) -> None:
        if self._loading:
            return
        s = self.current_step()
        if s is None:
            return

        def num(w: QLineEdit) -> float:
            try:
                return max(float(w.text()), 0.0) if w.text().strip() else 0.0
            except ValueError:
                return 0.0
        s.over = Overrides(rpm=self.o_rpm.value(), feed=num(self.o_feed), plunge=num(self.o_plunge),
                           depth_per_pass=self.o_doc.value() or 0.0,
                           stepover_pct=float(self.o_step.value()))
        self.changed()

    def open_tools(self) -> None:
        s = self.current_step()
        dlg = ToolsDialog(self.tools, self.settings, self.project.material, self,
                          select=s.tool if s else None)
        if dlg.exec():
            self.tools_changed()
            self.toolsChanged.emit()

    def tools_changed(self) -> None:
        self._fill_steps()
        self.changed(now=True)

    # ------------------------------------------------------------ generate / show
    def changed(self, now: bool = False) -> None:
        self._autosave()
        if now:
            self.regenerate()
        else:
            self._regen.start()

    def regenerate(self) -> None:
        self._regen.stop()
        self.output = generate(self.project, self.tools, self.settings)
        out = self.output
        for i in range(len(self.project.steps)):
            self._step_text(i)
        # messages
        self.msgs.clear()
        order = {ERROR: 0, WARN: 1, INFO: 2}
        for m in sorted(out.messages, key=lambda m: (order[m.level], m.step if m.step is not None else -1)):
            where = f"Step {m.step + 1}: " if m.step is not None else ""
            it = QListWidgetItem(f"{LEVEL_SYMBOLS[m.level]}  {where}{m.text}")
            it.setForeground(QColor(LEVEL_COLORS[m.level] if m.level != INFO else theme.TEXT))
            it.setData(Qt.ItemDataRole.UserRole, m.step)
            self.msgs.addItem(it)
        if out.ok and not any(m.level == WARN for m in out.messages):
            ok = QListWidgetItem("✓  Ready to save. Every step worked out with its bit.")
            ok.setForeground(QColor(theme.OK))
            self.msgs.insertItem(0, ok)
        # parts
        keep = self.part.currentData()
        self.part.blockSignals(True)
        self.part.clear()
        if len(out.files) > 1:
            self.part.addItem("All bits together", -1)
        for k, f in enumerate(out.files):
            self.part.addItem(f"{k + 1}. {f.name}", k)
        idx = self.part.findData(keep)
        self.part.setCurrentIndex(idx if idx >= 0 else 0)
        self.part.setVisible(bool(out.files))
        self.part.blockSignals(False)
        self.title.setText(self.project.name)
        # totals
        secs = 0.0
        deepest = 0.0
        lines = 0
        for f in out.files:
            st = analyze(parse_gcode(f.text), self.settings, f.name)
            secs += st.est_seconds
            deepest = min(deepest, st.z_range[0])
            lines += st.line_count
        if out.files:
            self.tiles["time"].set(time_text(secs), "Cutting and moving time. Add time for "
                                   "changing bits and the M0 pauses.")
            self.tiles["files"].set(str(len(out.files)), "\n".join(f.name for f in out.files))
            self.tiles["depth"].set(f"Z{deepest:.3f} in")
            self.tiles["lines"].set(f"{lines:,}")
        else:
            for t in self.tiles.values():
                t.set("–")
        self.save_btn.setEnabled(out.ok)
        self.dry_btn.setEnabled(out.ok)
        self._show_part()
        self._update_plan()

    def _show_part(self) -> None:
        out = self.output
        p = self.project
        ox, oy = p.offset()
        self.view.set_stock((-ox, -oy, p.stock_x - ox, p.stock_y - oy, p.stock_t))
        if not out or not out.files:
            self.view.set_cut_widths([])
            self.view.show_result(None)
            self.code.setPlainText("")
            return
        k = self.part.currentData()
        chosen = out.files if k in (None, -1) else [out.files[k]]
        text = ""
        widths = []
        for f in chosen:
            start = text.count("\n") + 1
            text += f.text
            end = text.count("\n")
            deepest = -min((p[2] for s in parse_gcode(f.text).segments for p in s.points),
                           default=0.0)
            widths.append((start, end, f.tool.width_at(deepest)))
        r = parse_gcode(text)
        self.view.set_cut_widths(widths if self.width_box.isChecked() else [])
        self.view.show_result(r)
        self.code.setPlainText(text)

    def _update_plan(self) -> None:
        i = self.current_index()
        s = self.current_step()
        out = self.output
        if s is None or out is None:
            self.plan.setText("")
            return
        t = self.tools.get(s.tool)
        if t is None:
            self.plan.setText(f"<span style='color:{theme.BAD}'>T{s.tool} isn't in the tool list. "
                              "Pick a bit above.</span>")
            return
        c = out.cut.get(i)
        parts = [f"<b>{tool_icon_text(t.kind)} {t.describe()}</b>"]
        if c is not None:
            if t.kind == "drill":
                parts.append(f"{c.rpm:,} RPM · drill F{c.feed:g} · pecks of {c.peck:.3f} in")
            else:
                parts.append(f"{c.rpm:,} RPM · feed F{c.feed:g} · plunge F{c.plunge:g}<br>"
                             f"{c.depth_per_pass:.4f} in per pass · stepover {c.stepover:.4f} in")
        for m in out.step_messages(i):
            color = LEVEL_COLORS[m.level]
            parts.append(f"<span style='color:{color}'>{LEVEL_SYMBOLS[m.level]} {m.text}</span>")
        if not s.enabled:
            parts.append(f"<span style='color:{theme.MUTED}'>This step is switched off.</span>")
        self.plan.setText("<br>".join(parts))

    def _on_msg_click(self, it: QListWidgetItem) -> None:
        i = it.data(Qt.ItemDataRole.UserRole)
        if isinstance(i, int) and 0 <= i < self.steps.count():
            self.steps.setCurrentRow(i)

    def _on_line_picked(self, line: int) -> None:
        self.view.set_highlight_line(line)
        # find which step wrote this line: the nearest "(STEP n: ...)" above it
        lines = self.code.toPlainText().splitlines()
        for k in range(min(line, len(lines)) - 1, -1, -1):
            if lines[k].startswith("(STEP "):
                try:
                    n = int(lines[k][6:].split(":")[0])
                except ValueError:
                    break
                if 0 < n <= self.steps.count():
                    self.steps.setCurrentRow(n - 1)
                break

    # ------------------------------------------------------------ save
    def save_dry_run(self) -> list[Path]:
        return self.save_to_jobs(dry=True)

    def save_to_jobs(self, dry: bool = False) -> list[Path]:
        out = generate(self.project, self.tools, self.settings)
        self.output = out
        if not out.ok:
            QMessageBox.warning(self, "Not ready", "Fix the steps marked ✗ first (see Checks).")
            return []
        files = dry_run(out) if dry else out.files
        folder = jobs_dir()
        targets = [folder / f.name for f in files]
        existing = [p for p in targets if p.exists()]
        if existing:
            ans = QMessageBox.question(
                self, "Replace jobs?",
                "These jobs are already in the library:\n\n" +
                "\n".join(p.name for p in existing) + "\n\nReplace them with the new version?")
            if ans != QMessageBox.StandardButton.Yes:
                return []
        written = []
        try:
            for f, path in zip(files, targets):
                path.write_text(f.text, encoding="latin-1", errors="replace")
                written.append(path)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save", str(exc))
            return written
        what = "dry-run file(s) — they run in the air, above the stock" if dry else "job file(s)"
        self.message.emit(f"Saved {len(written)} {what} to the Jobs library.")
        self.savedJobs.emit(written)
        return written

    def settings_changed(self) -> None:
        self.changed(now=True)


def example_project() -> Project:
    """What the Make tab shows the first time: a small name plate."""
    p = Project(name="Name plate", material="acrylic", stock_x=4.0, stock_y=1.5, stock_t=0.25)
    p.steps = [
        Step("text", 5, {"text": "A-TECH", "height": 0.5, "x": 2.0, "y": 0.5, "align": "center",
                         "depth": 0.02}),
        Step("holes", 4, {"pattern": "list", "points": "0.3, 0.75\n3.7, 0.75", "through": True}),
        Step("rect", 1, {"mode": "outside", "x": 0.1, "y": 0.1, "w": 3.8, "h": 1.3, "r": 0.15,
                         "through": True, "tabs": True}),
    ]
    return p


def project_json(p: Project) -> str:
    return json.dumps(p.to_dict(), indent=2)
