#!/bin/bash
# Runs the old-PC batch files (tools/win95/netdisc/kit) in DOSBox with
# stand-in programs (tools/tests/stub.asm) that log what would have run.
# Needs: nasm, dosbox.  Run: bash tools/tests/test_netdisc_bats.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
KIT="$HERE/../win95/netdisc/kit"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
fail=0
check() { if [ "$1" = "$2" ]; then echo "PASS $3"; else echo "FAIL $3"; echo "  expected: $(echo "$2" | head -5)"; echo "  got:      $(echo "$1" | head -5)"; fail=1; fi; }
crlf() { sed 's/\r$//; s/$/\r/' "$1" > "$2"; }
stub() { nasm -f bin -DTAG="'$2'" -DEXITCODE=$3 -o "$1" "$HERE/stub.asm"; }
t() { tr -d '\r' < "$1" 2>/dev/null; }

# fresh fake C: drive with the kit in C:\NETUP and stand-ins for Windows tools
fresh() {
  rm -rf "$W/c"; mkdir -p "$W/c/NETUP/ODI" "$W/c/WINDOWS/COMMAND" "$W/c/STUB"
  for f in "$KIT"/*.* "$KIT"/ODI/*.*; do crlf "$f" "$W/c/NETUP/${f#$KIT/}"; done
  nasm -f bin -o "$W/c/NETUP/MKFTP.COM" "$HERE/../win95/netdisc/src/MKFTP.ASM"
  stub "$W/c/NETUP/ODI/LSL.COM" 'LSL' 0
  stub "$W/c/NETUP/ODI/E100BODI.COM" 'E100BODI' 0
  stub "$W/c/WINDOWS/ODIHLP.EXE" 'ODIHLP' 0
  stub "$W/c/STUB/ATTRIB.COM" 'ATTRIB' 0
  stub "$W/c/STUB/FTP.COM" 'FTP' 0
  stub "$W/c/STUB/PING.COM" 'PING' 0
  : > "$W/c/WINDOWS/FTP.EXE"
}
run() {  # run DOS commands, one per argument
  # (DOSBox hangs if a whole batch file's output is redirected, so each
  #  batch runs under its own COMMAND /C, and RUNME.BAT ends with EXIT)
  printf '%s\r\n' '@echo off' 'set PATH=C:\STUB;Z:\' "$@" 'exit' > "$W/c/RUNME.BAT"
  local a=(); a+=(-c "mount c $W/c" -c "c:" -c "RUNME.BAT")
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 40 dosbox -noconsole "${a[@]}" >/dev/null 2>&1
}

# ---------- INSTALL / UNDO with an existing AUTOEXEC.BAT ----------
fresh
printf 'SET BLASTER=A220\r\nPATH C:\\WINDOWS;C:\\WINDOWS\\COMMAND\r\n' > "$W/c/AUTOEXEC.BAT"
cp "$W/c/AUTOEXEC.BAT" "$W/orig.bat"
run 'command /c C:\NETUP\INSTALL.BAT > C:\OUT.TXT'
check "$(t "$W/c/AUTOEXEC.BAT")" "$(printf '@call C:\\NETUP\\LOADODI.BAT\nSET BLASTER=A220\nPATH C:\\WINDOWS;C:\\WINDOWS\\COMMAND')" "INSTALL puts one line on top, keeps the rest"
cmp -s "$W/c/NETUP/AUTOEXEC.OLD" "$W/orig.bat" && r=1 || r=0
check "$r" "1" "INSTALL keeps an exact copy of the old AUTOEXEC.BAT"
[ -f "$W/c/NETUP/INSTALL.TAG" ] && r=1 || r=0
check "$r" "1" "INSTALL leaves its marker"
# (INSTALL's success message is not checked: DOSBox drops the outer
#  redirect after the "> nul" lines inside the batch; real Windows 95 doesn't)
run 'command /c C:\NETUP\INSTALL.BAT > C:\OUT.TXT'
check "$(grep -c LOADODI "$W/c/AUTOEXEC.BAT")" "1" "INSTALL twice adds the line only once"
grep -q 'Already installed' "$W/c/OUT.TXT" && r=1 || r=0
check "$r" "1" "INSTALL twice says already installed"
run 'command /c C:\NETUP\UNDO.BAT > C:\OUT.TXT'
cmp -s "$W/c/AUTOEXEC.BAT" "$W/orig.bat" && r=1 || r=0
check "$r" "1" "UNDO restores AUTOEXEC.BAT exactly"
[ -f "$W/c/NETUP/INSTALL.TAG" ] && r=0 || r=1
check "$r" "1" "UNDO removes the marker"
run 'command /c C:\NETUP\UNDO.BAT > C:\OUT.TXT'
grep -q 'Nothing changed' "$W/c/OUT.TXT" && r=1 || r=0
check "$r" "1" "UNDO when not installed changes nothing"
cmp -s "$W/c/AUTOEXEC.BAT" "$W/orig.bat" && r=1 || r=0
check "$r" "1" "AUTOEXEC.BAT still original after second UNDO"

# ---------- INSTALL with no AUTOEXEC.BAT ----------
fresh
run 'command /c C:\NETUP\INSTALL.BAT > C:\OUT.TXT'
check "$(t "$W/c/AUTOEXEC.BAT")" '@call C:\NETUP\LOADODI.BAT' "INSTALL creates AUTOEXEC.BAT when there was none"
check "$(t "$W/c/NETUP/INSTALL.TAG" | tr -d ' ')" "none" "marker says there was none"

# ---------- LOADODI at start-up ----------
loadodi() {  # $1 = CHOICE exit code, $2 = FIND exit code (0 found, 1 not)
  fresh
  stub "$W/c/WINDOWS/COMMAND/CHOICE.COM" 'CHOICE' "$1"
  stub "$W/c/WINDOWS/COMMAND/FIND.EXE" 'FIND' "$2"
  printf '@call C:\\NETUP\\LOADODI.BAT\r\nPATH C:\\WINDOWS\r\n' > "$W/c/AUTOEXEC.BAT"
  rm -f "$W/c/LOG.TXT"
  run 'command /c C:\NETUP\LOADODI.BAT > C:\OUT.TXT' 'cd > C:\CWD.TXT'
}
loadodi 1 1
check "$(t "$W/c/LOG.TXT")" "$(printf 'CHOICE /C:YN /T:Y,5 Load the network driver? Press N to skip\nLSL /C=C:\\NETUP\\ODI\\NET.CFG\nE100BODI\nFIND /i "ODIHLP"\nODIHLP')" "start-up: Y loads LSL, E100BODI, then ODIHLP"
check "$(t "$W/c/CWD.TXT")" 'C:\' "start-up leaves the current folder at C:\\"
loadodi 1 0
check "$(t "$W/c/LOG.TXT" | grep -c ODIHLP$)" "0" "start-up: ODIHLP not loaded twice when Windows already loads it"
grep -q '^E100BODI' <(t "$W/c/LOG.TXT") && r=1 || r=0
check "$r" "1" "start-up: driver still loaded in that case"
loadodi 2 1
check "$(t "$W/c/LOG.TXT" | grep -v '^CHOICE')" "" "start-up: N skips everything"
fresh; rm -f "$W/c/LOG.TXT"; printf 'X\r\n' > "$W/c/AUTOEXEC.BAT"
stub "$W/c/WINDOWS/COMMAND/FIND.EXE" 'FIND' 1
run 'command /c C:\NETUP\LOADODI.BAT > C:\OUT.TXT'
check "$(t "$W/c/LOG.TXT" | head -1)" 'LSL /C=C:\NETUP\ODI\NET.CFG' "start-up: no CHOICE.COM -> loads without asking"

# ---------- SEND ----------
fresh
mkdir -p "$W/c/MPSPRO/MILL"; printf 'G0 X0\r\n' > "$W/c/MPSPRO/GEAR.TAP"; head -c 999 /dev/urandom > "$W/c/MPSPRO/MILL/MILL.EXE"
rm -f "$W/c/LOG.TXT"
run 'command /c C:\NETUP\SEND.BAT > C:\OUT.TXT'
check "$(t "$W/c/LOG.TXT")" "$(printf 'PING -n 2 192.168.50.1\nFTP -n -s:C:\\NETUP\\SEND.FTP 192.168.50.1')" "SEND pings the laptop then runs FTP with the script"
exp='user anonymous guest
binary
put C:\NETUP\MANIFEST.TXT MANIFEST.TXT
mkdir MPSPRO
put C:\MPSPRO\GEAR.TAP MPSPRO/GEAR.TAP
mkdir MPSPRO/MILL
put C:\MPSPRO\MILL\MILL.EXE MPSPRO/MILL/MILL.EXE
quit'
check "$(t "$W/c/NETUP/SEND.FTP" | sort)" "$(echo "$exp" | sort)" "SEND.FTP = login, manifest, every file, quit"
check "$(t "$W/c/NETUP/SEND.FTP" | head -3 | tail -1)" 'put C:\NETUP\MANIFEST.TXT MANIFEST.TXT' "manifest goes first"
check "$(t "$W/c/NETUP/SEND.FTP" | tail -1)" 'quit' "script ends with quit"
check "$(t "$W/c/NETUP/MANIFEST.TXT" | sort)" "$(printf 'MPSPRO/GEAR.TAP 7\nMPSPRO/MILL/MILL.EXE 999')" "manifest sizes"
# folder missing: must not run FTP
fresh; rm -f "$W/c/LOG.TXT"
run 'command /c C:\NETUP\SEND.BAT > C:\OUT.TXT'
[ -f "$W/c/LOG.TXT" ] && r=0 || r=1
check "$r" "1" "SEND with no C:\\MPSPRO does not start FTP"
grep -q 'Could not make the list' "$W/c/OUT.TXT" && r=1 || r=0
check "$r" "1" "SEND with no C:\\MPSPRO says so"
# other folder by argument
fresh; mkdir -p "$W/c/OTHER"; printf 'x' > "$W/c/OTHER/A.TXT"; rm -f "$W/c/LOG.TXT"
run 'command /c C:\NETUP\SEND.BAT C:\OTHER > C:\OUT.TXT'
grep -q 'put C:\\OTHER\\A.TXT OTHER/A.TXT' <(t "$W/c/NETUP/SEND.FTP") && r=1 || r=0
check "$r" "1" "SEND C:\\OTHER sends that folder"
# no FTP.EXE
fresh; rm -f "$W/c/WINDOWS/FTP.EXE" "$W/c/LOG.TXT"; mkdir -p "$W/c/MPSPRO"
run 'command /c C:\NETUP\SEND.BAT > C:\OUT.TXT'
grep -q 'FTP.EXE is missing' "$W/c/OUT.TXT" && r=1 || r=0
check "$r" "1" "SEND without FTP.EXE says so"

[ $fail = 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
