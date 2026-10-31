#!/usr/bin/env python3
# shop_set_duration.py - sets the shop DURATION (seconds, 0 = permanent) of one or more items in an Event Boutique file.
# Works on the client file (gshop1.data) or the server file (gshopsev1.data). Writes a NEW file; never edits the input.
# Usage: python shop_set_duration.py <in> <out> <seconds> <item id> [<item id> ...]      e.g.  ... 0 28297 28523
import struct, sys, hashlib, os
if len(sys.argv) < 5:
    sys.exit('usage: python shop_set_duration.py <in> <out> <seconds> <item id> [<item id> ...]')
src, dst, secs = sys.argv[1], sys.argv[2], int(sys.argv[3])
ids = [int(x) for x in sys.argv[4:]]
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
d = bytearray(open(src, 'rb').read()); N = len(d)
stamp, n = struct.unpack_from('<II', d, 0)
if N - 8 == n * 232:
    kind, R, ITEM, SLOT0 = 'server (gshopsev1)', 232, 12, 20
elif N - 8 >= n * 1448 and (N - 8 - n * 1448) < 4096:
    kind, R, ITEM, SLOT0 = 'client (gshop1)', 1448, 140, 148
else:
    sys.exit('file size %d does not fit a 232-byte server or 1448-byte client shop with %d items - nothing done' % (N, n))
print('file kind:', kind, '| items:', n)
for iid in ids:
    hits = [i for i in range(n) if struct.unpack_from('<I', d, 8 + i * R + ITEM)[0] == iid]
    if len(hits) != 1:
        sys.exit('expected exactly one record selling item %d, found %d - nothing done' % (iid, len(hits)))
    o = 8 + hits[0] * R + SLOT0
    price, a, dur = struct.unpack_from('<3i', d, o)
    struct.pack_into('<i', d, o + 8, secs)
    print('record %d item %d: price %d, duration %d -> %d' % (hits[0], iid, price, dur, secs))
open(dst, 'wb').write(d)
print('wrote', dst, '| md5 out:', hashlib.md5(d).hexdigest())
