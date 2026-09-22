# To-Do List

Ordered roughly by what has to happen before the next thing can. See
`JOURNAL.md` for the full backstory behind each item.

**Plan as of 2026-09-22**: Phase 0 and Phase 1 below are the whole
active plan — verify the machine still works with the original
software, then build the Windows 11 app as a G-code importer/sender
talking to a plain "receiver" program on the old PC. **The hardware
retrofit (TurboTaig/GRBL/etc., kept further down for reference only)
is no longer part of the active plan** — owner decided Phase 0/1 is
sufficient on its own, not just a stepping stone. That section would
only become relevant again if the old PC or MPS2003 ever stops working
entirely.

**Standing safety rule for all phases**: a job must never be able to
start running on the machine without a person physically present to
confirm it. Never design around this, in this phase or later ones.

## Phase 0 — verify the machine still physically works

- [ ] Test-cut a piece of acrylic using the **original, unmodified**
      MPS2003 software on the existing Windows 95 PC. Safety sequence
      (from the manual itself): move each axis by hand with power off
      first (check for binding); mount a plastics-appropriate cutter;
      secure the stock firmly; run **Preview, then Dry Run** (built
      into MPS2003) before any real cut; start with the simplest
      possible job (a shallow face or small engraving), not a full
      cutout.

## Phase 1 — Windows 11 app as G-code importer/sender + plain "receiver" on the old PC

- [ ] Check what network adapter is actually in the old PC: **Start →
      Settings → Control Panel → System → Device Manager → Network
      adapters**. Owner says it already has a WiFi/Ethernet card —
      need to confirm exactly what, to know what's actually usable.
- [ ] Set up a **private, isolated, direct link** between the old PC
      and the new Windows 11 PC only (a single Ethernet cable, or a
      small dedicated switch with just these two machines on it) —
      explicitly **not** the school's actual WiFi/network. Rationale
      logged in `JOURNAL.md`: Windows 95 has no modern WiFi/WPA2
      driver support and no security patches ever, so joining the
      real school network is both likely-infeasible and a real risk
      most IT departments would block.
- [ ] Design and build the **"receiver" program** for the old PC:
      listens for an incoming G-code file over the isolated link and
      saves it to `C:\MPSPRO`. **No username/password** — dropped by
      owner (2026-09-22) since the link is isolated point-to-point, so
      there's no one else who could reach it. Must **never** auto-load
      or auto-run the file — a person still has to load/start it in
      MPS2003 themselves (see standing safety rule above).
      - Windows 95 can't run modern software (no Python 3, no current
        .NET) — this has to be written in period-appropriate tooling,
        most practically **Visual Basic 6** or **plain C with
        Winsock**. Separate small codebase from the main app. Not
        started.
- [x] Scaffold the Windows 11 app (Python + PySide6) as a G-code
      **importer/previewer/sender**. **Beta built 2026-09-22** — see
      `windows-app/` (run with `pip install -r requirements.txt` then
      `python main.py`; `windows-app/README.md` has the full rundown).
      Working: opens `.tap`/`.nc`/`.gcode`/`.txt` files, validates every
      command against exactly what MPS2003 supports (`G00 G01 G02 G03
      G17 G20 G21 G43 G81 G83 G98 G99`, `M02 M97 M99` — see
      `JOURNAL.md`) and lists anything unsupported as a warning, renders
      a 2D toolpath preview, and sends the file over TCP to a receiver
      host/port. Tested end-to-end against a throwaway dev-only mock
      receiver (`windows-app/dev_tools/mock_receiver.py`) since the real
      Windows-95-side receiver doesn't exist yet (see below). **Not yet
      tested against the real machine, real network link, or real
      receiver** — that's the point of Phase 0 above and the item below.
      Native G-code generation inside the app is a possible nice-to-have
      later, not required now.
- [ ] Write the real receiver program for the old Windows 95 PC
      (Visual Basic 6 or C/Winsock — see item above) and test the beta
      app against it for real, over the actual isolated Ethernet link.

## Reference only — hardware retrofit (NOT part of the active plan)

Everything below this point is **not currently planned work**. Kept
only in case the old PC or MPS2003 ever stops working entirely and a
full retrofit becomes necessary again.

### Before any hardware is touched or ordered

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

### Once the TurboTaig/upgrade board situation is sorted

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

### Software (not started — explicitly on hold until hardware plan locks)

- [ ] Scaffold the Python + PySide6 desktop app.
- [ ] G-code sender/streamer talking to the retrofit board over
      USB-serial.
- [ ] Toolpath preview + manual jog controls + job queue UI.
- [ ] Test against the bench-tested hardware from the step above.

## Logistics

- [ ] Owner sending more machine photos "Tuesday" — revisit `JOURNAL.md`
      and this list once those arrive, update as needed.
