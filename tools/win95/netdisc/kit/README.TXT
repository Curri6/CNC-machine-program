NETWORK KIT FOR THE OLD WINDOWS 95 PC (IBM NetVista A40)
=========================================================

Goal: send C:\MPSPRO to the laptop over a network cable.

Why this kit: the Windows 95 driver for this network chip (Intel 82801BA
"PRO/100 VE", PCI 8086:2449) will not start (Code 10). Intel's DOS ODI
driver E100BODI.COM does support this chip. Windows 95 can use a DOS ODI
driver through its "Existing ODI Driver" adapter plus ODIHLP.EXE.

Steps (each one ends with a photo):
 1. Inside Windows, MS-DOS Prompt:  H:   then  COPYNET
      copies this kit to C:\NETUP (nothing else is changed)
 2. Restart in MS-DOS mode, type  C:\NETUP\TEST
      loads the driver once to see if it finds the card; type EXIT after
 3. Still in MS-DOS mode:  C:\NETUP\INSTALL
      adds one line to the top of C:\AUTOEXEC.BAT (old copy kept)
 4. Windows Network settings: add "Existing ODI Driver", set TCP/IP
    to 192.168.50.2 / 255.255.255.0, restart; then  C:\NETUP\CHECK
 5. Laptop: receive_files.bat.  Old PC:  C:\NETUP\SEND

Undo: C:\NETUP\UNDO puts C:\AUTOEXEC.BAT back. At start-up you can also
press N when asked "Load the network driver?" to skip it once.
If Windows will not start: press F8 at "Starting Windows 95", choose
"Safe mode command prompt only", then type  C:\NETUP\UNDO

Files:
 COPYNET.BAT  copy the kit to C:\NETUP; find ODIHLP.EXE / FTP.EXE in the
              Windows 95 CAB files in C:\NETSETUP\WIN95
 TEST.BAT     one-time driver test (MS-DOS mode). TEST OLD = older driver
 INSTALL.BAT  add  @call C:\NETUP\LOADODI.BAT  to the top of AUTOEXEC.BAT
 LOADODI.BAT  loads LSL.COM, E100BODI.COM and ODIHLP.EXE at start-up
 UNDO.BAT     remove it again
 CHECK.BAT    show the set-up for a photo (changes nothing)
 SEND.BAT     send C:\MPSPRO (uses MKFTP.COM and Windows' FTP.EXE)
 MKFTP.COM    makes the FTP list of every file and a MANIFEST.TXT of sizes
 ODI\         LSL.COM (Novell v2.20), E100BODI.COM (Intel v4.13, 2004),
              NET.CFG; ODI\OLD\E100BODI.COM = Intel v4.01 (2001)
 NDIS2\       Intel E100B.DOS v4.59 (spare driver type, not used yet)
 EXTRA\MTCP\  mTCP DOS network programs (need a packet driver, not used)

Source and notes: github.com/Curri6/CNC-machine-program (tools/win95)
