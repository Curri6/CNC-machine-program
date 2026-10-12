@echo off
rem CHECK.BAT - shows what is set up, for a photo. Changes nothing.
rem Run it in an MS-DOS Prompt window inside Windows:  C:\NETUP\CHECK
echo ===== C:\AUTOEXEC.BAT =====
if exist C:\AUTOEXEC.BAT type C:\AUTOEXEC.BAT
echo ===== network programs in memory (each should be listed once) =====
mem /c | find /i "LSL"
mem /c | find /i "E100BODI"
mem /c | find /i "ODIHLP"
echo ===== Windows files =====
if exist C:\WINDOWS\ODIHLP.EXE echo ODIHLP.EXE found
if exist C:\WINDOWS\FTP.EXE echo FTP.EXE found
if exist C:\WINDOWS\PROTOCOL.INI echo PROTOCOL.INI found
echo ===== can it reach the laptop? =====
ping -n 2 192.168.50.1
echo Take a photo of this screen.
