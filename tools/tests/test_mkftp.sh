#!/bin/bash
# Tests MKFTP.COM (tools/win95/netdisc/MKFTP.ASM) in DOSBox.
# Needs: nasm, dosbox.  Run: bash tools/tests/test_mkftp.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../win95/netdisc/src/MKFTP.ASM"
W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
fail=0
check() { if [ "$1" = "$2" ]; then echo "PASS $3"; else echo "FAIL $3"; echo "  expected: $2"; echo "  got:      $1"; fail=1; fi; }

nasm -f bin -w+all -o "$W/MKFTP.COM" "$SRC" || { echo "FAIL assemble"; exit 1; }
D="$W/drive"; mkdir -p "$D/NETUP"; cp "$W/MKFTP.COM" "$D/NETUP/"

# normal tree
mkdir -p "$D/MPSPRO/MILL/SUB1/DEEP" "$D/MPSPRO/INSTALL" "$D/MPSPRO/EMPTY"
head -c 1234 /dev/urandom > "$D/MPSPRO/BOLTHOLE.TAP"
: > "$D/MPSPRO/ZERO.DAT"
head -c 70000 /dev/urandom > "$D/MPSPRO/PARAMS.DAT"
head -c 99 /dev/urandom > "$D/MPSPRO/MILL/MILL.EXE"
head -c 300000 /dev/urandom > "$D/MPSPRO/MILL/SUB1/DEEP/BIG.BIN"
head -c 17 /dev/urandom > "$D/MPSPRO/INSTALL/SETUP.EXE"
# too deep (23 levels)
p="$D/DEEPT"; for i in $(seq 1 23); do p="$p/D$i"; done; mkdir -p "$p"; echo hi > "$p/X.TXT"
echo a > "$D/DEEPT/D1/TOP.TXT"
# path longer than DOS allows
q="$D/LONGT"; for i in $(seq 1 10); do q="$q/LONGNAME"; done; mkdir -p "$q"; echo z > "$q/F.TXT"
mkdir -p "$D/EMP"

printf '%s\r\n' '@echo off' \
 'MKFTP C:\MPSPRO > O1.TXT' 'if errorlevel 1 echo bad> R1.TXT' 'if not errorlevel 1 echo 0> R1.TXT' \
 'copy BODY.FTP B1.FTP > NUL' 'copy MANIFEST.TXT M1.TXT > NUL' \
 'MKFTP C:\MPSPRO\ > O1B.TXT' 'copy MANIFEST.TXT M1B.TXT > NUL' \
 'MKFTP C:\NOPE > O2.TXT' 'if errorlevel 1 echo 1> R2.TXT' \
 'MKFTP > O3.TXT' 'if errorlevel 1 echo 1> R3.TXT' \
 'MKFTP C:\DEEPT > O4.TXT' 'if errorlevel 4 echo 4> R4.TXT' \
 'MKFTP C:\LONGT > O5.TXT' 'if errorlevel 4 echo 4> R5.TXT' \
 'MKFTP C:\EMP > O6.TXT' 'if not errorlevel 1 echo 0> R6.TXT' 'copy BODY.FTP B6.FTP > NUL' \
 > "$D/NETUP/T.BAT"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 120 dosbox -noconsole \
  -c "mount c $D" -c "c:" -c "cd netup" -c "T.BAT" -c exit >/dev/null 2>&1
N="$D/NETUP"
t() { tr -d '\r' < "$1" 2>/dev/null; }

check "$(t "$N/R1.TXT")" "0" "normal tree exits 0"
check "$(t "$N/O1.TXT")" "MKFTP: 6 files in 5 subfolders, 371350 bytes." "normal tree summary"
exp_body='mkdir MPSPRO
mkdir MPSPRO/EMPTY
mkdir MPSPRO/INSTALL
put C:\MPSPRO\INSTALL\SETUP.EXE MPSPRO/INSTALL/SETUP.EXE
mkdir MPSPRO/MILL
mkdir MPSPRO/MILL/SUB1
mkdir MPSPRO/MILL/SUB1/DEEP
put C:\MPSPRO\MILL\SUB1\DEEP\BIG.BIN MPSPRO/MILL/SUB1/DEEP/BIG.BIN
put C:\MPSPRO\MILL\MILL.EXE MPSPRO/MILL/MILL.EXE
put C:\MPSPRO\BOLTHOLE.TAP MPSPRO/BOLTHOLE.TAP
put C:\MPSPRO\PARAMS.DAT MPSPRO/PARAMS.DAT
put C:\MPSPRO\ZERO.DAT MPSPRO/ZERO.DAT'
# DOS directory order can differ from this, so compare sorted
check "$(t "$N/B1.FTP" | sort)" "$(echo "$exp_body" | sort)" "BODY.FTP lines"
check "$(head -1 "$N/B1.FTP" | tr -d '\r')" "mkdir MPSPRO" "BODY.FTP starts with mkdir of the top folder"
exp_man='MPSPRO/BOLTHOLE.TAP 1234
MPSPRO/INSTALL/SETUP.EXE 17
MPSPRO/MILL/MILL.EXE 99
MPSPRO/MILL/SUB1/DEEP/BIG.BIN 300000
MPSPRO/PARAMS.DAT 70000
MPSPRO/ZERO.DAT 0'
check "$(t "$N/M1.TXT" | sort)" "$exp_man" "MANIFEST.TXT names and sizes"
check "$(t "$N/M1B.TXT" | sort)" "$exp_man" "trailing backslash accepted"
# every folder's mkdir comes before anything inside it
ok=1; seen=""
while read -r a b c; do
  if [ "$a" = mkdir ]; then seen="$seen|$b"; else par="${c%/*}"; case "$seen|" in *"|$par|"*) ;; *) ok=0;; esac; fi
done < <(t "$N/B1.FTP")
check "$ok" "1" "mkdir before put"
grep -q $'\r$' "$N/B1.FTP" && crlf=1 || crlf=0
check "$crlf" "1" "CRLF line endings"
check "$(t "$N/R2.TXT")" "1" "missing folder exits 1"
check "$(t "$N/O2.TXT")" 'MKFTP: folder not found: C:\NOPE' "missing folder message"
check "$(t "$N/R3.TXT")" "1" "no argument exits 1"
check "$(t "$N/R4.TXT")" "4" "too-deep tree exits 4"
grep -q 'SKIPPED, folders nested too deep' "$N/O4.TXT" && r=1 || r=0
check "$r" "1" "too-deep tree prints a warning"
check "$(t "$N/R5.TXT")" "4" "too-long path exits 4 (never silent)"
grep -q 'SKIPPED, cannot read folder' "$N/O5.TXT" && r=1 || r=0
check "$r" "1" "too-long path prints a warning"
check "$(t "$N/R6.TXT")" "0" "empty folder exits 0"
check "$(t "$N/B6.FTP")" "mkdir EMP" "empty folder body"

[ $fail = 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
