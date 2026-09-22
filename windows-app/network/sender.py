"""Send a finished G-code job to the receiver program on the old PC.

Protocol (kept deliberately simple, since the real receiver has to be
written in old, Windows-95-compatible tooling -- see JOURNAL.md):

    1. Connect via plain TCP to the receiver's host:port.
    2. Send a single line "SEND <filename> <byte-count>\\n" (ASCII,
       newline-terminated).
    3. Send exactly <byte-count> bytes of raw G-code file content.
    4. Close the connection.

No authentication, no encryption -- this is intentional. The link is a
private, isolated point-to-point Ethernet cable between only the
Windows 11 PC and the old PC, not the school's shared network, so
there's no one else who could reach it (see JOURNAL.md for the
reasoning). The receiver only ever saves the file; it must never
auto-run it -- a person still has to load and start the job in MPS2003
themselves.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

DEFAULT_PORT = 8420  # arbitrary; must match whatever the VB6/C receiver listens on
CONNECT_TIMEOUT_SECONDS = 5.0


@dataclass
class SendResult:
    ok: bool
    message: str


def send_job(host: str, filename: str, data: bytes, port: int = DEFAULT_PORT) -> SendResult:
    """Send one G-code file to the receiver. Blocking; call from a
    background thread in the UI so the window doesn't freeze."""
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS) as sock:
            header = f"SEND {filename} {len(data)}\n".encode("ascii")
            sock.sendall(header)
            sock.sendall(data)
        return SendResult(ok=True, message=f"Sent {len(data)} bytes to {host}:{port}.")
    except (OSError, socket.timeout) as exc:
        return SendResult(ok=False, message=f"Failed to send to {host}:{port} — {exc}")
