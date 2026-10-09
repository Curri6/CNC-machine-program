public class FileIStream : IStream {
    FileStream fs;
    public FileIStream(string path) { fs = File.OpenRead(path); }
    public void Read(byte[] pv, int cb, IntPtr pcbRead) { int n = fs.Read(pv, 0, cb); if (pcbRead != IntPtr.Zero) Marshal.WriteInt32(pcbRead, n); }
    public void Seek(long dlibMove, int dwOrigin, IntPtr plibNewPosition) { fs.Seek(dlibMove, (SeekOrigin)dwOrigin); }
    public void Write(byte[] pv, int cb, IntPtr pcbWritten) { throw new NotImplementedException(); }
    public void SetSize(long libNewSize) { throw new NotImplementedException(); }
    public void CopyTo(IStream pstm, long cb, IntPtr pcbRead, IntPtr pcbWritten) { throw new NotImplementedException(); }
    public void Commit(int grfCommitFlags) { }
    public void Revert() { }
    public void LockRegion(long a, long b, int c) { }
    public void UnlockRegion(long a, long b, int c) { }
    public void Stat(out System.Runtime.InteropServices.ComTypes.STATSTG s, int f) { s = new System.Runtime.InteropServices.ComTypes.STATSTG(); }
    public void Clone(out IStream ppstm) { throw new NotImplementedException(); }
}
