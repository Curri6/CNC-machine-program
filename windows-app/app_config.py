"""Folders and settings for the A-Tech CNC app.

Everything lives in one folder the teacher can find in File Explorer:

    Documents\\A-Tech CNC\\
        Jobs\\             job files added to the app (the library)
        To Old PC\\        jobs waiting for the old PC to fetch over the cable
        Received\\         backups the old PC sent (one folder per session)
        Projects\\         projects saved from the Make G-code tab
        settings.json
        tools.json        the bit (tool) list
        current.cncproj   the project open in the Make tab, kept for next time

Set the environment variable CNC_APP_HOME to use a different folder
(the tests do this).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Settings:
    # Network (must match what the old PC was set up with)
    laptop_ip: str = "192.168.50.1"
    old_pc_ip: str = "192.168.50.2"
    ftp_port: int = 21

    # Machine (from the old PC's C:\MPSPRO\PARAM3.DAT, 2026-10-14)
    rapid_in_per_min: float = 13.5   # 600 + 800 x 1.5 steps/s at 8000 steps/in
    steps_per_inch: int = 8000

    # Job checks
    max_depth_in: float = 0.5        # warn if a cut goes deeper than this below Z0
    work_x_in: float = 0.0           # work area size; 0 = don't check
    work_y_in: float = 0.0
    default_feed_in_per_min: float = 10.0  # used for the time estimate if no F is set

    # Making G-code (Make tab)
    # Spindle speeds the mill can be set to. Typical Taig belt steps; change
    # them to the speeds on your mill. One number = a fixed-speed spindle.
    spindle_rpms: str = "1100, 1800, 2700, 4000, 6000, 10000"
    safe_z_in: float = 0.1           # height for moves between cuts (above the top, Z0)
    climb_milling: bool = False      # False = conventional: kinder to an old mill with backlash
    tab_height_in: float = 0.03      # holding tabs left on cut-outs that go all the way through

    def rpm_choices(self) -> list[int]:
        out = []
        for part in self.spindle_rpms.replace(";", ",").split(","):
            try:
                v = int(float(part.strip()))
            except ValueError:
                continue
            if v > 0:
                out.append(v)
        return sorted(set(out)) or [10000]

    def save(self, path: Path | None = None) -> None:
        path = path or settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def app_home() -> Path:
    env = os.environ.get("CNC_APP_HOME")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "A-Tech CNC"


def jobs_dir() -> Path:
    return _ensure(app_home() / "Jobs")


def outbox_dir() -> Path:
    return _ensure(app_home() / "To Old PC")


def received_dir() -> Path:
    return _ensure(app_home() / "Received")


def projects_dir() -> Path:
    return _ensure(app_home() / "Projects")


def tools_path() -> Path:
    return app_home() / "tools.json"


def settings_path() -> Path:
    return app_home() / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    s = Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return s
    for f in fields(Settings):
        if f.name in data:
            try:
                setattr(s, f.name, type(getattr(s, f.name))(data[f.name]))
            except (TypeError, ValueError):
                pass
    return s


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
