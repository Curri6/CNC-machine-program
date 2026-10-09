#!/bin/sh
# Builds the test images for test_disc_check.ps1 (needs xorriso). Run from
# this folder. Fake .CAB/.INF files stand in for the real ones.
set -e
rm -rf src src2 && mkdir -p src/WIN95 src/INTEL/WIN9X src2/WIN95
for i in 02 03 04 05 06; do head -c 300000 /dev/urandom > src/WIN95/WIN95_$i.CAB; cp src/WIN95/WIN95_$i.CAB src2/WIN95/; done
echo "[Version]" > src/INTEL/WIN9X/NET8255X.INF; head -c 50000 /dev/urandom > src/INTEL/WIN9X/E100B.SYS
X="xorriso -as mkisofs -quiet"
$X -J -V WIN95NET -o t0.iso src          # blank-disc image, Joliet
$X -V WIN95NET -o tplain.iso src         # no Joliet
$X -J -C 0,50000 -o t1.iso src           # later session starting at block 50000
$X -J -o tnointel.iso src2               # missing INTEL folder
head -c 2000000 /dev/zero > zeros.iso    # not ISO 9660 at all
