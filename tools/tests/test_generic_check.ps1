# Tests the generic "burn this folder" check (ExpectedFiles) in
# burn_win95_disc.ps1. Needs gen.iso: a later session at block 93952 holding
# 5 files (built by the test commands in JOURNAL.md, 2026-10-12).
$src = Get-Content -Raw ../burn_win95_disc.ps1
$cs = [regex]::Match($src, "(?s)\`$CheckSource = @'\r?\n(.*?)\r?\n'@").Groups[1].Value
Add-Type -TypeDefinition ($cs + "`n" + (Get-Content -Raw TestStream.cs)) -CompilerOptions '-langversion:5'
function T($name, $expect, $start, $pass) {
    [Win95DiscCheck]::ExpectedFiles = $expect
    $s = New-Object FileIStream (Resolve-Path gen.iso).Path
    try { $r = [Win95DiscCheck]::Verify($s, $start); $ok = $true } catch { $r = $_.Exception.InnerException.Message; $ok = $false }
    "$(if ($ok -eq $pass) {'PASS'} else {'FAIL'})  $name -> $r"
}
T 'generic: right count, right start' 5 93952 $true
T 'generic: wrong count'              6 93952 $false
T 'generic: wrong start'              5 0     $false
T 'WIN95/INTEL mode on generic disc' -1 93952 $false
