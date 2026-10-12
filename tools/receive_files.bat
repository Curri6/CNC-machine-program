@echo off
rem Receives the C:\MPSPRO backup from the old Windows 95 PC over the network cable.
rem Double-click it. Windows asks for administrator rights (needed to set the
rem cable port's address and the temporary firewall rules).
net session >nul 2>&1
if errorlevel 1 (
    echo Asking Windows for administrator rights...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0receive_files.ps1"
pause
