# Runs verify_win95_disc.ps1 end to end with a file-backed fake ScsiDisc.
# Set FAKEDISC to an image with a session written at block 93952 (see
# JOURNAL.md 2026-10-10). Run: pwsh -File test_verify_mainflow.ps1
$src = Get-Content -Raw ../verify_win95_disc.ps1
$cs = [regex]::Match($src, "(?s)\`$Source = @'\r?\n(.*?)\r?\n'@").Groups[1].Value
$cs = $cs -replace 'public class ScsiDisc : IStream', 'public class ScsiDiscReal : IStream' -replace 'public ScsiDisc\(', 'public ScsiDiscReal('
$fake = @'
public class ScsiDisc : IStream {
    FileStream fs; long basePos, pos;
    public string OpenedAs = "fake"; public string LastReadError = "";
    public ScsiDisc(string l) { fs = File.OpenRead(Environment.GetEnvironmentVariable("FAKEDISC")); }
    public string DiscInfo() { return "disc complete (finalized), last session complete, sessions 2, tracks 1-2"; }
    public int LastTrack() { return 2; }
    public long TrackStart(int t) { return t == 2 ? 93952 : 0; }
    public string DescribeTrack(int t) { return "track " + t + " (fake)"; }
    public string Probe(long s) { return "block " + s + ": read OK (fake)"; }
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
