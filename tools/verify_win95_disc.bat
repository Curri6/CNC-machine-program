@echo off
rem Double-click to check the burned Win95 disc (read-only). Keep next to
rem verify_win95_disc.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0verify_win95_disc.ps1"
if errorlevel 1 pause
