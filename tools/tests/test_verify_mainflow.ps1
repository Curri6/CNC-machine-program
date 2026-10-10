# Runs verify_win95_disc.ps1 end to end with a file-backed fake drive that
# gives the same odd session answer as the real laptop drive (2026-10-10).
# Set FAKEDISC to an image with a session written at block 93952.
# Runs the verifier's real main flow with DiscDevice replaced by a file-backed
# fake that returns the same odd session answer the laptop drive gave.
$src = Get-Content -Raw ../verify_win95_disc.ps1
$cs = [regex]::Match($src, "(?s)\`$Source = @'\r?\n(.*?)\r?\n'@").Groups[1].Value
$cs = $cs -replace 'public class DiscDevice : IStream', 'public class DiscDeviceReal : IStream' -replace 'public DiscDevice\(', 'public DiscDeviceReal('
$fake = @'
public class DiscDevice : IStream {
    FileStream fs; long basePos, pos;
    public DiscDevice(string l) { fs = File.OpenRead(Environment.GetEnvironmentVariable("FAKEDISC")); }
    public int LastSessionNumber() { return 2; }
    public long LastSessionStart() { return 4294770687L; }
    public string SessionRaw() { return "00-0A-01-02-00-14-02-00-FF-FC-FF-FF"; }
    public string[] Tracks() { return new string[] { "track 1 at block 0", "track 2 at block 93952", "end of disc at block 124000" }; }
    public void StartAt(long sector) { basePos = sector * 2048; pos = 0; }
    public void Read(byte[] pv, int cb, IntPtr pcbRead) { int n = 0; if (basePos + pos < fs.Length) { fs.Seek(basePos + pos, SeekOrigin.Begin); n = fs.Read(pv, 0, cb); } pos += n; if (pcbRead != IntPtr.Zero) Marshal.WriteInt32(pcbRead, n); }
    public void Seek(long d, int o, IntPtr p) { pos = d; }
    public void Write(byte[] pv, int cb, IntPtr w) { } public void SetSize(long s) { } public void CopyTo(IStream a, long b, IntPtr c, IntPtr d) { }
    public void Commit(int f) { } public void Revert() { } public void LockRegion(long a, long b, int c) { } public void UnlockRegion(long a, long b, int c) { }
    public void Stat(out System.Runtime.InteropServices.ComTypes.STATSTG s, int f) { s = new System.Runtime.InteropServices.ComTypes.STATSTG(); }
    public void Clone(out IStream p) { p = null; }
    public void Close() { fs.Dispose(); }
}
'@
$main = $src -replace "(?s)\`$Source = @'\r?\n.*?\r?\n'@", "`$Source = `$null" -replace 'Add-Type -TypeDefinition \$Source -ErrorAction Stop', '' -replace "Read-Host 'Drive letter[^']*'", "''" -replace "Read-Host 'Press Enter to close'", "''" -replace 'exit 0', ''
Add-Type -TypeDefinition ($cs + "`n" + $fake)
Invoke-Expression $main
