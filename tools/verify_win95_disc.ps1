<#
verify_win95_disc.ps1

READ-ONLY check of a burned disc, from the laptop, without the old PC.
It reads what Windows 95 will read:
  1. the disc's session list (where the last burned section starts -
     that is where Windows 95 looks), and
  2. that section itself, straight off the disc, through the same check
     the burn tool uses (ISO 9660 + Joliet, WIN95 with .CAB files, INTEL
     with an .INF, every address inside the section).
It only ever sends the drive three READ commands (enforced in the code).
Needs Run as administrator (Windows requires it for direct drive commands).

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

// Talks to the drive with its own read commands (SCSI pass-through), which
// gets past Windows' idea of where the disc ends. ONLY three read commands
// can ever be sent: READ(10) 0x28, READ DISC INFORMATION 0x51, READ TRACK
// INFORMATION 0x52. Anything else is refused before it reaches the drive.
public class ScsiDisc : IStream
{
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern Microsoft.Win32.SafeHandles.SafeFileHandle CreateFile(string name, uint access, uint share,
        IntPtr sa, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool DeviceIoControl(Microsoft.Win32.SafeHandles.SafeFileHandle h, uint code, byte[] inBuf, int inSize,
        byte[] outBuf, int outSize, out int returned, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern int QueryDosDevice(string deviceName, StringBuilder target, int max);

    static readonly byte[] Allowed = new byte[] { 0x28, 0x51, 0x52 };
    Microsoft.Win32.SafeHandles.SafeFileHandle h;
    long basePos, pos;
    public string OpenedAs;
    public string LastReadError = "";

    public ScsiDisc(string letter)
    {
        StringBuilder target = new StringBuilder(260);
        string dev = "\\\\.\\" + letter + ":";
        if (QueryDosDevice(letter + ":", target, target.Capacity) > 0)
        {
            string t = target.ToString();
            int i = t.IndexOf("CdRom", StringComparison.OrdinalIgnoreCase);
            if (i >= 0) dev = "\\\\.\\" + t.Substring(i);
        }
        // Windows requires read+write ACCESS on the handle for pass-through.
        // That does not write anything: only the read commands above are sent.
        h = CreateFile(dev, 0xC0000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
        if (h.IsInvalid)
        {
            int err = Marshal.GetLastWin32Error();
            throw new Exception("Could not open " + dev + " (Windows error " + err + ")." +
                (err == 5 ? " Close this, right-click verify_win95_disc.bat and choose Run as administrator." : ""));
        }
        OpenedAs = dev;
    }

    static void PutInt(byte[] b, int o, int v) { b[o] = (byte)v; b[o + 1] = (byte)(v >> 8); b[o + 2] = (byte)(v >> 16); b[o + 3] = (byte)(v >> 24); }
    static int GetInt(byte[] b, int o) { return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24); }
    static long BE(byte[] b, int o) { return ((long)b[o] << 24) | ((long)b[o + 1] << 16) | ((long)b[o + 2] << 8) | b[o + 3]; }

    byte[] Run(byte[] cdb, int dataLen)
    {
        if (Array.IndexOf(Allowed, cdb[0]) < 0) throw new Exception("Refusing non-read drive command 0x" + cdb[0].ToString("X2"));
        bool x64 = IntPtr.Size == 8;
        int sptLen = x64 ? 56 : 44;          // sizeof(SCSI_PASS_THROUGH)
        int senseOff = sptLen;
        int dataOff = x64 ? 88 : 76;
        byte[] buf = new byte[dataOff + dataLen];
        buf[0] = (byte)sptLen;               // Length
        buf[6] = (byte)cdb.Length;           // CdbLength
        buf[7] = 32;                         // SenseInfoLength
        buf[8] = 1;                          // DataIn = SCSI_IOCTL_DATA_IN
        PutInt(buf, 12, dataLen);            // DataTransferLength
        PutInt(buf, 16, 30);                 // TimeOutValue (s)
        if (x64) { PutInt(buf, 24, dataOff); PutInt(buf, 32, senseOff); Array.Copy(cdb, 0, buf, 36, cdb.Length); }
        else     { PutInt(buf, 20, dataOff); PutInt(buf, 24, senseOff); Array.Copy(cdb, 0, buf, 28, cdb.Length); }
        int ret;
        if (!DeviceIoControl(h, 0x0004D004, buf, buf.Length, buf, buf.Length, out ret, IntPtr.Zero))
            throw new Exception("drive command 0x" + cdb[0].ToString("X2") + " failed (Windows error " + Marshal.GetLastWin32Error() + ")");
        if (buf[2] != 0)
        {
            int key = buf[senseOff + 2] & 0x0F, asc = buf[senseOff + 12], ascq = buf[senseOff + 13];
            string what = "";
            if (key == 5 && asc == 0x21) what = " = address past the recorded area";
            else if (key == 5 && asc == 0x64) what = " = illegal mode for this track";
            else if (key == 3 && asc == 0x11) what = " = unrecoverable read error (unreadable data)";
            else if (key == 3 && asc == 0x02) what = " = no seek complete";
            else if (key == 3) what = " = medium error";
            else if (key == 2) what = " = drive not ready";
            throw new Exception("drive said sense " + key.ToString("X") + "/" + asc.ToString("X2") + "/" + ascq.ToString("X2") + what);
        }
        int got = GetInt(buf, 12);
        if (got <= 0 || got > dataLen) got = dataLen;
        byte[] data = new byte[got];
        Array.Copy(buf, dataOff, data, 0, got);
        return data;
    }

    int lastTrack = 1;
    public string DiscInfo()
    {
        byte[] cdb = new byte[10]; cdb[0] = 0x51; cdb[8] = 34;
        byte[] d = Run(cdb, 34);
        string[] st = new string[] { "empty", "incomplete (more can be added)", "complete (finalized)", "other" };
        string[] ss = new string[] { "empty", "incomplete", "reserved", "complete" };
        int sessions = d[4] | (d[9] << 8);
        lastTrack = d[6] | (d[11] << 8);
        return "disc " + st[d[2] & 3] + ", last session " + ss[(d[2] >> 2) & 3] +
               ", sessions " + sessions + ", tracks " + (d[3]) + "-" + lastTrack;
    }
    public int LastTrack() { return lastTrack; }

    byte[] TrackData(int track)
    {
        byte[] cdb = new byte[10]; cdb[0] = 0x52; cdb[1] = 0x01;
        cdb[2] = (byte)(track >> 24); cdb[3] = (byte)(track >> 16); cdb[4] = (byte)(track >> 8); cdb[5] = (byte)track;
        cdb[8] = 48;
        return Run(cdb, 48);
    }
    public long TrackStart(int track) { return BE(TrackData(track), 8); }
    public string DescribeTrack(int track)
    {
        byte[] d = TrackData(track);
        bool blank = (d[6] & 0x40) != 0, rt = (d[6] & 0x80) != 0, lraV = (d[7] & 0x02) != 0, nwaV = (d[7] & 1) != 0;
        string state = blank ? "BLANK (nothing written)" : (rt ? "reserved/incomplete" : "written");
        return "track " + track + " (session " + (d[3] | (d[33] << 8)) + "): start " + BE(d, 8) +
               ", size " + BE(d, 24) + " blocks (" + (BE(d, 24) * 2048 / 1048576) + " MB), " + state +
               (lraV ? ", last recorded block " + BE(d, 28) : "") + (nwaV ? ", next writable " + BE(d, 12) : ", closed");
    }

    public byte[] ReadBlocks(long lba, int count)
    {
        byte[] cdb = new byte[10]; cdb[0] = 0x28;
        cdb[2] = (byte)(lba >> 24); cdb[3] = (byte)(lba >> 16); cdb[4] = (byte)(lba >> 8); cdb[5] = (byte)lba;
        cdb[7] = (byte)(count >> 8); cdb[8] = (byte)count;
        return Run(cdb, count * 2048);
    }

    public string Probe(long lba)
    {
        try
        {
            byte[] b = ReadBlocks(lba, 1);
            bool zero = true;
            for (int i = 0; i < b.Length; i++) if (b[i] != 0) { zero = false; break; }
            string id = b.Length >= 6 ? Encoding.ASCII.GetString(b, 1, 5) : "";
            return "block " + lba + ": read OK" + (zero ? " (all zeros)" : "") +
                   ((id == "CD001" || id == "BEA01" || id == "NSR02" || id == "NSR03") ? " [" + id + "]" : "");
        }
        catch (Exception e) { return "block " + lba + ": FAILED - " + e.Message; }
    }

    public void StartAt(long sector) { basePos = sector * 2048; pos = 0; }

    public void Read(byte[] pv, int cb, IntPtr pcbRead)
    {
        int n = 0;
        try
        {
            int count = Math.Min(cb / 2048, 16);
            if (count > 0)
            {
                byte[] b = ReadBlocks((basePos + pos) / 2048, count);
                n = Math.Min(b.Length, cb);
                Array.Copy(b, pv, n);
                pos += n;
            }
        }
        catch (Exception e) { LastReadError = e.Message; n = 0; }
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

    $disc = New-Object ScsiDisc $letter
    try {
        Write-Host "Reading via:  $($disc.OpenedAs)  (drive's own read commands only)"
        Write-Host "Drive says:   $($disc.DiscInfo())"
        $track2Start = $null
        for ($t = 1; $t -le [math]::Min($disc.LastTrack(), 10); $t++) {
            try {
                Write-Host "  $($disc.DescribeTrack($t))"
                if ($t -eq 2) { $track2Start = $disc.TrackStart(2) }
            } catch { Write-Host "  track ${t}: could not read info - $($_.Exception.Message)" }
        }
        Write-Host ''
        Write-Host 'Read test:'
        foreach ($b in @(16, 256, 93000, 93951, 93952, 93968, 93969)) { Write-Host "  $($disc.Probe($b))" }
        Write-Host ''

        $expected = 93952   # where the burn tool wrote the new section
        $starts = @($expected)
        if ($track2Start -and $track2Start -ne $expected -and $track2Start -lt 2400000) { $starts += $track2Start }
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
                if ($disc.LastReadError) { $m += " (drive: $($disc.LastReadError))" }
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
