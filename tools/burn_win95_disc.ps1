<#
burn_win95_disc.ps1

Burns the WIN95 (.CAB files) and INTEL (driver) folders onto a disc the
old Windows 95 PC can read: plain ISO 9660 + Joliet, no UDF, and the disc
is closed (finalized) at the end. Windows 11's normal "Burn to disc" uses
UDF for DVDs, which Windows 95 can't see.

Uses only what's built into Windows (IMAPI2). Nothing to install.

Safe by default: it first only LOOKS at the disc and tells you what it
found. Nothing is written unless you type YES.

Start it with burn_win95_disc.bat (double-click), which sits next to this
file.
#>

$ErrorActionPreference = 'Stop'

function Pause-Exit([int]$code) {
    Write-Host ''
    Read-Host 'Press Enter to close'
    # Always 0 so the .bat launcher only adds its own pause if PowerShell
    # itself couldn't start the script.
    exit 0
}

$MediaNames = @{
    0 = 'Unknown'; 1 = 'CD-ROM (pressed, not writable)'; 2 = 'CD-R'; 3 = 'CD-RW'
    4 = 'DVD-ROM (pressed, not writable)'; 5 = 'DVD-RAM'; 6 = 'DVD+R'; 7 = 'DVD+RW'
    8 = 'DVD+R DL'; 9 = 'DVD-R'; 10 = 'DVD-RW'; 11 = 'DVD-R DL'; 12 = 'Disk'
    13 = 'DVD+RW DL'
}
$Rewritable = @(3, 5, 7, 10, 13)

# IMAPI_FORMAT2_DATA_MEDIA_STATE flags
$ST_OVERWRITE_ONLY = 0x1
$ST_BLANK          = 0x2
$ST_APPENDABLE     = 0x4
$ST_FINAL_SESSION  = 0x8
$ST_DAMAGED        = 0x400
$ST_ERASE_REQUIRED = 0x800
$ST_WRITE_PROTECT  = 0x2000
$ST_FINALIZED      = 0x4000
$ST_UNSUPPORTED    = 0x8000

# Safety check: reads back the finished disc image BEFORE it is burned and
# refuses to burn unless Windows 95 will be able to read it. Tested against
# good and deliberately broken images (see JOURNAL.md, 2026-10-09).
$CheckSource = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

// Reads back the disc image IMAPI2 built, before it is burned, and checks
// that Windows 95 will be able to read it: an ISO 9660 primary volume
// descriptor, a root directory holding WIN95 (with .CAB files) and INTEL
// (with an .INF), and every directory/file address inside this session.
// Written in C# 5 so Windows PowerShell 5.1's Add-Type can compile it.
public static class Win95DiscCheck
{
    const int S = 2048;

    class Entry
    {
        public string Name;
        public bool IsDir;
        public uint Lba;
        public uint Len;
    }

    class Reader
    {
        IStream st;
        MemoryStream buf = new MemoryStream();
        IntPtr pRead;
        public Reader(IStream st) { this.st = st; pRead = Marshal.AllocHGlobal(4); }
        public void Close() { Marshal.FreeHGlobal(pRead); }

        // Reads forward only (no Seek), so it works on any stream.
        public byte[] Sector(long rel)
        {
            if (rel < 0) throw new Exception("Address points before the start of this session (sector " + rel + ").");
            if (rel > 200000) throw new Exception("Address is unreasonably far into the image (sector " + rel + ").");
            long need = (rel + 1) * S;
            byte[] chunk = new byte[65536];
            while (buf.Length < need)
            {
                Marshal.WriteInt32(pRead, 0);
                st.Read(chunk, chunk.Length, pRead);
                int n = Marshal.ReadInt32(pRead);
                if (n <= 0) throw new Exception("Image ends before sector " + rel + ".");
                buf.Write(chunk, 0, n);
            }
            byte[] s = new byte[S];
            Array.Copy(buf.GetBuffer(), rel * S, s, 0, S);
            return s;
        }
    }

    static uint U32(byte[] b, int o) { return (uint)(b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)); }

    static List<Entry> ReadDir(Reader r, long start, uint vol, uint lba, uint len, bool joliet)
    {
        CheckRange(start, vol, lba, "directory");
        List<Entry> list = new List<Entry>();
        uint sectors = (len + S - 1) / S;
        for (uint i = 0; i < sectors; i++)
        {
            byte[] sec = r.Sector(lba + i - start);
            int p = 0;
            while (p < S)
            {
                int rl = sec[p];
                if (rl == 0) break;
                if (p + rl > S || rl < 34) throw new Exception("Damaged directory record.");
                int nl = sec[p + 32];
                Entry e = new Entry();
                e.Lba = U32(sec, p + 2);
                e.Len = U32(sec, p + 10);
                e.IsDir = (sec[p + 25] & 2) != 0;
                if (nl == 1 && (sec[p + 33] == 0 || sec[p + 33] == 1)) { p += rl; continue; }
                string name = joliet ? Encoding.BigEndianUnicode.GetString(sec, p + 33, nl)
                                     : Encoding.ASCII.GetString(sec, p + 33, nl);
                int semi = name.IndexOf(';');
                if (semi >= 0) name = name.Substring(0, semi);
                if (name.EndsWith(".")) name = name.Substring(0, name.Length - 1);
                e.Name = name;
                list.Add(e);
                p += rl;
            }
        }
        return list;
    }

    static void CheckRange(long start, uint vol, uint lba, string what)
    {
        if (lba < start || lba >= vol)
            throw new Exception("A " + what + " address (" + lba + ") is outside this session (" + start + " to " + vol +
                                "). The new section would be unreadable. Nothing was burned.");
    }

    static Entry Find(List<Entry> list, string name, bool dir)
    {
        foreach (Entry e in list)
            if (e.IsDir == dir && string.Equals(e.Name, name, StringComparison.OrdinalIgnoreCase)) return e;
        return null;
    }

    static int CountFiles(Reader r, long start, uint vol, Entry dir, bool joliet, string ext, int depth)
    {
        int n = 0;
        foreach (Entry e in ReadDir(r, start, vol, dir.Lba, dir.Len, joliet))
        {
            if (e.IsDir) { if (depth < 6) n += CountFiles(r, start, vol, e, joliet, ext, depth + 1); continue; }
            if (e.Len > 0) CheckRange(start, vol, e.Lba, "file");
            if (e.Name.EndsWith(ext, StringComparison.OrdinalIgnoreCase)) n++;
        }
        return n;
    }

    static string CheckTree(Reader r, long start, uint vol, byte[] vd, bool joliet)
    {
        uint rootLba = U32(vd, 158);
        uint rootLen = U32(vd, 166);
        List<Entry> root = ReadDir(r, start, vol, rootLba, rootLen, joliet);
        string which = joliet ? "Joliet" : "ISO 9660";
        Entry win95 = Find(root, "WIN95", true);
        Entry intel = Find(root, "INTEL", true);
        if (win95 == null) throw new Exception(which + " listing has no WIN95 folder. Nothing was burned.");
        if (intel == null) throw new Exception(which + " listing has no INTEL folder. Nothing was burned.");
        int cabs = CountFiles(r, start, vol, win95, joliet, ".CAB", 0);
        int infs = CountFiles(r, start, vol, intel, joliet, ".INF", 0);
        if (cabs == 0) throw new Exception(which + " listing: WIN95 has no .CAB files. Nothing was burned.");
        if (infs == 0) throw new Exception(which + " listing: INTEL has no .INF file. Nothing was burned.");
        return which + ": WIN95 " + cabs + " CAB, INTEL " + infs + " INF";
    }

    public static string Verify(object comStream, long expectedStart)
    {
        Reader r = new Reader((IStream)comStream);
        try
        {
            byte[] pvd = r.Sector(16);
            if (pvd[0] != 1 || Encoding.ASCII.GetString(pvd, 1, 5) != "CD001")
                throw new Exception("No ISO 9660 volume descriptor. Windows 95 could not read this. Nothing was burned.");
            uint vol = U32(pvd, 80);
            // Tools differ on whether a later session's volume size counts
            // from the start of the disc or from the start of the session.
            if (vol <= expectedStart) vol = (uint)(expectedStart + vol);
            List<string> parts = new List<string>();
            parts.Add("start block " + expectedStart);
            parts.Add(CheckTree(r, expectedStart, vol, pvd, false));

            bool joliet = false, udf = false;
            for (int i = 17; i < 64; i++)
            {
                byte[] d = r.Sector(i);
                if (Encoding.ASCII.GetString(d, 1, 5) != "CD001")
                    throw new Exception("Volume descriptor list is damaged. Nothing was burned.");
                if (d[0] == 255)
                {
                    // A UDF recognition sequence, if any, follows the terminator.
                    for (int j = i + 1; j < i + 4; j++)
                    {
                        string id = Encoding.ASCII.GetString(r.Sector(j), 1, 5);
                        if (id == "BEA01" || id == "NSR02" || id == "NSR03") udf = true;
                    }
                    break;
                }
                if (d[0] == 2 && d[88] == 0x25 && d[89] == 0x2F && (d[90] == 0x40 || d[90] == 0x43 || d[90] == 0x45))
                {
                    joliet = true;
                    parts.Add(CheckTree(r, expectedStart, vol, d, true));
                }
            }
            parts.Add(joliet ? "Joliet: yes" : "Joliet: no (short 8.3 names only)");
            parts.Add(udf ? "UDF: also present" : "UDF: none");
            return string.Join(" | ", parts.ToArray());
        }
        finally { r.Close(); }
    }

    public static bool TryRewind(object comStream)
    {
        try { ((IStream)comStream).Seek(0, 0, IntPtr.Zero); return true; }
        catch { return false; }
    }
}
'@

try {
    Write-Host '=== Win95 disc burner (ISO 9660 + Joliet) ===' -ForegroundColor Cyan
    try { Add-Type -TypeDefinition $CheckSource -ErrorAction Stop }
    catch {
        Write-Host 'Could not load the safety check, so nothing will be burned.' -ForegroundColor Red
        Write-Host $_.Exception.Message
        Write-Host 'Take a screenshot of this window and send it to Claude.'
        Pause-Exit 1
    }
    Write-Host 'Close any File Explorer windows showing the disc drive first.'
    Write-Host ''

    # ---- 1. Find the burner -------------------------------------------------
    $master = New-Object -ComObject IMAPI2.MsftDiscMaster2
    if ($master.Count -lt 1) { Write-Host 'No disc burner found.' -ForegroundColor Red; Pause-Exit 1 }

    $recorderId = $null
    $recorderLabel = $null
    for ($i = 0; $i -lt $master.Count; $i++) {
        $r = New-Object -ComObject IMAPI2.MsftDiscRecorder2
        $r.InitializeDiscRecorder($master.Item($i))
        $label = "$($r.VolumePathNames -join ',') $($r.VendorId.Trim()) $($r.ProductId.Trim())"
        if (-not $recorderId) { $recorderId = $master.Item($i); $recorderLabel = $label }
    }
    Write-Host "Burner:  $recorderLabel"

    $recorder = New-Object -ComObject IMAPI2.MsftDiscRecorder2
    $recorder.InitializeDiscRecorder($recorderId)
    $format = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
    $format.Recorder = $recorder
    $format.ClientName = 'CNC Win95 disc'

    # ---- 2. Look at the disc ------------------------------------------------
    if (-not $format.IsCurrentMediaSupported($recorder)) {
        Write-Host 'No writable disc in the drive (or this disc type cannot be written).' -ForegroundColor Red
        Pause-Exit 1
    }
    $mediaType = [int]$format.CurrentPhysicalMediaType
    $status = [int]$format.CurrentMediaStatus
    $mediaName = $MediaNames[$mediaType]; if (-not $mediaName) { $mediaName = "type $mediaType" }
    $freeMB = [math]::Round(($format.FreeSectorsOnMedia * 2048) / 1MB)

    $flags = @()
    if ($status -band $ST_BLANK)          { $flags += 'blank' }
    if ($status -band $ST_APPENDABLE)     { $flags += 'open (more can be added)' }
    if ($status -band $ST_FINALIZED)      { $flags += 'closed/finalized' }
    if ($status -band $ST_OVERWRITE_ONLY) { $flags += 'overwritable' }
    if ($status -band $ST_ERASE_REQUIRED) { $flags += 'needs erasing first' }
    if ($status -band $ST_DAMAGED)        { $flags += 'DAMAGED' }
    if ($status -band $ST_WRITE_PROTECT)  { $flags += 'write-protected' }
    if ($status -band $ST_UNSUPPORTED)    { $flags += 'unsupported' }

    if ($flags.Count -eq 0) { $flags += 'unknown' }
    Write-Host "Disc:    $mediaName"
    Write-Host ("Status:  {0}   (code 0x{1:X})" -f ($flags -join ', '), $status)
    Write-Host "Free:    $freeMB MB"
    Write-Host ''

    if (($status -band 0xF) -eq 0 -and -not ($status -band ($ST_FINALIZED -bor $ST_DAMAGED -bor $ST_ERASE_REQUIRED))) {
        Write-Host 'The drive did not report a clear disc state (it may still be busy).' -ForegroundColor Yellow
        Write-Host 'Eject the disc, put it back in, wait until the drive light stops, then try again.'
        Write-Host 'Nothing was written.'
        Pause-Exit 1
    }

    if ($status -band ($ST_DAMAGED -bor $ST_WRITE_PROTECT -bor $ST_UNSUPPORTED)) {
        Write-Host 'This disc cannot be written.' -ForegroundColor Red
        Pause-Exit 1
    }

    $isRW = $Rewritable -contains $mediaType
    $mode = $null
    if ($status -band $ST_BLANK) {
        $mode = 'blank'
        $plan = 'Burn WIN95 + INTEL onto this blank disc and close it.'
    } elseif ($status -band $ST_OVERWRITE_ONLY) {
        $mode = 'overwrite'
        $plan = 'OVERWRITE everything on this rewritable disc with WIN95 + INTEL and close it.'
    } elseif ($isRW) {
        $mode = 'erase'
        $plan = 'ERASE this rewritable disc, then burn WIN95 + INTEL onto it and close it.'
    } elseif ($status -band $ST_APPENDABLE) {
        $mode = 'append'
        $plan = 'ADD a new Win95-readable section with WIN95 + INTEL to this disc and close it. ' +
                '(What is already on the disc stays physically there but will no longer be listed.) ' +
                'Note: some old drives only read the first section of a DVD, so this may still not show up on the old PC.'
    } else {
        Write-Host 'This disc is closed and write-once. Nothing more can be added to it.' -ForegroundColor Yellow
        Write-Host 'It is not damaged, it just cannot take more files.'
        Pause-Exit 1
    }

    # ---- 3. Pick the folders ------------------------------------------------
    Add-Type -AssemblyName System.Windows.Forms
    function Pick-Folder([string]$prompt) {
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = $prompt
        $dlg.ShowNewFolderButton = $false
        if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return $null }
        return $dlg.SelectedPath
    }

    Write-Host 'Pick the WIN95 folder (the one with the .CAB files)...'
    $win95 = Pick-Folder 'Pick the WIN95 folder (the one full of .CAB files)'
    if (-not $win95) { Write-Host 'Cancelled. Nothing was written.'; Pause-Exit 0 }
    $cabs = @(Get-ChildItem -LiteralPath $win95 -Filter *.cab -File)
    if ($cabs.Count -eq 0) {
        Write-Host "No .CAB files directly inside $win95 - wrong folder? Nothing was written." -ForegroundColor Red
        Pause-Exit 1
    }
    Write-Host "  $win95 ($($cabs.Count) .CAB files)"

    Write-Host 'Pick the INTEL driver folder (the one with the .INF file)...'
    $intel = Pick-Folder 'Pick the Intel PRO/100 VE Windows 95 driver folder (contains a .INF file)'
    if (-not $intel) { Write-Host 'Cancelled. Nothing was written.'; Pause-Exit 0 }
    $infs = @(Get-ChildItem -LiteralPath $intel -Filter *.inf -File -Recurse)
    if ($infs.Count -eq 0) {
        Write-Host "No .INF file inside $intel - wrong folder? Nothing was written." -ForegroundColor Red
        Pause-Exit 1
    }
    Write-Host "  $intel ($($infs.Count) .INF file(s))"

    $sizeMB = [math]::Round(((Get-ChildItem -LiteralPath $win95, $intel -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
    Write-Host "Total:   $sizeMB MB"
    if ($sizeMB -ge $freeMB) {
        Write-Host 'That does not fit on this disc. Nothing was written.' -ForegroundColor Red
        Pause-Exit 1
    }

    # ---- 4. Stage files into WIN95NET\WIN95 and WIN95NET\INTEL --------------
    $stage = Join-Path $env:TEMP 'WIN95NET_stage'
    if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
    New-Item -ItemType Directory -Path (Join-Path $stage 'WIN95') | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $stage 'INTEL') | Out-Null

    $jobs = @()
    foreach ($pair in @(@($win95, 'WIN95'), @($intel, 'INTEL'))) {
        $base = (Resolve-Path -LiteralPath $pair[0]).Path.TrimEnd('\')
        foreach ($f in Get-ChildItem -LiteralPath $base -Recurse -File) {
            $jobs += , @($f.FullName, (Join-Path (Join-Path $stage $pair[1]) $f.FullName.Substring($base.Length + 1)))
        }
    }
    for ($i = 0; $i -lt $jobs.Count; $i++) {
        Write-Progress -Activity 'Step 1 of 3: preparing files' -Status "$($i + 1) of $($jobs.Count)" `
            -PercentComplete ([int](100 * $i / [math]::Max(1, $jobs.Count)))
        $dest = $jobs[$i][1]
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        Copy-Item -LiteralPath $jobs[$i][0] -Destination $dest
    }
    Write-Progress -Activity 'Step 1 of 3: preparing files' -Completed

    # Release the COM objects used for looking; the runspace makes its own.
    foreach ($o in @($format, $recorder, $master)) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($o) }

    # All disc work happens in one background STA runspace (so a progress bar
    # can run here). Its objects are kept in $global: between the two phases.
    $rs = [runspacefactory]::CreateRunspace()
    $rs.ApartmentState = 'STA'
    # Both phases MUST run on the same thread. COM objects made in an STA
    # thread die when that thread ends, and by default each invocation gets
    # a new thread ("COM object that has been separated from its underlying
    # RCW cannot be used" - first real run, 2026-10-10).
    $rs.ThreadOptions = 'ReuseThread'
    $rs.Open()
    $ps = [PowerShell]::Create()
    $ps.Runspace = $rs

    function Run-Phase([string]$script, [object[]]$argList, [string]$activity, [int]$est) {
        $ps.Commands.Clear()
        [void]$ps.AddScript($script)
        foreach ($a in $argList) { [void]$ps.AddArgument($a) }
        $h = $ps.BeginInvoke()
        $sw = [Diagnostics.Stopwatch]::StartNew()
        while (-not $h.IsCompleted) {
            $pct = [math]::Min(99, [int](100 * $sw.Elapsed.TotalSeconds / $est))
            Write-Progress -Activity $activity `
                -Status "about $pct% (estimated) - $([int]$sw.Elapsed.TotalSeconds)s elapsed" -PercentComplete $pct
            Start-Sleep -Milliseconds 500
        }
        Write-Progress -Activity $activity -Completed
        try { return $ps.EndInvoke($h) }
        catch { if ($_.Exception.InnerException) { throw $_.Exception.InnerException } else { throw } }
    }

    function Get-DiscReport {
        try {
            $m = New-Object -ComObject IMAPI2.MsftDiscMaster2
            $r = New-Object -ComObject IMAPI2.MsftDiscRecorder2
            $r.InitializeDiscRecorder($recorderId)
            $f = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
            $f.Recorder = $r
            $f.ClientName = 'CNC Win95 disc'
            $st = [int]$f.CurrentMediaStatus
            $fl = @()
            if ($st -band $ST_BLANK)          { $fl += 'blank' }
            if ($st -band $ST_APPENDABLE)     { $fl += 'open (more can be added)' }
            if ($st -band $ST_FINALIZED)      { $fl += 'closed/finalized' }
            if ($st -band $ST_DAMAGED)        { $fl += 'DAMAGED' }
            if ($st -band $ST_ERASE_REQUIRED) { $fl += 'needs erasing first' }
            if ($fl.Count -eq 0) { $fl += ('unknown (code 0x{0:X}) - drive may still be busy' -f $st) }
            $nwa = '?'; try { $nwa = $f.NextWritableAddress } catch { }
            $free = [math]::Round(($f.FreeSectorsOnMedia * 2048) / 1MB)
            foreach ($o in @($f, $r, $m)) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($o) }
            return "Status: $($fl -join ', ') | Free: $free MB | next write block: $nwa"
        } catch { return "Could not re-read the disc: $($_.Exception.Message)" }
    }

    function Stop-All {
        try { $ps.Dispose(); $rs.Close() } catch { }
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    }

    # ---- 5. Build the disc image and CHECK it (nothing is written yet) -------
    $phaseA = {
        param($recorderId, $stage, $mode, $mediaType)
        $ErrorActionPreference = 'Stop'
        $global:recorder = New-Object -ComObject IMAPI2.MsftDiscRecorder2
        $global:recorder.InitializeDiscRecorder($recorderId)
        $global:format = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
        $global:format.Recorder = $global:recorder
        $global:format.ClientName = 'CNC Win95 disc'
        $global:format.ForceMediaToBeClosed = $true
        if ($mode -eq 'overwrite') { $global:format.ForceOverwrite = $true }

        $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
        if ($mode -eq 'erase') {
            # The disc will be blank after erasing; size the image for that.
            $fsi.ChooseImageDefaultsForMediaType($mediaType)
        } else {
            $fsi.ChooseImageDefaults($global:recorder)
        }
        $start = 0
        if ($mode -eq 'append') {
            # Start the new session right after the old one, without importing
            # the old (UDF) file list. Per Microsoft's IMAPI2 docs, when the
            # previous session is not imported the session start block must be
            # set by hand; otherwise the image is built as if it started at
            # block 0 and the new session is unreadable.
            $start = $global:format.NextWritableAddress
            $fsi.SessionStartBlock = $start
            $fsi.FreeMediaBlocks = $global:format.FreeSectorsOnMedia
        }
        $fsi.FileSystemsToCreate = 3   # 1 = ISO 9660, 2 = Joliet. No UDF.
        $fsi.VolumeName = 'WIN95NET'
        $fsi.Root.AddTree($stage, $false)
        if ($fsi.SessionStartBlock -ne $start) {
            throw "Image start ($($fsi.SessionStartBlock)) does not match the disc position ($start). Nothing was burned."
        }

        $image = $fsi.CreateResultImage()
        $global:stream = $image.ImageStream
        $summary = [Win95DiscCheck]::Verify($global:stream, [long]$start)
        if (-not [Win95DiscCheck]::TryRewind($global:stream)) {
            # Could not rewind the checked stream; build an identical fresh one.
            $global:stream = $fsi.CreateResultImage().ImageStream
        }
        $global:fsi = $fsi
        "$summary | image $([math]::Round($image.TotalBlocks * 2048 / 1MB, 1)) MB"
        # DVD 1x = 675 sectors/s, CD 1x = 75 sectors/s.
        $unit = 675; if ($mediaType -le 3) { $unit = 75 }
        $speeds = @()
        try { foreach ($v in $global:format.SupportedWriteSpeeds) { $speeds += [math]::Round($v / $unit, 1) } } catch { }
        $cur = '?'
        try { $cur = [math]::Round($global:format.CurrentWriteSpeed / $unit, 1) } catch { }
        "SPEED: current ${cur}x, drive supports for this disc: $(($speeds | Sort-Object) -join 'x, ')x"
        "@@SPEEDS $(($speeds | Sort-Object | ForEach-Object { $_.ToString([Globalization.CultureInfo]::InvariantCulture) }) -join ';')"
    }

    try {
        $check = Run-Phase $phaseA.ToString() @($recorderId, $stage, $mode, $mediaType) `
            'Step 2 of 3: building and checking the disc image (nothing written yet)' 30
    }
    catch { Stop-All; throw }
    Write-Host ''
    Write-Host 'CHECK PASSED - Windows 95 will be able to read this image:' -ForegroundColor Green
    $supported = @()
    foreach ($line in $check) {
        if ("$line".StartsWith('@@SPEEDS')) {
            foreach ($v in ("$line".Substring(8).Trim() -split ';')) {
                if ($v) { $supported += [double]::Parse($v, [Globalization.CultureInfo]::InvariantCulture) }
            }
            continue
        }
        Write-Host "  $line"
    }

    # ---- 6. Confirm -----------------------------------------------------------
    Write-Host ''
    Write-Host "PLAN: $plan" -ForegroundColor Yellow
    $answer = Read-Host 'Type YES to burn (anything else cancels)'
    if ($answer -cne 'YES') { Stop-All; Write-Host 'Cancelled. Nothing was written.'; Pause-Exit 0 }

    # Burn speed. 8x and 2x both failed on this drive + disc before
    # (2026-10-10), so the default is 4x when the drive offers it.
    $speedX = 0
    if ($supported.Count -gt 0) {
        $default = $supported[0]
        if ($supported -contains 4) { $default = 4 }
        $pick = Read-Host "Burn speed - choices: $(($supported) -join 'x, ')x. Press Enter for ${default}x"
        if (-not $pick) { $speedX = $default }
        else {
            $num = 0.0
            if ([double]::TryParse(($pick -replace '[xX ]', '' -replace ',', '.'), [Globalization.NumberStyles]::Float,
                    [Globalization.CultureInfo]::InvariantCulture, [ref]$num) -and ($supported -contains $num)) { $speedX = $num }
            else { Stop-All; Write-Host "'$pick' is not one of the choices. Cancelled. Nothing was written."; Pause-Exit 0 }
        }
        Write-Host "Burning at ${speedX}x."
    }

    # ---- 7. Burn ---------------------------------------------------------------
    $phaseB = {
        param($mode, $speedX, $unit)
        $ErrorActionPreference = 'Stop'
        if ($mode -eq 'erase') {
            $erase = New-Object -ComObject IMAPI2.MsftDiscFormat2Erase
            $erase.Recorder = $global:recorder
            $erase.ClientName = 'CNC Win95 disc'
            $erase.FullErase = $false
            $erase.EraseMedia()
            $global:format = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
            $global:format.Recorder = $global:recorder
            $global:format.ClientName = 'CNC Win95 disc'
            $global:format.ForceMediaToBeClosed = $true
        }
        if ($speedX -gt 0) { $global:format.SetWriteSpeed([int]($speedX * $unit), $false) }
        $global:format.Write($global:stream)
        $global:recorder.EjectMedia()
        'OK'
    }

    $est = [math]::Max(90, [int]($sizeMB / 2.5) + 60)   # rough guess, seconds
    if ($mode -eq 'erase') { $est += 120 }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $result = $null
    $unit = 675; if ($mediaType -le 3) { $unit = 75 }
    if ($speedX -gt 0) { $est = [math]::Max($est, [int]($sizeMB / ($speedX * $unit * 2048 / 1MB)) + 60) }
    try { $result = Run-Phase $phaseB.ToString() @($mode, $speedX, $unit) 'Step 3 of 3: burning disc - do NOT eject' $est }
    catch {
        $e = $_.Exception
        Stop-All
        Write-Host ''
        Write-Host 'The burn failed:' -ForegroundColor Red
        Write-Host "  $($e.Message)"
        Write-Host ("  Error code: 0x{0:X8}   after {1}s   at {2}x" -f $e.HResult, [int]$sw.Elapsed.TotalSeconds, $speedX)
        Write-Host ''
        Write-Host 'Disc state BEFORE this burn:' -ForegroundColor Yellow
        Write-Host "  Status: $($flags -join ', ') | Free: $freeMB MB"
        Write-Host 'Disc state NOW:' -ForegroundColor Yellow
        Write-Host "  $(Get-DiscReport)"
        Write-Host ''
        Write-Host 'Take a screenshot of this window and send it to Claude. Do not run it again yet.'
        Pause-Exit 1
    }
    Stop-All

    if ($result -contains 'OK') {
        Write-Host ''
        Write-Host "Done in $([int]$sw.Elapsed.TotalSeconds)s. The disc has been ejected." -ForegroundColor Green
        Write-Host 'Take it to the old PC and open the CD/DVD drive. You should see WIN95 and INTEL.'
        Pause-Exit 0
    }
    Write-Host 'The burn did not report success.' -ForegroundColor Red
    Pause-Exit 1
}
catch {
    Write-Host ''
    Write-Host 'Something went wrong:' -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ''
    Write-Host 'Take a screenshot of this window and send it to Claude.'
    Pause-Exit 1
}
