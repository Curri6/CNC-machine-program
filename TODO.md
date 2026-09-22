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
- [x] Power on the Windows 95 machine and check for the original
      software. **Done** — `C:\MPSPRO` is fully intact (MPS2003 and
      relatives, plus config files). See `JOURNAL.md`.
- [ ] **Back up `C:\MPSPRO` entirely** (ideally a full disk image) before
      anything ever happens to that drive — it's a working reference
      for the exact G-code dialect and motion parameters. Not yet done.
- [ ] Open the remaining config files not yet checked: `Param3.dat`,
      `Param51.dat`, `Param51s.dat`, `Paramp3.dat` (Notepad, like
      `Params.dat` already read).
- [ ] **Physically trace the PC's parallel port cable** — `Params.dat`
      confirms the real working setup uses the PC's own standard
      LPT1/LPT2 ports (888/632 decimal), not the spectraLIGHT ISA card
      address. Find out: does that cable plug into the MicroProto
      breakout box (DIN X/Y/Z/A connectors) or the spectraLIGHT box's
      `COMPUTER` port? This is now **higher priority** than the DB25
      pinout research below — it tells us which box is actually live,
      and may make the spectraLIGHT-specific pinout research moot.
- [ ] Confirm the `COMPUTER` DB25 pinout for whichever box turns out to
      be the active one — still only have a secondhand forum summary
      (see `JOURNAL.md`), not verified against a primary source.
      - [x] Sent a documentation request to Intelitek (support form /
            info@intelitek.com) asking for the Interface Card's pinout —
            **no reply after several days; follow up by phone** (script
            already worked out, see chat).
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
            (multimeter/logic analyzer) while jogging a single axis via
            the now-confirmed working `Steptxt`/MPSTEXT program — only
            once the area around the mill is confirmed physically clear.
- [ ] Check whether other schools received similar Perkins-funded
      spectraLIGHT/MicroMill equipment around the same time — a sister
      machine elsewhere might still have its manual or nameplate intact.
- [ ] Check whether this PC/setup ever had a second parallel port card
      (for a 4th/"A" rotary axis) — `Params.dat` confirms the software
      is configured to expect one (port 632/0x278/LPT2) but the one back
      panel photo we have only shows a single built-in DB25. Worth
      checking the 3 expansion-slot brackets on the back of the case for
      a second DB25 we might have missed.

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
