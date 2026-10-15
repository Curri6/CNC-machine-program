"""Tools dialog: the list of bits (end mills, drills, V-bits) the Make tab
can use, and what the app will do with each one."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox,
    QToolButton, QVBoxLayout, QWidget,
)

from app_config import Settings
from cam.tools import COMMON_TOOLS, KINDS, MATERIALS, Tool, ToolLibrary, cutting_data, parse_length
from ui import theme
from ui.widgets import Card


def tool_icon_text(kind: str) -> str:
    return {"flat": "▮", "ball": "◖", "drill": "▼", "vbit": "∨"}.get(kind, "•")


class ToolsDialog(QDialog):
    def __init__(self, tools: ToolLibrary, settings: Settings, material: str = "acrylic",
                 parent=None, select: int | None = None):
        super().__init__(parent)
        self.setWindowTitle("Bits (tool list)")
        self.resize(860, 560)
        self.lib = tools
        self.settings = settings
        self.work: list[Tool] = copy.deepcopy(tools.tools)
        self._loading = False

        root = QVBoxLayout(self)
        intro = QLabel("Add every bit you use. When a step uses a bit, the app works out the "
                       "spindle speed, feeds, depth per pass and how to cut with it — a drill "
                       "only goes straight down, an end mill is moved over by its radius, a "
                       "V-bit engraves on the line.")
        intro.setWordWrap(True)
        intro.setObjectName("Muted")
        root.addWidget(intro)
        row = QHBoxLayout()
        root.addLayout(row, 1)

        left = Card("Bits")
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show)
        left.body.addWidget(self.list, 1)
        btns = QHBoxLayout()
        add = QPushButton("＋  New bit")
        add.setObjectName("Primary")
        add.clicked.connect(lambda: self._add(Tool(0)))
        common = QToolButton()
        common.setText("Common sizes ▾")
        common.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(common)
        for label, t in COMMON_TOOLS:
            menu.addAction(label, lambda t=t: self._add(copy.deepcopy(t)))
        common.setMenu(menu)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("Danger")
        self.del_btn.clicked.connect(self._delete)
        btns.addWidget(add)
        btns.addWidget(common)
        btns.addStretch(1)
        btns.addWidget(self.del_btn)
        left.body.addLayout(btns)
        left.setMinimumWidth(330)
        row.addWidget(left)

        right = Card("This bit")
        self.form_host = QWidget()
        form = QFormLayout(self.form_host)
        form.setVerticalSpacing(8)
        self.number = QSpinBox()
        self.number.setRange(1, 99)
        self.number.setPrefix("T")
        self.kind = QComboBox()
        for k, v in KINDS.items():
            self.kind.addItem(v, k)
        self.size = QLineEdit()
        self.size.setPlaceholderText("e.g. 1/8, 0.125 or 3mm")
        self.flutes = QSpinBox()
        self.flutes.setRange(1, 8)
        self.length = QLineEdit()
        self.length.setPlaceholderText("e.g. 1/2")
        self.angle = QDoubleSpinBox()
        self.angle.setRange(10, 179)
        self.angle.setSuffix("°")
        self.angle.setDecimals(0)
        self.tip = QLineEdit()
        self.tip.setPlaceholderText("0 for a sharp point")
        self.carbide = QCheckBox("Carbide (not HSS steel)")
        self.name = QLineEdit()
        self.notes = QLineEdit()
        form.addRow("Number", self.number)
        form.addRow("Kind", self.kind)
        form.addRow("Diameter", self.size)
        form.addRow("Flutes", self.flutes)
        form.addRow("Cutting length", self.length)
        form.addRow("Angle", self.angle)
        form.addRow("Tip width", self.tip)
        form.addRow("", self.carbide)
        form.addRow("Name (optional)", self.name)
        form.addRow("Notes", self.notes)
        self.form = form
        right.body.addWidget(self.form_host)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color: {theme.BAD};")
        self.err.setWordWrap(True)
        right.body.addWidget(self.err)

        what = QHBoxLayout()
        what.addWidget(QLabel("<b>What the app will do in</b>"))
        self.mat = QComboBox()
        for k, m in MATERIALS.items():
            self.mat.addItem(m.name, k)
        self.mat.setCurrentIndex(max(self.mat.findData(material), 0))
        self.mat.currentIndexChanged.connect(self._explain)
        what.addWidget(self.mat, 1)
        right.body.addLayout(what)
        self.explain = QLabel("")
        self.explain.setWordWrap(True)
        self.explain.setTextFormat(Qt.TextFormat.RichText)
        self.explain.setStyleSheet(f"background: {theme.BG}; border-radius: 8px; padding: 8px;")
        right.body.addWidget(self.explain)
        right.body.addStretch(1)
        row.addWidget(right, 1)

        for w in (self.size, self.length, self.tip, self.name, self.notes):
            w.textChanged.connect(self._edited)
        for w in (self.number, self.flutes):
            w.valueChanged.connect(self._edited)
        self.angle.valueChanged.connect(self._edited)
        self.kind.currentIndexChanged.connect(self._edited)
        self.carbide.toggled.connect(self._edited)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        self.buttons = bb
        root.addWidget(bb)

        self._fill_list()
        pick = 0
        for i, t in enumerate(self.work):
            if t.number == select:
                pick = i
        self.list.setCurrentRow(pick if self.work else -1)

    # ------------------------------------------------------------ list
    def _fill_list(self, keep: int | None = None) -> None:
        cur = self.list.currentRow() if keep is None else keep
        self.list.blockSignals(True)
        self.list.clear()
        for t in self.work:
            it = QListWidgetItem(f"{tool_icon_text(t.kind)}   {t.label()}")
            self.list.addItem(it)
        self.list.blockSignals(False)
        if self.work:
            self.list.setCurrentRow(min(max(cur, 0), len(self.work) - 1))
        self.del_btn.setEnabled(bool(self.work))
        self.form_host.setEnabled(bool(self.work))

    def _add(self, t: Tool) -> None:
        t.number = max((x.number for x in self.work), default=0) + 1
        self.work.append(t)
        self._fill_list(keep=len(self.work) - 1)
        self._show(len(self.work) - 1)

    def _delete(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.work):
            del self.work[i]
            self._fill_list(keep=max(i - 1, 0))
            self._show(self.list.currentRow())

    def _show(self, i: int) -> None:
        if not (0 <= i < len(self.work)):
            self.explain.setText("")
            return
        t = self.work[i]
        self._loading = True
        self.number.setValue(t.number)
        self.kind.setCurrentIndex(max(self.kind.findData(t.kind), 0))
        self.size.setText(f"{t.diameter:.4f}".rstrip("0").rstrip("."))
        self.flutes.setValue(t.flutes)
        self.length.setText(f"{t.cut_length:.4f}".rstrip("0").rstrip("."))
        self.angle.setValue(t.angle)
        self.tip.setText(f"{t.tip:.4f}".rstrip("0").rstrip(".") or "0")
        self.carbide.setChecked(t.carbide)
        self.name.setText(t.name)
        self.name.setPlaceholderText(Tool(t.number, t.kind, t.diameter, t.flutes, angle=t.angle,
                                          tip=t.tip).describe())
        self.notes.setText(t.notes)
        self._loading = False
        self._rows()
        self._explain()

    def _rows(self) -> None:
        k = self.kind.currentData()
        self.form.setRowVisible(self.angle, k in ("vbit", "drill"))
        self.form.setRowVisible(self.tip, k == "vbit")
        self.form.setRowVisible(self.flutes, k != "drill")

    def _edited(self) -> None:
        if self._loading:
            return
        i = self.list.currentRow()
        if not (0 <= i < len(self.work)):
            return
        t = self.work[i]
        self._rows()
        errs = []
        t.number = self.number.value()
        t.kind = self.kind.currentData()
        for attr, w, what in (("diameter", self.size, "Diameter"),
                              ("cut_length", self.length, "Cutting length"),
                              ("tip", self.tip, "Tip width")):
            try:
                v = parse_length(w.text() or "0")
                if attr == "diameter" and v <= 0:
                    raise ValueError("must be more than 0")
                setattr(t, attr, v)
                w.setStyleSheet("")
            except ValueError as exc:
                errs.append(f"{what}: {exc}")
                w.setStyleSheet(f"border: 1px solid {theme.BAD};")
        t.flutes = self.flutes.value()
        t.angle = self.angle.value()
        t.carbide = self.carbide.isChecked()
        t.name = self.name.text()
        t.notes = self.notes.text()
        self.name.setPlaceholderText(Tool(t.number, t.kind, t.diameter, t.flutes, angle=t.angle,
                                          tip=t.tip).describe())
        nums = [x.number for x in self.work]
        if nums.count(t.number) > 1:
            errs.append(f"Two bits are T{t.number}. Each bit needs its own number.")
        self.err.setText("\n".join(errs))
        it = self.list.item(i)
        if it:
            it.setText(f"{tool_icon_text(t.kind)}   {t.label()}")
        self._explain()

    def _explain(self) -> None:
        i = self.list.currentRow()
        if not (0 <= i < len(self.work)):
            return
        t = self.work[i]
        mat = self.mat.currentData()
        c = cutting_data(t, mat, self.settings.rapid_in_per_min, self.settings.rpm_choices(),
                         depth=0.02)
        does = {
            "flat": "Pockets, cut-outs, holes (any size bigger than the bit — milled round), "
                    "lines, text and facing.",
            "ball": "Pockets, cut-outs, lines and text, with rounded bottoms.",
            "drill": "Holes of its own size only, straight down in pecks.",
            "vbit": f"Engraving lines and text (the groove gets wider the deeper it goes: "
                    f"{t.width_at(0.02):.3f} in wide at 0.02 in deep), and marking hole centres.",
        }[t.kind]
        lines = [f"<b>Can do:</b> {does}",
                 f"<b>Spindle:</b> {c.rpm:,} RPM &nbsp; <b>Feed:</b> F{c.feed:g} in/min &nbsp; "
                 f"<b>Plunge:</b> F{c.plunge:g}"]
        if t.kind == "drill":
            lines.append(f"<b>Pecks:</b> {c.peck:.3f} in, pulling out between pecks to clear chips")
        else:
            lines.append(f"<b>Depth per pass:</b> {c.depth_per_pass:.4f} in &nbsp; "
                         f"<b>Pocket stepover:</b> {c.stepover:.4f} in")
        for n in c.notes:
            lines.append(f"<span style='color:{theme.MUTED}'>{n}</span>")
        self.explain.setText("<br>".join(lines))

    # ------------------------------------------------------------ save
    def _save(self) -> None:
        nums = [t.number for t in self.work]
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if dup:
            QMessageBox.warning(self, "Two bits with one number",
                                f"T{dup[0]} is used twice. Give each bit its own number.")
            return
        if any(t.diameter <= 0 for t in self.work):
            QMessageBox.warning(self, "Missing size", "Every bit needs a diameter.")
            return
        self.lib.tools = sorted(copy.deepcopy(self.work), key=lambda t: t.number)
        if not self.lib.tools:
            self.lib.load()
        self.lib.save()
        self.accept()
