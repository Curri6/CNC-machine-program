"""A-Tech CNC: jobs, preview and file transfer for the MicroMill.

Run with: python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402
from ui.icon import app_icon  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    if sys.platform.startswith("win"):
        try:  # own taskbar icon instead of Python's
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ATechCNC.App.1")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("A-Tech CNC")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.STYLE)
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
