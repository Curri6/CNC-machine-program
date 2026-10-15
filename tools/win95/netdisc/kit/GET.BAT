@echo off
rem GET.BAT - fetch a job from the laptop (A-Tech CNC app) into C:\MPSPRO.
rem Use it in an MS-DOS Prompt window inside Windows:  C:\NETUP\GET JOB1.TAP
if "%1"=="" goto usage
if not exist C:\MPSPRO\NUL goto nompspro
echo user anonymous x> C:\NETUP\GET.FTP
echo binary>> C:\NETUP\GET.FTP
echo lcd C:\MPSPRO>> C:\NETUP\GET.FTP
echo get %1>> C:\NETUP\GET.FTP
echo quit>> C:\NETUP\GET.FTP
ftp -n -s:C:\NETUP\GET.FTP 192.168.50.1
echo.
if exist C:\MPSPRO\%1 echo Done: C:\MPSPRO\%1 is ready. Load it in MPS2003 (option 2).
if not exist C:\MPSPRO\%1 echo NOT RECEIVED. Is the app's link on? Is the name right?
goto end
:usage
echo Type the job name after GET, for example:  C:\NETUP\GET JOB1.TAP
goto end
:nompspro
echo C:\MPSPRO is missing.
:end
