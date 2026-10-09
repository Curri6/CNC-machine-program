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

try {
    Write-Host '=== Win95 disc burner (ISO 9660 + Joliet) ===' -ForegroundColor Cyan
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

    Write-Host "Disc:    $mediaName"
    Write-Host "Status:  $($flags -join ', ')"
    Write-Host "Free:    $freeMB MB"
    Write-Host ''

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

    # ---- 4. Confirm ---------------------------------------------------------
    Write-Host ''
    Write-Host "PLAN: $plan" -ForegroundColor Yellow
    $answer = Read-Host 'Type YES to go ahead (anything else cancels)'
    if ($answer -cne 'YES') { Write-Host 'Cancelled. Nothing was written.'; Pause-Exit 0 }

    # ---- 5. Stage files into WIN95NET\WIN95 and WIN95NET\INTEL --------------
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
        Write-Progress -Activity 'Step 1 of 2: preparing files' -Status "$($i + 1) of $($jobs.Count)" `
            -PercentComplete ([int](100 * $i / [math]::Max(1, $jobs.Count)))
        $dest = $jobs[$i][1]
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        Copy-Item -LiteralPath $jobs[$i][0] -Destination $dest
    }
    Write-Progress -Activity 'Step 1 of 2: preparing files' -Completed

    # Release the COM objects used for checking; the burn makes its own.
    foreach ($o in @($format, $recorder, $master)) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($o) }

    # ---- 6. Burn (in a background STA runspace so we can show progress) ----
    $burn = {
        param($recorderId, $stage, $mode)
        $ErrorActionPreference = 'Stop'
        $recorder = New-Object -ComObject IMAPI2.MsftDiscRecorder2
        $recorder.InitializeDiscRecorder($recorderId)

        if ($mode -eq 'erase') {
            $erase = New-Object -ComObject IMAPI2.MsftDiscFormat2Erase
            $erase.Recorder = $recorder
            $erase.ClientName = 'CNC Win95 disc'
            $erase.FullErase = $false
            $erase.EraseMedia()
        }

        $format = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
        $format.Recorder = $recorder
        $format.ClientName = 'CNC Win95 disc'
        $format.ForceMediaToBeClosed = $true
        if ($mode -eq 'overwrite') { $format.ForceOverwrite = $true }

        $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
        $fsi.ChooseImageDefaults($recorder)
        if ($mode -eq 'append') {
            # Start the new session right after the old one, without importing
            # the old (UDF) file list. Per Microsoft's IMAPI2 docs, when the
            # previous session is not imported the session start block must be
            # set by hand; otherwise the image is built as if it started at
            # block 0 and the new session is unreadable.
            $fsi.SessionStartBlock = $format.NextWritableAddress
            $fsi.FreeMediaBlocks = $format.FreeSectorsOnMedia
        }
        $fsi.FileSystemsToCreate = 3   # 1 = ISO 9660, 2 = Joliet. No UDF.
        $fsi.VolumeName = 'WIN95NET'
        $fsi.Root.AddTree($stage, $false)

        $image = $fsi.CreateResultImage()
        $format.Write($image.ImageStream)
        $recorder.EjectMedia()
        'OK'
    }

    $est = [math]::Max(90, [int]($sizeMB / 2.5) + 60)   # rough guess, seconds
    if ($mode -eq 'erase') { $est += 120 }

    $rs = [runspacefactory]::CreateRunspace()
    $rs.ApartmentState = 'STA'
    $rs.Open()
    $ps = [PowerShell]::Create()
    $ps.Runspace = $rs
    [void]$ps.AddScript($burn).AddArgument($recorderId).AddArgument($stage).AddArgument($mode)
    $handle = $ps.BeginInvoke()
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while (-not $handle.IsCompleted) {
        $pct = [math]::Min(99, [int](100 * $sw.Elapsed.TotalSeconds / $est))
        Write-Progress -Activity 'Step 2 of 2: burning disc - do NOT eject' `
            -Status "about $pct% (estimated) - $([int]$sw.Elapsed.TotalSeconds)s elapsed" -PercentComplete $pct
        Start-Sleep -Milliseconds 500
    }
    Write-Progress -Activity 'Step 2 of 2: burning disc - do NOT eject' -Completed

    $result = $null
    try { $result = $ps.EndInvoke($handle) }
    catch { if ($_.Exception.InnerException) { throw $_.Exception.InnerException } else { throw } }
    finally { $ps.Dispose(); $rs.Close() }

    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue

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
