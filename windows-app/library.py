"""The job library (Documents\\A-Tech CNC\\Jobs) and getting a job ready
for the old PC. No UI here, so it can be tested on its own."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from app_config import Settings
from gcode.analysis import JobStats, analyze
from gcode.dosfile import dos_name, is_dos_name, to_dos_text
from gcode.parser import ParseResult, parse_gcode
from link.ftp_server import read_manifest

JOB_EXTS = {".tap", ".nc", ".gcode", ".gco", ".ngc", ".cnc", ".ncc", ".txt"}


@dataclass
class Job:
    path: Path
    text: str
    result: ParseResult
    stats: JobStats


class JobLibrary:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._cache: dict[Path, tuple[float, int, Job]] = {}

    def jobs(self) -> list[Path]:
        return sorted((p for p in self.folder.iterdir()
                       if p.is_file() and p.suffix.lower() in JOB_EXTS),
                      key=lambda p: p.name.lower())

    def add(self, sources: list[Path]) -> list[tuple[Path, str]]:
        """Copy files into the library. Returns (path, note) per file;
        note is '' / 'already there' / 'renamed' / an error message."""
        out = []
        for src in sources:
            src = Path(src)
            if not src.is_file():
                out.append((src, "not a file"))
                continue
            if src.suffix.lower() not in JOB_EXTS:
                out.append((src, f"not a job file ({src.suffix or 'no extension'})"))
                continue
            dest = self.folder / src.name
            if dest.exists() and dest.read_bytes() == src.read_bytes():
                out.append((dest, "already there"))
                continue
            note = ""
            n = 2
            while dest.exists():
                dest = self.folder / f"{src.stem} ({n}){src.suffix}"
                note = "renamed"
                n += 1
            try:
                shutil.copy2(src, dest)
            except OSError as exc:
                out.append((src, str(exc)))
                continue
            out.append((dest, note))
        return out

    def remove(self, path: Path) -> None:
        path = Path(path)
        if path.parent.resolve() != self.folder.resolve():
            raise ValueError("only files in the job library can be removed")
        path.unlink(missing_ok=True)
        self._cache.pop(path, None)

    def load(self, path: Path, settings: Settings) -> Job:
        path = Path(path)
        st = path.stat()
        hit = self._cache.get(path)
        if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
            return hit[2]
        text = path.read_bytes().decode("latin-1")
        result = parse_gcode(text)
        job = Job(path, text, result, analyze(result, settings, path.name))
        self._cache[path] = (st.st_mtime, st.st_size, job)
        return job

    def refresh_settings(self) -> None:
        self._cache.clear()


def suggest_old_pc_name(name: str, outbox: Path) -> str:
    upper = name.upper()
    if is_dos_name(upper) and upper.rsplit(".", 1)[-1] in ("TAP", "NC", "TXT"):
        return upper
    return dos_name(name)


def old_pc_names(received_dir: Path) -> set[str]:
    """File names C:\\MPSPRO had in the newest backup (from its manifest)."""
    folders = sorted((p for p in Path(received_dir).glob("received_*") if p.is_dir()),
                     key=lambda p: p.name)
    for f in reversed(folders):
        mf = f / "MANIFEST.TXT"
        if mf.is_file():
            return {k.rsplit("/", 1)[-1].upper() for k in read_manifest(mf)}
    return set()


def put_in_outbox(src: Path, name: str, outbox: Path) -> Path:
    """Copy a job into the To Old PC folder under its DOS name, with DOS
    line endings. The old PC then fetches it with GET NAME."""
    name = name.upper()
    if not is_dos_name(name):
        raise ValueError(f"'{name}' is not a DOS 8.3 name (up to 8 letters, a dot, up to 3).")
    dest = Path(outbox) / name
    dest.write_bytes(to_dos_text(Path(src).read_bytes()))
    return dest
