@echo off
rem UNDO.BAT - puts C:\AUTOEXEC.BAT back the way it was before INSTALL.BAT.
if not exist C:\NETUP\INSTALL.TAG goto notinst
attrib -r -h -s C:\AUTOEXEC.BAT
if exist C:\NETUP\AUTOEXEC.OLD goto restore
rem There was no AUTOEXEC.BAT before INSTALL; keep any lines Windows added
rem since, but take out ours.
find /v /i "NETUP\LOADODI" < C:\AUTOEXEC.BAT > C:\NETUP\AUTOEXEC.TMP
type C:\NETUP\AUTOEXEC.TMP > C:\AUTOEXEC.BAT
del C:\NETUP\AUTOEXEC.TMP
goto undone
:restore
rem TYPE, not COPY, so an empty (0-byte) old file is restored too
type C:\NETUP\AUTOEXEC.OLD > C:\AUTOEXEC.BAT
:undone
del C:\NETUP\INSTALL.TAG
echo UNDONE. C:\AUTOEXEC.BAT is back to how it was. Restart the computer.
goto end
:notinst
echo INSTALL.BAT was not used (no C:\NETUP\INSTALL.TAG). Nothing changed.
:end
