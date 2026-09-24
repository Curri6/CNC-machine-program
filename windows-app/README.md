# A-Tech CNC Job Sender (beta)

Windows 11 desktop app for the A-Tech CNC machine project. See
`JOURNAL.md`, `TODO.md`, and `PARTS_LIST.md` in the repo root for the
full backstory — short version: the old Windows 95 PC keeps running
the original MPS2003 software exactly as it always has, and this app
is the modern front end that lets you open a G-code file, check it
against what MPS2003 actually supports, preview the toolpath, and
export a copy ready to carry over to the machine.

**Status: beta.** Built to unblock development while the machine's
mechanical/electrical soundness is being verified separately (Phase 0
in `TODO.md`).

## What this app does

- Opens a G-code file (`.tap`, `.nc`, `.gcode`, or plain `.txt`).
- Checks every command against the exact set MPS2003 understands
  (`gcode/parser.py` — see `JOURNAL.md` for where that list came from)
  and lists anything unsupported as a warning before you export it.
- Renders a 2D top-down toolpath preview (rapid moves dashed gray,
  cutting moves solid blue) so you can sanity-check the job visually.
- Exports a copy of the file to wherever you choose — a USB drive, a
  floppy, anywhere — ready to carry over to the machine.

## What this app deliberately does NOT do

- **No networking.** The CNC machine is in a teacher's classroom, so
  every job already has to be carried over there in person regardless
  — a network transfer feature wouldn't save that step. (An earlier
  version of this app had a network sender; it was removed once that
  became clear. See `JOURNAL.md` if you're wondering where it went.)
- It does not talk to the CNC machine directly, and it never will
  unless the hardware retrofit plan (currently out of scope — see
  `JOURNAL.md`) is revisited.
- It never auto-runs anything. Per the project's standing safety rule,
  a person must always be physically present at the old computer to
  load and start a job in MPS2003 themselves.
- It's not a CAD/CAM tool. It imports G-code made elsewhere (any
  computer in the school, any CAM software) rather than generating
  toolpaths from scratch.

## Running it

```
pip install -r requirements.txt
python main.py
```

## Layout

```
main.py              entry point
gcode/parser.py       G-code parsing + MPS2003 command validation + toolpath flattening
ui/main_window.py     the whole app window
ui/toolpath_view.py   2D toolpath preview widget
tests/                sanity tests (no test framework needed: `python tests/test_parser.py`)
```

## Known gaps / not done yet

- Toolpath preview assumes absolute positioning throughout (matches
  what the MPS2003 manual documents — G90/G91 were never shown in its
  examples). An imported file using incremental mode will be flagged
  as using an unsupported code rather than rendered incorrectly.
- No packaging/installer yet for handing this to someone else to run.
