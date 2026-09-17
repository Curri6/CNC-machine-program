# To-Do List

Ordered roughly by what has to happen before the next thing can. See
`JOURNAL.md` for the full backstory behind each item.

## Before any hardware is touched or ordered

- [ ] Download and upload the two manual PDFs so they can actually be
      read (this session's network access couldn't fetch them directly):
      - spectraLIGHT Mill manual (Intelitek)
      - MicroMill 2000 manual (MicroProto/Taig)
- [ ] Confirm the `COMPUTER` DB25 pinout against that manual — the pinout
      in `JOURNAL.md` is from a secondhand forum summary, not verified yet.
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
