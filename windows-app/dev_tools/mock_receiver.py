"""DEV/TEST TOOL ONLY -- not the real receiver.

This stands in for the actual receiver program that has to be written
separately for the old Windows 95 PC (in Visual Basic 6 or C with
Winsock -- see JOURNAL.md; Windows 95 can't run Python). It exists so
the Windows 11 app's networking code can be tested on a modern machine
without needing the real vintage hardware.

Speaks the same tiny protocol as network/sender.py: a "SEND <filename>
<byte-count>\\n" header followed by that many bytes, then closes.
Saves each received file into ./received_jobs/ and never runs anything
-- matching the standing safety rule that a job must never auto-start.

Usage: python mock_receiver.py [port]
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

DEFAULT_PORT = 8420
OUTPUT_DIR = Path(__file__).resolve().parent / "received_jobs"


def _read_line(conn: socket.socket) -> bytes:
    buf = bytearray()
    while not buf.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            break
        buf += chunk
    return bytes(buf)


def _read_exact(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(min(4096, n - len(buf)))
        if not chunk:
            break
        buf += chunk
    return bytes(buf)


def handle_connection(conn: socket.socket, addr) -> None:
    with conn:
        header = _read_line(conn).decode("ascii", errors="replace").strip()
        if not header.startswith("SEND "):
            print(f"[mock_receiver] Bad header from {addr}: {header!r}")
            return
        _, filename, size_str = header.split(" ", 2)
        size = int(size_str)
        data = _read_exact(conn, size)
        if len(data) != size:
            print(
                f"[mock_receiver] Short read from {addr}: expected {size}, "
                f"got {len(data)}"
            )
            return

        OUTPUT_DIR.mkdir(exist_ok=True)
        dest = OUTPUT_DIR / Path(filename).name
        dest.write_bytes(data)
        print(f"[mock_receiver] Saved {len(data)} bytes from {addr} -> {dest}")
        print("[mock_receiver] (not auto-running it -- matches the real receiver's behavior)")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(1)
        print(f"[mock_receiver] Listening on port {port}. Ctrl+C to stop.")
        try:
            while True:
                conn, addr = server.accept()
                handle_connection(conn, addr)
        except KeyboardInterrupt:
            print("\n[mock_receiver] Stopped.")


if __name__ == "__main__":
    main()
