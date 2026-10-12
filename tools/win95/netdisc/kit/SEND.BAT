@echo off
rem SEND.BAT - last step: send all of C:\MPSPRO to the laptop by FTP.
rem The laptop must be running receive_files.bat first.
rem Run it in an MS-DOS Prompt window inside Windows:  C:\NETUP\SEND
rem (SEND C:\OTHER sends a different folder.)
C:
cd \NETUP
if not exist C:\NETUP\MKFTP.COM goto nokit
if not exist C:\WINDOWS\FTP.EXE goto noftp
echo.
if not "%1"=="" goto other
echo Listing C:\MPSPRO ...
MKFTP C:\MPSPRO
goto made
:other
echo Listing %1 ...
MKFTP %1
:made
if errorlevel 4 goto partial
if errorlevel 1 goto mkfail
goto listed
:partial
echo.
echo WARNING: some files above were SKIPPED. Take a photo. The rest will be sent.
pause
:listed
copy /b C:\NETUP\HEAD.FTP+C:\NETUP\BODY.FTP+C:\NETUP\TAIL.FTP C:\NETUP\SEND.FTP > nul
if not exist C:\NETUP\SEND.FTP goto mkfail
echo.
echo Checking the laptop answers ...
ping -n 2 192.168.50.1
echo.
echo Sending (this shows each file; it can take a few minutes) ...
ftp -n -s:C:\NETUP\SEND.FTP 192.168.50.1
echo.
echo ==================================================================
echo Finished. Look at the LAPTOP window: it says CHECK PASSED if every
echo file arrived. Take a photo of both screens.
echo ==================================================================
goto end
:nokit
echo C:\NETUP is missing. Run COPYNET from the disc first.
goto end
:noftp
echo C:\WINDOWS\FTP.EXE is missing. It comes with TCP/IP (Control Panel,
echo Network). Run COPYNET from the disc again; it tries to copy it in.
goto end
:mkfail
echo Could not make the list of files. Take a photo of this screen.
:end
