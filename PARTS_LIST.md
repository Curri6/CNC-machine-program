# Parts List

**Status: NOT part of the active plan (as of 2026-09-22).** Owner
decided the current plan (keep the old PC running MPS2003, use the new
Windows 11 app as a G-code importer/sender — see `JOURNAL.md` and
`TODO.md`) is sufficient on its own, so the hardware retrofit this list
describes is **not something to buy right now**. Kept as reference only,
in case the old PC or MPS2003 ever stops working entirely and a full
retrofit becomes necessary. Nothing below should be purchased unless
that changes.

## Retrofit motion control (reference only, not currently needed)

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

## Backup of C:\MPSPRO (2026-10-12) - nothing to buy

- Uses only what's on hand: the working DVD-R (second session for the
  network kit), a network cable between the old PC and the laptop, and
  free downloads the owner already made (Intel PRO/100 6.2 package with
  Novell LSL.COM, Intel PRODOS, mTCP). Nothing to buy.
- 2026-10-14: owner got two new blank DVD-Rs (one for NETDISC as a
  first session, one spare). The old drive reads only a disc's first
  section, so each new kit needs a fresh disc.
- 2026-10-15: the A-Tech CNC app (Windows 11) needs nothing new either:
  the same network cable, and the laptop's Ethernet port or a USB network
  adapter it already has.
- 2026-10-15: the app's test checklist (windows-app/TESTING.md) needs
  nothing new: the laptop, the cable, the old PC, mill switched off.
- 2026-10-15: drill-bit settings question: software only, nothing to buy.
- 2026-10-15: the G-code maker uses whatever bits the school already has;
  enter them in the app's ⛏ Bits list. Nothing to buy.
- 2026-10-15: materials question: software only, nothing to buy.
- 2026-10-15: what's left to run a job is checks at the mill, not parts.

## Not needed

- No air compressor / pneumatics — confirmed the small 12V pump found
  nearby is unrelated to this machine (see `JOURNAL.md`).
- No phone/tablet hardware — desktop-only per owner's requirement.
- No ISA card, no vintage PC — the whole point of the retrofit is to
  avoid needing either.
