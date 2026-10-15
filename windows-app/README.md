# A-Tech CNC (Windows 11 app)

Making G-code, previewing jobs and moving files for the school's MicroMill, whose old
Windows 95 PC runs MPS2003. The full how-to is in the app's **Help** tab.

| Tab | What it does |
| --- | --- |
| **Jobs** | Library of job files (add, or drag them in). Preview in top, front, side and 3D, colored by depth. ▶ Play moves the tool through the job; clicking the preview finds that G-code line. Summary (size, deepest cut, estimated time, feeds). Checks against MPS2003 and your limits. **Send to old PC** / **Save copy to USB**. |
| **Make G-code** | Design a job as steps — holes (list, grid, bolt circle), rectangles and circles (pocket, cut out, cut a hole, engrave), text in any font, lines, facing — and pick a bit for each. The app works out spindle speed, feeds, passes, offsets, pecks and holding tabs for that bit and material, refuses jobs a bit can't do (a drill can't pocket; a hole bigger than the drill needs an end mill, which mills it round), previews it with the stock and the bit's width, and saves one job file per bit to the Jobs library. |
| **⛏ Bits** | The tool list (tools.json): flat and ball end mills, drills, V-bits, with size, flutes, cutting length, angle. Shows what the app will do with each bit in each material. |
| **Machine Link** | Lights for the laptop address (192.168.50.1), the old PC (192.168.50.2 ping) and the link. One-time **Set up network…** (asks for admin). Jobs waiting for the old PC, backups received (checked against the old PC's manifest and zipped), activity log, and the commands to type on the old PC. |
| **Help** | Step-by-step instructions. |

**The app never starts a job and can't move the machine.** A person at the
machine loads and runs each job in MPS2003.

## Getting it

* **ATechCNC.exe**: download it from
  https://github.com/Curri6/CNC-machine-program/releases/latest/download/ATechCNC.exe
  (built by GitHub Actions, workflow **Build Windows app**, every time
  `windows-app/` changes on main). It's one file; double-click to run. Windows may show
  "Windows protected your PC" the first time; click **More info → Run anyway**.
* **From source**: install Python 3.10+ from python.org, then double-click
  `run_app.bat`. The first run installs PySide6.
* **Developers**: `pip install -r requirements.txt`, then `python main.py`.

## How the cable link works

The old PC only has Windows 95's own `FTP.EXE`, so the app is a small FTP
server (`link/ftp_server.py`), and the old PC always starts each transfer:

* **Backup, old PC → app**: `C:\NETUP\SEND` uploads C:\MPSPRO plus a
  MANIFEST.TXT of sizes. Each backup goes into `Documents\A-Tech CNC\Received`
  and is checked against the manifest, then zipped if every file matches.
* **Jobs, app → old PC**: **Send to old PC** puts the job under an 8.3 name
  with DOS line endings into `Documents\A-Tech CNC\To Old PC`. The old PC
  runs `C:\NETUP\GET NAME.TAP`. `GET.BAT` itself is served by the app; the
  Help tab shows how to fetch it the first time.

Only active-mode FTP is offered (the mode Windows 95 uses). The data
connection may only go back to the computer that connected. Only
192.168.50.x can connect. Uploads can't leave the backup folder, and
downloads only come from To Old PC.

## Files

| Path | |
| --- | --- |
| `main.py` | entry point |
| `app_config.py` | folders (`Documents\A-Tech CNC`) and settings.json |
| `library.py` | job library, DOS names, putting jobs in To Old PC |
| `gcode/parser.py` | G-code reader (modal moves, G90/G91/G92, arcs, G81/G83) |
| `gcode/analysis.py` | summary, time estimate, checks |
| `gcode/dosfile.py` | 8.3 names, CRLF |
| `cam/tools.py` | bits, materials, speeds and feeds (`cutting_data`) |
| `cam/operations.py` | the step types and how each bit cuts them |
| `cam/geometry.py`, `cam/builder.py` | shapes; writing MPS2003-style G-code |
| `cam/program.py` | projects (.cncproj) and one job file per bit |
| `link/ftp_server.py` | the link |
| `link/netcheck.py`, `link/network_setup.ps1` | address check, ping, one-time setup (admin) |
| `link/old_pc_files.py` | GET.BAT |
| `ui/` | screens and theme |
| `ATechCNC.spec` | PyInstaller recipe for the exe |

## Tests

```
python -m tests.test_parser    # G-code reader
python -m tests.test_core      # settings, DOS names, analysis, library
python -m tests.test_cam       # the G-code maker: bits, feeds, every step type
python -m tests.test_link      # FTP link, incl. the real `ftp` client if installed
python -m tests.test_ui        # the screens, offscreen (QT_QPA_PLATFORM=offscreen)
```

## How the G-code maker writes jobs

Only what MPS2003's manual lists and its own sample jobs use: `G20`, `G90`,
`G00`/`G01` in inches with four decimals, comments on their own line in
`( )`, `M00` to pause (put in the bit, set and start the spindle, press C),
`M02` at the end. No `M03` spindle codes, no `G41` cutter compensation and
no canned drilling cycles: the app works out the offsets, arcs (as short
straight moves) and pecks itself, so nothing depends on how MPS2003 treats
those codes. One file per bit, because the mill has no tool changer and Z
has to be zeroed again after each bit change.

Speeds and feeds (`cam/tools.py`): best spindle speed from the material's
surface speed and the bit's size; feed from chip per tooth × flutes × RPM;
if that's over the machine's top speed (13.5 in/min, Settings) the feed is
capped and the **spindle is slowed** to keep a real chip, picking from the
spindle speeds in Settings. Depth per pass and stepover come from the
material and the bit, limited by the bit's cutting length. These are
cautious starting points for a light mill.
