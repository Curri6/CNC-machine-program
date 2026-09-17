# Parts List

**Status: tentative.** These are the parts the retrofit plan in
`JOURNAL.md` currently points to, but nothing here should be bought yet —
everything is contingent on confirming the `COMPUTER` DB25 pinout against
the real manual first (see `TODO.md`). If the pinout or signal path turns
out different than expected, this list changes.

## Retrofit motion control

- **GRBL-compatible controller board** — generates the real-time
  step/direction pulses in hardware so the PC no longer has to. An
  Arduino Uno + a "CNC Shield V3" is the cheapest, most common way to get
  a GRBL controller with screw-terminal step/dir/enable breakouts; an
  all-in-one board (e.g. an Openbuilds BlackBox-style board) is a pricier
  but tidier alternative. Needs 3 axes (X/Y/Z) at minimum; check whether
  the mill's `A` axis connector is actually used before assuming a 4th
  axis is needed.
  - Note: GRBL/Arduino boards output native 5V TTL logic, which lines up
    with the "needs a strong 5V output, 3.3V won't work" requirement
    found for the spectraLIGHT `COMPUTER` port — good sign this pairing
    will work electrically, but still needs confirming.

- **DB25 male connector + cable/breakout** — to wire the new board's
  step/dir/enable/spindle-on signals into the spectraLIGHT box's existing
  `COMPUTER` socket, pin-for-pin per the confirmed pinout.

- **USB A-to-B (or A-to-Micro, depending on board) cable** — connects the
  new controller board to the Windows 11 PC.

## Testing / safety (get these regardless of final board choice)

- **Multimeter** — needed before touching wiring to confirm actual pin
  assignments and check for continuity/shorts, rather than trusting the
  secondhand pinout blindly.
- **Small standoffs/enclosure or perfboard** — to mount the new
  controller board safely near the spectraLIGHT box rather than leaving
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
