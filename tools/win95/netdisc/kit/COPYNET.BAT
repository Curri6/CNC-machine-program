@echo off
rem COPYNET.BAT - step 1: copy this network kit from the disc to C:\NETUP.
rem Run it inside Windows, in an MS-DOS Prompt window:
rem     H:          (the CD/DVD drive letter)
rem     COPYNET
if not exist \NETDISC.TAG goto wrongdir
echo.
echo Copying the network kit to C:\NETUP ...
xcopy \*.* C:\NETUP\ /s /e /c
if not exist C:\NETUP\NETDISC.TAG goto copyfail
if not exist C:\NETUP\MKFTP.COM goto copyfail
if not exist C:\NETUP\ODI\LSL.COM goto copyfail
if not exist C:\NETUP\ODI\E100BODI.COM goto copyfail
if not exist C:\NETUP\ODI\NET.CFG goto copyfail
if not exist C:\NETUP\LOADODI.BAT goto copyfail
attrib -r C:\NETUP\*.* /s
echo.
echo Looking for ODIHLP.EXE and FTP.EXE (Windows 95 files) ...
C:
if exist C:\WINDOWS\ODIHLP.EXE goto haveodi
if not exist C:\NETSETUP\WIN95\NUL goto haveodi
cd \NETSETUP\WIN95
for %%c in (*.CAB) do extract /y /l C:\WINDOWS %%c odihlp.exe
cd \
:haveodi
if exist C:\WINDOWS\FTP.EXE goto haveftp
if not exist C:\NETSETUP\WIN95\NUL goto haveftp
cd \NETSETUP\WIN95
for %%c in (*.CAB) do extract /y /l C:\WINDOWS %%c ftp.exe
cd \
:haveftp
echo.
echo ==================== RESULT ====================
echo Kit copied to C:\NETUP: OK
if exist C:\WINDOWS\ODIHLP.EXE echo ODIHLP.EXE: found
if not exist C:\WINDOWS\ODIHLP.EXE echo ODIHLP.EXE: NOT FOUND (Windows will ask for it later)
if exist C:\WINDOWS\FTP.EXE echo FTP.EXE: found
if not exist C:\WINDOWS\FTP.EXE echo FTP.EXE: NOT FOUND (comes with TCP/IP)
echo ================================================
echo Take a photo of this screen.
goto end

:wrongdir
echo.
echo This must be run from the disc. Type the disc's drive letter
echo first (for example  H:  then Enter), then type  COPYNET
goto end

:copyfail
echo.
echo COPY FAILED - some files did not reach C:\NETUP.
echo Take the disc out, put it back in, wait 10 seconds, and run COPYNET again.
goto end

:end
