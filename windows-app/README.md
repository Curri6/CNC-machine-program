# A-Tech CNC Job Sender (beta)

Windows 11 desktop app for the A-Tech CNC machine project. See
`JOURNAL.md`, `TODO.md`, and `PARTS_LIST.md` in the repo root for the
full backstory — short version: the old Windows 95 PC keeps running
the original MPS2003 software exactly as it always has, and this app
is the modern front end that lets you open a G-code file, check it
against what MPS2003 actually supports, preview the toolpath, and send
it to a small receiver program on the old PC over a private, isolated
Ethernet link.

**Status: beta.** Built to unblock development while the machine's
mechanical/electrical soundness is being verified separately (Phase 0
in `TODO.md`). Not yet tested against the real machine or the real
receiver program — only against a dev-only mock receiver (see
`dev_tools/mock_receiver.py`).

## What this app does

- Opens a G-code file (`.tap`, `.nc`, `.gcode`, or plain `.txt`).
- Checks every command against the exact set MPS2003 understands
  (`gcode/parser.py` — see `JOURNAL.md` for where that list came from)
  and lists anything unsupported as a warning before you send it.
- Renders a 2D top-down toolpath preview (rapid moves dashed gray,
  cutting moves solid blue) so you can sanity-check the job visually.
- Sends the file over a plain TCP connection to the receiver program's
  host/port.

## What this app deliberately does NOT do

- It does not talk to the CNC machine directly, and it never will
  unless the hardware retrofit plan (currently out of scope — see
  `JOURNAL.md`) is revisited.
- It never auto-runs anything on the old PC. Per the project's standing
  safety rule, a person must always be physically present at the old
  computer to load and start a job in MPS2003 themselves.
- It doesn't require a username/password on the receiver side — that
  was intentionally dropped since the link is a private, isolated
  point-to-point Ethernet connection with nothing else on it, not the
  school's shared network.
- It's not a CAD/CAM tool. It imports G-code made elsewhere (any
  computer in the school, any CAM software) rather than generating
  toolpaths from scratch.

## Running it

```
pip install -r requirements.txt
python main.py
```

## Trying it without the real machine

The real receiver program has to be written separately for the old
Windows 95 PC, in period-appropriate tooling (Visual Basic 6 or plain
C with Winsock — Windows 95 can't run Python or modern .NET). That
hasn't been built yet. In the meantime, `dev_tools/mock_receiver.py` is
a throwaway Python stand-in that speaks the same tiny protocol
(`network/sender.py`'s docstring has the exact wire format) so the
sending side of this app can be tested on a modern machine:

```
python dev_tools/mock_receiver.py 8420
```

Then, in the app, point Host at `127.0.0.1` and Port at `8420` and hit
Send — the file lands in `dev_tools/received_jobs/`.

## Layout

```
main.py              entry point
gcode/parser.py       G-code parsing + MPS2003 command validation + toolpath flattening
ui/main_window.py     the whole app window
ui/toolpath_view.py   2D toolpath preview widget
network/sender.py     TCP client that sends a job to the receiver
dev_tools/            dev-only tools, not shipped to the real machine
tests/                sanity tests (no test framework needed: `python tests/test_parser.py`)
```

## Known gaps / not done yet

- No jog controls or live machine status — out of scope for this phase
  entirely (see "What this app deliberately does NOT do" above).
- Toolpath preview assumes absolute positioning throughout (matches
  what the MPS2003 manual documents — G90/G91 were never shown in its
  examples). An imported file using incremental mode will be flagged
  as using an unsupported code rather than rendered incorrectly.
- The real Windows-95-side receiver program doesn't exist yet — that's
  a separate, near-term piece of work (see `TODO.md`, Phase 1).
- No packaging/installer yet for handing this to someone else to run.
