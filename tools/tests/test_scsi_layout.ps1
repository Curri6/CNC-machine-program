# Checks the SCSI_PASS_THROUGH field offsets that verify_win95_disc.ps1
# writes by hand against .NET's own layout of the struct (64-bit).
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
[StructLayout(LayoutKind.Sequential)]
public struct SCSI_PASS_THROUGH {
    public ushort Length; public byte ScsiStatus, PathId, TargetId, Lun, CdbLength, SenseInfoLength, DataIn;
    public uint DataTransferLength; public uint TimeOutValue; public UIntPtr DataBufferOffset; public uint SenseInfoOffset;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)] public byte[] Cdb;
}
"@
$t = [SCSI_PASS_THROUGH]
"pointer size: $([IntPtr]::Size) bytes"
"sizeof          = $([Runtime.InteropServices.Marshal]::SizeOf($t))   (script uses 56)"
foreach ($f in 'ScsiStatus','CdbLength','SenseInfoLength','DataIn','DataTransferLength','TimeOutValue','DataBufferOffset','SenseInfoOffset','Cdb') {
  "{0,-18} @ {1}" -f $f, [Runtime.InteropServices.Marshal]::OffsetOf($t, $f)
}
"(script writes: ScsiStatus 2, CdbLength 6, SenseInfoLength 7, DataIn 8, DataTransferLength 12, TimeOut 16, DataBufferOffset 24, SenseInfoOffset 32, Cdb 36)"
