# Testing the A-Tech CNC app (by hand)

Take a photo of anything that doesn't match. The automated tests run on
every push (see README → Tests); this list covers what only a person can
check: the real laptop, the real cable and the real old PC.

**Safety:** the mill stays switched off for all of this. Nothing here
moves the machine. A person is present at the old PC the whole time.

## Part A — laptop only (no cable needed)

1. [ ] Download https://github.com/Curri6/CNC-machine-program/releases/latest/download/ATechCNC.exe
       and double-click it. If "Windows protected your PC" appears, click
       **More info → Run anyway**. If the firewall asks, click **Allow**.
2. [ ] Drag Tuesday's backup folder into the window:
       `Downloads\CNC_backup\received_…\MPSPRO`. The real jobs (KNIGHT.TAP,
       GEAR.TAP, …) appear in the list on the left.
3. [ ] Click **KNIGHT.TAP**. The preview draws it. Try:
       - **Top / Front / Side / 3D** buttons
       - mouse wheel = zoom, drag = move, double-click = fit
       - **Rapids** off and on (dashed lines = moves in the air)
4. [ ] Click **▶ Play**. The tool moves through the job and the G-code line
       on the right lights up as it goes. Drag the slider back and forth.
5. [ ] Click a line in the drawing. The G-code list jumps to that line.
6. [ ] Look at **Summary** (size, deepest cut, time) and **Checks**. Do the
       numbers look right for the knight? (Photo.)
7. [ ] **⚙ Settings**: change "Warn if deeper than" to 0.01 in, Save. The
       knight now shows a depth warning. Put it back: Settings →
       **Restore Defaults** → **Save**.
8. [ ] **? Help**: click through every section.
9. [ ] Close the app and open it again. The jobs are still in the list.

## Part B — the cable

Close any old `receive_files.bat` window first (only one program can use
the link at a time). Cable plugged in, old PC on and at the Windows desktop.

10. [ ] **Machine Link** tab. Lights:
        - Laptop address 192.168.50.1: green. If red, click
          **Set up network…** and say Yes to the admin question.
        - Old PC answers: green within a few seconds.
        - Link: on.
        (Photo of the three lights.)

## Part C — send a job to the old PC

11. [ ] Get SQUARE1.TAP (a 0.5 in square in the air, Z+0.25, cuts nothing):
        open https://raw.githubusercontent.com/Curri6/CNC-machine-program/main/tools/jobs/SQUARE1.TAP
        and press Ctrl+S. Drag the saved file into the app.
12. [ ] The preview shows a square, and Checks say it only moves in the air.
13. [ ] **Send to old PC ➜**. Make the name `SQUARE1.TAP`, click OK. It
        appears under "Waiting for the old PC" on Machine Link.
14. [ ] **First time only**, on the old PC, open an MS-DOS Prompt and type:
        ```
        ftp 192.168.50.1
        ```
        user `anonymous`, password `x`, then
        ```
        lcd C:\NETUP
        get GET.BAT
        quit
        ```
15. [ ] On the old PC: `C:\NETUP\GET SQUARE1.TAP`. It says
        "Done: C:\MPSPRO\SQUARE1.TAP is ready". The app's Activity log shows "Sent to old PC: SQUARE1.TAP".
        (Photo of both screens.)
16. [ ] On the old PC: open SQUARE1.TAP in MPS2003 and press **P** (Plot
        Preview). It draws a square. **Do not run it.** (Photo.)

## Part D — backup from the old PC

17. [ ] On the old PC: `C:\NETUP\SEND`. Every file scrolls past.
18. [ ] In the app, "Backups from the old PC" shows a new backup with a
        ✓ (checked, 20 files) and a zip. Click **Open backup**. (Photo.)

## Part E — make a job with the app

19. [ ] **⛏ Bits** (top right): the list has T1 1/8 flat end mill, T2 1/16 flat,
        T3 1/8 ball, T4 1/8 drill, T5 60° V-bit. Change them to the bits you
        really have (size, flutes, cutting length). Click each and read
        "What the app will do". (Photo.)
20. [ ] **Settings → Spindle speeds**: type the speeds your spindle can be set
        to (look on the mill's belt guard or manual). Save.
21. [ ] **Make G-code** tab: it opens with a sample "Name plate" (text, 2
        holes, a cut-out). Click each step; the right side says which bit,
        the RPM, feed and passes. Try 3D. (Photo.)
22. [ ] Pick step 2 (holes), change "Hole size" to 1/4. It turns red: the
        1/8 drill can't make 1/4 holes. Change the bit to T1 (end mill): it
        goes green and mills them round. Put it back.
23. [ ] **Save to Jobs ➜**: three files appear on the Jobs tab
        (Name plate T5 / T4 / T1). Each shows ✓ in its Checks.
24. [ ] Send **Name plate T5.tap** to the old PC (name NAMEPLT5.TAP), fetch it
        with `C:\NETUP\GET NAMEPLT5.TAP`, and Plot Preview (P) it in MPS2003.
        **Do not run it.** Does MPS2003 accept every line? (Photo.)

## If something goes wrong

- Old PC light red → on the old PC run `C:\NETUP\CHECK` (photo).
- "Link could not start" → another program is using the link (close
  `receive_files.bat`), then click **Turn link on**.
- GET says "Not connected" or hangs → photo of the old PC screen and the
  app's Activity log.
