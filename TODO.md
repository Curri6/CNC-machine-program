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
- [x] ~~Physically trace the PC's parallel port cable~~ — **resolved by
      cross-checking both manuals instead** (2026-09-22): neither
      manual mentions the other company's product, and the spectraLIGHT
      box's own interconnection diagram shows its axis ports are
      designed for 15-pin/9-pin D-sub cables to Light Machines' *own*
      mill, not the round DIN connectors on the MicroProto panel.
      Working conclusion: **the spectraLIGHT box is not part of this
      machine's active signal path** — the MicroProto panel is. See
      `JOURNAL.md`. A physical trace of the cable plugged into the
      spectraLIGHT box's `COMPUTER` port would still make this fully
      certain rather than "very likely," but is no longer blocking.
- [x] Research how the MicroProto controller actually works. **Done**
      (2026-09-22) — found it very likely uses **raw 3-wire phase
      control per motor**, not step/direction (matches the two-port-
      address evidence in `Params.dat`), and that a generic modern
      step/dir board cannot be wired straight into it (a forum report
      of someone trying exactly that got broken, one-step-only motion).
      See `JOURNAL.md` for the full writeup and sources.
- [ ] **Check the physical driver box/cards for an existing step/dir
      upgrade board** (TurboTaig, MicroProto's own 2003 board, or the
      2006 closed-loop variant) before assuming none is installed —
      would change or eliminate the need to buy one.
- [ ] If none is installed: **buy a TurboTaig board** (Homann Designs,
      ~AU$169, part# TC-01) or track down MicroProto's own official
      step/dir upgrade board — this converts the old 3-wire phase
      interface to standard step/direction, replacing the need to
      reverse-engineer the phase pinout ourselves. See `JOURNAL.md` for
      product links.
- [ ] Confirm the step/dir pinout on the TurboTaig (or equivalent)
      board's input connector (`J9` per the one review found) once it's
      in hand — this is the connector our GRBL-based board will feed.
      Much simpler/better-documented than chasing the MicroProto panel's
      own internal pinout would have been.
      - [x] Sent a documentation request to Intelitek about the
            spectraLIGHT Interface Card — no longer very relevant given
            the spectraLIGHT box is believed unrelated; no reply after
            several days either way.
- [ ] Check whether other schools received similar Perkins-funded
      spectraLIGHT/MicroMill equipment around the same time — a sister
      machine elsewhere might still have its manual or nameplate intact.
- [ ] Check whether this PC/setup ever had a second parallel port card
      (for a 4th/"A" rotary axis) — `Params.dat` confirms the software
      is configured to expect one (port 632/0x278/LPT2) but the one back
      panel photo we have only shows a single built-in DB25. Worth
      checking the 3 expansion-slot brackets on the back of the case for
      a second DB25 we might have missed.

## Once the TurboTaig/upgrade board situation is sorted

- [ ] Pick the exact GRBL-based motion-control board to feed the
      TurboTaig (or equivalent) board's step/dir input — see
      `PARTS_LIST.md`.
- [ ] Order parts.
- [ ] Wire the GRBL board's step/dir output into the TurboTaig board's
      `J9` (or equivalent) input, and confirm the TurboTaig board's
      output still connects correctly to the original MicroProto driver
      cards.
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
