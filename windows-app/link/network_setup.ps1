# network_setup.ps1 - one-time network setup for the A-Tech CNC app.
# The app starts this with administrator rights (Windows asks first).
#
#   -Action Set   give the laptop's network-cable port the address
#                 192.168.50.1 and allow FTP (port 21) + ping from
#                 192.168.50.x only, through the Windows firewall
#   -Action Undo  put back what Set changed
#
# What Set changed is written to <StateDir>\network_state.txt so Undo
# can reverse exactly that. Works in Windows PowerShell 5.1.
param(
    [ValidateSet('Set', 'Undo')][string]$Action = 'Set',
    [string]$LaptopIP = '192.168.50.1',
    [int]$Port = 21,
    [string]$StateDir = "$env:USERPROFILE\Documents\A-Tech CNC"
)
$ErrorActionPreference = 'Stop'
$RuleName = 'A-Tech CNC link'
$State = Join-Path $StateDir 'network_state.txt'
function Say([string]$m, [string]$c = 'Gray') { Write-Host $m -ForegroundColor $c }
function Done([int]$code) { Say ''; Read-Host 'Press Enter to close'; exit $code }

Say "=== A-Tech CNC: network $Action ===" Cyan
try {
    if ($Action -eq 'Undo') {
        if (Test-Path $State) {
            foreach ($l in Get-Content $State) {
                $kv = $l.Split('=', 2)
                if ($kv[0] -eq 'dhcp')  { & netsh interface ipv4 set address $kv[1] dhcp | Out-Null; Say "Put '$($kv[1])' back to automatic address." Green }
                if ($kv[0] -eq 'added') { & netsh interface ipv4 delete address $kv[1] $LaptopIP | Out-Null; Say "Removed $LaptopIP from '$($kv[1])'." Green }
            }
            Remove-Item $State -Force
        } else { Say 'This app did not change any address, so none was put back.' }
        Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        Say 'Firewall rules removed.' Green
        Done 0
    }

    $have = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -eq $LaptopIP }
    if ($have) {
        Say "This laptop already has $LaptopIP on '$($have[0].InterfaceAlias)'. Good." Green
    } else {
        $nics = @(Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
                  Where-Object { $_.PhysicalMediaType -match '802\.3' -or $_.MediaType -match '802\.3' } |
                  Where-Object { $_.PhysicalMediaType -notmatch 'Wireless|Native 802\.11' })
        if ($nics.Count -eq 0) { Say 'No network-cable (Ethernet) port found. Plug in the USB network adapter and try again.' Red; Done 1 }
        for ($i = 0; $i -lt $nics.Count; $i++) { Say ("  {0} = {1}  ({2}, {3})" -f ($i + 1), $nics[$i].Name, $nics[$i].InterfaceDescription, $nics[$i].Status) }
        $pick = 0
        if ($nics.Count -gt 1) {
            $ans = Read-Host 'Type the number of the port the cable to the old PC is plugged into'
            if (-not [int]::TryParse($ans, [ref]$pick) -or $pick -lt 1 -or $pick -gt $nics.Count) { Say 'Not a valid number. Nothing was changed.' Red; Done 1 }
            $pick--
        }
        $nic = $nics[$pick]
        [void][System.IO.Directory]::CreateDirectory($StateDir)
        $dhcp = (Get-NetIPInterface -InterfaceIndex $nic.ifIndex -AddressFamily IPv4).Dhcp
        if ("$dhcp" -eq 'Enabled') {
            Add-Content $State "dhcp=$($nic.Name)"
            & netsh interface ipv4 set address $nic.Name static $LaptopIP 255.255.255.0 | Out-Null
        } else {
            Add-Content $State "added=$($nic.Name)"
            & netsh interface ipv4 add address $nic.Name $LaptopIP 255.255.255.0 | Out-Null
        }
        if ($LASTEXITCODE -ne 0) { Say 'Windows refused the address change.' Red; Done 1 }
        Say "Set '$($nic.Name)' to $LaptopIP." Green
    }
    Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress 192.168.50.0/24 -Profile Any | Out-Null
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol ICMPv4 -IcmpType 8 -RemoteAddress 192.168.50.0/24 -Profile Any | Out-Null
    Say 'Firewall: FTP and ping allowed from 192.168.50.x only.' Green
    Say 'Done. You can close this window and go back to the app.' Cyan
    Done 0
} catch {
    Say "Something went wrong: $($_.Exception.Message)" Red
    Done 1
}
