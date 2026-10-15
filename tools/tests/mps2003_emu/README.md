# Checking app-made jobs in the real MPS2003 (emulated)

`run_job.sh` runs the MicroMill's own MPS2003.EXE (from a backup of the old
PC's C:\MPSPRO) inside DOSBox, loads one job, switches on PLOT PREVIEW, runs
it, and takes screenshots. DOSBox has no parallel port, so nothing can move.

    tools/tests/mps2003_emu/run_job.sh ~/MPSPRO JOB1.TAP 0.45 60 shots/

Needs: dosbox, Xvfb, xdotool, xwd (x11-apps), Python with Pillow.
MPS2003.EXE and the sample jobs are MicroProto's files and stay out of git.

2026-10-15 results (images/mps2003-emulator-*.png): every step type the app
makes (pockets, circles, milled holes, drilling, lines, text, cut-out with
tabs, facing) loaded, plotted in the right place and ran to END OF PROGRAM.
MPS2003 stops at the M00 and shows the comment line above it, e.g.
"(PUT IN T4, SPINDLE ON AT 4000 RPM, THEN PRESS C)"; C continues.
