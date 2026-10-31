#!/usr/bin/env python3
# blessing_duration.py - makes Jones' (22198) and O'Malley's (28524) Blessing TIMED in an Event Boutique shop file.
# Works on the client file (gshop1.data) or the server file (gshopsev1.data).
# NEVER edits the input: it writes a NEW file. Refuses unless everything is exactly where expected.
# Usage: python blessing_duration.py <input shop file> <output shop file> [seconds]   (default 604800 = 7 days)
import struct, sys, hashlib, os

if len(sys.argv) < 3:
    sys.exit('usage: python blessing_duration.py <in> <out> [seconds]')
src, dst = sys.argv[1], sys.argv[2]
secs = int(sys.argv[3]) if len(sys.argv) > 3 else 604800
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
IDS = (22198, 28524)

d = bytearray(open(src, 'rb').read())
N = len(d)
stamp, n = struct.unpack_from('<II', d, 0)
if N - 8 == n * 232:
    kind, R, ITEM = 'server (gshopsev1)', 232, 12
elif N - 8 >= n * 1448 and (N - 8 - n * 1448) < 4096:
    kind, R, ITEM = 'client (gshop1)', 1448, 140
else:
    sys.exit('file size %d does not fit a 232-byte server or 1448-byte client shop with %d items - nothing done' % (N, n))
SLOT0 = ITEM + 8 if kind.startswith('client') else 20   # first price slot: client item+8 (=148), server 20
print('file kind:', kind, '| items:', n, '| record size:', R, '| stamp:', hex(stamp))

done = 0
for i in range(n):
    o = 8 + i * R
    iid = struct.unpack_from('<I', d, o + ITEM)[0]
    if iid in IDS:
        price, a, dur = struct.unpack_from('<3i', d, o + SLOT0)
        print('record %d item %d: price %d duration %d' % (i, iid, price, dur))
        if dur != 0:
            sys.exit('duration is already %d on item %d - nothing done' % (dur, iid))
        struct.pack_into('<i', d, o + SLOT0 + 8, secs)
        done += 1
if done != len(IDS):
    sys.exit('found %d of %d blessing records - nothing done' % (done, len(IDS)))
open(dst, 'wb').write(d)
print('wrote', dst, '| %d items changed to %d seconds' % (done, secs))
print('md5 in :', hashlib.md5(open(src, 'rb').read()).hexdigest())
print('md5 out:', hashlib.md5(open(dst, 'rb').read()).hexdigest())
