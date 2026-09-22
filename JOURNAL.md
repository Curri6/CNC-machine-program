# Project Journal

Running log of findings and decisions for the A-Tech CNC machine
replacement-software project. Read this first if you're picking this
project up after a gap — it exists so nothing has to be re-discovered
from scratch.

## Goal

Build a modern replacement for the discontinued software that used to
program/run the school's CNC mill. Requirements set by the project owner
so far:

- A native desktop application (explicitly **not** a web page/browser UI —
  compared to Bambu Studio as the reference for feel).
- Target OS: **Windows 11** on modern PC hardware.
- No phone/companion app — desktop only.
- Needs to both (a) send G-code/cutting jobs to the machine, and
  (b) be the path for "updating" the machine's control electronics.

## Hardware identified (as of 2026-09-17)

The machine is a small educational benchtop CNC mill, likely purchased
with Carl D. Perkins Vocational Education funds (Nevada). Three main
pieces of original equipment:

1. **Mill mechanics**: badged **MicroProto Systems "MicroMill 2000HD/LE"**
   (MicroProto is a spin-off of Taig Tools). Axis motors are standard
   **Lin Engineering 5718L-10D, 1.0A NEMA 23 steppers**. Spindle is a
   separate **Franklin Electric 1/4 HP 115V AC induction motor**
   (3450 RPM) — not part of the precision motion system, just on/off.
   A silver interface panel (mounted on/near the mill) exposes DIN-style
   connectors labeled `X`, `Y`, `Z`, `A`, an `I/O PORT`, and an
   `XYZA PORT`.

   ![MicroProto MicroMill 2000HD/LE nameplate](images/micromill-2000-nameplate.jpg)
   ![MicroMill axis interface panel with DIN connectors](images/micromill-2000-axis-panel.jpg)
   ![Lin Engineering 5718L-10D stepper motor driving an axis](images/lin-engineering-stepper-motor.jpg)
   ![Franklin Electric spindle motor nameplate](images/franklin-electric-spindle-motor.jpg)

2. **Controller/driver box**: badged **Light Machines Corporation
   "spectraLIGHT"** (Light Machines was later acquired by **Intelitek**).
   This is the box with all the fused power distribution (`MOTOR DRIVES`,
   `MAIN`, `SPINDLE`, `ACC1`, `ACC2`) and connectors: `A & B AXES` (DB15),
   `C AXIS` (DB9), `TTL I/O` (DB9), and — the important one —
   **`COMPUTER` (DB25)**. Warning label says "do not open, no user
   serviceable parts inside."

   ![spectraLIGHT controller box front panel](images/spectralight-front-panel.jpg)
   ![spectraLIGHT controller box rear panel showing MOTOR DRIVES, COMPUTER, TTL I/O, A & B AXES, C AXIS](images/spectralight-back-panel.jpg)

   Working theory (not yet confirmed against a wiring diagram): the
   MicroProto mill/breakout panel is the original hardware, and at some
   point the school added/swapped in the Light Machines spectraLIGHT box
   as the driver/controller electronics feeding it. Not confirmed which
   box's output feeds which box's input.

3. **Original computer**: an **IBM NetVista** (Machine Type 6578, Model
   KCU, manufactured ~2001, Pentium III/4 era). Back panel has exactly
   one **DB25 parallel port** + two DB9 serial ports (COM1/COM2), PS/2,
   early USB, VGA. **Currently still boots to Windows 95** (per owner,
   2026-09-17). A previous, unsuccessful repair attempt by others wanted
   to move this machine to Linux instead.

   ![IBM NetVista rear panel showing the single DB25 parallel port and two DB9 serial ports](images/ibm-netvista-back-panel.jpg)
   ![IBM NetVista nameplate: Machine Type 6578, Model KCU](images/ibm-netvista-nameplate.jpg)

   Not yet checked: whether the original CNC software (MicroProto's
   MPS2000/MPS2003 DOS CAM program, and/or Light Machines' spectraLIGHT
   software) is still installed on this Win95 drive. **This should be
   checked before the drive is touched/wiped** — if the software's still
   there, it's a goldmine now that the original manuals are confirmed
   lost.

   Ruled out: a small 12V DC air pump + generic "Power Charger" 12V/5A
   adapter found nearby is **unrelated** to the CNC system (no branding
   or wiring tying it in) — this machine has no pneumatics at all, fully
   electric (steppers + AC spindle motor only).

## MicroMill 2000 manual (MPS2003 software) — now read in full

The owner uploaded this one and it could be read directly (had to install
`poppler-utils` in the sandbox first — noted here in case a future session
hits the same "pdftoppm not installed" error). It's a **software/user
manual for the original MPS2003 DOS program**, not a hardware/wiring
manual, so it doesn't contain a DB25 pin table — but it confirms and adds
important detail:

- **Confirms direct parallel-port bit-banging**, exactly as theorized.
  MPS2003 talks straight to PC hardware I/O ports: the XYZ axes are
  addressed at port base **888 decimal (0x378 — the standard LPT1
  address)**, and there's an optional **4th axis ("A") printer port
  card at 632 decimal (0x278 — standard LPT2)**, supplied specifically
  with the rotary-table option. So a machine with the 4th axis installed
  would need *two* parallel ports on the PC — worth checking whether this
  particular PC ever had a second LPT card, since its back panel (per
  photos) only showed one DB25.
- Confirms a separate **"driver unit"** (amplifier hardware, distinct
  from the PC) takes those raw parallel signals and drives the actual
  stepper motors. Explicitly warned in the troubleshooting section: the
  driver unit must stay under continuous software control or it
  overheats — "DO NOT leave the driver unit on if it is not under
  control of the software." Confirms troubleshooting for "motors just
  vibrate" points at the printer cable/port, not a smarter protocol.
- **Motion calibration constants**, useful later for configuring
  whatever retrofit board we land on: 20 rev/inch lead screw, 1.8°/step
  motors, half-stepping → **8000 steps/inch** (0.000125 in/step) as the
  factory default; the manual also shows how to fine-tune this
  (e.g. 7992 steps/inch) if a given lead screw's true pitch varies
  slightly.
- **Original G-code dialect supported by MPS2003** (useful if we ever
  find old job files, and as a sanity baseline — our new software isn't
  required to match this, since we're not reusing this program):
  `G00 G01 G02 G03 G17 G20 G21 G43 G81 G83 G98 G99` and
  `M02 M97 M99`. Fairly minimal/classic subset — notably no explicit
  G90/G91 mention found, no tool-change M-codes, no canned pattern
  cycles beyond drilling/peck-drilling.
- No mention anywhere of Light Machines or spectraLIGHT — consistent
  with the theory that the spectraLIGHT box was a **later replacement**
  for MicroProto's original driver unit + MPS2003 combo, not part of the
  machine's original design.

**Still missing**: the actual DB25 pin assignments for whichever
box/driver unit is currently in the signal path. This manual didn't have
it — need the spectraLIGHT manual (see next section — now read, but it
turns out this doesn't have the pin table either) or a physical
trace/continuity check.

## spectraLIGHT Mill manual — now read in full (251 pages)

Owner sent this one as a zip (the PDF was too large to upload directly).
This is the **full official manual** — installation, the Windows 95
"Control Program" GUI, G-code reference, robotic I/O, safety, everything.
Confirms and substantially sharpens the picture:

- **The `COMPUTER` DB25 is not a parallel port at all — it's a
  dedicated ISA bus expansion card** ("the spectraLIGHT Interface Card"),
  installed in a full-size expansion slot inside the original PC. The
  manual explicitly warns installers: "Do not get the Interface Card
  mixed up with the parallel port which uses the same type of
  connector" — i.e. it just *looks* like a parallel port (same DB25
  shell) but is wired to the ISA bus, not the PC's built-in LPT hardware.
  Factory I/O address is **0x3A0** (reserved for Bisync cards on the
  classic PC/AT I/O address map), and there's a software panel in the
  Control Program to change this address if it conflicts with another
  card.
- This **removes all ambiguity about reusing the original PC-side
  hardware**: ISA slots don't exist on any PC made in the last ~20 years,
  full stop — not even as an option via a simple adapter. There was
  never a version of "keep the original interface, just get a new PC"
  that could have worked. This confirms the retrofit plan is the only
  viable path, not just the recommended one.
- **The manual does not publish a pin-level signal table for the DB25
  cable coming out of this Interface Card.** It's an end-user
  install/operate guide, not an engineering reference. So the
  secondhand forum pinout below is still our only lead on the actual
  signal assignments — not confirmed by a primary source yet.
- Also documented, for completeness: a separate 9-pin cable runs
  directly from the Interface Card to the machining center itself
  (spindle-related, bypasses the Controller Box), and the Controller
  Box connects to the machining center via a 15-pin `A & B AXES` cable
  and a 9-pin `C AXIS` cable. There's also a documented 9-pin `TTL I/O`
  / robotic accessory connector with its own pin table (inputs/outputs
  for external automation, ±5V/TTL levels, 1mA max output) — useful
  context, but it's for accessory integration, not the main axis drive
  signals.
- Confirms the currently-installed OS really is running the
  **spectraLIGHT Windows 95 GUI "Control Program"** (not the MicroProto
  MPS2003 DOS program) — so when the machine is powered on, look for a
  Windows program/folder actually named something like "spectraLIGHT"
  or "Control Program," not "MPS2003."

## Machine powered on — found the live MPSPRO installation (2026-09-22)

Owner got the Windows 95 machine booted (login dialog turned out to be
the classic Win9x non-enforcing logon — Cancel/blank credentials got
straight to the desktop, as expected). The desktop itself was stock/empty
(no CNC shortcuts), but `C:\MPSPRO` is **fully intact**:

```
Bolthole.tap  Ellipse.tap  Facef.tap  Facer.tap  Gear.tap  Knight.tap
Textdemo.tap  Install  Mill  Mps2003  Mpsm97  Mpsprob3
Param3.dat  Param51.dat  Param51s.dat  Paramp3.dat  Params.dat
Steptxt  Textm97
```

Two big findings from opening files here:

- **`Params.dat` confirms the real, working port addresses** — and they
  match the manual's documented *standard* values exactly, not the
  spectraLIGHT ISA card's address:
  ```
  0
  0
  0
  0
  888     <- XYZ port base = 0x378 = standard PC LPT1
  890
  632     <- A (4th axis) port base = 0x278 = standard PC LPT2
  600
  200
  10
  0
  16
  16
  0
  8
  INCH
  ```
  (First four `0`s are likely the last-saved X/Y/Z/A position, all
  homed/zeroed. The values after 632 are probably rapid-speed/backlash/
  step-mode settings per the manual's calibration section — not fully
  decoded, and not needed for our purposes. The `888`/`632` match is the
  important part.)

  **This is a significant update to the working theory.** It means the
  software actually configured and (presumably) used on this machine
  talks through the **PC's own built-in standard parallel port
  hardware** (LPT1, and LPT2 for the 4th axis) — not the spectraLIGHT
  Interface Card's proprietary ISA bus address (0x3A0) at all. That
  raises an open question we didn't have before: **is the spectraLIGHT
  box even the thing currently wired to this PC's parallel port**, or is
  the MicroProto native breakout box (the one with the round DIN X/Y/Z/A
  connectors) the one actually in the live signal path, with the
  spectraLIGHT box unused/legacy or wired in for something unrelated
  (e.g. just spindle control)? **Next time at the machine: physically
  trace the cable from the PC's DB25 parallel port to whichever box it
  actually plugs into** — this settles it conclusively either way.
  This is good news either way for the retrofit: a standard LPT1/LPT2
  step/dir setup is a well-understood, common target (this is exactly
  what generic hobby CNC breakout boards and GRBL-adjacent controllers
  already expect), more so than the spectraLIGHT ISA card scenario.

- **`Steptxt` is not a text file — it's a live DOS control program**
  ("MPSTEXT V3.0"), showing real-time axis position (X/Y/Z/A, all
  0.0000), feed rate, jog increment, and a manual jog / load program /
  run program / zero axis menu. **This is working control software that
  can actually move the machine** if the driver box and motors are
  powered and connected — treat it with the same care as running the
  original software for real. Owner was advised not to press any menu
  keys (Manual Jog, Run Program, Zero Axis) until the area around the
  mill is confirmed clear.

Not yet opened: `Param3.dat`, `Param51.dat`, `Param51s.dat`,
`Paramp3.dat` (other config variants — probably per-job or per-material
presets), `Mill` (separate program, purpose unknown), `Mps2003` /
`Mpsm97` / `Mpsprob3` (the actual control program executables — not run
yet, deliberately, until we're sure it's safe to do so with the machine
in its current physical state).

## Key technical finding: why this can't just move to a new Windows PC as-is

Web research (see Sources below) turned up a secondhand pinout for the
spectraLIGHT `COMPUTER` DB25 port — it's a **plain step/direction
parallel-port breakout**, functionally the same scheme used by
Mach3/TurboCNC-era hobby CNC controllers:

```
Pin 22: Enable          Pin 6:  X Direction     Pin 21: X Step
Pin 18: Y Direction     Pin 20: Y Step          Pin 5:  Z Direction
Pin 19: Z Step          Pin 17: Enable          Pin 4:  Spindle On
Pin 23: E-Stop          Pin 13: Home            Pin 24: Limit
Pin 1:  Accessory       Pin 11: Cover           Pin 2:  Chuck
Pin 7:  Ground
```
(**Still not verified against a primary source** — neither manual we've
read has it; see Open Items. It's plausible this is still roughly right
even though we now know it's an ISA card rather than a plain parallel
port — a lot of ISA-era motion cards just used the bus to receive fast
register writes from the CPU and then output plain TTL step/dir pulses
on their external connector — but "plausible" isn't "confirmed.")

Also found: the spectraLIGHT needs "an LPT card with a strong 5V
output — a 3.3V card will not work" — this actually lines up with the
"ISA card, not the parallel port" finding above; the forum poster was
likely describing the same Interface Card, imprecisely.

Put together with the Windows-95-was-the-original-OS fact: this old
setup relied on the PC itself bit-banging real-time step pulses out the
parallel port, something Win95's minimal task-switching allowed, but
which modern OSes (Windows 11 included — this is *worse* than even
Windows XP/7 for this purpose) cannot do reliably. This is the same
reason the earlier would-be fixers wanted to switch to Linux
(a real-time-patched Linux kernel, à la LinuxCNC, is the traditional fix
for restoring that low-jitter timing) — same problem, different fix.

## Decision: retrofit plan

Rather than fight for real-time performance on a general-purpose PC OS
(what both Win95-original and the Linux-retrofit idea were doing), the
plan is to remove the real-time requirement from the PC entirely:

1. Keep the mechanical mill, the NEMA 23 steppers, the spindle motor, and
   ideally the spectraLIGHT box's internal drive amplifiers.
2. Replace only the PC-side signal generation with a small, modern,
   well-documented motion-control board (GRBL-based controller is the
   leading candidate — cheap, open protocol, huge community, and this
   exact retrofit pattern is documented by the LinuxCNC community for a
   sibling Light Machines product, the Benchman XTr, using a Mesa
   5i25/7i77 board instead). It wires into the *same* DB25 pins the old
   PC used to drive, so (if the pinout above holds up) no changes needed
   inside the spectraLIGHT box at all.
3. That board handles all real-time step timing in hardware. The Windows
   11 PC just streams G-code over USB at non-time-critical speed.

## Software plan

- Native desktop app, **Python + Qt (PySide6)** — real native window,
  cross-platform if ever needed, mature serial/USB libraries, good fit
  for toolpath preview / jogging / job control UI in the style of Bambu
  Studio.
- Talks to the retrofit motion-control board over USB-serial with
  G-code, using whatever protocol that board's firmware speaks (GRBL's
  line-based G-code-over-serial is the leading candidate).
- Explicitly not a web app / browser UI (owner's requirement).
- No phone companion app (owner's requirement, reversed an earlier
  direction).

## Open items / next steps

1. ~~Get the official manuals read.~~ **Done** — both manuals (MicroMill
   2000 / MPS2003, and spectraLIGHT Mill) have been uploaded and read.
2. ~~Check the Windows 95 machine before touching its drive.~~ **Done** —
   machine boots, `C:\MPSPRO` is fully intact with the original MPS2003
   installation and config files. See the new section above. Still
   haven't opened `Param3.dat` / `Param51.dat` / `Param51s.dat` /
   `Paramp3.dat` or run `Mill`/`Mps2003`/`Mpsm97`/`Mpsprob3` — do that
   next, running programs only once the area around the mill is
   confirmed physically safe.
3. **Physically trace the PC's parallel port cable** — `Params.dat`
   shows the real working config uses the PC's own standard LPT1/LPT2
   ports (888/632 decimal), not the spectraLIGHT Interface Card's ISA
   address. So: does that cable actually plug into the MicroProto
   breakout box (DIN X/Y/Z/A connectors) or the spectraLIGHT box's
   `COMPUTER` port? This decides which box is actually live and
   answers the "how do the two boxes relate" question directly —
   higher priority now than the DB25-pinout research below, since it
   might make that research moot (if the spectraLIGHT box isn't even
   in the active signal path, we may not need its pinout at all).
4. **Confirm the real DB25 pin assignments** for whichever box turns out
   to be the active one. Options: (a) contact Intelitek support (in
   progress, no reply yet after several days — a phone follow-up is
   the suggested next step) or the hobbyist forum/blog leads (see
   Sources); or (b) an empirical approach — with the machine powered
   and the area clear, use a multimeter or logic analyzer to probe the
   cable's pins while jogging a single axis via the now-confirmed
   `Steptxt`/MPSTEXT program, to see which pins toggle.
5. Once the active box and its pinout are confirmed: finalize exact
   retrofit board + parts list.
6. Before wiping/reformatting the Win95 drive for any reason: back up
   the entire `C:\MPSPRO` folder (and ideally a full disk image) —
   it's a working reference implementation of the exact G-code dialect
   and motion parameters this machine expects.
7. Owner is sending more info/photos as they come — revisit this
   journal and update it as they do.
8. No code has been written yet — explicitly deferred by owner until
   hardware/software plan is settled.

## Sources referenced this session

- [spectraLIGHT Lathe Manual PDF](https://www.tock.pl/images/Nowa_strona_15_04_2021/spectraLIGHT_Lathe_Manual_EN.pdf)
- [spectraLIGHT Mill manual (Intelitek) — uploaded by owner as a zip and read in full this session (251 pages)](https://downloads.intelitek.com/Manuals/CNC/Discontinued_Machines/spectraLIGHT_Mill_WIN_Manual.pdf)
- [MicroMill 2000 User's Manual (soigeneris.com mirror) — uploaded by owner and read in full this session](https://www.soigeneris.com/Document/Taig/MPS2000_Manual.pdf)
- [MicroProto Systems site](http://www.microproto.com/micromill2000.htm)
- [LinuxCNC forum: Light Machine Corp. Benchman XTr retrofit](https://forum.linuxcnc.org/30-cnc-machines/27204-light-machine-corp-benchman-xtr-retrofit)
- [LinuxCNC forum: Light Machines Company Mill](https://forum.linuxcnc.org/16-stepconf-wizard/3501-light-machines-company-mill)
- [Steven Rhine / Rhine Labs: Light Machines spectraLight restore blog](https://www.stevenrhine.com/?p=1175)
