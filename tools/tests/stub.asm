; Stand-in DOS program for batch-file tests: appends "TAG args" to C:\LOG.TXT
; and exits with EXITCODE.  nasm -f bin -DTAG='"FTP"' -DEXITCODE=0 -o FTP.COM stub.asm
        org     100h
%ifndef EXITCODE
%define EXITCODE 0
%endif
        mov     dx, logname
        mov     ax, 3D01h               ; open for write
        int     21h
        jnc     .opened
        mov     ah, 3Ch
        xor     cx, cx
        mov     dx, logname
        int     21h
        jc      .quit
.opened:
        mov     bx, ax
        mov     ax, 4202h               ; seek to end
        xor     cx, cx
        xor     dx, dx
        int     21h
        mov     ah, 40h
        mov     cx, taglen
        mov     dx, tag
        int     21h
        mov     ah, 40h
        xor     ch, ch
        mov     cl, [80h]
        mov     dx, 81h
        int     21h
        mov     ah, 40h
        mov     cx, 2
        mov     dx, crlf
        int     21h
        mov     ah, 3Eh
        int     21h
.quit:  mov     ax, 4C00h + EXITCODE
        int     21h
logname db 'C:\LOG.TXT', 0
tag     db TAG
taglen  equ $ - tag
crlf    db 13, 10
