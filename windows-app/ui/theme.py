"""Colors and the Qt style sheet: a clean, light Windows 11-style look."""

from __future__ import annotations

ACCENT = "#2563eb"
ACCENT_DARK = "#1d4ed8"
ACCENT_SOFT = "#dbeafe"
BG = "#f3f5f9"
CARD = "#ffffff"
BORDER = "#e2e6ee"
TEXT = "#1f2937"
MUTED = "#6b7280"
OK = "#16a34a"
WARN = "#d97706"
BAD = "#dc2626"
INFO = "#2563eb"

# preview colors
VIEW_BG = "#141922"
VIEW_GRID = "#232b38"
VIEW_GRID_MAJOR = "#2f3a4b"
VIEW_RAPID = "#7c8799"
VIEW_TOOL = "#fb923c"
VIEW_HILITE = "#facc15"
VIEW_ORIGIN = "#ef4444"

STYLE = f"""
* {{ font-family: "Segoe UI", "Segoe UI Variable", Arial, sans-serif; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QWidget#Page {{ background: {BG}; }}
QDialog, QMessageBox {{ background: {CARD}; }}
QWidget#Header {{ background: {CARD}; border-bottom: 1px solid {BORDER}; }}
QLabel#AppTitle {{ font-size: 15pt; font-weight: 600; }}
QLabel#AppSub {{ color: {MUTED}; }}
QFrame#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#CardTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Big {{ font-size: 14pt; font-weight: 600; }}
QLabel#TileValue {{ font-size: 12.5pt; font-weight: 600; }}
QLabel#TileLabel {{ color: {MUTED}; font-size: 8.5pt; }}
QFrame#Tile {{ background: {BG}; border-radius: 8px; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 8px 18px; margin: 4px 2px;
                border-radius: 8px; font-weight: 600; }}
QTabBar::tab:selected {{ background: {ACCENT_SOFT}; color: {ACCENT_DARK}; }}
QTabBar::tab:hover:!selected {{ background: #eef1f6; color: {TEXT}; }}

QPushButton {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 7px; padding: 7px 14px; }}
QPushButton:hover {{ background: #f5f7fb; border-color: #c9d1de; }}
QPushButton:pressed {{ background: #e9edf4; }}
QPushButton:disabled {{ color: #a3aab6; background: #f6f7f9; }}
QPushButton#Primary {{ background: {ACCENT}; color: white; border: 1px solid {ACCENT}; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {ACCENT_DARK}; }}
QPushButton#Primary:disabled {{ background: #9db7f0; border-color: #9db7f0; color: #eef3ff; }}
QPushButton#Danger {{ color: {BAD}; }}
QPushButton#Flat, QToolButton#Flat {{ border: none; background: transparent; padding: 5px 9px; }}
QPushButton#Flat:hover, QToolButton#Flat:hover {{ background: #eef1f6; }}
QToolButton#Seg {{ background: {CARD}; border: 1px solid {BORDER}; padding: 5px 11px; }}
QToolButton#Seg:checked {{ background: {ACCENT_SOFT}; color: {ACCENT_DARK}; border-color: #b9cdfa; font-weight: 600; }}

QListWidget, QPlainTextEdit, QTextBrowser, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QListWidget::item {{ padding: 7px 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QListWidget::item:hover:!selected {{ background: #f3f6fb; }}
QPlainTextEdit#Code {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 9.5pt; }}
QPlainTextEdit#Log {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt; }}

QSlider::groove:horizontal {{ height: 6px; background: {BORDER}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: white; border: 2px solid {ACCENT}; width: 14px; margin: -6px 0; border-radius: 9px; }}
QProgressBar {{ background: {BORDER}; border: none; border-radius: 5px; height: 10px; text-align: center; font-size: 8pt; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QStatusBar {{ background: {CARD}; border-top: 1px solid {BORDER}; color: {MUTED}; }}
QSplitter::handle {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: #cfd6e2; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #cfd6e2; border-radius: 4px; min-width: 30px; }}
QToolTip {{ background: {TEXT}; color: white; border: none; padding: 5px; }}
"""
