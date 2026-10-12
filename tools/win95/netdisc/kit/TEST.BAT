@echo off
rem TEST.BAT - step 2: try Intel's DOS network driver once, without changing
rem anything. Use it in MS-DOS mode:
rem   Start > Shut Down > "Restart the computer in MS-DOS mode" > Yes
rem   then type   C:\NETUP\TEST
rem   (TEST OLD tries the older 2001 driver instead.)
rem Afterwards type  EXIT  to go back to Windows.
C:
cd \NETUP\ODI
if not exist LSL.COM goto nokit
echo.
echo ===== 1. Loading LSL.COM (Novell Link Support Layer) =====
LSL.COM /C=C:\NETUP\ODI\NET.CFG
echo.
echo ===== 2. Loading E100BODI.COM (Intel network driver) =====
if "%1"=="OLD" goto old
if "%1"=="old" goto old
E100BODI.COM
goto loaded
:old
OLD\E100BODI.COM
:loaded
echo.
echo ===== Take a photo of this whole screen now. =====
echo Look for the adapter's node address and a line about the cable link.
pause
echo Unloading the test drivers ...
if "%1"=="OLD" goto uold
if "%1"=="old" goto uold
E100BODI.COM /U
goto unl
:uold
OLD\E100BODI.COM /U
:unl
LSL.COM /U
cd \
echo Done. Type EXIT to go back to Windows.
goto end
:nokit
cd \
echo C:\NETUP\ODI is missing. Run COPYNET from the disc first (inside Windows).
:end
