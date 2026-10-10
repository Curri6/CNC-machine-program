# Runs the script's own speed-list and speed-choice code against sample inputs.
$src = Get-Content -Raw ../burn_win95_disc.ps1
$speeds = @(8.0, 2.0, 4.0)
$emit = [regex]::Match($src, '(?m)^\s*("@@SPEEDS .*")\s*$').Groups[1].Value
$line = Invoke-Expression $emit
"emitted: $line"
$parse = [regex]::Match($src, '(?s)(    \$supported = @\(\)\r?\n    foreach \(\$line in \$check\) \{.*?\n    \}\n)').Groups[1].Value
$check = @('start block 93952 | ...', 'SPEED: ...', $line)
function Write-Host { }   # silence display lines
Invoke-Expression $parse
"parsed supported: $($supported -join ', ')"
$choose = [regex]::Match($src, '(?s)(    \$speedX = 0\r?\n.*?Burning at \$\{speedX\}x\."\r?\n    \})').Groups[1].Value
function Stop-All { }
function Pause-Exit($c) { throw "CANCELLED" }
foreach ($in in @('', '4x', '8', '2 x', '3', 'fast')) {
    function Read-Host($p) { $script:in }
    $script:in = $in
    try { Invoke-Expression $choose; "input '$in' -> burn at ${speedX}x" } catch { "input '$in' -> cancelled, nothing written" }
}
