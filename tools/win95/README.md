# WIN95ICH.INF: Win95-only driver INF for the NetVista's on-board NIC

The on-board LAN on the IBM NetVista A40 (type 6578) is Intel ICH2
`PCI\VEN_8086&DEV_2449` (PRO/100 VE). Intel's PRO/100 6.1.3 package
(`NET55A9X.INF`, 2002-02-25) matches that chip, but for it:

- the NDIS3 (Windows 95) copy list `[E100B.ndis3.CopyFiles]` is **empty**,
- it registers `DeviceVxDs = e100bnt5.sys` (NDIS5, Win98SE/ME/2000) and
  the NDI helper `8255indi.dll,i557NdiProc`, plus a Win98 ACPI
  wake-on-LAN static VxD (`WOL558.vxd`).

On this Windows 95 the install hung every time at the point where Windows
runs that helper and loads the driver (four freezes, 2026-10-12).

The package's Windows 95 driver, `E100B.SYS` (NDIS3, version 6.01.03),
**does support this chip**: it contains `cmp eax, 24498086h` and
`cmp ecx, 24498086h` (VEN_8086/DEV_2449), next to the checks for
1031/1032 (the other ICH LAN IDs).

`WIN95ICH.INF` installs just `E100B.SYS` as a standard Win95 NDIS3
adapter (`*ndis` loader, ndis3 upper / ethernet lower), with the two
plain driver values Intel sets for ICH2 (`PcNic=1`, `MWIEnable=0`). It
leaves out the Intel helper DLL, the NDIS5 driver, and the WOL VxD. It
is built from Intel's own INF entries plus the standard Win95 network
INF layout. **Not tested on real Windows 95**; there's no Win95 here.

Use: put it in its own folder with a copy of `E100B.SYS` (e.g.
`C:\NETSETUP\ICH`) and point Update Driver → Other Locations there.

## Result and next route (2026-10-12)

`WIN95ICH.INF` installs cleanly but `E100B.SYS` stays at Code 10. The next
route is Intel's DOS ODI driver (`E100BODI.COM` v4.13) on Novell
`LSL.COM` v2.20, joined to Windows 95 by `ODIHLP.EXE` and the built-in
"Existing ODI Driver" adapter. The kit for that is in `netdisc/`: the
disc's own `README.TXT` lists the steps, `build_netdisc.sh` assembles
the disc folder, and `../receive_files.bat` is the laptop side.
