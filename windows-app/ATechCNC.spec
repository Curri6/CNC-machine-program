# PyInstaller recipe for A-Tech CNC.exe (one file, no console window).
# Build on Windows:  pip install -r requirements.txt pyinstaller
#                    pyinstaller ATechCNC.spec
# The exe lands in dist\ATechCNC.exe.
a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=[("link/network_setup.ps1", "link"), ("assets/app.png", "assets")],
    excludes=["tkinter", "matplotlib", "numpy", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="ATechCNC",
    icon="assets/app.ico",
    console=False,
    upx=False,
)
