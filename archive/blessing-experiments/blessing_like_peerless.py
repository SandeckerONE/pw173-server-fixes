#!/usr/bin/env python3
# blessing_like_peerless.py - TWO-PART EXPERIMENT on a COPY of elements.data. Same size in, same size out.
#   Jones' Blessing (22198)    : only the effect list is duplicated (the 2nd list, which Peerless fills and ours leaves empty)
#   O'Malley's Blessing (28524): the same, PLUS item level 16, quality 3 and Peerless-style flags
# Refuses unless every field is exactly where and what it should be. Never edits the input; writes a NEW file.
# Usage: python blessing_like_peerless.py <elements.data copy> <output file>
import struct, sys, hashlib, os

if len(sys.argv) != 3:
    sys.exit('usage: python blessing_like_peerless.py <input elements.data copy> <output file>')
src, dst = sys.argv[1], sys.argv[2]
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')

d = bytearray(open(src, 'rb').read())
N = len(d)
print('input size', N, 'md5', hashlib.md5(d).hexdigest())


def u(o):
    return struct.unpack_from('<I', d, o)[0]


def record(item_id, name):
    key = struct.pack('<III', item_id, 21213, 21285)
    hits, i = [], d.find(key)
    while i != -1:
        if d[i + 12:i + 76].decode('utf-16le', 'ignore').split('\x00')[0] == name:
            hits.append(i)
        i = d.find(key, i + 1)
    if len(hits) != 1:
        sys.exit('expected exactly one record for %s (%d), found %d - nothing done' % (name, item_id, len(hits)))
    return hits[0]


def copy_list(o):
    A = bytes(d[o + 564:o + 820])
    if any(u(o + 820 + 8 * k) for k in range(32)):
        sys.exit('second list is not empty on this record - nothing done')
    if not any(u(o + 564 + 8 * k) for k in range(32)):
        sys.exit('first list is empty - nothing done')
    d[o + 820:o + 1076] = A


# Jones' Blessing: list only
oj = record(22198, "Jones' Blessing")
copy_list(oj)
print("Jones' (22198) at", oj, ': second list filled')

# O'Malley's Blessing: list + level + quality + flags
oo = record(28524, "O'Malley's Blessing")
if (u(oo + 368), u(oo + 400), u(oo + 1124)) != (0, 1, 0x13):
    sys.exit("O'Malley's fields are not the expected originals (0, 1, 0x13) - nothing done")
copy_list(oo)
struct.pack_into('<I', d, oo + 368, 16)
struct.pack_into('<I', d, oo + 400, 3)
struct.pack_into('<I', d, oo + 1124, 0x4017)
print("O'Malley's (28524) at", oo, ': second list filled, level 16, quality 3, flags 0x4017')

assert len(d) == N
open(dst, 'wb').write(d)
print('wrote', dst)
print('md5 out:', hashlib.md5(d).hexdigest())
