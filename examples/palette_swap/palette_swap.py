#!/usr/bin/env python3
"""palette_swap.py - replaces 5 seasonal prizes in the main Palette of Fortune table (elements.data e344,
record 6064 "彩票配置表") with other items, and makes the replacements normal (non-seasonal) prizes.

Prize entry (16 bytes): item id u32, chance (f32), 0, seasonal flag u32 (1 = seasonal special).
The 5 swaps below are the ones we used; edit SWAPS for your own choice (offsets are inside the record).
Used live on our server (server and client patched together).

Finds the record by its id and name (not by a fixed file offset or md5), checks every entry holds the
expected old item before changing it, and skips entries already swapped.
Never edits the input; writes a NEW file of the same size.
Usage:  python palette_swap.py <elements.data in> <elements.data out>
Patch the server's and the client's elements.data the same way.
"""
import os, struct, sys

REC_ID, REC_NAME = 6064, '彩票配置表'
SWAPS = [  # (offset in record, old id, new id, label)
    (2124, 68145, 38256, 'Soul Nail Disk -> Crown of Madness (3-star)'),
    (2140, 68146, 50265, 'Soul Cleanse Lotion -> Dull Draconic Essence'),
    (1644, 69456, 55190, 'Cosmos Conduit Pack -> Dull Zenith Skull Shard Pack'),
    (1660, 70565, 50238, 'Sacred Celestial Infant Extract -> Sigil of Elysium'),
    (1164, 64629, 50239, 'Moonlight Crystal Fragment -> Dragonbreath Sigil'),
]

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, dst = sys.argv[1], sys.argv[2]
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
d = bytearray(open(src, 'rb').read())
key = struct.pack('<I', REC_ID) + REC_NAME.encode('utf-16le')
rec = d.find(key)
if rec < 0 or d.find(key, rec + 1) >= 0:
    sys.exit('Palette record %d not found exactly once - nothing written' % REC_ID)
done = 0
for off, old, new, label in SWAPS:
    p = rec + off
    cur, chance, zero, special = struct.unpack_from('<IIII', d, p)
    if cur == new and special == 0:
        print('  already swapped: ' + label); continue
    if cur != old or special != 1:
        sys.exit('%s: found id %d flag %d, expected %d flag 1 - nothing written' % (label, cur, special, old))
    struct.pack_into('<I', d, p, new)      # item id
    struct.pack_into('<I', d, p + 12, 0)   # seasonal flag off -> normal prize
    print('  ' + label); done += 1
open(dst, 'wb').write(d)
print('written %s: %d prizes swapped, same size' % (dst, done))
