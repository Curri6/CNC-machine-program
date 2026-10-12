@echo off
rem LOADODI.BAT - loads Intel's DOS network driver before Windows 95 starts.
rem Called from the first line of C:\AUTOEXEC.BAT (added by C:\NETUP\INSTALL.BAT).
rem Press N at the start-up question to skip it once; C:\NETUP\UNDO.BAT removes it.
if not exist C:\NETUP\ODI\E100BODI.COM goto end
if not exist C:\WINDOWS\COMMAND\CHOICE.COM goto load
echo.
C:\WINDOWS\COMMAND\CHOICE.COM /C:YN /T:Y,5 Load the network driver? Press N to skip
if errorlevel 2 goto end
:load
C:
cd \NETUP\ODI
LSL.COM /C=C:\NETUP\ODI\NET.CFG
E100BODI.COM
cd \
rem ODIHLP.EXE joins the driver to Windows 95. If Windows already put its
rem own ODIHLP line in AUTOEXEC.BAT, let that one load it (never twice).
if not exist C:\WINDOWS\ODIHLP.EXE goto end
if not exist C:\WINDOWS\COMMAND\FIND.EXE goto hlp
C:\WINDOWS\COMMAND\FIND.EXE /i "ODIHLP" < C:\AUTOEXEC.BAT > nul
if not errorlevel 1 goto end
:hlp
C:\WINDOWS\ODIHLP.EXE
:end
