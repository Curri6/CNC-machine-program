import struct, sys
from PIL import Image
d = open(sys.argv[1], 'rb').read()
f = struct.unpack('>25I', d[:100])
hsize, w, h, bpp, bpl, ncol = f[0], f[4], f[5], f[11], f[12], f[19]
off = hsize + ncol * 12
mode = 'BGRX' if bpl >= w * 4 and bpp != 24 else 'BGR'
img = Image.frombuffer('RGB', (w, h), d[off:off + bpl * h], 'raw', mode, bpl, 1)
if len(sys.argv) > 3:
    img = img.crop(tuple(int(v) for v in sys.argv[3].split(',')))
img.save(sys.argv[2])
