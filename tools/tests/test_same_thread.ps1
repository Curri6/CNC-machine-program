# Checks that both phases of burn_win95_disc.ps1 run on the same thread.
# COM objects made on an STA thread die with that thread, so a new thread
# per phase breaks the burn. Run: pwsh -File test_same_thread.ps1 from here.
$ErrorActionPreference = 'Stop'
$src = Get-Content -Raw ../burn_win95_disc.ps1
$rsBlock = [regex]::Match($src, "(?s)(    \`$rs = \[runspacefactory\].*?\`$ps\.Runspace = \`$rs)").Groups[1].Value
$fn = [regex]::Match($src, "(?s)(    function Run-Phase.*?\n    }\n)").Groups[1].Value
# STA apartments don't exist on Linux; drop only that line for this test.
$rsBlockLinux = ($rsBlock -split "`n" | Where-Object { $_ -notmatch "ApartmentState" }) -join "`n"
Invoke-Expression $fn
$tid = { [Threading.Thread]::CurrentThread.ManagedThreadId }

Invoke-Expression $rsBlockLinux
$a = (Run-Phase $tid.ToString() @() 'A' 5)[0]; $b = (Run-Phase $tid.ToString() @() 'B' 5)[0]
"script's runspace setup: phase A thread $a, phase B thread $b -> " + $(if ($a -eq $b) { 'SAME thread (fixed)' } else { 'DIFFERENT threads (bug)' })
$ps.Dispose(); $rs.Close()

Invoke-Expression ($rsBlockLinux -replace "(?m)^.*ThreadOptions.*$", "")
$a = (Run-Phase $tid.ToString() @() 'A' 5)[0]; $b = (Run-Phase $tid.ToString() @() 'B' 5)[0]
"old setup (no ReuseThread): phase A thread $a, phase B thread $b -> " + $(if ($a -eq $b) { 'same thread' } else { 'DIFFERENT threads - this is what broke the burn' })
