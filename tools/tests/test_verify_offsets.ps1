# Tests verify_win95_disc.ps1 reading a later session at its start block.
# Needs wholedisc.img: 50000 random blocks followed by t1.iso from
# make_test_isos.sh (see JOURNAL.md 2026-10-10).
$src = Get-Content -Raw ../verify_win95_disc.ps1
$cs = [regex]::Match($src, "(?s)\`$Source = @'\r?\n(.*?)\r?\n'@").Groups[1].Value
# Same Read/StartAt arithmetic as DiscDevice, backed by a file instead of a drive.
$fake = @'
public class FileDisc : IStream {
    FileStream fs; long basePos, pos;
    public FileDisc(string p) { fs = File.OpenRead(p); }
    public void StartAt(long sector) { basePos = sector * 2048; pos = 0; }
    public void Read(byte[] pv, int cb, IntPtr pcbRead) {
        fs.Seek(basePos + pos, SeekOrigin.Begin); int n = fs.Read(pv, 0, cb); pos += n;
        if (pcbRead != IntPtr.Zero) Marshal.WriteInt32(pcbRead, n); }
    public void Seek(long d, int o, IntPtr p) { pos = d; }
    public void Write(byte[] pv, int cb, IntPtr w) { throw new NotSupportedException(); }
    public void SetSize(long s) { } public void CopyTo(IStream a, long b, IntPtr c, IntPtr d) { }
    public void Commit(int f) { } public void Revert() { } public void LockRegion(long a, long b, int c) { }
    public void UnlockRegion(long a, long b, int c) { }
    public void Stat(out System.Runtime.InteropServices.ComTypes.STATSTG s, int f) { s = new System.Runtime.InteropServices.ComTypes.STATSTG(); }
    public void Clone(out IStream p) { p = null; }
}
'@
Add-Type -TypeDefinition ($cs + "`n" + $fake)
foreach ($t in @(@(50000, $true, 'session 2 found where the TOC says'), @(0, $false, 'reading from block 0 (old session) instead'), @(49000, $false, 'wrong session start'))) {
    $d = New-Object FileDisc "$PWD/wholedisc.img"; $d.StartAt($t[0])
    try { $r = [Win95DiscCheck]::Verify($d, [long]$t[0]); $ok = $true } catch { $r = $_.Exception.InnerException.Message; $ok = $false }
    $v = if ($ok -eq $t[1]) { 'PASS' } else { 'FAIL' }
    "$v  $($t[2]) -> $r"
}
