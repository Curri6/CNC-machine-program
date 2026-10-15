#!/bin/bash
# Plot-preview one job in the real MPS2003.EXE, inside DOSBox, and take
# screenshots. Nothing is connected: DOSBox has no parallel port, so no
# machine can move. Needs dosbox, Xvfb, xdotool, xwd and Python + Pillow.
#
#   run_job.sh MPSPRO_DIR JOB.TAP [PLOT_SCALE] [SECONDS] [OUT_DIR]
#
# MPSPRO_DIR is a copy of C:\MPSPRO from a backup (MPS2003.EXE + PARAM*.DAT;
# MicroProto's files are not in this repo). MPS2003's preview runs at the
# real feed speed, so give long jobs enough SECONDS.
#
# Keys it presses (the same a person types on the old PC):
#   2, TAP, Enter, Down, Enter     load the job
#   M, L, scale, Enter             plot scale
#   P                              PLOT PREVIEW on
#   M, 3, C                        run program, continuous
#   C                              past the M00 pause at the top of the job
set -e
SRC=$1; JOB=$2; SCALE=${3:-0.45}; WAIT=${4:-60}; OUT=${5:-$PWD/shots}
HERE=$(cd "$(dirname "$0")" && pwd)
N=$(basename "$JOB"); N=${N%.*}
export DISPLAY=:${EMU_DISPLAY:-99}
mkdir -p "$OUT"
WORK=$(mktemp -d)
mkdir "$WORK/MPSPRO"
cp "$SRC"/*.EXE "$SRC"/*.DAT "$WORK/MPSPRO/"
cp "$JOB" "$WORK/MPSPRO/"
cat > "$WORK/d.conf" <<CONF
[sdl]
output=surface
[dosbox]
machine=svga_s3
memsize=16
[cpu]
cycles=20000
[render]
frameskip=0
aspect=false
scaler=none
[mixer]
nosound=true
[autoexec]
mount c $WORK
c:
cd \\MPSPRO
mps2003
CONF
xdpyinfo >/dev/null 2>&1 || { Xvfb "$DISPLAY" -screen 0 1024x768x24 >/dev/null 2>&1 & sleep 2; }
pkill -x dosbox || true
SDL_AUDIODRIVER=dummy dosbox -conf "$WORK/d.conf" >/dev/null 2>&1 &
sleep 6
W=$(xdotool search --name DOSBox | head -1)
key() { xdotool windowfocus --sync "$W" 2>/dev/null || true
        [ -n "$1" ] && xdotool type --delay 120 --window "$W" "$1"; shift
        for k in "$@"; do xdotool key --delay 150 --window "$W" "$k"; done; }
shot() { eval "$(xdotool getwindowgeometry --shell "$W")"
         xwd -root -silent > "$WORK/s.xwd"
         python3 "$HERE/xwd2png.py" "$WORK/s.xwd" "$OUT/$1.png" "$X,$Y,$((X+WIDTH)),$((Y+HEIGHT))"; }
key "" 2; sleep 1; key TAP Return; sleep 2; key "" Down; sleep 1; key "" Return; sleep 5
shot "${N}_loaded"
key "" m l; sleep 1; key "$SCALE" Return; sleep 1; key "" p; sleep 1; key "" m 3; sleep 1; key "" c; sleep 3
shot "${N}_pause"
key "" c; sleep "$WAIT"
shot "${N}_end"
pkill -x dosbox || true
echo "screenshots in $OUT"
