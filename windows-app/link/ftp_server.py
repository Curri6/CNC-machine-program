"""The cable link to the old Windows 95 PC: a tiny FTP server.

The old PC has no modern software, only Windows 95's own FTP.EXE, so
the laptop is the server and the old PC is always the one that starts
a transfer:

* Backup (old PC -> laptop): C:\\NETUP\\SEND on the old PC uploads every
  file of C:\\MPSPRO plus a MANIFEST.TXT of sizes. Files land in
  Received\\received_<date_time>\\ and are checked against the manifest;
  if all arrive with the right size, the folder is zipped.
* Jobs (laptop -> old PC): files in the "To Old PC" folder can be
  fetched with ``get NAME.TAP``. Only plain file names in that folder can
  be fetched. Text jobs are sent with DOS (CRLF) line endings.

Same behavior as tools/receive_files.ps1 (tested there against the real
machine on 2026-10-14). Only active-mode FTP (PORT) is offered, which is
what Windows 95 FTP.EXE uses, and PORT may only point back to the
computer that connected (no FTP bounce).

A job is never started from here: the old PC only receives a file, and
a person at the machine still loads and runs it in MPS2003.
"""

from __future__ import annotations

import datetime as _dt
import re
import socket
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from gcode.dosfile import is_text_job, to_dos_text

_BAD_NAME = re.compile(r'[<>:"|?*\x00-\x1f]')
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", re.I)


@dataclass
class LinkEvent:
    kind: str          # "status" "connect" "file" "manifest" "sent" "check" "error" "session_end"
    text: str
    data: dict | None = None


def resolve_remote(cwd: list[str], arg: str) -> list[str] | None:
    """FTP path (/, \\, C:\\...) -> safe list of names under the backup
    folder, or None if a name is not allowed. '..' never climbs above
    the backup folder."""
    a = arg.strip().replace("\\", "/")
    a = re.sub(r"^[A-Za-z]:", "", a)
    parts = [] if a.startswith("/") else list(cwd)
    for seg in a.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        if (_BAD_NAME.search(seg) or _RESERVED.match(seg) or seg.endswith((".", " "))
                or len(seg) > 100):
            return None
        parts.append(seg)
    if len(parts) > 30:
        return None
    return parts


def read_manifest(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in path.read_bytes().decode("latin-1").splitlines():
        line = line.strip()
        name, _, size = line.rpartition(" ")
        if name and size.isdigit():
            out[name] = int(size)
    return out


def check_backup(folder: Path) -> tuple[bool, list[str], dict[str, int]]:
    """Compare every file listed in MANIFEST.TXT with what arrived."""
    mf = folder / "MANIFEST.TXT"
    if not mf.is_file():
        return False, ["No MANIFEST.TXT arrived, so the files cannot be checked."], {}
    manifest = read_manifest(mf)
    problems = []
    for name, size in manifest.items():
        parts = resolve_remote([], name)
        p = folder.joinpath(*parts) if parts else None
        if p is None or not p.is_file():
            problems.append(f"MISSING: {name}")
        elif p.stat().st_size != size:
            problems.append(f"WRONG SIZE: {name} (old PC {size}, got {p.stat().st_size})")
    return (not problems and bool(manifest)), problems, manifest


class LinkServer:
    def __init__(
        self,
        received_root: Path,
        outbox: Path,
        bind_ip: str = "0.0.0.0",
        port: int = 21,
        allowed_prefix: str | None = "192.168.50.",
        on_event: Callable[[LinkEvent], None] | None = None,
        helper_files: dict[str, bytes] | None = None,
    ):
        self.received_root = Path(received_root)
        self.outbox = Path(outbox)
        self.bind_ip = bind_ip
        self.port = port
        self.allowed_prefix = allowed_prefix
        self.on_event = on_event or (lambda e: None)
        # extra files (e.g. GET.BAT) the old PC can always fetch; not listed
        self.helper_files = dict(helper_files or {})
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ control
    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Bind and start accepting. Raises OSError if the port is busy."""
        if self.running:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.bind_ip, self.port))
        s.listen(4)
        s.settimeout(0.5)
        self._sock = s
        self.port = s.getsockname()[1]
        self._stop.clear()
        self._thread = threading.Thread(target=self._accept_loop, name="cnc-link", daemon=True)
        self._thread.start()
        self._emit("status", f"Link is on (port {self.port}). Waiting for the old PC.")

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        self._sock = None
        self._emit("status", "Link is off.")

    # ------------------------------------------------------------ internals
    def _emit(self, kind: str, text: str, **data) -> None:
        try:
            self.on_event(LinkEvent(kind, text, data or None))
        except Exception:  # never let the UI break the server
            pass

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            ip = addr[0]
            if self.allowed_prefix and not ip.startswith(self.allowed_prefix):
                self._emit("error", f"Refused a connection from {ip} (not the old PC).")
                conn.close()
                continue
            threading.Thread(target=self._session_safe, args=(conn, ip), daemon=True).start()

    def _session_safe(self, conn: socket.socket, ip: str) -> None:
        with self._lock:          # one old PC, one session at a time
            try:
                _Session(self, conn, ip).run()
            except Exception as exc:  # pragma: no cover - logged for the user
                self._emit("error", f"Connection problem: {exc}")
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def outbox_files(self) -> list[Path]:
        try:
            return sorted((p for p in self.outbox.iterdir() if p.is_file()), key=lambda p: p.name.upper())
        except OSError:
            return []

    def outbox_bytes(self, p: Path) -> bytes:
        data = p.read_bytes()
        return to_dos_text(data) if is_text_job(p.name) else data


class _Session:
    def __init__(self, server: LinkServer, conn: socket.socket, ip: str):
        self.srv = server
        self.conn = conn
        self.ip = ip
        self.cwd: list[str] = []
        self.data_ep: tuple[str, int] | None = None
        self.folder: Path | None = None   # created on the first upload
        self.got = 0
        self.got_bytes = 0
        self.expect: dict[str, int] = {}
        conn.settimeout(600)
        self.rfile = conn.makefile("rb")

    # --- helpers
    def send(self, text: str) -> None:
        self.conn.sendall((text + "\r\n").encode("latin-1"))

    def read_line(self) -> str | None:
        raw = self.rfile.readline(4096)
        if not raw:
            return None
        raw = bytes(b for b in raw if b < 0xF0)   # drop telnet IAC bytes
        return raw.decode("latin-1").rstrip("\r\n")

    def ensure_folder(self) -> Path:
        if self.folder is None:
            stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            f = self.srv.received_root / f"received_{stamp}"
            n = 2
            while f.exists():
                f = self.srv.received_root / f"received_{stamp}_{n}"
                n += 1
            f.mkdir(parents=True)
            self.folder = f
        return self.folder

    def local(self, parts: list[str]) -> Path:
        return self.ensure_folder().joinpath(*parts)

    def open_data(self) -> socket.socket | None:
        ep, self.data_ep = self.data_ep, None
        if ep is None:
            return None
        try:
            return socket.create_connection(ep, timeout=15)
        except OSError:
            return None

    def find_outbox(self, arg: str) -> Path | None:
        name = re.split(r"[\\/:]", arg.strip())[-1]
        if name in ("", ".", ".."):
            return None
        for p in self.srv.outbox_files():
            if p.name.upper() == name.upper():
                return p
        return None

    # --- main loop
    def run(self) -> None:
        srv = self.srv
        srv._emit("connect", f"Old PC connected from {self.ip}.", ip=self.ip)
        self.send("220 A-Tech CNC link ready")
        try:
            while True:
                line = self.read_line()
                if line is None:
                    break
                cmd, _, arg = line.partition(" ")
                cmd = cmd.upper()
                if cmd == "QUIT":
                    self.send("221 Bye")
                    break
                self.handle(cmd, arg)
        except (OSError, socket.timeout) as exc:
            srv._emit("error", f"Connection problem: {exc}")
        finally:
            self.finish()

    def finish(self) -> None:
        srv = self.srv
        srv._emit("session_end", f"Session ended: {self.got} file(s) received.",
                  received=self.got, folder=str(self.folder) if self.folder else None)
        if self.folder and (self.folder / "MANIFEST.TXT").is_file():
            ok, problems, manifest = check_backup(self.folder)
            zip_path = None
            if ok:
                zip_path = self.folder.with_suffix(".zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for p in sorted(self.folder.rglob("*")):
                        z.write(p, p.relative_to(self.folder).as_posix())
                total = sum(manifest.values())
                srv._emit("check", f"CHECK PASSED: all {len(manifest)} files arrived with the "
                          f"right sizes ({total} bytes).", ok=True, folder=str(self.folder),
                          zip=str(zip_path), problems=[])
            else:
                srv._emit("check", f"CHECK FAILED: {len(problems)} of {len(manifest)} files missing "
                          "or wrong. Run SEND on the old PC again.", ok=False,
                          folder=str(self.folder), zip=None, problems=problems)

    def handle(self, cmd: str, arg: str) -> None:
        srv = self.srv
        if cmd == "USER":
            self.send("331 Any password will do")
        elif cmd == "PASS":
            self.send("230 Logged in")
        elif cmd == "SYST":
            self.send("215 UNIX Type: L8")
        elif cmd in ("TYPE", "MODE", "STRU", "NOOP", "ALLO"):
            self.send("200 OK")
        elif cmd in ("PWD", "XPWD"):
            self.send(f'257 "/{"/".join(self.cwd)}"')
        elif cmd in ("CWD", "XCWD"):
            p = resolve_remote(self.cwd, arg)
            if p is not None and (not p or (self.folder and self.local(p).is_dir())):
                self.cwd = p
                self.send("250 OK")
            else:
                self.send("550 No such folder")
        elif cmd in ("CDUP", "XCUP"):
            self.cwd = self.cwd[:-1]
            self.send("250 OK")
        elif cmd in ("MKD", "XMKD"):
            p = resolve_remote(self.cwd, arg)
            if not p:
                self.send("553 Name not allowed")
                return
            lp = self.local(p)
            if lp.exists():
                self.send("550 Already exists")
                return
            lp.mkdir(parents=True)
            self.send(f'257 "/{"/".join(p)}" created')
        elif cmd == "PORT":
            nums = arg.split(",")
            try:
                v = [int(x) for x in nums]
                if len(v) != 6 or any(not 0 <= x <= 255 for x in v):
                    raise ValueError
            except ValueError:
                self.send("501 Bad PORT")
                return
            ip = ".".join(map(str, v[:4]))
            port = v[4] * 256 + v[5]
            if ip != self.ip or port < 1024:
                self.send("504 Only the old PC itself")
                return
            self.data_ep = (ip, port)
            self.send("200 PORT OK")
        elif cmd == "STOR":
            self.stor(arg)
        elif cmd == "RETR":
            f = self.find_outbox(arg)
            helper = None
            if f is None:
                want = re.split(r"[\\/:]", arg.strip())[-1].upper()
                helper = next((k for k in srv.helper_files if k.upper() == want), None)
            if helper is not None:
                self.send_bytes(helper, srv.helper_files[helper])
                return
            if f is None:
                self.send("550 Not in the To Old PC folder")
                return
            if self.data_ep is None:
                self.send("425 Send PORT first")
                return
            data = srv.outbox_bytes(f)
            dc = self.open_data()
            if dc is None:
                self.send("425 Could not connect back to the old PC")
                return
            self.send(f"150 Sending {f.name} ({len(data)} bytes)")
            try:
                dc.sendall(data)
                ok = True
            except OSError:
                ok = False
            finally:
                dc.close()
            if ok:
                self.send(f"226 Done, {len(data)} bytes")
                srv._emit("sent", f"Sent to old PC: {f.name} ({len(data)} bytes)",
                          name=f.name, size=len(data))
            else:
                self.send("426 Transfer broke off")
                srv._emit("error", f"Sending {f.name} broke off.")
        elif cmd in ("LIST", "NLST"):
            if self.data_ep is None:
                self.send("425 Send PORT first")
                return
            rows = []
            for f in srv.outbox_files():
                if cmd == "NLST":
                    rows.append(f.name)
                else:
                    t = _dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d %H:%M")
                    rows.append(f"-rw-r--r-- 1 owner group {len(srv.outbox_bytes(f)):>10} {t} {f.name}")
            dc = self.open_data()
            if dc is None:
                self.send("425 Could not connect back to the old PC")
                return
            self.send("150 Files in To Old PC")
            try:
                dc.sendall("".join(r + "\r\n" for r in rows).encode("latin-1"))
            except OSError:
                pass
            finally:
                dc.close()
            self.send("226 Done")
        else:
            self.send("502 Not supported here")

    def send_bytes(self, name: str, data: bytes) -> None:
        if self.data_ep is None:
            self.send("425 Send PORT first")
            return
        dc = self.open_data()
        if dc is None:
            self.send("425 Could not connect back to the old PC")
            return
        self.send(f"150 Sending {name} ({len(data)} bytes)")
        try:
            dc.sendall(data)
        finally:
            dc.close()
        self.send(f"226 Done, {len(data)} bytes")
        self.srv._emit("sent", f"Sent to old PC: {name} ({len(data)} bytes)", name=name,
                       size=len(data), helper=True)

    def stor(self, arg: str) -> None:
        srv = self.srv
        p = resolve_remote(self.cwd, arg)
        if not p:
            self.send("553 Name not allowed")
            return
        if self.data_ep is None:
            self.send("425 Send PORT first")
            return
        lp = self.local(p)
        lp.parent.mkdir(parents=True, exist_ok=True)
        dc = self.open_data()
        if dc is None:
            self.send("425 Could not connect back to the old PC")
            return
        self.send("150 Sending")
        tmp = lp.with_name(lp.name + ".part")
        n = 0
        ok = True
        try:
            dc.settimeout(60)
            with open(tmp, "wb") as fh:
                while True:
                    chunk = dc.recv(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
                    n += len(chunk)
        except OSError:
            ok = False
        finally:
            dc.close()
        if not ok:
            tmp.unlink(missing_ok=True)
            self.send("426 Transfer broke off")
            srv._emit("error", f"Receiving /{'/'.join(p)} broke off.")
            return
        tmp.replace(lp)
        name = "/".join(p)
        if len(p) == 1 and name.upper() == "MANIFEST.TXT":
            self.expect = read_manifest(lp)
            srv._emit("manifest", f"List of files received: {len(self.expect)} files, "
                      f"{sum(self.expect.values())} bytes to come.",
                      files=len(self.expect), total=sum(self.expect.values()))
        else:
            self.got += 1
            self.got_bytes += n
            srv._emit("file", f"{name}  {n} bytes", name=name, size=n, index=self.got,
                      total_files=len(self.expect), got_bytes=self.got_bytes,
                      total_bytes=sum(self.expect.values()))
        self.send(f"226 Done, {n} bytes")
