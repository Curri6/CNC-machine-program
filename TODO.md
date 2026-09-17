# To-Do List

Ordered roughly by what has to happen before the next thing can. See
`JOURNAL.md` for the full backstory behind each item.

## Before any hardware is touched or ordered

- [x] MicroMill 2000 manual (MicroProto/Taig) — uploaded and read. It's a
      software manual, no DB25 pin table, but confirmed the direct
      parallel-port bit-banging theory and gave useful motion constants.
      See `JOURNAL.md`.
- [ ] Download and upload the **spectraLIGHT Mill manual** (Intelitek) —
      still needed, this session's network access couldn't fetch it
      directly: `https://downloads.intelitek.com/Manuals/CNC/Discontinued_Machines/spectraLIGHT_Mill_WIN_Manual.pdf`
- [ ] Confirm the `COMPUTER` DB25 pinout — still only have a secondhand
      forum summary (see `JOURNAL.md`), not verified against a primary
      source yet. Neither manual read so far has a pin table, so this may
      end up needing a physical continuity trace instead.
- [ ] Check whether this PC/setup ever had a second parallel port card
      (for a 4th/"A" rotary axis, per the MPS2003 manual) — the one back
      panel photo we have only shows a single DB25.
- [ ] Power on the Windows 95 machine and check for the original CNC
      software (MicroProto MPS2000/MPS2003, and/or spectraLIGHT software)
      still installed. **Do this before wiping or reimaging that drive.**
      If found, copy off: the program itself, any config/calibration
      files, and any saved job files.
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
