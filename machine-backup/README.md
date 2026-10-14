# C:\MPSPRO settings from the real machine (2026-10-14)

Copied over the network from the IBM NetVista A40 (Windows 95) with the
`tools/win95/netdisc` kit. All 20 files of `C:\MPSPRO` arrived with the
right sizes (`MANIFEST.TXT`). Only the machine's own settings and batch
files are kept here. The five control programs (`.EXE`) and the seven
sample jobs (`.TAP`) are MicroProto Systems files, so they stay in the
owner's backup zip (`MPSPRO_backup_20261014_145353.zip`), not in this
repo.

## Which program uses which settings file

Found from the file name inside each program:

| Program | Version string | Settings file |
| --- | --- | --- |
| `MPS2003.EXE` (what `MILL.BAT` starts) | M P S 2000 V3.0 | **`PARAM3.DAT`** |
| `MPSM97.EXE` (M97 subroutines) | M P S 2000 V3.0 | `PARAM51.DAT` |
| `TEXTM97.EXE` | MPSTEXT V3.0 | `PARAM51S.DAT` |
| `STEPTXT.EXE` | MPSTEXT V3.0 | `PARAMS.DAT` |
| `MPSPROB3.EXE` (probe/digitizer) | M P S 2000 V2.2 | `PARAMP3.DAT` |

## What the lines mean

These are best guesses, matched against the MPS2000 manual
("Program Description and Operation" and "RAPID/ACCEL"). The program
saves "the current X,Y,Z,A coordinates, Tool H offsets and Printer Ports"
when you quit.

| Line | PARAM3.DAT | Meaning (best guess) |
| --- | --- | --- |
| 1–4 | 2226, 0, -1189, 0 | last X, Y, Z, A position in motor steps (2226 / 8000 = 0.278 in) |
| 5 | 888 | XYZ printer port = 0x378 (LPT1) |
| 6 | 890 | 888 + 2 = LPT1 control register |
| 7 | 632 | A-axis printer port = 0x278 (LPT2) |
| 8 | 600 | Rapid Start (steps/s) |
| 9 | 800 | Accel Steps |
| 10 | 1.5 | Step Inc, so top rapid speed = 600 + 800 × 1.5 = 1800 steps/s = 13.5 in/min |
| 11 | 1 | backlash comp on (1) / off (manual: option 1 enables it) |
| 12–14 | 0, 0, 4 | not decoded (backlash values or step mode) |
| 15 | 8 | not decoded |
| 16 | INCH | units |
| 17–19 | 8000, 8000, 8000 | **steps per inch, X/Y/Z** |
| 20 | 80 | A-axis steps per degree (not confirmed) |
| 21 | TAP | default job file extension |
| 22 | C:\MPSPRO | job folder |
| 23–26 | 1, 1, 1, 1 | scale / depth inc / feed % / repeat (not confirmed) |
| 27 | .01 | not decoded |
| 28– | 0 … | tool length offsets (10 tools) |

`PARAMS.DAT` (STEPTXT) has a faster ramp, 600 + 200 × 10 = 2600 steps/s,
and its position is 0, 2610, 1743, 14358. `PARAMP3.DAT` adds probe
settings at the end (20000, 8000, -8000, 8, 80, 400, 400, `X.TAP`, 1, 15).

**For the retrofit, the key number is 8000 steps per inch on X, Y and Z.**
