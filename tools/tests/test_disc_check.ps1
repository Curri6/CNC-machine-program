# Tests the pre-burn safety check embedded in burn_win95_disc.ps1 against
# good and deliberately broken images. Run make_test_isos.sh first, then
# pwsh -File test_disc_check.ps1 from this folder. Every line should say PASS.
$ErrorActionPreference = 'Stop'
$src = Get-Content -Raw ../burn_win95_disc.ps1
$cs = [regex]::Match($src, "(?s)\`$CheckSource = @'\r?\n(.*?)\r?\n'@").Groups[1].Value
Add-Type -TypeDefinition ($cs + "`n" + (Get-Content -Raw TestStream.cs)) -CompilerOptions "-langversion:5"
function T($name, $file, $start, $expectPass) {
    $s = New-Object FileIStream (Resolve-Path $file).Path
    try { $r = [Win95DiscCheck]::Verify($s, $start); $ok = $true } catch { $r = $_.Exception.InnerException.Message; if (-not $r) { $r = $_.Exception.Message }; $ok = $false }
    $verdict = if ($ok -eq $expectPass) { 'PASS' } else { 'FAIL' }
    "$verdict  $name -> $r"
    $s2 = New-Object FileIStream (Resolve-Path $file).Path
    if (-not [Win95DiscCheck]::TryRewind($s2)) { "FAIL rewind" }
}
T 'blank disc image, start 0'          t0.iso 0 $true
T 'no Joliet, start 0'                 tplain.iso 0 $true
T 'append image built for 50000'       t1.iso 50000 $true
T 'append image checked as start 0'    t1.iso 0 $false
T 'start-0 image on disc at 50000 (old bug)' t0.iso 50000 $false
T 'missing INTEL folder'               tnointel.iso 0 $false
T 'no ISO 9660 at all'                 zeros.iso 0 $false
