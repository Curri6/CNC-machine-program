# Parts List

**Status: tentative.** These are the parts the retrofit plan in
`JOURNAL.md` currently points to, but nothing here should be bought yet
except possibly the TurboTaig board (see below) — check the physical
driver box for an existing upgrade board first. **Retrofit target as of
2026-09-22 is the MicroProto driver unit, not the spectraLIGHT box**
(see `JOURNAL.md` for why), and the driver unit is believed to use raw
3-wire phase control per motor rather than step/direction, requiring a
converter board rather than a direct wire-in.

## Retrofit motion control

- **TurboTaig board** (Homann Designs, ~AU$169, part# TC-01) — converts
  the MicroProto driver cards' original 3-wire-phase-per-motor interface
  into standard step/direction signals. This is the key part: without
  it, a generic modern controller board cannot drive this old hardware
  correctly (confirmed by a forum report of exactly that failing). Check
  first whether the machine already has this, MicroProto's own official
  2003 step/dir upgrade board, or the 2006 closed-loop variant installed
  — would change or eliminate this purchase. Also worth checking if
  MicroProto's own official board is still available to buy directly.

- **GRBL-compatible controller board** — generates the real-time
  step/direction pulses in hardware, feeding the TurboTaig board's
  step/dir input (its `J9` connector, per the one review found — pin
  detail on this still to confirm once the board is in hand). An
  Arduino Uno + a "CNC Shield V3" is the cheapest, most common way to
  get a GRBL controller with screw-terminal step/dir/enable breakouts;
  an all-in-one board (e.g. an Openbuilds BlackBox-style board) is a
  pricier but tidier alternative. Needs 3 axes (X/Y/Z) at minimum; check
  whether the mill's `A` axis connector is actually used (a rotary
  table physically installed) before assuming a 4th axis is needed —
  `Params.dat` shows the software is *configured* to expect one, which
  isn't the same as one being physically present.

- **Cable/connector matching the TurboTaig board's `J9` step/dir
  input** — exact type TBD once the board is in hand.

- **USB A-to-B (or A-to-Micro, depending on board) cable** — connects the
  GRBL controller board to the Windows 11 PC.

## Testing / safety (get these regardless of final board choice)

- **Multimeter** — needed before touching any wiring to confirm actual
  pin assignments and check for continuity/shorts.
- **USB logic analyzer** (e.g. a cheap 8-channel "Saleae clone") — a
  fallback, now lower-priority than before since the TurboTaig board
  sidesteps needing to know the MicroProto panel's own internal 3-wire
  phase pinout. Still handy for confirming the TurboTaig's step/dir
  side, or for general debugging.
- **Small standoffs/enclosure or perfboard** — to mount the new GRBL
  board and TurboTaig board safely near the MicroProto driver unit
  rather than leaving them loose.

## Computer

- **Windows 11 PC** to run the new software — confirm whether the owner
  already has a machine earmarked for this, or whether one needs to be
  bought/repurposed. Requirements are modest (this app is not
  performance-heavy since real-time work is offloaded to the controller
  board) — almost any current mini PC or existing laptop would do.

## Not needed

- No air compressor / pneumatics — confirmed the small 12V pump found
  nearby is unrelated to this machine (see `JOURNAL.md`).
- No phone/tablet hardware — desktop-only per owner's requirement.
- No ISA card, no vintage PC — the whole point of the retrofit is to
  avoid needing either.
