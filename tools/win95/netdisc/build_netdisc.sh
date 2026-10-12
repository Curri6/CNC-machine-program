#!/bin/bash
# Builds the NETDISC folder (burn it with burn_win95_disc.bat option 2).
#
#   build_netdisc.sh OUTDIR INTEL62_DIR PRODOS_DIR MTCP_DIR
#
#   INTEL62_DIR  extracted Intel_Pro_100-6.2.7z   (DOS/DOS/LSL.COM, E100bodi.com, ...)
#   PRODOS_DIR   extracted Intel PRODOS.exe        (PRO100/DOS/e100b.dos)
#   MTCP_DIR     extracted mTCP_2026-10-10.zip
#
# Intel's and Novell's files are not stored in this repository; they come
# from the owner's downloads. Needs: nasm, zip (optional, for OUTDIR.zip).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$1"; I62="$2"; PRO="$3"; MT="$4"
rm -rf "$OUT"; mkdir -p "$OUT/ODI/OLD" "$OUT/NDIS2" "$OUT/EXTRA/MTCP"

# our own files: text files get DOS (CRLF) line endings
for f in "$HERE"/kit/*.* "$HERE"/kit/ODI/*.*; do
  rel="${f#$HERE/kit/}"
  sed 's/\r$//; s/$/\r/' "$f" > "$OUT/$rel"
done
nasm -f bin -w+all -o "$OUT/MKFTP.COM" "$HERE/src/MKFTP.ASM"

need() { [ -f "$1" ] || { echo "missing: $1" >&2; exit 1; }; }
pick() { need "$1"; cp "$1" "$2"; }
pick "$I62/DOS/DOS/lsl.com"        "$OUT/ODI/LSL.COM"
pick "$I62/DOS/DOS/E100bodi.com"   "$OUT/ODI/E100BODI.COM"
pick "$I62/E100bodi.com"           "$OUT/ODI/OLD/E100BODI.COM"
pick "$PRO/PRO100/DOS/e100b.dos"   "$OUT/NDIS2/E100B.DOS"
pick "$PRO/PRO100/DOS/protocol.ini" "$OUT/NDIS2/PROTOCOL.INI"
pick "$PRO/PRO100/DOS/e100beds.nif" "$OUT/NDIS2/E100BEDS.NIF"
pick "$PRO/license.txt"            "$OUT/NDIS2/LICENSE.TXT"
pick "$I62/license.rtf"            "$OUT/ODI/LICENSE.RTF"
cp -r "$MT"/. "$OUT/EXTRA/MTCP/"

# the versions we checked (chip 8086:2449 supported; LSL new enough)
grep -aq 'v2.20 (960401)' "$OUT/ODI/LSL.COM"
grep -aq 'v4.13 (041123)' "$OUT/ODI/E100BODI.COM"
grep -aq 'v4.01 (011130)' "$OUT/ODI/OLD/E100BODI.COM"
grep -aq 'v4.59 050510' "$OUT/NDIS2/E100B.DOS"
for f in "$OUT/ODI/E100BODI.COM" "$OUT/ODI/OLD/E100BODI.COM" "$OUT/NDIS2/E100B.DOS"; do
  LC_ALL=C grep -aqP '\x86\x80\x49\x24' "$f" || { echo "chip ID not in $f" >&2; exit 1; }
done

# every name must be DOS 8.3 so MS-DOS mode and ISO 9660 can read it
bad=0
while IFS= read -r p; do
  n="$(basename "$p")"
  echo "$n" | grep -Eq '^[A-Za-z0-9_$~!#%&{}()@^-]{1,8}(\.[A-Za-z0-9_$~!#%&{}()@^-]{1,3})?$' || { echo "not 8.3: $p" >&2; bad=1; }
done < <(find "$OUT" -mindepth 1)
[ $bad = 0 ]

find "$OUT" -type f | wc -l | xargs echo "files:"
du -sk "$OUT" | cut -f1 | xargs echo "KB:"
if command -v zip >/dev/null; then (cd "$(dirname "$OUT")" && rm -f "$(basename "$OUT").zip" && zip -qr "$(basename "$OUT").zip" "$(basename "$OUT")"); fi
