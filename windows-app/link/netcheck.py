"""Network checks for the Machine Link screen.

* has_ip(ip): is this address set on one of the laptop's network ports?
* ping(ip): does the old PC answer?
* run_network_setup(action): open network_setup.ps1 with administrator
  rights (Windows asks first) to set or undo 192.168.50.1 and the
  firewall rules. Nothing changes without the person clicking Yes.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

SETUP_SCRIPT = Path(__file__).with_name("network_setup.ps1")


def has_ip(ip: str) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((ip, 0))
        return True
    except OSError:
        return False


def ping(ip: str, timeout_ms: int = 800) -> bool:
    if sys.platform.startswith("win"):
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip]
        flags = 0
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000 + 3,
                           creationflags=flags)
    except (OSError, subprocess.TimeoutExpired):
        return False
    # Windows ping can return 0 for "Destination host unreachable";
    # a real reply always has a TTL.
    return r.returncode == 0 and "ttl=" in r.stdout.lower()


def run_network_setup(action: str, laptop_ip: str, port: int, state_dir: Path) -> bool:
    """Start the setup script elevated. Returns False if it could not be
    started (not Windows, or the person said No)."""
    if not sys.platform.startswith("win"):
        return False
    import ctypes

    script = getattr(sys, "_MEIPASS", None)
    script = Path(script) / "link" / "network_setup.ps1" if script else SETUP_SCRIPT
    args = (f'-NoProfile -ExecutionPolicy Bypass -File "{script}" -Action {action} '
            f'-LaptopIP {laptop_ip} -Port {port} -StateDir "{state_dir}"')
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", args, None, 1)
    return rc > 32


def setup_state_exists(state_dir: Path) -> bool:
    return (Path(state_dir) / "network_state.txt").exists()


def open_folder(path: Path) -> None:
    path = Path(path)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
