@echo off
rem Check the burned Win95 disc (read-only). Right-click this file and
rem choose "Run as administrator". Keep next to verify_win95_disc.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0verify_win95_disc.ps1"
if errorlevel 1 pause
