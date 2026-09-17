# To-Do List

Ordered roughly by what has to happen before the next thing can. See
`JOURNAL.md` for the full backstory behind each item.

## Before any hardware is touched or ordered

- [x] MicroMill 2000 manual (MicroProto/Taig) — uploaded and read. It's a
      software manual, no DB25 pin table, but confirmed the direct
      parallel-port bit-banging theory and gave useful motion constants.
      See `JOURNAL.md`.
- [x] spectraLIGHT Mill manual (Intelitek) — uploaded as a zip and read
      in full (251 pages). Confirmed the `COMPUTER` DB25 is actually a
      dedicated **ISA bus expansion card** ("Interface Card," factory
      address 0x3A0), not a real parallel port — meaning the original
      PC-side hardware genuinely cannot be reused on any modern PC (no
      ISA slots exist anymore), full stop. See `JOURNAL.md`. Still no
      pin-level signal table in this manual either.
- [ ] Confirm the `COMPUTER` DB25 pinout — still only have a secondhand
      forum summary (see `JOURNAL.md`), not verified against a primary
      source. Neither manual has a pin table.
      - [x] Sent a documentation request to Intelitek (support form /
            info@intelitek.com) asking for the Interface Card's pinout —
            awaiting reply.
      - [ ] Post on forums that already discuss this exact hardware
            asking if anyone has the pinout from their own
            reverse-engineering: practicalmachinist.com ("Need help on a
            light machines spectralight cnc mill program mach 3"),
            homeshopmachinist.net ("Help with a spectraLIGHT mill"),
            cnczone.com.
      - [ ] Contact Steven Rhine / Rhine Labs (stevenrhine.com) — he's
            documented restoring this same Light Machines equipment and
            may have gotten further on the pinout.
      - [ ] Fallback if no one has it: empirically probe the cable
            (multimeter/logic analyzer) while jogging an axis on the
            still-working Win95 system.
- [ ] Check whether other schools received similar Perkins-funded
      spectraLIGHT/MicroMill equipment around the same time — a sister
      machine elsewhere might still have its manual or nameplate intact.
- [ ] Check whether this PC/setup ever had a second parallel port card
      (for a 4th/"A" rotary axis, per the MPS2003 manual) — the one back
      panel photo we have only shows a single DB25.
- [ ] Power on the Windows 95 machine and check for the **spectraLIGHT
      "Control Program"** (a real Windows 95 GUI app per the manual —
      more likely to be what's actually installed than MPS2003) and any
      config/calibration/job files. **Do this before wiping or
      reimaging that drive.** If found, copy off the program, configs,
      and any saved job files.
- [ ] Figure out the actual signal path between the two black boxes —
      does the spectraLIGHT box's output really feed the MicroProto
      breakout panel, or is it wired some other way? (Visual trace of the
      cable between them, or manual diagram, should answer this.)
- [ ] With the machine powered OFF, use a multimeter to confirm which
      wires go where inside the accessible connectors (not inside the
      sealed spectraLIGHT box) before assuming the pinout is correct.

## Once the pinout/signal path is confirmed

- [ ] Pick the exact retrofit motion-control board (GRBL-based board is
      the leading candidate — see `PARTS_LIST.md`).
- [ ] Order parts.
- [ ] Wire the new board into the spectraLIGHT box's existing `COMPUTER`
      DB25 socket, matching the confirmed pinout.
- [ ] Bench-test motion (jog each axis a small, safe distance) before
      trusting it with a real cutting job.

## Software (not started — explicitly on hold until hardware plan locks)

- [ ] Scaffold the Python + PySide6 desktop app.
- [ ] G-code sender/streamer talking to the retrofit board over
      USB-serial.
- [ ] Toolpath preview + manual jog controls + job queue UI.
- [ ] Test against the bench-tested hardware from the step above.

## Logistics

- [ ] Owner sending more machine photos "Tuesday" — revisit `JOURNAL.md`
      and this list once those arrive, update as needed.
