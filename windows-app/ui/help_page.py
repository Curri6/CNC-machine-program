"""Help tab: how to use the app, step by step."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QTextBrowser, QVBoxLayout, QWidget

from ui import theme
from ui.widgets import Card

_CSS = f"""
body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; color: {theme.TEXT}; }}
h1 {{ font-size: 17pt; margin: 0 0 4px 0; }}
h2 {{ font-size: 13pt; margin: 18px 0 6px 0; color: {theme.ACCENT_DARK}; }}
p, li {{ line-height: 145%; }}
code, .cmd {{ font-family: Consolas, monospace; background: #eef2f7; padding: 1px 4px; }}
.cmd {{ display: block; padding: 6px 10px; margin: 4px 0; }}
.box {{ background: #fff7ed; border: 1px solid #fed7aa; padding: 8px 12px; }}
.ok {{ color: {theme.OK}; font-weight: 600; }}
.warn {{ color: {theme.WARN}; font-weight: 600; }}
.muted {{ color: {theme.MUTED}; }}
td {{ padding: 3px 10px 3px 0; vertical-align: top; }}
"""

SECTIONS: list[tuple[str, str, str]] = [
    ("start", "Quick start", """
<h1>A-Tech CNC — quick start</h1>
<p>This app gets jobs ready for the MicroMill and moves files to and from the old
Windows 95 PC (the one that runs MPS2003) over a network cable.</p>
<ol>
<li><b>Add a job:</b> on the <b>Jobs</b> tab click <b>＋ Add jobs…</b> (or drag files onto the window) —
or make one on the <b>Make G-code</b> tab and click <b>Save to Jobs ➜</b>.</li>
<li><b>Check it:</b> look at the preview, the <b>Summary</b> and the <b>Checks</b>. Press <b>▶ Play</b> to watch the tool move.</li>
<li><b>Send it:</b> click <b>Send to old PC ➜</b>. The job waits in the <b>To Old PC</b> folder.</li>
<li><b>On the old PC</b> (MS-DOS Prompt): <table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>C:\\NETUP\\GET JOB1.TAP</code></td></tr></table></li>
<li><b>In MPS2003:</b> press <b>2</b> (Load Program), type <code>TAP</code>, pick the job, press <b>P</b> (Plot Preview) and run it once with no movement before cutting.</li>
</ol>
<p class="box"><b>Safety:</b> the app never starts a job and can't move the machine. A person
at the machine always loads and starts each job in MPS2003, and stays there while it runs.</p>
"""),
    ("jobs", "Adding and checking jobs", """
<h2>The job library</h2>
<p>Jobs you add are <b>copied</b> into <code>Documents\\A-Tech CNC\\Jobs</code>. The file you
added from is never changed. <b>Remove</b> deletes only the app's copy.</p>
<p>Job files can be <code>.TAP .NC .GCODE .NGC .CNC .TXT</code> — plain G-code text.
The search box filters the list by name.</p>
<h2>The preview</h2>
<table>
<tr><td><b>Top / Front / Side / 3D</b></td><td>which way you look at the job</td></tr>
<tr><td><b>Colors</b></td><td>cuts below Z0 go from light blue (shallow) to purple (deepest);
slate = feed moves above the work; dashed grey = rapid G0 moves (turn off with <b>Rapids</b>)</td></tr>
<tr><td><b>Red cross</b></td><td>the job's zero point (X0 Y0) — where you zero the machine in MPS2003 (option 4)</td></tr>
<tr><td><b>Mouse</b></td><td>wheel = zoom, drag = move, double-click = fit, click a line = show it in the G-code</td></tr>
<tr><td><b>▶ Play</b></td><td>moves the orange tool through the job; drag the slider to any point;
the speed box sets moves per step</td></tr>
</table>
<h2>Summary</h2>
<p><b>Estimated time</b> uses the job's feed rates and the machine's top speed (about
13.5 in/min from the old PC's settings). It doesn't count pauses for tool changes (M6) or stops
(M0), so the real job takes a bit longer.</p>
"""),
    ("make", "Making G-code (Make tab)", """
<h1>Making G-code</h1>
<p>The <b>Make G-code</b> tab writes jobs for you. Describe the part as a list of <b>steps</b>,
pick a <b>bit</b> for each step, and the app works out everything else: spindle speed, feed,
how many passes, where the bit has to go so the part comes out the right size, and pecks for
drilling.</p>
<h2>1. The project</h2>
<table>
<tr><td><b>Material</b></td><td>sets how fast and how deep the app cuts (acrylic, wax, wood, aluminum…)</td></tr>
<tr><td><b>Stock</b></td><td>size of the piece you clamp down: X × Y × thickness, in inches
(you can type <code>1/4</code>, <code>0.25</code> or <code>6mm</code>)</td></tr>
<tr><td><b>Zero at</b></td><td>where you will zero X and Y on the machine: the lower-left corner
of the stock, or its centre. Z0 is always the <b>top</b> of the stock.</td></tr>
</table>
<h2>2. Steps</h2>
<p>Click <b>＋ Add step</b> and pick one:</p>
<table>
<tr><td><b>⦿ Holes</b></td><td>a list of points, a grid, or a bolt circle. Hole size 0 = the bit's size.</td></tr>
<tr><td><b>▭ Rectangle / ◯ Circle</b></td><td><b>Pocket</b> clears the inside; <b>Cut out</b> keeps
the inside (bit runs outside the line); <b>Cut a hole</b> keeps the outside (bit runs inside the
line); <b>Engrave on the line</b> follows the line itself.</td></tr>
<tr><td><b>A Text</b></td><td>engraves the outline of the letters in any Windows font.
Letter height = height of a capital letter.</td></tr>
<tr><td><b>╱ Lines</b></td><td>the bit goes from point to point (a slot or a drawing).</td></tr>
<tr><td><b>▤ Face the top</b></td><td>takes a thin layer off the whole top so it's flat.</td></tr>
</table>
<p>All positions are inches from the <b>lower-left corner of the stock</b>; depths are how far
below the top. Steps run in the order of the list (↑ ↓ to move them). Untick a step to leave it
out without deleting it. Click a cut in the preview to jump to the step that made it.</p>
<h2>3. Check and save</h2>
<p>The preview shows the stock (dark box), every cut, and — with <b>Show bit width</b> — how
wide the bit really cuts. <b>Checks</b> lists anything wrong: <span class="warn">✗</span> must be
fixed before saving, <span class="warn">⚠</span> is worth a look.</p>
<p><b>Save to Jobs ➜</b> puts the job file(s) in the Jobs library, where you check them and
<b>Send to old PC</b> as usual. <b>Save…</b> (top of the Project card) keeps the project itself so
you can change it later; the app also remembers the last project when it closes.</p>
"""),
    ("bits", "Bits and speeds", """
<h1>Bits (the tool list)</h1>
<p>Click <b>⛏ Bits</b> at the top (or <b>Bits…</b> next to a step) to see the bits the app knows.
Add every bit you have: <b>＋ New bit</b>, or <b>Common sizes ▾</b> for the usual ones. Each bit
has a number (T1, T2…), a kind, a diameter and a cutting length.</p>
<h2>What each kind of bit does</h2>
<table>
<tr><td><b>▮ Flat end mill</b></td><td>everything. Cut-outs are moved out by the bit's radius (holes
in by the radius) so the part is the size you typed. Holes bigger than the bit are milled round.
Plunges need a centre-cutting end mill (most are).</td></tr>
<tr><td><b>◖ Ball end mill</b></td><td>like a flat end mill but with a round bottom; smaller
stepover so pocket floors aren't ridged.</td></tr>
<tr><td><b>▼ Drill</b></td><td>only goes straight down, in pecks, pulling out each time to clear
the chips. Holes must be the drill's size. Through holes go deep enough for the drill's point to
come out the bottom. A drill is refused for pockets, outlines, text and lines.</td></tr>
<tr><td><b>∨ V-bit</b></td><td>engraves on the line; the groove gets wider the deeper it goes. It can
also mark hole centres before drilling. It can't go deeper than its cone.</td></tr>
</table>
<h2>How the numbers are worked out</h2>
<ol>
<li>The best spindle speed for the bit's size and the material.</li>
<li>The feed that gives each tooth a proper chip. This mill's top speed is about 13.5 in/min
(Settings), so when that's too fast the app <b>slows the spindle</b> instead — a bit that spins
fast but moves slowly rubs, melts plastic and goes dull.</li>
<li>The nearest speed your spindle can be set to (Settings → Spindle speeds).</li>
<li>Depth per pass and stepover from the material and the bit's size, never more than the
bit's cutting length. Drilling is kept gentler (60% of top speed).</li>
</ol>
<p>The <b>Bits</b> window shows the result for each bit in each material. For a step you can tick
<b>Use my own speeds and feeds</b> and type your own numbers (0 = let the app decide).</p>
<p class="box">These are careful starting numbers for a small, light mill. Listen to the cut: a
squeal or melting plastic means the spindle is too fast or the feed too slow; chatter or a bent
bit means too deep or too fast.</p>
"""),
    ("running", "Running a job you made", """
<h1>Running a job made in the app</h1>
<p>The MicroMill has no tool changer, and MPS2003 can't re-zero Z partway through a job, so the
app makes <b>one job file per bit</b>, e.g. <code>Name plate T5.tap</code> (NAMEPLT5.TAP on the
old PC). Run them in the order shown in the Make tab:</p>
<ol>
<li>Clamp the stock. Zero X and Y where the project says (lower-left corner or centre) and
Z on the <b>top</b> of the stock (MPS2003 option 4).</li>
<li>Load the first file, press <b>P</b> (Plot Preview) and check it.</li>
<li>Run it. It starts with a pause (M0): put in the bit it names, set the spindle to the speed
it names, switch the spindle on, then press <b>C</b>. Stay at the machine.</li>
<li>When it finishes: spindle off, change to the next bit, <b>zero Z again</b> on the top of the
stock (don't touch X and Y), load the next file, and repeat.</li>
</ol>
<p>Cut-outs that go all the way through leave small <b>holding tabs</b> so the part doesn't
break loose and get thrown. Snip or file them off afterwards. Put a scrap board under the stock
for anything that goes through.</p>
<p class="muted">The files use only the plain G-code in MPS2003's manual: G00/G01 moves, inches
(G20), absolute (G90), M00 pauses, M02 at the end. No spindle codes (M03) or cutter
compensation (G41) — the app does the offsets itself.</p>
"""),
    ("checks", "What the checks mean", """
<h2>Checks</h2>
<p><span class="ok">✓</span> fine &nbsp; <span class="warn">⚠</span> look at this before cutting
&nbsp; <span style="color:#2563eb">ℹ</span> good to know</p>
<table>
<tr><td><b>Commands MPS2003's manual doesn't list</b></td><td>e.g. M03 (spindle on), G41 (cutter
comp). The machine's own sample jobs use some of these, and MPS2003 most likely skips them —
but check in Plot Preview first. The spindle on the MicroMill is switched by hand.</td></tr>
<tr><td><b>Deepest cut</b></td><td>warns if the job goes deeper than your limit (Settings, default 0.5 in).</td></tr>
<tr><td><b>Work area</b></td><td>only if you enter the table size in Settings.</td></tr>
<tr><td><b>Feed before any F</b></td><td>a cutting move with no feed rate set yet: MPS2003 uses the last one it had.</td></tr>
<tr><td><b>Faster than the machine</b></td><td>the MicroMill tops out around 13.5 in/min; faster feeds just run slower.</td></tr>
<tr><td><b>Millimetres</b></td><td>the machine is set to inches; an mm job will come out 25.4× too big unless MPS2003 is switched (U).</td></tr>
<tr><td><b>Not a DOS name</b></td><td>the old PC only uses 8-letter names; Send gives it one.</td></tr>
</table>
"""),
    ("send", "Sending a job to the old PC", """
<h2>Send to old PC</h2>
<ol>
<li>Pick the job and click <b>Send to old PC ➜</b>.</li>
<li>Choose its name on the old PC: up to 8 letters/numbers, then <code>.TAP</code>
(for example <code>GEAR2.TAP</code>). The app warns if the old PC already has a file with that name
(from the last backup) — fetching would <b>replace</b> it.</li>
<li>The job is copied into <code>To Old PC</code> with DOS line endings. It shows on the
<b>Machine Link</b> tab under <b>Waiting for the old PC</b>.</li>
<li>Make sure the link is <b>on</b> (green), then on the old PC, in an MS-DOS Prompt:
<table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>C:\\NETUP\\GET GEAR2.TAP</code></td></tr></table>
It says <b>Done</b> and the job is in <code>C:\\MPSPRO</code>.</li>
</ol>
<h2 id="getbat">First time: get GET.BAT</h2>
<p>The old PC needs the small <code>GET.BAT</code> helper once. With the link on, on the old PC
in an MS-DOS Prompt type, pressing Enter after each line:</p>
<table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>ftp 192.168.50.1</code></td></tr></table>
<p>User: <code>anonymous</code> &nbsp; Password: <code>x</code>, then:</p>
<table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>lcd C:\\NETUP</code></td></tr></table>
<table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>get GET.BAT</code></td></tr></table>
<table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>quit</code></td></tr></table>
<p>From then on it's always just <code>C:\\NETUP\\GET NAME.TAP</code>. (The same six lines with
<code>lcd C:\\MPSPRO</code> and <code>get NAME.TAP</code> also fetch a job without GET.BAT.)</p>
<h2>Save copy to USB…</h2>
<p>Saves the job with DOS line endings anywhere you pick, for carrying over by hand.</p>
"""),
    ("backup", "Backing up the old PC", """
<h2>Back up C:\\MPSPRO</h2>
<ol>
<li>Link <b>on</b> (Machine Link tab).</li>
<li>On the old PC, in an MS-DOS Prompt: <table class="cmdt" cellpadding="6" cellspacing="0" bgcolor="#eef2f7"><tr><td><code>C:\\NETUP\\SEND</code></td></tr></table></li>
<li>The app shows each file arriving and a progress bar, then checks every file against the old
PC's list of sizes. <b>CHECK PASSED</b> means everything arrived; the backup is also zipped.</li>
</ol>
<p>Backups are in <code>Documents\\A-Tech CNC\\Received</code>, one folder per backup, with a
<code>.zip</code> next to it. <b>Add its jobs to library</b> copies the backup's .TAP jobs into the
job library so you can preview them.</p>
<p class="muted">The last full backup (Oct 14, 2026) had 20 files, 832,754 bytes. Keep a copy of
the zip somewhere else too.</p>
"""),
    ("network", "First-time network setup", """
<h2>The cable</h2>
<p>Plug a network cable straight from the laptop's Ethernet port (or USB network adapter) into
the old PC. No router is needed.</p>
<table>
<tr><td><b>Laptop</b></td><td><code>192.168.50.1</code></td></tr>
<tr><td><b>Old PC</b></td><td><code>192.168.50.2</code> (already set up on Oct 14, 2026)</td></tr>
</table>
<h2>Set up network… (one time)</h2>
<p>On the <b>Machine Link</b> tab, click <b>Set up network…</b>. Windows asks for administrator
rights; a blue window then gives the cable port the address <code>192.168.50.1</code> and adds two
firewall rules that only allow FTP and ping from <code>192.168.50.x</code>. If the laptop already
has the address it says so and only adds the rules. <b>Undo network setup</b> puts it all back.</p>
<p>The first time the link is turned on, Windows may also ask whether to allow the app on the
network — click <b>Allow</b>.</p>
<h2>The three lights</h2>
<table>
<tr><td><b>Laptop address</b></td><td>green when 192.168.50.1 is set on this laptop.</td></tr>
<tr><td><b>Old PC</b></td><td>green when the old PC answers ping (it must be on, in Windows, cable in).</td></tr>
<tr><td><b>Link</b></td><td>green when the app is listening. It turns on by itself when the app opens.</td></tr>
</table>
"""),
    ("trouble", "Troubleshooting", """
<h2>Troubleshooting</h2>
<table>
<tr><td><b>Laptop address is red</b></td><td>Plug in the cable (or USB adapter) and click <b>Set up network…</b>.</td></tr>
<tr><td><b>Old PC not answering</b></td><td>Is it on and in Windows (not MS-DOS mode)? Cable plugged in at both ends?
At start-up the old PC asks "Load the network driver?" — it must load (don't press N).
On the old PC, <code>C:\\NETUP\\CHECK</code> shows the network status.</td></tr>
<tr><td><b>Link could not start</b></td><td>Another program is using port 21 — usually an old
<code>receive_files.bat</code> window. Close it, then <b>Turn link on</b>.</td></tr>
<tr><td><b>GET says NOT RECEIVED</b></td><td>Check the name matches exactly what's under <b>Waiting
for the old PC</b>, and that the link is on.</td></tr>
<tr><td><b>CHECK FAILED</b></td><td>Some files didn't arrive or arrived short. Run
<code>C:\\NETUP\\SEND</code> again.</td></tr>
<tr><td><b>Old PC won't start</b></td><td>At "Load the network driver?" press <b>N</b>.
To remove the driver: <code>del C:\\AUTOEXEC.BAT</code> then <code>del C:\\NETUP\\INSTALL.TAG</code> (the
file was empty before) and restart.</td></tr>
</table>
"""),
    ("about", "Folders and settings", """
<h2>Folders</h2>
<table>
<tr><td><code>Documents\\A-Tech CNC\\Jobs</code></td><td>the job library</td></tr>
<tr><td><code>Documents\\A-Tech CNC\\To Old PC</code></td><td>jobs the old PC can fetch (GET)</td></tr>
<tr><td><code>Documents\\A-Tech CNC\\Received</code></td><td>backups from the old PC (SEND)</td></tr>
<tr><td><code>Documents\\A-Tech CNC\\Projects</code></td><td>projects saved from the Make tab</td></tr>
<tr><td><code>Documents\\A-Tech CNC\\tools.json</code></td><td>the bit list</td></tr>
</table>
<h2>Settings (⚙ at the top)</h2>
<table>
<tr><td><b>Machine top speed</b></td><td>13.5 in/min, from the old PC's PARAM3.DAT (600 + 800 × 1.5 steps/s at 8000 steps/in).</td></tr>
<tr><td><b>Deepest cut warning</b></td><td>default 0.5 in.</td></tr>
<tr><td><b>Work area</b></td><td>table travel X × Y; 0 = don't check.</td></tr>
<tr><td><b>Spindle speeds</b></td><td>the speeds your spindle can be set to (typical Taig belt
steps to start with — change them to the ones on your mill). One number = one-speed spindle.</td></tr>
<tr><td><b>Safe height</b></td><td>how high above the top the bit travels between cuts (0.1 in).</td></tr>
<tr><td><b>Holding tab thickness</b></td><td>0.03 in.</td></tr>
<tr><td><b>Climb milling</b></td><td>off = conventional milling, kinder to an older mill with some play in it.</td></tr>
<tr><td><b>Addresses / port</b></td><td>only change if the old PC was set up differently.</td></tr>
</table>
<p class="muted">MPS2003 reads <code>C:\\MPSPRO\\PARAM3.DAT</code>. Never send .EXE, .DAT or .BAT files
to C:\\MPSPRO — the Send dialog blocks those names.</p>
"""),
]


class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        nav = Card("Help")
        self.nav = QListWidget()
        for _, title, _ in SECTIONS:
            self.nav.addItem(title)
        nav.body.addWidget(self.nav)
        nav.setFixedWidth(250)
        body = Card("")
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(True)
        self.text.setStyleSheet("QTextBrowser { border: none; padding: 6px 10px; }")
        self.text.document().setDefaultStyleSheet(_CSS)
        body.body.addWidget(self.text)
        lay.addWidget(nav)
        lay.addWidget(body, 1)
        self.nav.currentRowChanged.connect(self.show_section)
        self.nav.setCurrentRow(0)

    def show_section(self, i: int) -> None:
        if 0 <= i < len(SECTIONS):
            self.text.setHtml(SECTIONS[i][2])

    def show_key(self, key: str) -> None:
        for i, (k, _, _) in enumerate(SECTIONS):
            if k == key:
                self.nav.setCurrentRow(i)
