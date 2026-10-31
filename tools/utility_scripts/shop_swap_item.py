#!/usr/bin/env python3
# shop_swap_item.py - changes WHICH ITEM one Event Boutique record sells (price, tab and duration stay as they are).
# Works on the client file (gshop1.data) or the server file (gshopsev1.data). Writes a NEW file; never edits the input.
# Usage: python shop_swap_item.py <input shop file> <output shop file> <old item id> <new item id>   e.g. 28524 48060
import struct, sys, hashlib, os
if len(sys.argv) != 5:
    sys.exit('usage: python shop_swap_item.py <in> <out> <old item id> <new item id>')
src, dst, old, new = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
d = bytearray(open(src, 'rb').read()); N = len(d)
stamp, n = struct.unpack_from('<II', d, 0)
if N - 8 == n * 232:
    kind, R, ITEM = 'server (gshopsev1)', 232, 12
elif N - 8 >= n * 1448 and (N - 8 - n * 1448) < 4096:
    kind, R, ITEM = 'client (gshop1)', 1448, 140
else:
    sys.exit('file size %d does not fit a 232-byte server or 1448-byte client shop with %d items - nothing done' % (N, n))
print('file kind:', kind, '| items:', n)
hits = [i for i in range(n) if struct.unpack_from('<I', d, 8 + i * R + ITEM)[0] == old]
if len(hits) != 1:
    sys.exit('expected exactly one record selling item %d, found %d - nothing done' % (old, len(hits)))
if any(struct.unpack_from('<I', d, 8 + i * R + ITEM)[0] == new for i in range(n)):
    sys.exit('item %d is already sold in this shop - nothing done' % new)
struct.pack_into('<I', d, 8 + hits[0] * R + ITEM, new)
open(dst, 'wb').write(d)
print('record %d: item %d -> %d (4 bytes changed)' % (hits[0], old, new))
print('md5 in :', hashlib.md5(open(src, 'rb').read()).hexdigest())
print('md5 out:', hashlib.md5(d).hexdigest())
