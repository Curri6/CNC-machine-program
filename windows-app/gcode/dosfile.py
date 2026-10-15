"""Make job files safe for the old Windows 95 / MS-DOS PC.

MPS2003 is a DOS program: it lists jobs by their short 8.3 names
(up to 8 letters, a dot, up to 3 letters) and reads text with DOS
(CRLF) line endings.
"""

from __future__ import annotations

import re

# characters used when *making* a name: plain and easy to type in DOS
_DOS_OK = re.compile(r"[A-Z0-9_-]")
DOS_NAME_RE = re.compile(r"^[A-Z0-9_$~!#%&{}()@^-]{1,8}(\.[A-Z0-9_$~!#%&{}()@^-]{1,3})?$")
TEXT_JOB_EXTS = {".TAP", ".NC", ".TXT", ".GCO", ".GCODE", ".CNC", ".NCC", ".NGC"}
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)}


def is_dos_name(name: str) -> bool:
    return bool(DOS_NAME_RE.match(name)) and name.split(".")[0] not in _RESERVED


def dos_name(name: str, taken: set[str] | frozenset[str] = frozenset()) -> str:
    """Turn any file name into an 8.3 DOS name, e.g.
    'my gear (v2).nc' -> 'MYGEARV2.TAP'. Job files get the .TAP extension,
    which is what MPS2003's Load Program lists by default. `taken` holds
    upper-case names already in use; a ~N suffix keeps the result unique."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    ext_u = "." + ext.upper() if ext else ""
    if not ext or ext_u in TEXT_JOB_EXTS:
        ext_u = ".TAP"
    else:
        ext_u = "." + "".join(c for c in ext.upper() if _DOS_OK.match(c))[:3]
        if ext_u == ".":
            ext_u = ".TAP"
    base = "".join(c for c in stem.upper() if _DOS_OK.match(c)) or "JOB"
    if base in _RESERVED:
        base = "J" + base
    candidate = base[:8] + ext_u
    taken_u = {t.upper() for t in taken}
    n = 1
    while candidate in taken_u:
        suffix = f"~{n}"
        candidate = base[: 8 - len(suffix)] + suffix + ext_u
        n += 1
    return candidate


def to_dos_text(data: bytes) -> bytes:
    """CRLF line endings, ending with one CRLF. Bytes are kept as-is
    otherwise (Latin-1 round trip)."""
    text = data.decode("latin-1")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip("\n\x1a") + "\n"
    return text.replace("\n", "\r\n").encode("latin-1")


def is_text_job(name: str) -> bool:
    _, dot, ext = name.rpartition(".")
    return bool(dot) and ("." + ext.upper()) in TEXT_JOB_EXTS
