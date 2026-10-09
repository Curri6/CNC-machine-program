@echo off
rem Double-click this to burn the Win95 networking disc. It starts
rem burn_win95_disc.ps1 (keep both files in the same folder).
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0burn_win95_disc.ps1"
if errorlevel 1 pause
