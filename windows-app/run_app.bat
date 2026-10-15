@echo off
rem Runs A-Tech CNC from source (if you don't have ATechCNC.exe).
rem Needs Python 3.10+ from python.org. The first run installs PySide6 (about 1 minute).
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Setting up for the first time...
    py -3 -m venv .venv || python -m venv .venv || (echo Python is not installed. Get it from python.org & pause & exit /b 1)
    .venv\Scripts\python -m pip install -q -r requirements.txt || (pause & exit /b 1)
)
start "" .venv\Scripts\pythonw.exe main.py
