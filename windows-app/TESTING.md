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

11. [ ] Get the two test squares (0.5 in each): open these and press Ctrl+S
        on each, then drag both saved files into the app.
        https://raw.githubusercontent.com/Curri6/CNC-machine-program/main/tools/jobs/SQUARE1.TAP
        (0.25 in above the work, cuts nothing — for a real run later)
        https://raw.githubusercontent.com/Curri6/CNC-machine-program/main/tools/jobs/SQUARE0.TAP
        (at Z0 — for MPS2003's Plot Preview only)
12. [ ] The preview shows a square for each, and Checks say SQUARE1 only
        moves in the air.
13. [ ] **Send to old PC ➜** both, named `SQUARE1.TAP` and `SQUARE0.TAP`.
        They appear under "Waiting for the old PC" on Machine Link.
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
15. [ ] On the old PC: `C:\NETUP\GET SQUARE1.TAP`, then
        `C:\NETUP\GET SQUARE0.TAP`. Each says "Done: C:\MPSPRO\… is ready".
        The app's Activity log shows "Sent to old PC: …". (Photo of both screens.)
16. [ ] **Preview it in MPS2003 (no movement).** Leave the mill's motor power
        OFF for this test, so nothing can move.
        - Start MPS2003 the way you normally do (C:\MPSPRO\MILL).
        - Press 2 (Load Program), type `TAP`, press Enter, press ↓ until
          SQUARE0.TAP is picked, press Enter. The left side says PROGRAM:
          SQUARE0.TAP.
        - Press M (second menu), then P. The words PLOT PREVIEW appear on
          the left.
        - Press M, then 3 (Run Program), then C.
        - It draws a small square and says END OF PROGRAM. (Photo.)
        - Optional: load SQUARE1.TAP the same way and run it. The screen
          stays blank but it still says END OF PROGRAM: MPS2003's Plot
          Preview only draws moves at or below Z0, and SQUARE1 is all above
          the work. (Found by running MPS2003 in an emulator, 2026-10-16.)

## Part D — backup from the old PC

17. [ ] On the old PC: `C:\NETUP\SEND`. Every file scrolls past.
18. [ ] In the app, "Backups from the old PC" shows a new backup with a
        ✓ (checked, 20 files) and a zip. Click **Open backup**. (Photo.)

## Part E — make a job with the app

19. [ ] **⛏ Bits** (top right): the list has T1 1/8 flat end mill, T2 1/16 flat,
        T3 1/8 ball, T4 1/8 drill, T5 60° V-bit. Change them to the bits you
        really have (size, flutes, cutting length). Click each and read
        "What the app will do". (Photo.)
20. [ ] **Settings → Spindle speeds → From pulleys…**: unplug the mill, open the
        belt cover, and for each belt position measure across the motor pulley
        step and the spindle pulley step the belt sits on. Type them in; the
        app works out each speed (motor 3250 RPM, from its label). Use these
        speeds → Save. (Photo of the pulleys.)
21. [ ] **Make G-code** tab: it opens with a sample "Name plate" (text, 2
        holes, a cut-out). Click each step; the right side says which bit,
        the RPM, feed and passes. Try 3D. (Photo.)
22. [ ] Pick step 2 (holes), change "Hole size" to 1/4. It turns red: the
        1/8 drill can't make 1/4 holes. Change the bit to T1 (end mill): it
        goes green and mills them round. Put it back.
23. [ ] **Save to Jobs ➜**: three files appear on the Jobs tab
        (Name plate T5 / T4 / T1). Each shows ✓ in its Checks.
24. [ ] Send **Name plate T5.tap** to the old PC (name NAMEPLT5.TAP), fetch it
        with `C:\NETUP\GET NAMEPLT5.TAP`, and Plot Preview it in MPS2003:
        2, `TAP`, Enter, ↓, Enter, then M, P (PLOT PREVIEW shows on the left),
        M, 3, C. It stops at the first line with the bit and RPM message:
        press C. It draws the letters. (Photo.) Already checked in an emulator
        with the real MPS2003.EXE on 2026-10-15; this checks the real PC.
25. [ ] **Dry run** (the mill moves, cuts only air): Make tab → **Save a dry
        run** → send **Dry Name plate T5.tap** (DRYNAMT5.TAP). Clamp nothing
        under the bit, zero X, Y and Z, spindle OFF. Plot Preview OFF, run it,
        hand near the stop/power switch the whole time. Every move should be
        at least 1/4 in above Z0. (Its Plot Preview stays blank — it's all
        above Z0 — so preview NAMEPLT5.TAP instead, step 24.)
26. [ ] **First real cut** (Phase 0, person present): scrap acrylic, the name
        plate's T5 file only (engraving 0.02 in deep), spindle on at the speed
        it shows. Stop at once if anything sounds or looks wrong.

## If something goes wrong

- Old PC light red → on the old PC run `C:\NETUP\CHECK` (photo).
- "Link could not start" → another program is using the link (close
  `receive_files.bat`), then click **Turn link on**.
- GET says "Not connected" or hangs → photo of the old PC screen and the
  app's Activity log.
