# To-Do List

Ordered roughly by what has to happen before the next thing can. See
`JOURNAL.md` for the full backstory behind each item.

**Plan as of 2026-09-24**: Phase 0 and Phase 1 below are the whole
active plan — verify the machine still works with the original
software, then use the Windows 11 app as a G-code importer/previewer/
exporter. **No networking** — the machine is in a teacher's classroom,
so every job already has to be carried over there in person regardless,
which makes a network transfer pointless. The old PC needs no new
software and no network connection for this project at all; it just
keeps running MPS2003 exactly as it always has. **The hardware retrofit
(TurboTaig/GRBL/etc., kept further down for reference only) is no
longer part of the active plan** — owner decided Phase 0/1 is
sufficient on its own, not just a stepping stone. That section would
only become relevant again if the old PC or MPS2003 ever stops working
entirely.

**Standing safety rule for all phases**: a job must never be able to
start running on the machine without a person physically present to
confirm it. Never design around this, in this phase or later ones.

## Phase 0 — verify the machine still physically works

- [x] Motors (X/Y/Z), spindle motor, and original MPS2003 software
      confirmed working (2026-09-28, per owner).
- [x] **Back up `C:\MPSPRO`.** (2026-10-14: done over the network; zip reviewed; settings in `machine-backup/`.) Networking isn't installed on the Win95
      PC and there are no install files to add it, and Win95 can't
      read USB drives, so the network/FTP attempt was abandoned. See
      `JOURNAL.md` (2026-09-28). Two working options:
      - **Serial cable (owner's chosen route):** HyperTerminal is
        installed on the Win95 PC. Needs a USB-to-serial adapter
        (FTDI preferred) and a DB9 female-female null-modem cable.
        Send each file from HyperTerminal (Direct to Com1, 57600 8N1,
        no flow control, Zmodem) to Tera Term on the laptop (ZMODEM
        Receive, download dir `Downloads\CNC_backup`). Send from a
        `C:\MPSBAK` copy made with `xcopy /h` + `attrib -h -s -r` so
        hidden files are included.
      - **Floppy:** a blank floppy plus a USB floppy drive for the
        laptop; `xcopy C:\MPSPRO A:\ /s /e /h /i /c /y`.
      Once the files are uploaded, review the other `Param*.dat` files
      and the sample `.tap` jobs.
      - **Goal set 2026-09-28: enable networking on the Win95 PC, then
        send files over the network.** Device Manager shows the card as
        `PCI Ethernet Controller` with no driver. Steps:
        1. [x] Identify the card. **Done 2026-09-28:** it's
           `VEN_8086&DEV_2449`, the **Intel PRO/100 VE Network
           Connection** (on-board, Intel ICH2 chipset). It isn't in
           Win95's built-in adapter list, so it needs Intel's driver. The
           other PCI IDs are all Intel 815/ICH2 parts (graphics, USB,
           AC'97 audio, IDE, SMBus). Driver sources: Intel's legacy
           support page for the PRO/100 VE; failing that, Intel's own
           PRO/100 & PRO/1000 driver CD v9.0 on the Internet Archive
           (archive.org/details/pro1001000), which includes a Win95
           driver for PRO/100. Avoid third-party "driver download" sites.
        2. [ ] Get a legitimate Windows 95 CD (ask school IT). It's
           needed for TCP/IP and core networking files. First check the
           installed version (Control Panel → System → General) so the
           CD matches. An archive.org ISO was found 2026-09-29; only use
           it with IT's OK, burned to CD by IT.
        3. [x] Get the card's Windows 95 driver from the card maker.
           **Owner has it (2026-09-30).** Still to confirm that it's the
           Win9x version (.INF plus a WIN9X/WIN95 folder) before burning.
        4. [x] Get the driver onto the old PC via floppy (needs a USB
           floppy drive on the laptop) or a CD burned by IT. **Update
           2026-09-30:** owner has a DVD and burner. Burn one data DVD
           (Mastered/ISO 9660, not UDF) with `\WIN95\` CABs +
           `\INTEL\` driver. See `JOURNAL.md`. **2026-10-09:** the
           DVD burned, but Win95 sees it as empty (UDF and/or the drive
           can't read burned DVDs). The DeskCNC CD-R doesn't read in the
           old PC either. Next: run `tools/burn_win95_disc.bat` with the
           DVD in the laptop. It reports the disc type first, builds the
           image and verifies it ("CHECK PASSED") before asking for YES,
           then burns ISO 9660/Joliet. Send Claude a screenshot of the
           check before typing YES. **2026-10-10: the DVD is lost.** The
           laptop drive failed mid-burn, finalized the disc, and never
           recorded the new section (confirmed via MMC track info). Next:
           back up the DeskCNC CD-R's files, read its session state with
           `verify_win95_disc.bat` (admin), then decide on a CD burn.
           **Superseded 2026-10-10: a new blank DVD-R burned
           successfully** (4x, 142 s, ISO 9660 + Joliet at block 0).
           Next: verify on the laptop, then read it on the Win95 PC.
           **Done 2026-10-12:** VERIFIED on the laptop, and the Win95 PC
           reads it as `Win95net (H:)` with Intel + Win95 folders.
           The SD-608 had read errors/freezes during installs, so the disc
           was copied to `C:\NETSETUP` with xcopy; install from there.
        5. [ ] (2026-10-12: Intel's INF hangs Win95; the custom
           WIN95ICH.INF installs E100B.SYS cleanly, but it's Code 10
           (won't start the ICH2 chip). Next route: the ODI driver
           E100BODI.COM, which supports DEV_2449 but needs Novell's
           LSL.COM, not on the PC; ask IT. See JOURNAL.md.)
           **2026-10-12: LSL.COM found in the owner's Intel 6.2 download.
           Kit built (`tools/win95/netdisc`, tested). Next:**
           a. [x] (2026-10-14, Done) Burn NETDISC with burn tool option 2 onto the working
                  DVD-R (2nd session, 45 files; photo at CHECK PASSED).
           a2. [ ] Fix verify_win95_disc: generic mode, skip BLANK track,
                  judge by last written track (2026-10-14 false alarm).
           b0. [x] Session 2 on the old DVD: old drive reads only session 1
                  (2026-10-14). Re-burn NETDISC on a NEW blank DVD-R.
           b1. [x] (2026-10-14 done) Old disc: burn WIN95 + INTEL again as session 3 (option 1)
                  so new PCs show them; keep as labeled backup.
           b2. [x] (2026-10-14 done) New DVD-R: burn NETDISC as session 1 (option 2).
           b. [x] (2026-10-14) Old PC reads it? (H: shows README.TXT, COPYNET.BAT.)
           c. [x] (2026-10-14 OK; ODIHLP + FTP found) `H:` → `COPYNET` (photo).
           d. [x] (2026-10-14 PASSED: 8086/2449, 100 Mbps full duplex) MS-DOS mode → `C:\NETUP\TEST` (photo: card found? link?).
           e. [x] (2026-10-14: AUTOEXEC line typed by hand — file was 0 bytes; ODI adapter working) `C:\NETUP\INSTALL`; disable the Code 10 adapter; add
                  "Existing ODI Driver"; TCP/IP 192.168.50.2/24; restart;
                  `C:\NETUP\CHECK` (photo).
           i. [ ] Try the new app on the laptop (ATechCNC.exe from
                  github.com/Curri6/CNC-machine-program/releases/latest): Set up network…,
                  fetch GET.BAT once on the old PC, then Send to old PC + GET.
                  Step-by-step checklist: windows-app/TESTING.md (parts A–D).
           j. [x] (2026-10-15: "Make G-code" tab + ⛏ Bits list, app v1.1) tool
                  list and G-code making that adapts to each bit.
           k. [ ] (needed before the first made job is cut) At the mill: write down the real spindle speeds (belt steps) and
                  put them in Settings → Spindle speeds; check the bits you have
                  and enter them in ⛏ Bits (TESTING.md part E).
           l. [~] (2026-10-15: PASSED in DOSBox with the real MPS2003.EXE — all step
                  types, M00 pause + C) Same on the real old PC: NAMEPLT5.TAP,
                  M, P, M, 3, C. No cutting.
           o. [ ] Dry run DRYNAMT5.TAP on the mill (spindle off, cuts air), person present.
           t. [ ] **Spindle belt broke (2026-10-19).** Find a spare in school or have the
                  school get one (measure: length, width, notched). Blocks only real cutting;
                  jog check, travel and dry run can go ahead.
           r. [x] (2026-10-19: spare Z motor fitted, Z goes up and down) **BLOCKER (2026-10-16): Z jogs down but not up — Z motor is bad, being
                  replaced with the spare.** Then slow jog test, re-zero, direction check.
                  Later: multimeter-check the bad motor's cable at the motor end (may be fixable).
                  (Earlier notes:) Diagnose: slow jog,
                  top of travel?, hand-turn with power off, gib/lock screw, coupling
                  set screws, swap Z/X plugs; clean + light oil on Z leadscrew and dovetail.
                  2026-10-16: very hard to turn by hand → find the bind (motor vs screw vs gib).
                  Photo: brass nut corroded (green), old grease, looks tipped → clean + seat square.
                  Z axis now off the mill (parts in the right order); bench test, oil, refit aligned.
                  Works apart, binds when reassembled → alignment/gib/pinch; rebuild one step at a time.
                  No dry run or cutting until fixed.
           s. [ ] X/Y look swapped in the jog check (X moves the table toward you):
                  confirm; if so swap the X and Y plugs back (power off) and redo step 25.
           q. [ ] Jog check (TESTING.md 25): + direction of X, Y, Z; read X/Y travel →
                  Settings → Work area. Owner's ruler photos 2026-10-16: table ~18 in.
           p. [ ] First cut: NAMEPLT5.TAP on scrap acrylic (0.02 in engraving), person present.
           m. [ ] Later, if wanted: import drawings (DXF/SVG) into the Make tab;
                  filled (pocketed) letters.
           n. [ ] After the first real cuts, adjust the material numbers if they
                  feel too slow or too aggressive (cam/tools.py MATERIALS).
           h. [ ] Laptop → old PC: send SQUARE1.TAP and SQUARE0.TAP, GET both, and
                  Plot Preview SQUARE0 in MPS2003 with the motor power OFF (M, P, M, 3,
                  C). SQUARE1's preview is blank by design (all above Z0). Built and
                  tested 2026-10-14; waiting on the real try.
           g. [ ] Ask whether MPS2003 really ignores M03/M07/G40/G41 (factory
                  samples use them): run GEAR.TAP in Plot Preview (P) — no
                  movement — and watch for an error. Person present.
           f. [x] (2026-10-14 DONE: 20 files, 832,754 bytes, CHECK PASSED) Laptop `receive_files.bat`, old PC `C:\NETUP\SEND`;
                  upload the zip here. Install the card driver and TCP/IP; set a static IP of
           192.168.50.2 / 255.255.255.0. **In progress 2026-09-28:**
           adapter added as the built-in "Intel EtherExpress PRO/100
           (PCI)" driver (may not fit the VE chip), TCP/IP added with
           192.168.50.2/24, computer named `A-TECH-IBM`. **Blocked:**
           Windows asked for the Win95 CD and couldn't find `arp.exe`
           on the hard drive. Needs the CD (step 2).
        6. [ ] Send files with the FTP steps in `JOURNAL.md`
           (2026-09-28): `pyftpdlib` on the laptop at 192.168.50.1,
           Win95 `ftp.exe` with `mput`.
      - **Update 2026-09-28: no purchases possible.** Near term,
        photograph the text files (`Param3.dat`, `Param51.dat`,
        `Param51s.dat`, `Paramp3.dat`, plus a sample `.tap` or two) in
        Notepad/WordPad for review. For a real backup, ask the teacher
        or tech department to lend a USB floppy drive, a
        serial cable + USB-serial adapter, or a Windows 95 install CD.
        Not urgent, since the machine is working.
- [ ] Test-cut a piece of acrylic using the **original, unmodified**
      MPS2003 software on the existing Windows 95 PC. Safety sequence
      (from the manual itself): move each axis by hand with power off
      first (check for binding); mount a plastics-appropriate cutter;
      secure the stock firmly; run **Preview, then Dry Run** (built
      into MPS2003) before any real cut; start with the simplest
      possible job (a shallow face or small engraving), not a full
      cutout.

## Phase 1 — Windows 11 app as G-code importer/previewer/exporter

- [x] ~~Networking (isolated link, then real school network, receiver
      program, etc.)~~ — **dropped entirely 2026-09-24.** The machine
      is in a teacher's classroom, so files already have to be carried
      over in person regardless; a network path wouldn't save that
      trip. See `JOURNAL.md`'s 2026-09-24 update. The old PC needs no
      new software and no network connection for this project — it
      just keeps running MPS2003 as-is, and receives files exactly like
      it always has (manually, on removable media). The school IT
      approval to join the network still stands on record if a real
      reason for it ever comes up, but nothing here depends on it.
- [x] Scaffold the Windows 11 app (Python + PySide6) as a G-code
      **importer/previewer/exporter**. **Beta built 2026-09-22, updated
      2026-09-24** — see `windows-app/` (run with `pip install -r
      requirements.txt` then `python main.py`; `windows-app/README.md`
      has the full rundown). Working: opens `.tap`/`.nc`/`.gcode`/`.txt`
      files, validates every command against exactly what MPS2003
      supports (`G00 G01 G02 G03 G17 G20 G21 G43 G81 G83 G98 G99`,
      `M02 M97 M99` — see `JOURNAL.md`) and lists anything unsupported
      as a warning, renders a 2D toolpath preview, and **exports a copy
      of the file to wherever you choose** (USB drive, floppy, etc.) to
      carry over to the machine. The networking code (TCP sender, mock
      receiver) has been removed — see `JOURNAL.md`. **Not yet tested
      against the real machine** — that's the point of Phase 0 above.
      Native G-code generation inside the app is a possible nice-to-have
      later, not required now.

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
- [x] **Back up `C:\MPSPRO` entirely** — done 2026-10-14 over the network
      (all 20 files; owner keeps the zip). A full disk image is still not done.
- [x] Open the remaining config files — done 2026-10-14, decoded in
      `machine-backup/README.md` (MPS2003 uses PARAM3.DAT).
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
