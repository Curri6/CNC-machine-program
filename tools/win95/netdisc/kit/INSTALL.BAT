@echo off
rem INSTALL.BAT - step 3: make Windows 95 load Intel's DOS network driver at
rem every start-up. Adds ONE line to the top of C:\AUTOEXEC.BAT:
rem     @call C:\NETUP\LOADODI.BAT
rem A copy of the old file is kept as C:\NETUP\AUTOEXEC.OLD.
rem C:\NETUP\UNDO.BAT puts the old file back.
if not exist C:\NETUP\LOADODI.BAT goto nokit
if not exist C:\NETUP\TOPLINE.TXT goto nokit
if exist C:\NETUP\INSTALL.TAG goto already
if not exist C:\AUTOEXEC.BAT goto noauto
attrib -r -h -s C:\AUTOEXEC.BAT
copy C:\AUTOEXEC.BAT C:\NETUP\AUTOEXEC.OLD > nul
if not exist C:\NETUP\AUTOEXEC.OLD goto fail
if exist C:\NETUP\AUTOEXEC.NEW del C:\NETUP\AUTOEXEC.NEW
copy /b C:\NETUP\TOPLINE.TXT+C:\AUTOEXEC.BAT C:\NETUP\AUTOEXEC.NEW > nul
if not exist C:\NETUP\AUTOEXEC.NEW goto fail
copy C:\NETUP\AUTOEXEC.NEW C:\AUTOEXEC.BAT > nul
del C:\NETUP\AUTOEXEC.NEW
echo had > C:\NETUP\INSTALL.TAG
goto done
:noauto
if exist C:\NETUP\AUTOEXEC.OLD del C:\NETUP\AUTOEXEC.OLD
copy C:\NETUP\TOPLINE.TXT C:\AUTOEXEC.BAT > nul
echo none > C:\NETUP\INSTALL.TAG
goto done

:done
echo.
echo INSTALLED. C:\AUTOEXEC.BAT now starts like this:
echo ------------------------------------------------
type C:\AUTOEXEC.BAT
echo ------------------------------------------------
echo Take a photo of this screen.
goto end
:already
echo Already installed (C:\NETUP\INSTALL.TAG exists). Nothing changed.
echo C:\NETUP\UNDO.BAT removes it.
goto end
:nokit
echo C:\NETUP is missing files. Run COPYNET from the disc first.
goto end
:fail
echo FAILED - C:\AUTOEXEC.BAT was NOT changed.
:end
