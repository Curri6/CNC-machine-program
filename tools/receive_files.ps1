# receive_files.ps1 - receive the C:\MPSPRO backup from the old Windows 95 PC.
#
# Runs a tiny FTP server on the laptop's network-cable port (192.168.50.1).
# The old PC runs C:\NETUP\SEND.BAT, which uploads every file plus a
# MANIFEST.TXT listing every file's size. This script checks every file
# against that list and zips the result.
#
# It also works the other way: put a job file (e.g. JOB1.TAP) in
# Downloads\CNC_backup\to_old_pc and the old PC can fetch it with Windows
# 95's own ftp ("get JOB1.TAP"). Only files in that folder can be fetched.
# Text job files (.TAP .NC .TXT .GCO .CNC) are sent with DOS (CRLF) line
# endings, which MPS2003 expects.
#
# It changes two settings only while it runs and puts them back when you
# press Q: the cable port's IP address (only if you type YES) and two
# temporary firewall rules (FTP port 21 and ping, only from 192.168.50.x).
#
# Start it with receive_files.bat (it asks for administrator rights).
# Works in Windows PowerShell 5.1 and PowerShell 7.

param(
    [switch]$TestMode,                 # for tools/tests: no network/firewall changes
    [string]$ListenIP = '',
    [int]$Port = 21,
    [string]$OutDir = '',
    [switch]$ExitAfterSession          # for tools/tests: stop after one FTP session
)

$ErrorActionPreference = 'Stop'
$LaptopIP = '192.168.50.1'
$OldPcIP  = '192.168.50.2'
$Latin1   = [System.Text.Encoding]::GetEncoding(28591)
$RuleName = 'CNC backup receiver (temporary)'
$StateFile = Join-Path ([System.IO.Path]::GetTempPath()) 'cnc_receiver_state.txt'

function Say([string]$msg, [string]$color = 'Gray') { Write-Host $msg -ForegroundColor $color }

# ---------------------------------------------------------------- settings
function Undo-Settings {
    # Puts back whatever an earlier run changed (also after a crash or a closed window).
    if (-not (Test-Path $StateFile)) { return }
    $lines = Get-Content $StateFile
    foreach ($l in $lines) {
        $kv = $l.Split('=', 2)
        if ($kv.Count -ne 2) { continue }
        switch ($kv[0]) {
            'dhcp'  { Say "Putting '$($kv[1])' back to automatic (DHCP) address..."
                      & netsh interface ipv4 set address $kv[1] dhcp | Out-Null }
            'added' { Say "Removing $LaptopIP from '$($kv[1])'..."
                      & netsh interface ipv4 delete address $kv[1] $LaptopIP | Out-Null }
            'rule'  { Get-NetFirewallRule -DisplayName $kv[1] -ErrorAction SilentlyContinue |
                          Remove-NetFirewallRule -ErrorAction SilentlyContinue }
        }
    }
    Remove-Item $StateFile -Force
    Say 'Network settings are back to how they were.' Green
}

function Add-State([string]$line) { Add-Content -Path $StateFile -Value $line }

function Set-Up-Network {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $admin = (New-Object Security.Principal.WindowsPrincipal $id).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) {
        Say 'This needs administrator rights. Start it with receive_files.bat.' Red
        exit 1
    }
    Undo-Settings

    $already = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
               Where-Object { $_.IPAddress -eq $LaptopIP }
    if ($already) {
        Say "This laptop already has $LaptopIP on '$($already[0].InterfaceAlias)'. Good." Green
    } else {
        $nics = @(Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
                  Where-Object { $_.PhysicalMediaType -match '802\.3' -or $_.MediaType -match '802\.3' } |
                  Where-Object { $_.PhysicalMediaType -notmatch 'Wireless|Native 802\.11' })
        if ($nics.Count -eq 0) {
            Say 'No network-cable (Ethernet) port found on this laptop.' Red
            Say 'If it uses a USB network adapter, plug it in and run this again.' Red
            exit 1
        }
        Say ''
        Say 'Network-cable ports on this laptop:'
        for ($i = 0; $i -lt $nics.Count; $i++) {
            Say ("  {0} = {1}  ({2}, {3})" -f ($i + 1), $nics[$i].Name, $nics[$i].InterfaceDescription, $nics[$i].Status)
        }
        $pick = 0
        if ($nics.Count -gt 1) {
            $ans = Read-Host 'Type the number of the port the cable is plugged into'
            if (-not [int]::TryParse($ans, [ref]$pick) -or $pick -lt 1 -or $pick -gt $nics.Count) {
                Say 'Not a valid number. Nothing was changed.' Red; exit 1
            }
            $pick--
        }
        $nic = $nics[$pick]
        if ($nic.Status -ne 'Up') {
            Say "'$($nic.Name)' shows no cable link yet ($($nic.Status)). That's OK if the old PC is off;" Yellow
            Say 'it should show Up once the old PC has started with its network driver.' Yellow
        }
        $dhcp = (Get-NetIPInterface -InterfaceIndex $nic.ifIndex -AddressFamily IPv4).Dhcp
        Say ''
        Say "To talk to the old PC, '$($nic.Name)' needs the address $LaptopIP."
        Say 'This script sets it now and puts it back when you press Q at the end.'
        $yes = Read-Host 'Type YES to set it'
        if ($yes -ne 'YES') { Say 'Nothing was changed.'; exit 1 }
        if ("$dhcp" -eq 'Enabled') {
            Add-State "dhcp=$($nic.Name)"
            & netsh interface ipv4 set address $nic.Name static $LaptopIP 255.255.255.0 | Out-Null
        } else {
            Add-State "added=$($nic.Name)"
            & netsh interface ipv4 add address $nic.Name $LaptopIP 255.255.255.0 | Out-Null
        }
        if ($LASTEXITCODE -ne 0) { Say 'Windows refused the address change.' Red; Undo-Settings; exit 1 }
        Say "Set '$($nic.Name)' to $LaptopIP." Green
    }

    Add-State "rule=$RuleName"
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP `
        -LocalPort $Port -RemoteAddress 192.168.50.0/24 -Profile Any | Out-Null
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol ICMPv4 `
        -IcmpType 8 -RemoteAddress 192.168.50.0/24 -Profile Any | Out-Null
    Say 'Firewall: allowed FTP and ping from 192.168.50.x only, until you press Q.' Green
}

# ---------------------------------------------------------------- paths
$BadName = '[<>:"|?*\x00-\x1F]'
$Reserved = '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$'

function Resolve-Remote([string]$cwd, [string]$arg) {
    # Turns an FTP path (any of / \ C:\...) into a list of safe folder/file
    # names under the backup folder. Returns $null if a name is not allowed.
    $a = $arg.Trim() -replace '\\', '/'
    $a = $a -replace '^[A-Za-z]:', ''
    $parts = New-Object System.Collections.ArrayList
    if (-not $a.StartsWith('/')) {
        foreach ($p in $cwd.Split('/')) { if ($p) { [void]$parts.Add($p) } }
    }
    foreach ($seg in $a.Split('/')) {
        if ($seg -eq '' -or $seg -eq '.') { continue }
        if ($seg -eq '..') { if ($parts.Count) { $parts.RemoveAt($parts.Count - 1) }; continue }
        if ($seg -match $BadName -or $seg -match $Reserved -or $seg.EndsWith('.') -or
            $seg.EndsWith(' ') -or $seg.Length -gt 100) { return $null }
        [void]$parts.Add($seg)
    }
    if ($parts.Count -gt 30) { return $null }
    return ,([string[]]$parts.ToArray())
}

function Local-Path([string[]]$parts) {
    $p = $script:Root
    foreach ($s in $parts) { $p = Join-Path $p $s }
    return $p
}

# ---------------------------------------------------------------- manifest
function Read-Manifest([string]$file) {
    $m = [ordered]@{}
    foreach ($l in [System.IO.File]::ReadAllLines($file, $Latin1)) {
        $l = $l.Trim()
        if (-not $l) { continue }
        $i = $l.LastIndexOf(' ')
        if ($i -lt 1) { continue }
        $size = 0L
        if ([long]::TryParse($l.Substring($i + 1), [ref]$size)) {
            $m[$l.Substring(0, $i)] = $size
        }
    }
    return $m
}

function Check-Backup {
    $mf = Join-Path $script:Root 'MANIFEST.TXT'
    if (-not (Test-Path $mf)) { Say 'No MANIFEST.TXT arrived, so the files cannot be checked.' Red; return $false }
    $m = Read-Manifest $mf
    $bad = 0
    foreach ($k in $m.Keys) {
        $lp = Local-Path (Resolve-Remote '/' $k)
        if (-not (Test-Path -LiteralPath $lp -PathType Leaf)) { Say "  MISSING: $k" Red; $bad++; continue }
        $len = (Get-Item -LiteralPath $lp).Length
        if ($len -ne $m[$k]) { Say "  WRONG SIZE: $k (old PC $($m[$k]), got $len)" Red; $bad++ }
    }
    $total = 0L; foreach ($v in $m.Values) { $total += $v }
    if ($bad -eq 0 -and $m.Count -gt 0) {
        Say ''
        Say "CHECK PASSED: all $($m.Count) files arrived with the right sizes ($total bytes)." Green
        $zip = Join-Path $script:OutBase ("MPSPRO_backup_{0}.zip" -f $script:Stamp)
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($script:Root, $zip)
        Say "Zipped: $zip" Green
        Say 'Upload that zip file to Claude.' Green
        return $true
    }
    Say "CHECK FAILED: $bad of $($m.Count) files missing or wrong. Run SEND on the old PC again." Red
    return $false
}

# ---------------------------------------------------------------- outbox
$TextJob = '\.(TAP|NC|TXT|GCO|CNC|NCC)$'

function Is-DosName([string]$n) {
    return $n -match '^[A-Za-z0-9_$~!#%&{}()@^-]{1,8}(\.[A-Za-z0-9_$~!#%&{}()@^-]{1,3})?$'
}

function Outbox-Files {
    return @(Get-ChildItem -LiteralPath $script:Outbox -File -ErrorAction SilentlyContinue |
             Sort-Object Name)
}

function Outbox-Bytes($file) {
    # What the old PC will receive: text jobs get CRLF line endings.
    $b = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($file.Name -notmatch $TextJob) { return ,$b }
    $t = $Latin1.GetString($b) -replace "`r`n", "`n" -replace "`r", "`n" -replace "`n", "`r`n"
    return ,$Latin1.GetBytes($t)
}

function Find-Outbox([string]$arg) {
    # Only a plain file name that is really in the outbox; no paths.
    $name = ($arg.Trim() -split '[\\/:]')[-1]
    if (-not $name -or $name -eq '.' -or $name -eq '..') { return $null }
    foreach ($f in Outbox-Files) { if ($f.Name -ieq $name) { return $f } }
    return $null
}

function Show-Outbox {
    $files = Outbox-Files
    if ($files.Count -eq 0) {
        Say "To send a job TO the old PC: put it in $script:Outbox"
        return
    }
    Say "Ready to send to the old PC (in $script:Outbox):"
    foreach ($f in $files) {
        $note = ''
        if (-not (Is-DosName $f.Name)) { $note = '  <- rename to 8 letters + .TAP (DOS can''t use this name)' }
        Say ("  {0}  {1} bytes{2}" -f $f.Name, $f.Length, $note)
    }
}

# ---------------------------------------------------------------- FTP
function Send-Line($stream, [string]$text) {
    $b = $Latin1.GetBytes($text + "`r`n")
    $stream.Write($b, 0, $b.Length)
}

function Read-Line($stream) {
    $buf = New-Object System.IO.MemoryStream
    while ($true) {
        $c = $stream.ReadByte()
        if ($c -lt 0) { if ($buf.Length) { break } else { return $null } }
        if ($c -eq 0xFF) { [void]$stream.ReadByte(); [void]$stream.ReadByte(); continue }  # telnet IAC
        if ($c -eq 10) { break }
        if ($c -ne 13) { $buf.WriteByte([byte]$c) }
        if ($buf.Length -gt 2000) { break }
    }
    return $Latin1.GetString($buf.ToArray())
}

function Open-Data($ep) {
    $dc = New-Object System.Net.Sockets.TcpClient
    $ar = $dc.BeginConnect($ep[0], $ep[1], $null, $null)
    if (-not $ar.AsyncWaitHandle.WaitOne(15000)) { $dc.Close(); return $null }
    try { $dc.EndConnect($ar) } catch { $dc.Close(); return $null }
    return $dc
}

function Run-Session($client) {
    $remote = $client.Client.RemoteEndPoint.Address
    $remoteText = $remote.ToString() -replace '^::ffff:', ''
    if (-not $TestMode -and -not $remoteText.StartsWith('192.168.50.')) {
        Say "Refused a connection from $remoteText (not the old PC)." Yellow
        $client.Close(); return
    }
    Say ''
    Say "Old PC connected from $remoteText." Green
    $s = $client.GetStream()
    $s.ReadTimeout = 600000
    $cwd = '/'
    $dataEp = $null
    $got = 0; $gotBytes = 0L
    Send-Line $s '220 CNC backup receiver ready'
    try {
        while ($true) {
            $line = Read-Line $s
            if ($null -eq $line) { break }
            $sp = $line.IndexOf(' ')
            if ($sp -lt 0) { $cmd = $line.ToUpperInvariant(); $arg = '' }
            else { $cmd = $line.Substring(0, $sp).ToUpperInvariant(); $arg = $line.Substring($sp + 1) }
            switch -Regex ($cmd) {
                '^USER$'        { Send-Line $s '331 Any password will do'; break }
                '^PASS$'        { Send-Line $s '230 Logged in'; break }
                '^(SYST)$'      { Send-Line $s '215 UNIX Type: L8'; break }
                '^(TYPE|MODE|STRU)$' { Send-Line $s '200 OK'; break }
                '^(NOOP|ALLO)$' { Send-Line $s '200 OK'; break }
                '^X?PWD$'       { Send-Line $s ('257 "{0}"' -f $cwd); break }
                '^X?CWD$' {
                    $p = Resolve-Remote $cwd $arg
                    if ($null -ne $p -and (Test-Path -LiteralPath (Local-Path $p) -PathType Container)) {
                        $cwd = '/' + ($p -join '/'); Send-Line $s '250 OK'
                    } else { Send-Line $s '550 No such folder' }
                    break
                }
                '^(CDUP|XCUP)$' {
                    $p = Resolve-Remote $cwd '..'; $cwd = '/' + ($p -join '/'); Send-Line $s '250 OK'; break
                }
                '^X?MKD$' {
                    $p = Resolve-Remote $cwd $arg
                    if ($null -eq $p -or $p.Count -eq 0) { Send-Line $s '553 Name not allowed'; break }
                    $lp = Local-Path $p
                    if (Test-Path -LiteralPath $lp) { Send-Line $s '550 Already exists'; break }
                    [void][System.IO.Directory]::CreateDirectory($lp)
                    Send-Line $s ('257 "/{0}" created' -f ($p -join '/'))
                    break
                }
                '^PORT$' {
                    $n = $arg.Split(',')
                    $ok = $n.Count -eq 6
                    $v = @(); foreach ($x in $n) { $t = 0; if (-not [int]::TryParse($x.Trim(), [ref]$t) -or $t -lt 0 -or $t -gt 255) { $ok = $false }; $v += $t }
                    if ($ok) {
                        $ip = '{0}.{1}.{2}.{3}' -f $v[0], $v[1], $v[2], $v[3]
                        $pt = $v[4] * 256 + $v[5]
                        if ($ip -ne $remoteText -or $pt -lt 1024) { Send-Line $s '504 Only the old PC itself'; break }
                        $dataEp = @($ip, $pt); Send-Line $s '200 PORT OK'
                    } else { Send-Line $s '501 Bad PORT' }
                    break
                }
                '^(STOR)$' {
                    $p = Resolve-Remote $cwd $arg
                    if ($null -eq $p -or $p.Count -eq 0) { Send-Line $s '553 Name not allowed'; break }
                    if ($null -eq $dataEp) { Send-Line $s '425 Send PORT first'; break }
                    $lp = Local-Path $p
                    $dir = Split-Path -Parent $lp
                    if (-not (Test-Path -LiteralPath $dir)) { [void][System.IO.Directory]::CreateDirectory($dir) }
                    $dc = Open-Data $dataEp
                    $dataEp = $null
                    if ($null -eq $dc) { Send-Line $s '425 Could not connect back to the old PC'; break }
                    Send-Line $s '150 Sending'
                    $tmp = $lp + '.part'
                    $n = 0L
                    $okFile = $true
                    $fs = [System.IO.File]::Create($tmp)
                    try {
                        $ds = $dc.GetStream(); $ds.ReadTimeout = 60000
                        $b = New-Object byte[] 65536
                        while (($r = $ds.Read($b, 0, $b.Length)) -gt 0) { $fs.Write($b, 0, $r); $n += $r }
                    } catch { $okFile = $false } finally { $fs.Close(); $dc.Close() }
                    if (-not $okFile) {
                        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
                        Send-Line $s '426 Transfer broke off'; Say "  FAILED: /$($p -join '/')" Red; break
                    }
                    if (Test-Path -LiteralPath $lp) { Remove-Item -LiteralPath $lp -Force }
                    Move-Item -LiteralPath $tmp -Destination $lp
                    $name = ($p -join '/')
                    if ($p.Count -eq 1 -and $name -ieq 'MANIFEST.TXT') {
                        $script:Expect = Read-Manifest $lp
                        $script:ExpectBytes = 0L; foreach ($x in $script:Expect.Values) { $script:ExpectBytes += $x }
                        Say ("  List of files received: {0} files, {1} bytes to come." -f $script:Expect.Count, $script:ExpectBytes)
                    } else {
                        $got++; $gotBytes += $n
                        $of = ''
                        if ($script:Expect -and $script:Expect.Count) {
                            $of = " of $($script:Expect.Count)"
                            $pct = 100
                            if ($script:ExpectBytes -gt 0) { $pct = [Math]::Min(100, [int](100 * $gotBytes / $script:ExpectBytes)) }
                            Write-Progress -Activity 'Receiving C:\MPSPRO from the old PC' -Status "$got$of files" -PercentComplete $pct
                        }
                        Say ("  [{0}{1}] {2}  {3} bytes" -f $got, $of, $name, $n)
                    }
                    Send-Line $s ("226 Done, {0} bytes" -f $n)
                    break
                }
                '^RETR$' {
                    $f = Find-Outbox $arg
                    if ($null -eq $f) { Send-Line $s '550 Not in the to_old_pc folder'; break }
                    if ($null -eq $dataEp) { Send-Line $s '425 Send PORT first'; break }
                    $bytes = Outbox-Bytes $f
                    $dc = Open-Data $dataEp
                    $dataEp = $null
                    if ($null -eq $dc) { Send-Line $s '425 Could not connect back to the old PC'; break }
                    Send-Line $s ("150 Sending {0} ({1} bytes)" -f $f.Name, $bytes.Length)
                    $okFile = $true
                    try { $ds = $dc.GetStream(); $ds.Write($bytes, 0, $bytes.Length); $ds.Flush() }
                    catch { $okFile = $false } finally { $dc.Close() }
                    if ($okFile) {
                        Send-Line $s ("226 Done, {0} bytes" -f $bytes.Length)
                        Say ("  SENT to old PC: {0}  {1} bytes" -f $f.Name, $bytes.Length) Green
                    } else { Send-Line $s '426 Transfer broke off'; Say "  FAILED sending $($f.Name)" Red }
                    break
                }
                '^(LIST|NLST)$' {
                    if ($null -eq $dataEp) { Send-Line $s '425 Send PORT first'; break }
                    $out = New-Object System.Text.StringBuilder
                    foreach ($f in Outbox-Files) {
                        if ($cmd -eq 'NLST') { [void]$out.Append($f.Name + "`r`n") }
                        else {
                            $n = (Outbox-Bytes $f).Length
                            [void]$out.Append(('-rw-r--r-- 1 owner group {0,10} {1} {2}' -f $n, $f.LastWriteTime.ToString('MMM dd HH:mm', [Globalization.CultureInfo]::InvariantCulture), $f.Name) + "`r`n")
                        }
                    }
                    $bytes = $Latin1.GetBytes($out.ToString())
                    $dc = Open-Data $dataEp
                    $dataEp = $null
                    if ($null -eq $dc) { Send-Line $s '425 Could not connect back to the old PC'; break }
                    Send-Line $s '150 Files in to_old_pc'
                    try { $ds = $dc.GetStream(); $ds.Write($bytes, 0, $bytes.Length) } catch { } finally { $dc.Close() }
                    Send-Line $s '226 Done'
                    break
                }
                '^QUIT$' { Send-Line $s '221 Bye'; return }
                default  { Send-Line $s '502 Not supported here' }
            }
        }
    } catch {
        Say "Connection problem: $($_.Exception.Message)" Yellow
    } finally {
        Write-Progress -Activity 'Receiving C:\MPSPRO from the old PC' -Completed
        $client.Close()
        Say "Session ended: $got files received."
    }
}

# ---------------------------------------------------------------- main
$script:Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
if ($OutDir) { $script:OutBase = $OutDir }
else { $script:OutBase = Join-Path $env:USERPROFILE 'Downloads\CNC_backup' }
$script:Root = Join-Path $script:OutBase ("received_" + $script:Stamp)
[void][System.IO.Directory]::CreateDirectory($script:Root)
$script:Outbox = Join-Path $script:OutBase 'to_old_pc'
[void][System.IO.Directory]::CreateDirectory($script:Outbox)
$script:Expect = $null; $script:ExpectBytes = 0L

Say '=== Receive the CNC backup from the old Windows 95 PC ===' Cyan
try {
    if (-not $TestMode) { Set-Up-Network }
    $bindIP = [System.Net.IPAddress]::Any
    if ($ListenIP) { $bindIP = [System.Net.IPAddress]::Parse($ListenIP) }
    $listener = New-Object System.Net.Sockets.TcpListener($bindIP, $Port)
    try { $listener.Start() } catch {
        Say "Could not start on port $Port ($($_.Exception.Message)). Is another FTP server running?" Red
        exit 1
    }
    Say ''
    Say "Ready. Files will be saved in: $script:Root" Green
    Say 'Now, on the old PC, open an MS-DOS Prompt and type:  C:\NETUP\SEND'
    Show-Outbox
    Say 'Press Q here when you are finished (this puts the network settings back).'
    $ping = New-Object System.Net.NetworkInformation.Ping
    $lastPing = [DateTime]::MinValue; $lastAns = $null; $passed = $false
    while ($true) {
        if ($listener.Pending()) {
            Run-Session ($listener.AcceptTcpClient())
            if (Test-Path (Join-Path $script:Root 'MANIFEST.TXT')) { $passed = Check-Backup }
            if ($ExitAfterSession) { break }
            Say 'Press Q to finish, or run SEND on the old PC again.'
        }
        $key = $null
        try { if ([Console]::KeyAvailable) { $key = [Console]::ReadKey($true) } } catch { }
        if ($key -and $key.Key -eq 'Q') { break }
        if (-not $TestMode -and ([DateTime]::Now - $lastPing).TotalSeconds -ge 3) {
            $lastPing = [DateTime]::Now
            $ans = $false
            try { $ans = ($ping.Send($OldPcIP, 700).Status -eq 'Success') } catch { }
            if ($ans -ne $lastAns) {
                if ($ans) { Say "Old PC ($OldPcIP) answers ping: YES - the network works." Green }
                else { Say "Old PC ($OldPcIP) answers ping: no (not yet)" Yellow }
                $lastAns = $ans
            }
        }
        Start-Sleep -Milliseconds 200
    }
    $listener.Stop()
} finally {
    if (-not $TestMode) { Undo-Settings }
}
if ($passed) { exit 0 } else { exit 3 }
