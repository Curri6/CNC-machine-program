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
rem TYPE + redirection, not COPY: DOS COPY skips a 0-byte file, and Windows
rem 95 often leaves C:\AUTOEXEC.BAT empty (it did on this PC, 2026-10-14).
if exist C:\NETUP\AUTOEXEC.OLD del C:\NETUP\AUTOEXEC.OLD
type C:\AUTOEXEC.BAT > C:\NETUP\AUTOEXEC.OLD
if not exist C:\NETUP\AUTOEXEC.OLD goto fail
if exist C:\NETUP\AUTOEXEC.NEW del C:\NETUP\AUTOEXEC.NEW
type C:\NETUP\TOPLINE.TXT > C:\NETUP\AUTOEXEC.NEW
type C:\AUTOEXEC.BAT >> C:\NETUP\AUTOEXEC.NEW
if not exist C:\NETUP\AUTOEXEC.NEW goto fail
type C:\NETUP\AUTOEXEC.NEW > C:\AUTOEXEC.BAT
del C:\NETUP\AUTOEXEC.NEW
echo had > C:\NETUP\INSTALL.TAG
goto done
:noauto
if exist C:\NETUP\AUTOEXEC.OLD del C:\NETUP\AUTOEXEC.OLD
type C:\NETUP\TOPLINE.TXT > C:\AUTOEXEC.BAT
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
