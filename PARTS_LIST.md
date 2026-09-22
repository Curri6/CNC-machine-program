# Parts List

**Status: tentative.** These are the parts the retrofit plan in
`JOURNAL.md` currently points to, but nothing here should be bought yet —
everything is contingent on confirming the real signal pinout first (see
`TODO.md`). **Retrofit target as of 2026-09-22 is the MicroProto driver
unit/axis panel, not the spectraLIGHT box** — see `JOURNAL.md` for why
(the spectraLIGHT box is very likely leftover from a different, unrelated
Light Machines mill, not part of this machine's actual signal path). If
that conclusion changes, this list changes too.

## Retrofit motion control

- **GRBL-compatible controller board** — generates the real-time
  step/direction pulses in hardware so the PC no longer has to. An
  Arduino Uno + a "CNC Shield V3" is the cheapest, most common way to get
  a GRBL controller with screw-terminal step/dir/enable breakouts; an
  all-in-one board (e.g. an Openbuilds BlackBox-style board) is a pricier
  but tidier alternative. Needs 3 axes (X/Y/Z) at minimum; check whether
  the mill's `A` axis connector is actually used before assuming a 4th
  axis is needed (the MPS2003 config expects a 4th-axis port to exist,
  per `Params.dat`, but that doesn't confirm a rotary table is actually
  installed on this specific machine).
  - Note: GRBL/Arduino boards output native 5V TTL logic. The old
    "needs a strong 5V output" comment found earlier turned out to be
    about the (probably unrelated) spectraLIGHT Interface Card, not
    this hardware — worth re-confirming voltage expectations once the
    MicroProto panel's actual pinout is known.

- **Connector + cable/breakout matching the MicroProto panel's
  connectors** — likely small round DIN-style plugs (matching the `X`,
  `Y`, `Z`, `A`, `I/O PORT` sockets photographed on that panel) rather
  than a DB25 — to wire the new board's step/dir/enable/spindle-on
  signals in, pin-for-pin, once the pinout is confirmed.

- **USB A-to-B (or A-to-Micro, depending on board) cable** — connects the
  new controller board to the Windows 11 PC.

## Testing / safety (get these regardless of final board choice)

- **Multimeter** — needed before touching wiring to confirm actual pin
  assignments and check for continuity/shorts, rather than trusting the
  secondhand pinout blindly.
- **USB logic analyzer** (e.g. a cheap 8-channel "Saleae clone") — likely
  needed. Neither manual has a pin-level signal table for the MicroProto
  panel's connectors. If the hobbyist-forum leads don't turn up a
  pinout, the fallback is probing the panel's connector pins with a
  logic analyzer while the still-working Windows 95 system (via the
  confirmed-working `Steptxt`/MPSTEXT program) jogs a single axis, to
  empirically capture which pins are X/Y/Z step and direction. Cheap and
  reusable for future debugging too.
- **Small standoffs/enclosure or perfboard** — to mount the new
  controller board safely near the MicroProto panel rather than leaving
  it loose.

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
