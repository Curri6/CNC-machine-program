"""A project (stock + steps) and turning it into job files.

One job file per bit. The MicroMill has no tool changer and MPS2003 can't
re-zero Z in the middle of a job, so each bit gets its own file: run the
first, change the bit, zero Z on the top of the stock again, run the next.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app_config import Settings
from cam.builder import Builder, comment_text
from cam.operations import ERROR, GENERATORS, INFO, STEP_TYPES, WARN, Ctx, Step
from cam.tools import MATERIALS, CutData, Overrides, Tool, ToolLibrary, cutting_data

PROJECT_EXT = ".cncproj"


@dataclass
class Project:
    name: str = "My project"
    material: str = "acrylic"
    stock_x: float = 4.0
    stock_y: float = 3.0
    stock_t: float = 0.25
    origin: str = "corner"          # where X0 Y0 is: "corner" (lower left) or "center"
    steps: list[Step] = field(default_factory=list)

    def offset(self) -> tuple[float, float]:
        return (self.stock_x / 2, self.stock_y / 2) if self.origin == "center" else (0.0, 0.0)

    # ------------------------------------------------------------ files
    def to_dict(self) -> dict:
        d = asdict(self)
        d["version"] = 1
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        steps = []
        for s in d.get("steps", []):
            if s.get("kind") not in STEP_TYPES:
                continue
            over = Overrides(**{k: v for k, v in (s.get("over") or {}).items()
                                if k in Overrides.__dataclass_fields__})
            steps.append(Step(kind=s["kind"], tool=int(s.get("tool", 1)), params=s.get("params", {}),
                              over=over, name=s.get("name", ""), enabled=bool(s.get("enabled", True))))
        p = cls(name=str(d.get("name", "My project")), material=str(d.get("material", "acrylic")),
                stock_x=float(d.get("stock_x", 4)), stock_y=float(d.get("stock_y", 3)),
                stock_t=float(d.get("stock_t", 0.25)), origin=str(d.get("origin", "corner")),
                steps=steps)
        if p.material not in MATERIALS:
            p.material = "acrylic"
        return p

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class Message:
    level: str
    step: int | None          # index into project.steps, or None for the whole project
    text: str


@dataclass
class OutFile:
    tool: Tool
    name: str                 # file name for the job library, e.g. "Nameplate T5.tap"
    text: str
    steps: list[int]


@dataclass
class Output:
    files: list[OutFile]
    messages: list[Message]
    cut: dict[int, CutData]   # per step index

    @property
    def ok(self) -> bool:
        return bool(self.files) and not any(m.level == ERROR for m in self.messages)

    def step_messages(self, i: int) -> list[Message]:
        return [m for m in self.messages if m.step == i]


_SAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def file_stem(name: str) -> str:
    s = _SAFE_NAME.sub("", name).strip().strip(".") or "Project"
    return s[:60]


def tool_for(step: Step, tools: ToolLibrary) -> Tool | None:
    return tools.get(step.tool)


def step_cut(step: Step, tool: Tool, project: Project, settings: Settings) -> CutData:
    ctx_depth = 0.0
    try:
        ctx_depth = float(step.params.get("depth") or 0.0)
    except (TypeError, ValueError):
        pass
    return cutting_data(tool, project.material, settings.rapid_in_per_min, settings.rpm_choices(),
                        depth=ctx_depth, overrides=step.over)


def generate(project: Project, tools: ToolLibrary, settings: Settings) -> Output:
    msgs: list[Message] = []
    cut: dict[int, CutData] = {}
    if project.stock_x <= 0 or project.stock_y <= 0 or project.stock_t <= 0:
        msgs.append(Message(ERROR, None, "The stock size must be more than 0 in every direction."))
        return Output([], msgs, cut)
    active = [(i, s) for i, s in enumerate(project.steps) if s.enabled]
    if not active:
        msgs.append(Message(INFO, None, "Add a step (＋ Add step) to make some G-code."))
        return Output([], msgs, cut)

    order: list[int] = []
    for _, s in active:
        if s.tool not in order:
            order.append(s.tool)

    files: list[OutFile] = []
    stem = file_stem(project.name)
    mat = MATERIALS[project.material]
    for part, tnum in enumerate(order, 1):
        tool = tools.get(tnum)
        idxs = [i for i, s in active if s.tool == tnum]
        if tool is None:
            for i in idxs:
                msgs.append(Message(ERROR, i, f"Uses T{tnum}, which isn't in the tool list. "
                                    "Pick a bit for this step."))
            continue
        b = Builder(settings.safe_z_in, project.offset())
        b.z = settings.safe_z_in          # the header goes up there first
        used: list[int] = []
        body_start = None
        rpm = None
        for i in idxs:
            step = project.steps[i]
            c = step_cut(step, tool, project, settings)
            cut[i] = c
            ctx = Ctx(project.stock_x, project.stock_y, project.stock_t, tool, c,
                      settings.max_depth_in, settings.climb_milling, settings.tab_height_in)
            mark = len(b.lines)
            b.comment(f"STEP {i + 1}: {step.title()}")
            if body_start is None:
                body_start = mark
            GENERATORS[step.kind](step, ctx, b)
            for level, text in ctx.msgs:
                msgs.append(Message(level, i, text))
            for n in c.notes:
                if n != mat.note and not n.startswith(("Feed held", "Drilling held")):
                    msgs.append(Message(INFO, i, n))
            if ctx.has_error:
                del b.lines[mark:]          # leave a broken step out completely
                continue
            used.append(i)
            rpm = rpm or c.rpm
            if c.rpm != rpm:
                msgs.append(Message(WARN, i, f"Wants {c.rpm:,} RPM but this bit's file starts at "
                                    f"{rpm:,} RPM. Change the speed when MPS2003 pauses."))
                b.lines.insert(mark + 1, f"(SET SPINDLE TO {c.rpm} RPM, THEN PRESS C)")
                b.lines.insert(mark + 2, "M00")
        if not used:
            continue
        b.up()
        b.rapid(project.offset()[0], project.offset()[1])
        body = b.lines
        name = f"{stem}.tap" if len(order) == 1 else f"{stem} T{tnum}.tap"
        head = _header(project, tool, mat.name, part, len(order), rpm or 0, settings)
        text = "\n".join(head + body + ["M02", ""])
        files.append(OutFile(tool, name, text, used))
    if files and mat.note:
        msgs.append(Message(INFO, None, mat.note))
    if len(files) > 1:
        msgs.append(Message(INFO, None, (
            f"{len(files)} files, one per bit. Run them in order; after each one change the bit "
            "and zero Z on the top of the stock again (X and Y stay where they are).")))
    return Output(files, msgs, cut)


def _header(project: Project, tool: Tool, material: str, part: int, parts: int, rpm: int,
            settings: Settings) -> list[str]:
    zero = ("LOWER LEFT CORNER OF THE STOCK" if project.origin == "corner"
            else "CENTRE OF THE STOCK")
    lines = [
        f"({comment_text('A-TECH CNC: ' + project.name)})",
        f"(PART {part} OF {parts})" if parts > 1 else None,
        f"({comment_text(f'BIT T{tool.number}: {tool.describe()}')})",
        f"({comment_text(f'{material}, STOCK {project.stock_x:g} X {project.stock_y:g} X {project.stock_t:g} IN')})",
        f"(ZERO X0 Y0 = {zero}, Z0 = TOP OF THE STOCK)",
        "G20",
        "G90",
        f"G00 Z{settings.safe_z_in:.4f}",
        f"(PUT IN T{tool.number}, SPINDLE ON AT {rpm} RPM, THEN PRESS C)",
        "M00",
    ]
    return [ln for ln in lines if ln]
