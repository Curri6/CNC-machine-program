; MKFTP.COM - write an FTP upload script for a whole folder tree.
;
; Windows 95's FTP.EXE cannot upload subfolders by itself.  This walks a
; folder and writes two files in the current directory:
;
;   BODY.FTP      "mkdir" / "put" lines for FTP.EXE -s:  (one per folder/file)
;   MANIFEST.TXT  "remote/path size" for every file, so the laptop can check
;                 that everything arrived with the right size.
;
; Usage:  MKFTP C:\MPSPRO
;   Remote names are MPSPRO/..., using forward slashes.
;
; Exit codes: 0 ok, 1 bad usage / folder not found, 2 cannot write output,
;             4 finished but some paths were too long and were skipped.
;
; Build:  nasm -f bin -o MKFTP.COM MKFTP.ASM

        cpu     386
        org     100h

MAXDEPTH equ    20
DTASIZE  equ    48
MAXPATH  equ    200             ; longest local path we will build

start:
        cld
        ; --- read the first word of the command tail into lpath ---
        movzx   bx, byte [80h]
        mov     byte [81h+bx], 0
        mov     si, 81h
.skip:  lodsb
        cmp     al, ' '
        je      .skip
        cmp     al, 9
        je      .skip
        dec     si
        mov     di, lpath
.copy:  lodsb
        cmp     al, ' '
        jbe     .copied         ; space, tab, CR or 0 ends the word
        cmp     di, lpath+MAXPATH
        jae     usage
        stosb
        jmp     .copy
.copied:
        mov     ax, di
        sub     ax, lpath
        ; strip trailing backslashes
.strip: or      ax, ax
        jz      usage
        mov     bx, ax
        cmp     byte [lpath+bx-1], '\'
        jne     .stripped
        dec     ax
        jmp     .strip
.stripped:
        mov     [llen], ax
        ; remote prefix = text after the last '\' or ':'
        mov     bx, ax
.back:  or      bx, bx
        jz      .found
        mov     al, [lpath+bx-1]
        cmp     al, '\'
        je      .found
        cmp     al, ':'
        je      .found
        dec     bx
        jmp     .back
.found: lea     si, [lpath+bx]
        mov     cx, [llen]
        sub     cx, bx
        jz      usage
        mov     [rlen], cx
        mov     di, rpath
        rep     movsb

        ; --- create the two output files ---
        mov     dx, fn_body
        call    create
        mov     [h_body], ax
        mov     dx, fn_man
        call    create
        mov     [h_man], ax

        ; "mkdir PREFIX"
        call    emit_mkdir

        mov     byte [depth], 0
        call    walk

        mov     bx, [h_body]
        mov     ah, 3Eh
        int     21h
        mov     bx, [h_man]
        mov     ah, 3Eh
        int     21h

        cmp     byte [notfound], 0
        je      .report
        mov     si, msg_nf
        call    print_z
        mov     si, lpath
        mov     cx, [llen]
        call    print_n
        call    print_crlf
        mov     al, 1
        jmp     exit

.report:
        ; "MKFTP: N files in M folders, B bytes."
        mov     si, msg_sum1
        call    print_z
        mov     eax, [nfiles]
        call    print_dec
        mov     si, msg_sum2
        call    print_z
        mov     eax, [ndirs]
        call    print_dec
        mov     si, msg_sum3
        call    print_z
        mov     eax, [nbytes]
        call    print_dec
        mov     si, msg_sum4
        call    print_z
        mov     al, [errcode]
        cmp     al, 0
        jne     exit
        cmp     dword [nskip], 0
        je      exit
        mov     al, 4
exit:   mov     ah, 4Ch
        int     21h

usage:  mov     si, msg_usage
        call    print_z
        mov     al, 1
        jmp     exit

; create file named at DX, return handle in AX; exit 2 on failure
create: xor     cx, cx
        mov     ah, 3Ch
        int     21h
        jc      .fail
        ret
.fail:  mov     si, msg_create
        call    print_z
        mov     si, dx
        call    print_z
        call    print_crlf
        mov     al, 2
        jmp     exit

; ---------------------------------------------------------------------------
; walk: list lpath[0..llen) and recurse into subfolders.
; Each depth level has its own DTA so FindNext state survives recursion.
walk:
        push    bp
        movzx   ax, byte [depth]
        mov     cx, DTASIZE
        mul     cx
        add     ax, dtas
        mov     bp, ax
        mov     dx, bp
        mov     ah, 1Ah                 ; set DTA
        int     21h

        ; lpath + "\*.*"
        mov     di, lpath
        add     di, [llen]
        mov     si, s_star
        mov     cx, 5
        rep     movsb
        mov     dx, lpath
        mov     cx, 37h                 ; read-only, hidden, system, dir, archive
        mov     ah, 4Eh
        int     21h
        jnc     .entry
        ; A real folder always lists "." first, so any failure here means
        ; DOS could not read it (path too long, bad disk...).  Never skip
        ; silently.
        cmp     byte [depth], 0
        jne     .unreadable
        mov     byte [notfound], 1
        jmp     .done
.unreadable:
        inc     dword [nskip]
        mov     si, msg_unread
        call    print_z
        mov     si, lpath
        mov     cx, [llen]
        call    print_n
        call    print_crlf
        jmp     .done

.entry:
        cmp     byte [bp+1Eh], '.'      ; "." and ".."
        je      .next
        test    byte [bp+15h], 08h      ; volume label
        jnz     .next
        ; name length
        lea     si, [bp+1Eh]
        call    strlen                  ; CX = length
        mov     [nlen], cx
        ; room for "\name" plus "\*.*" in lpath?
        mov     ax, [llen]
        add     ax, cx
        add     ax, 6
        cmp     ax, MAXPATH
        jb      .fits
        inc     dword [nskip]
        mov     si, msg_long
        call    print_z
        mov     si, lpath
        mov     cx, [llen]
        call    print_n
        mov     si, s_bslash
        mov     cx, 1
        call    print_n
        lea     si, [bp+1Eh]
        call    print_z
        call    print_crlf
        jmp     .next
.fits:
        test    byte [bp+15h], 10h
        jnz     .dir

        ; ---- a file ----
        call    emit_put
        inc     dword [nfiles]
        mov     eax, [bp+1Ah]
        add     [nbytes], eax
        jmp     .next

.dir:   ; ---- a subfolder ----
        push    word [llen]
        push    word [rlen]
        call    append_name
        call    emit_mkdir
        inc     dword [ndirs]
        cmp     byte [depth], MAXDEPTH-1
        jb      .recurse
        inc     dword [nskip]
        mov     si, msg_deep
        call    print_z
        mov     si, lpath
        mov     cx, [llen]
        call    print_n
        call    print_crlf
        jmp     .back
.recurse:
        inc     byte [depth]
        call    walk
        dec     byte [depth]
.back:  pop     word [rlen]
        pop     word [llen]
        mov     dx, bp                  ; child changed the DTA; restore ours
        mov     ah, 1Ah
        int     21h

.next:  mov     ah, 4Fh
        int     21h
        jnc     .entry
.done:  pop     bp
        ret

; append "\name" to lpath and "/name" to rpath (name at bp+1Eh, nlen)
append_name:
        mov     di, lpath
        add     di, [llen]
        mov     al, '\'
        stosb
        lea     si, [bp+1Eh]
        mov     cx, [nlen]
        rep     movsb
        mov     di, rpath
        add     di, [rlen]
        mov     al, '/'
        stosb
        lea     si, [bp+1Eh]
        mov     cx, [nlen]
        rep     movsb
        mov     ax, [nlen]
        inc     ax
        add     [llen], ax
        add     [rlen], ax
        ret

; body line: "mkdir <rpath>"
emit_mkdir:
        mov     di, linebuf
        mov     si, s_mkdir
        call    cat_z
        mov     si, rpath
        mov     cx, [rlen]
        rep     movsb
        call    cat_crlf
        mov     bx, [h_body]
        jmp     write_line

; body line: "put <lpath>\name <rpath>/name"
; manifest line: "<rpath>/name <size>"
emit_put:
        mov     di, linebuf
        mov     si, s_put
        call    cat_z
        mov     si, lpath
        mov     cx, [llen]
        rep     movsb
        mov     al, '\'
        stosb
        lea     si, [bp+1Eh]
        mov     cx, [nlen]
        rep     movsb
        mov     al, ' '
        stosb
        call    cat_remote
        call    cat_crlf
        mov     bx, [h_body]
        call    write_line

        mov     di, linebuf
        call    cat_remote
        mov     al, ' '
        stosb
        mov     eax, [bp+1Ah]
        call    cat_dec
        call    cat_crlf
        mov     bx, [h_man]
        jmp     write_line

cat_remote:
        mov     si, rpath
        mov     cx, [rlen]
        rep     movsb
        mov     al, '/'
        stosb
        lea     si, [bp+1Eh]
        mov     cx, [nlen]
        rep     movsb
        ret

cat_crlf:
        mov     ax, 0A0Dh
        stosw
        ret

; copy ASCIIZ at SI to DI (without the 0)
cat_z:  lodsb
        or      al, al
        jz      .e
        stosb
        jmp     cat_z
.e:     ret

; append EAX in decimal at DI
cat_dec:
        push    si
        mov     si, numbuf+11
        mov     ebx, 10
.d:     xor     edx, edx
        div     ebx
        add     dl, '0'
        dec     si
        mov     [si], dl
        or      eax, eax
        jnz     .d
.c:     cmp     si, numbuf+11
        je      .x
        movsb
        jmp     .c
.x:     pop     si
        ret

; write linebuf..DI to handle BX
write_line:
        mov     cx, di
        mov     dx, linebuf
        sub     cx, dx
        mov     ah, 40h
        push    cx
        int     21h
        pop     cx
        jc      .bad
        cmp     ax, cx
        je      .ok
.bad:   mov     byte [errcode], 2
.ok:    ret

; CX = length of ASCIIZ at SI
strlen: push    si
        xor     cx, cx
.l:     lodsb
        or      al, al
        jz      .e
        inc     cx
        jmp     .l
.e:     pop     si
        ret

; --- console output ---
print_z:
        push    si
        call    strlen
        call    print_n
        pop     si
        ret
print_n:                        ; SI, CX
        mov     dx, si
        mov     bx, 1
        mov     ah, 40h
        int     21h
        ret
print_crlf:
        mov     si, s_crlf
        mov     cx, 2
        jmp     print_n
print_dec:                      ; EAX
        mov     di, numout
        call    cat_dec
        mov     cx, di
        mov     si, numout
        sub     cx, si
        jmp     print_n

; ---------------------------------------------------------------------------
fn_body   db 'BODY.FTP', 0
fn_man    db 'MANIFEST.TXT', 0
s_star    db '\*.*', 0
s_bslash  db '\'
s_mkdir   db 'mkdir ', 0
s_put     db 'put ', 0
s_crlf    db 13, 10
msg_usage db 'Usage: MKFTP C:\FOLDER', 13, 10
          db 'Writes BODY.FTP and MANIFEST.TXT in the current directory.', 13, 10, 0
msg_create db 'MKFTP: cannot create ', 0
msg_nf    db 'MKFTP: folder not found: ', 0
msg_long  db 'MKFTP: SKIPPED, path too long: ', 0
msg_unread db 'MKFTP: SKIPPED, cannot read folder: ', 0
msg_deep  db 'MKFTP: SKIPPED, folders nested too deep below: ', 0
msg_sum1  db 'MKFTP: ', 0
msg_sum2  db ' files in ', 0
msg_sum3  db ' subfolders, ', 0
msg_sum4  db ' bytes.', 13, 10, 0

depth     db 0
notfound  db 0
errcode   db 0
          align 4
nfiles    dd 0
ndirs     dd 0
nbytes    dd 0
nskip     dd 0
llen      dw 0
rlen      dw 0
nlen      dw 0
h_body    dw 0
h_man     dw 0

section .bss
numbuf    resb 12
numout    resb 12
lpath     resb MAXPATH+16
rpath     resb MAXPATH+16
linebuf   resb 2*MAXPATH+64
dtas      resb MAXDEPTH*DTASIZE
