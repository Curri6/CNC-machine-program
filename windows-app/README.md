# A-Tech CNC (Windows 11 app)

Jobs, preview and file transfer for the school's MicroMill, whose old
Windows 95 PC runs MPS2003. The full how-to is in the app's **Help** tab.

| Tab | What it does |
| --- | --- |
| **Jobs** | Library of job files (add, or drag them in). Preview in top, front, side and 3D, colored by depth. ▶ Play moves the tool through the job; clicking the preview finds that G-code line. Summary (size, deepest cut, estimated time, feeds). Checks against MPS2003 and your limits. **Send to old PC** / **Save copy to USB**. |
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
| `link/ftp_server.py` | the link |
| `link/netcheck.py`, `link/network_setup.ps1` | address check, ping, one-time setup (admin) |
| `link/old_pc_files.py` | GET.BAT |
| `ui/` | screens and theme |
| `ATechCNC.spec` | PyInstaller recipe for the exe |

## Tests

```
python -m tests.test_parser    # G-code reader
python -m tests.test_core      # settings, DOS names, analysis, library
python -m tests.test_link      # FTP link, incl. the real `ftp` client if installed
python -m tests.test_ui        # the screens, offscreen (QT_QPA_PLATFORM=offscreen)
```
