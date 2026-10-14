"""Tests tools/receive_files.ps1 (the laptop FTP receiver) with Python ftplib.

Talks to it the way Windows 95 FTP.EXE does (active mode PORT, XMKD/XPWD),
checks file contents byte-for-byte, unsafe names, and the manifest check.

Run:  python3 -I tools/tests/test_receiver.py /path/to/pwsh
"""
import ftplib, hashlib, io, os, socket, subprocess, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'receive_files.ps1')
PWSH = sys.argv[1] if len(sys.argv) > 1 else 'pwsh'
fails = 0


def check(cond, name):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond:
        fails += 1


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def start(out):
    port = free_port()
    p = subprocess.Popen([PWSH, '-NoProfile', '-File', SCRIPT, '-TestMode', '-ListenIP', '127.0.0.1',
                          '-Port', str(port), '-OutDir', out, '-ExitAfterSession'],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(('127.0.0.1', port), 0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    # that probe connection was a session of its own; the server ends after
    # one session, so start a fresh one for the real test
    p.wait(timeout=30)
    p = subprocess.Popen([PWSH, '-NoProfile', '-File', SCRIPT, '-TestMode', '-ListenIP', '127.0.0.1',
                          '-Port', str(port), '-OutDir', out, '-ExitAfterSession'],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for _ in range(100):
        try:
            f = ftplib.FTP()
            f.connect('127.0.0.1', port, timeout=10)
            return p, f
        except OSError:
            time.sleep(0.2)
    raise RuntimeError('server did not start')


def received_dir(out):
    d = [x for x in os.listdir(out) if x.startswith('received_')]
    d.sort(key=lambda x: os.path.getmtime(os.path.join(out, x)))
    return os.path.join(out, d[-1])


def run_case(files, manifest, extra=None):
    out = tempfile.mkdtemp()
    p, f = start(out)
    f.set_pasv(False)
    f.login('anonymous', 'guest')
    f.voidcmd('TYPE I')
    f.storbinary('STOR MANIFEST.TXT', io.BytesIO(manifest.encode('latin-1')))
    for name, data in files:
        f.storbinary('STOR ' + name, io.BytesIO(data))
    res = extra(f) if extra else None
    f.quit()
    log = p.communicate(timeout=60)[0].decode('latin-1')
    return out, p.returncode, log, res


# --- case 1: normal backup, Win95-style commands, content check ---
blobs = {
    'MPSPRO/BOLTHOLE.TAP': os.urandom(1234),
    'MPSPRO/MILL/MILL.EXE': os.urandom(200000),
    'MPSPRO/MILL/SUB/EMPTY.DAT': b'',
    'MPSPRO/PARAMS.DAT': bytes(range(256)) * 10,   # every byte value, incl. CR/LF/0xFF
}
man = ''.join('%s %d\r\n' % (k, len(v)) for k, v in blobs.items())


def win95_cmds(f):
    r = {}
    r['xmkd'] = f.sendcmd('XMKD MPSPRO/NEWDIR')
    r['xmkd_again'] = None
    try:
        f.sendcmd('XMKD MPSPRO/NEWDIR')
    except ftplib.error_perm as e:
        r['xmkd_again'] = str(e)
    r['xpwd'] = f.sendcmd('XPWD')
    r['cwd'] = f.sendcmd('CWD MPSPRO')
    r['pwd2'] = f.sendcmd('PWD')
    f.storbinary('STOR REL.TXT', io.BytesIO(b'relative'))
    r['cdup'] = f.sendcmd('CDUP')
    r['pwd3'] = f.sendcmd('PWD')
    bad = {}
    for name in ['../../ESCAPE.TXT', '..\\..\\ESCAPE2.TXT', 'C:\\WINDOWS\\EVIL.TXT', 'A/B:C.TXT',
                 'CON', 'AUX.TXT', 'X|Y', 'TRAIL.']:
        try:
            f.storbinary('STOR ' + name, io.BytesIO(b'x'))
            bad[name] = 'stored'
        except ftplib.error_perm as e:
            bad[name] = str(e)[:3]
    r['bad'] = bad
    try:
        f.sendcmd('PORT 10,0,0,9,200,1')
        r['port_other'] = 'accepted'
    except ftplib.error_perm as e:
        r['port_other'] = str(e)[:3]
    try:
        f.sendcmd('SITE CHMOD 777 X')
        r['unknown'] = 'ok'
    except ftplib.error_perm as e:
        r['unknown'] = str(e)[:3]
    return r


out, rc, log, r = run_case(list(blobs.items()), man, win95_cmds)
root = received_dir(out)
for k, v in blobs.items():
    pth = os.path.join(root, *k.split('/'))
    check(os.path.isfile(pth) and open(pth, 'rb').read() == v, 'content identical: ' + k)
check(rc == 0, 'exit code 0 when everything arrived')
check('CHECK PASSED: all 4 files' in log, 'CHECK PASSED reported')
check(r['xmkd'].startswith('257'), 'XMKD creates folder')
check(os.path.isdir(os.path.join(root, 'MPSPRO', 'NEWDIR')), 'XMKD folder exists on disk')
check(r['xmkd_again'] is not None and r['xmkd_again'].startswith('550'), 'XMKD on existing folder -> 550')
check(r['xpwd'] == '257 "/"', 'XPWD at root')
check(r['pwd2'] == '257 "/MPSPRO"', 'CWD then PWD')
check(open(os.path.join(root, 'MPSPRO', 'REL.TXT'), 'rb').read() == b'relative', 'relative STOR after CWD')
check(r['pwd3'] == '257 "/"', 'CDUP back to root')
# '..' can never climb above the backup folder: it lands inside it
check(not os.path.exists(os.path.join(out, 'ESCAPE.TXT')) and
      not os.path.exists(os.path.join(os.path.dirname(out), 'ESCAPE.TXT')), '../ cannot escape')
check(os.path.isfile(os.path.join(root, 'ESCAPE.TXT')), '../ name lands inside backup folder')
check(os.path.isfile(os.path.join(root, 'ESCAPE2.TXT')), '..\\ name lands inside backup folder')
check(os.path.isfile(os.path.join(root, 'WINDOWS', 'EVIL.TXT')), 'drive letter path lands inside backup folder')
for name in ['A/B:C.TXT', 'CON', 'AUX.TXT', 'X|Y', 'TRAIL.']:
    check(r['bad'][name] == '553', 'refused unsafe name ' + name)
check(r['port_other'] == '504', 'PORT to another computer refused')
check(r['unknown'] == '502', 'unknown command -> 502')
z = [x for x in os.listdir(out) if x.endswith('.zip')]
check(len(z) == 1, 'zip made')
if z:
    with zipfile.ZipFile(os.path.join(out, z[0])) as zf:
        names = set(n.replace('\\', '/') for n in zf.namelist())
        check('MPSPRO/MILL/MILL.EXE' in names and zf.read([n for n in zf.namelist() if n.replace('\\', '/') == 'MPSPRO/MILL/MILL.EXE'][0]) == blobs['MPSPRO/MILL/MILL.EXE'],
              'zip holds the right content')

# --- case 2: a file missing and one with the wrong size ---
man2 = man + 'MPSPRO/NOTSENT.TAP 55\r\n'
files2 = [(k, v) for k, v in blobs.items() if k != 'MPSPRO/PARAMS.DAT'] + [('MPSPRO/PARAMS.DAT', b'short')]
out2, rc2, log2, _ = run_case(files2, man2)
check(rc2 != 0, 'exit code not 0 when files are missing')
check('MISSING: MPSPRO/NOTSENT.TAP' in log2, 'missing file reported')
check('WRONG SIZE: MPSPRO/PARAMS.DAT' in log2, 'wrong size reported')
check('CHECK FAILED' in log2, 'CHECK FAILED reported')
check(not [x for x in os.listdir(out2) if x.endswith('.zip')], 'no zip when the check fails')

# --- case 3: the old PC fetches a job from the to_old_pc folder ---
out3 = tempfile.mkdtemp()
box = os.path.join(out3, 'to_old_pc'); os.makedirs(box)
open(os.path.join(box, 'JOB1.TAP'), 'wb').write(b'G00 Z0.25\nG01 X0.5 F10\nM02\n')   # LF only
blob = os.urandom(5000)
open(os.path.join(box, 'DATA.BIN'), 'wb').write(blob)
open(os.path.join(out3, 'SECRET.TXT'), 'wb').write(b'not in the outbox')
p3, f3 = start(out3)
f3.set_pasv(False)
f3.login('anonymous', 'guest')
f3.voidcmd('TYPE I')
got = io.BytesIO(); f3.retrbinary('RETR JOB1.TAP', got.write)
check(got.getvalue() == b'G00 Z0.25\r\nG01 X0.5 F10\r\nM02\r\n', 'job sent with DOS CRLF line endings')
got = io.BytesIO(); f3.retrbinary('RETR job1.tap', got.write)
check(got.getvalue().startswith(b'G00 Z0.25\r\n'), 'name match ignores upper/lower case')
got = io.BytesIO(); f3.retrbinary('RETR DATA.BIN', got.write)
check(got.getvalue() == blob, 'non-job file sent byte-for-byte')
names = f3.nlst()
check(sorted(names) == ['DATA.BIN', 'JOB1.TAP'], 'NLST lists the to_old_pc folder: %r' % names)
lines = []; f3.retrlines('LIST', lines.append)
check(len(lines) == 2 and lines[1].endswith('JOB1.TAP') and ' 30 ' in lines[1], 'LIST shows names and sent sizes: %r' % lines)
for bad in ['SECRET.TXT', '../SECRET.TXT', '..\\SECRET.TXT', 'C:\\SECRET.TXT', 'NOPE.TAP', '..']:
    try:
        f3.retrbinary('RETR ' + bad, io.BytesIO().write)
        r = 'sent'
    except ftplib.error_perm as e:
        r = str(e)[:3]
    check(r == '550', 'refused outside/missing file %r' % bad)
f3.quit()
log3 = p3.communicate(timeout=60)[0].decode('latin-1')
check('SENT to old PC: JOB1.TAP' in log3, 'laptop window shows what was sent')
check('JOB1.TAP  27 bytes' in log3, 'outbox listed at start')
check(not os.path.exists(os.path.join(box, 'JOB1.TAP.part')), 'outbox left untouched')

print('ALL PASS' if fails == 0 else '%d FAILED' % fails)
sys.exit(1 if fails else 0)
