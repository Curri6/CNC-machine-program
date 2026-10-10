<#
verify_win95_disc.ps1

READ-ONLY check of a burned disc, from the laptop, without the old PC.
It reads what Windows 95 will read:
  1. the disc's session list (where the last burned section starts -
     that is where Windows 95 looks), and
  2. that section itself, straight off the disc, through the same check
     the burn tool uses (ISO 9660 + Joliet, WIN95 with .CAB files, INTEL
     with an .INF, every address inside the section).
It opens the drive for reading only. It cannot write to the disc.

Start it with verify_win95_disc.bat (double-click).
#>

$ErrorActionPreference = 'Stop'

function Pause-Exit {
    Write-Host ''
    Read-Host 'Press Enter to close'
    exit 0
}

$Source = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

// Reads back the disc image IMAPI2 built, before it is burned, and checks
// that Windows 95 will be able to read it: an ISO 9660 primary volume
// descriptor, a root directory holding WIN95 (with .CAB files) and INTEL
// (with an .INF), and every directory/file address inside this session.
// Written in C# 5 so Windows PowerShell 5.1's Add-Type can compile it.
public static class Win95DiscCheck
{
    const int S = 2048;

    class Entry
    {
        public string Name;
        public bool IsDir;
        public uint Lba;
        public uint Len;
    }

    class Reader
    {
        IStream st;
        MemoryStream buf = new MemoryStream();
        IntPtr pRead;
        public Reader(IStream st) { this.st = st; pRead = Marshal.AllocHGlobal(4); }
        public void Close() { Marshal.FreeHGlobal(pRead); }

        // Reads forward only (no Seek), so it works on any stream.
        public byte[] Sector(long rel)
        {
            if (rel < 0) throw new Exception("Address points before the start of this session (sector " + rel + ").");
            if (rel > 200000) throw new Exception("Address is unreasonably far into the image (sector " + rel + ").");
            long need = (rel + 1) * S;
            byte[] chunk = new byte[65536];
            while (buf.Length < need)
            {
                Marshal.WriteInt32(pRead, 0);
                st.Read(chunk, chunk.Length, pRead);
                int n = Marshal.ReadInt32(pRead);
                if (n <= 0) throw new Exception("Image ends before sector " + rel + ".");
                buf.Write(chunk, 0, n);
            }
            byte[] s = new byte[S];
            Array.Copy(buf.GetBuffer(), rel * S, s, 0, S);
            return s;
        }
    }

    static uint U32(byte[] b, int o) { return (uint)(b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)); }

    static List<Entry> ReadDir(Reader r, long start, uint vol, uint lba, uint len, bool joliet)
    {
        CheckRange(start, vol, lba, "directory");
        List<Entry> list = new List<Entry>();
        uint sectors = (len + S - 1) / S;
        for (uint i = 0; i < sectors; i++)
        {
            byte[] sec = r.Sector(lba + i - start);
            int p = 0;
            while (p < S)
            {
                int rl = sec[p];
                if (rl == 0) break;
                if (p + rl > S || rl < 34) throw new Exception("Damaged directory record.");
                int nl = sec[p + 32];
                Entry e = new Entry();
                e.Lba = U32(sec, p + 2);
                e.Len = U32(sec, p + 10);
                e.IsDir = (sec[p + 25] & 2) != 0;
                if (nl == 1 && (sec[p + 33] == 0 || sec[p + 33] == 1)) { p += rl; continue; }
                string name = joliet ? Encoding.BigEndianUnicode.GetString(sec, p + 33, nl)
                                     : Encoding.ASCII.GetString(sec, p + 33, nl);
                int semi = name.IndexOf(';');
                if (semi >= 0) name = name.Substring(0, semi);
                if (name.EndsWith(".")) name = name.Substring(0, name.Length - 1);
                e.Name = name;
                list.Add(e);
                p += rl;
            }
        }
        return list;
    }

    static void CheckRange(long start, uint vol, uint lba, string what)
    {
        if (lba < start || lba >= vol)
            throw new Exception("A " + what + " address (" + lba + ") is outside this session (" + start + " to " + vol +
                                "). The new section would be unreadable. Nothing was burned.");
    }

    static Entry Find(List<Entry> list, string name, bool dir)
    {
        foreach (Entry e in list)
            if (e.IsDir == dir && string.Equals(e.Name, name, StringComparison.OrdinalIgnoreCase)) return e;
        return null;
    }

    static int CountFiles(Reader r, long start, uint vol, Entry dir, bool joliet, string ext, int depth)
    {
        int n = 0;
        foreach (Entry e in ReadDir(r, start, vol, dir.Lba, dir.Len, joliet))
        {
            if (e.IsDir) { if (depth < 6) n += CountFiles(r, start, vol, e, joliet, ext, depth + 1); continue; }
            if (e.Len > 0) CheckRange(start, vol, e.Lba, "file");
            if (e.Name.EndsWith(ext, StringComparison.OrdinalIgnoreCase)) n++;
        }
        return n;
    }

    static string CheckTree(Reader r, long start, uint vol, byte[] vd, bool joliet)
    {
        uint rootLba = U32(vd, 158);
        uint rootLen = U32(vd, 166);
        List<Entry> root = ReadDir(r, start, vol, rootLba, rootLen, joliet);
        string which = joliet ? "Joliet" : "ISO 9660";
        Entry win95 = Find(root, "WIN95", true);
        Entry intel = Find(root, "INTEL", true);
        if (win95 == null) throw new Exception(which + " listing has no WIN95 folder. Nothing was burned.");
        if (intel == null) throw new Exception(which + " listing has no INTEL folder. Nothing was burned.");
        int cabs = CountFiles(r, start, vol, win95, joliet, ".CAB", 0);
        int infs = CountFiles(r, start, vol, intel, joliet, ".INF", 0);
        if (cabs == 0) throw new Exception(which + " listing: WIN95 has no .CAB files. Nothing was burned.");
        if (infs == 0) throw new Exception(which + " listing: INTEL has no .INF file. Nothing was burned.");
        return which + ": WIN95 " + cabs + " CAB, INTEL " + infs + " INF";
    }

    public static string Verify(object comStream, long expectedStart)
    {
        Reader r = new Reader((IStream)comStream);
        try
        {
            byte[] pvd = r.Sector(16);
            if (pvd[0] != 1 || Encoding.ASCII.GetString(pvd, 1, 5) != "CD001")
                throw new Exception("No ISO 9660 volume descriptor. Windows 95 could not read this. Nothing was burned.");
            uint vol = U32(pvd, 80);
            // Tools differ on whether a later session's volume size counts
            // from the start of the disc or from the start of the session.
            if (vol <= expectedStart) vol = (uint)(expectedStart + vol);
            List<string> parts = new List<string>();
            parts.Add("start block " + expectedStart);
            parts.Add(CheckTree(r, expectedStart, vol, pvd, false));

            bool joliet = false, udf = false;
            for (int i = 17; i < 64; i++)
            {
                byte[] d = r.Sector(i);
                if (Encoding.ASCII.GetString(d, 1, 5) != "CD001")
                    throw new Exception("Volume descriptor list is damaged. Nothing was burned.");
                if (d[0] == 255)
                {
                    // A UDF recognition sequence, if any, follows the terminator.
                    for (int j = i + 1; j < i + 4; j++)
                    {
                        string id = Encoding.ASCII.GetString(r.Sector(j), 1, 5);
                        if (id == "BEA01" || id == "NSR02" || id == "NSR03") udf = true;
                    }
                    break;
                }
                if (d[0] == 2 && d[88] == 0x25 && d[89] == 0x2F && (d[90] == 0x40 || d[90] == 0x43 || d[90] == 0x45))
                {
                    joliet = true;
                    parts.Add(CheckTree(r, expectedStart, vol, d, true));
                }
            }
            parts.Add(joliet ? "Joliet: yes" : "Joliet: no (short 8.3 names only)");
            parts.Add(udf ? "UDF: also present" : "UDF: none");
            return string.Join(" | ", parts.ToArray());
        }
        finally { r.Close(); }
    }

    public static bool TryRewind(object comStream)
    {
        try { ((IStream)comStream).Seek(0, 0, IntPtr.Zero); return true; }
        catch { return false; }
    }
}

// Read-only access to the disc in a drive: the session list (where the
// last burned section starts) and raw 2048-byte sectors, exposed as an
// IStream so Win95DiscCheck.Verify can read straight off the disc.
public class DiscDevice : IStream
{
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern Microsoft.Win32.SafeHandles.SafeFileHandle CreateFile(string name, uint access, uint share,
        IntPtr sa, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool DeviceIoControl(Microsoft.Win32.SafeHandles.SafeFileHandle h, uint code, byte[] inBuf, int inSize,
        byte[] outBuf, int outSize, out int returned, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetFilePointerEx(Microsoft.Win32.SafeHandles.SafeFileHandle h, long dist, out long newPos, uint method);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool ReadFile(Microsoft.Win32.SafeHandles.SafeFileHandle h, byte[] buf, int toRead, out int read, IntPtr overlapped);

    Microsoft.Win32.SafeHandles.SafeFileHandle h;
    long basePos, pos;

    public DiscDevice(string letter)
    {
        // GENERIC_READ only, so this can never write to the disc.
        h = CreateFile("\\\\.\\" + letter + ":", 0x80000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
        if (h.IsInvalid)
        {
            int err = Marshal.GetLastWin32Error();
            throw new Exception("Could not open drive " + letter + ": (Windows error " + err + ")." +
                (err == 5 ? " Right-click verify_win95_disc.bat and choose Run as administrator." : ""));
        }
        int r;
        // Let reads go past the end of the first (UDF) section. Harmless if refused.
        DeviceIoControl(h, 0x00090083, null, 0, null, 0, out r, IntPtr.Zero);
    }

    byte[] SessionData()
    {
        byte[] inb = new byte[4];
        inb[0] = 1;                       // CDROM_READ_TOC_EX_FORMAT_SESSION, LBA addresses
        byte[] outb = new byte[12];
        int r;
        if (!DeviceIoControl(h, 0x00024054, inb, 4, outb, outb.Length, out r, IntPtr.Zero))
            throw new Exception("Could not read the disc's session list (Windows error " + Marshal.GetLastWin32Error() + ").");
        return outb;
    }

    public int LastSessionNumber() { return SessionData()[3]; }

    public string SessionRaw()
    {
        byte[] b = SessionData();
        return BitConverter.ToString(b);
    }

    // Plain track list (TOC format 0): "track N starts at block X", one per
    // track, so the session starts can be read even if the session-format
    // answer looks odd.
    public string[] Tracks()
    {
        byte[] inb = new byte[4];
        inb[0] = 0;                       // CDROM_READ_TOC_EX_FORMAT_TOC, LBA addresses
        inb[1] = 1;                       // starting from track 1
        byte[] outb = new byte[4 + 8 * 100];
        int r;
        if (!DeviceIoControl(h, 0x00024054, inb, 4, outb, outb.Length, out r, IntPtr.Zero))
            return new string[] { "track list unavailable (Windows error " + Marshal.GetLastWin32Error() + ")" };
        int len = (outb[0] << 8) | outb[1];
        int count = Math.Min((len - 2) / 8, 100);
        System.Collections.Generic.List<string> list = new System.Collections.Generic.List<string>();
        for (int i = 0; i < count; i++)
        {
            int o = 4 + i * 8;
            long a = ((long)outb[o + 4] << 24) | ((long)outb[o + 5] << 16) | ((long)outb[o + 6] << 8) | outb[o + 7];
            int tn = outb[o + 2];
            list.Add((tn == 0xAA ? "end of disc" : "track " + tn) + " at block " + a);
        }
        return list.ToArray();
    }

    // Start of the last session = where Windows 95 looks for files.
    public long LastSessionStart()
    {
        byte[] b = SessionData();
        return ((long)b[8] << 24) | ((long)b[9] << 16) | ((long)b[10] << 8) | b[11];
    }

    public void StartAt(long sector) { basePos = sector * 2048; pos = 0; }

    public void Read(byte[] pv, int cb, IntPtr pcbRead)
    {
        long np;
        int n = 0;
        if (SetFilePointerEx(h, basePos + pos, out np, 0) && ReadFile(h, pv, cb, out n, IntPtr.Zero)) pos += n;
        else n = 0;
        if (pcbRead != IntPtr.Zero) Marshal.WriteInt32(pcbRead, n);
    }
    public void Seek(long dlibMove, int dwOrigin, IntPtr plibNewPosition) { pos = dlibMove; }
    public void Write(byte[] pv, int cb, IntPtr pcbWritten) { throw new NotSupportedException("read-only"); }
    public void SetSize(long libNewSize) { throw new NotSupportedException("read-only"); }
    public void CopyTo(IStream pstm, long cb, IntPtr pcbRead, IntPtr pcbWritten) { throw new NotSupportedException(); }
    public void Commit(int grfCommitFlags) { }
    public void Revert() { }
    public void LockRegion(long libOffset, long cb, int dwLockType) { }
    public void UnlockRegion(long libOffset, long cb, int dwLockType) { }
    public void Stat(out System.Runtime.InteropServices.ComTypes.STATSTG pstatstg, int grfStatFlag)
    { pstatstg = new System.Runtime.InteropServices.ComTypes.STATSTG(); }
    public void Clone(out IStream ppstm) { throw new NotSupportedException(); }
    public void Close() { h.Dispose(); }
}

'@

try {
    Write-Host '=== Win95 disc check (read-only) ===' -ForegroundColor Cyan
    Add-Type -TypeDefinition $Source -ErrorAction Stop

    $letter = Read-Host 'Drive letter of the DVD drive (press Enter for E)'
    if (-not $letter) { $letter = 'E' }
    $letter = $letter.Trim().TrimEnd(':').ToUpper()

    $disc = New-Object DiscDevice $letter
    try {
        $sessions = $disc.LastSessionNumber()
        $reported = $disc.LastSessionStart()
        Write-Host "Sessions on disc:      $sessions"
        Write-Host "Drive says last session starts at block $reported"
        Write-Host "  (raw answer: $($disc.SessionRaw()))"
        foreach ($t in $disc.Tracks()) { Write-Host "  $t" }
        Write-Host ''

        $expected = 93952   # where the burn tool wrote the new section
        $starts = @($expected)
        if ($reported -gt 0 -and $reported -lt 2400000 -and $reported -ne $expected) { $starts += $reported }

        $good = $false
        foreach ($st in $starts) {
            $disc.StartAt($st)
            try {
                $summary = [Win95DiscCheck]::Verify($disc, [long]$st)
                Write-Host "VERIFIED at block ${st} - the Windows 95 section is on the disc and complete:" -ForegroundColor Green
                Write-Host "  $summary"
                $good = $true
            }
            catch {
                $m = $_.Exception.Message
                if ($_.Exception.InnerException) { $m = $_.Exception.InnerException.Message }
                $m = $m -replace ' Nothing was burned\.', ''
                Write-Host "Not readable at block ${st}: $m" -ForegroundColor Red
            }
        }
        Write-Host ''
        if ($good) {
            Write-Host 'The new section is on the disc and complete. Whether the old PC finds it'
            Write-Host 'depends on its own drive reading the second session - only the old PC can test that.'
        } else {
            Write-Host 'Take a screenshot of this window and send it to Claude.'
        }
    }
    finally { $disc.Close() }
    Pause-Exit
}
catch {
    $m = $_.Exception.Message
    if ($_.Exception.InnerException) { $m = $_.Exception.InnerException.Message }
    $m = $m -replace ' Nothing was burned\.', ''
    Write-Host ''
    Write-Host 'NOT VERIFIED:' -ForegroundColor Red
    Write-Host "  $m"
    Write-Host ''
    Write-Host 'Take a screenshot of this window and send it to Claude.'
    Pause-Exit
}
