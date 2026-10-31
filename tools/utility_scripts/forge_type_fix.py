#!/usr/bin/env python3
"""forge_type_fix.py - fixes "Invalid service request" at forges (PWI 1.7.3, elements.data e344).

The 1.7.3 gs does not serve crafting services whose production type (+72 in list 55) is 1.
This sets those services to type 0 (plain crafting). Tested in game on Nature Forge: Tomes
(Tome / Fate / Lord tabs) and Aerogear Forge Med.

Patch the SERVER's and the CLIENT's elements.data the same way: the client picks the request type
from its own file. Test the client without an auto-updating launcher (it would put the old file back).

Never edits the input; writes a NEW file of the same size. Refuses unless:
  - the crafting service list header [55][349][1228] is found exactly once,
  - the type-1 services are exactly the 16 of the stock 1.7.3 data (use --any to accept another set),
  - only the type fields changed in the result.

Usage:  python forge_type_fix.py <elements.data> <output file> [--any] [--list]
"""
import os, struct, sys

LIST_ID, COUNT, SIZE = 55, 349, 1228
TYPE_OFF = 72
STOCK = {18153, 19214, 22105, 24591, 24690, 25399, 28058, 29935, 33954, 33956, 33958, 42760, 43020, 43021, 51191, 67504}

args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = {a for a in sys.argv[1:] if a.startswith('--')}
if not args or (len(args) < 2 and '--list' not in flags):
    sys.exit(__doc__)
d = bytearray(open(args[0], 'rb').read())
hdr = struct.pack('<3I', LIST_ID, COUNT, SIZE)
pos = d.find(hdr)
if pos < 0 or d.find(hdr, pos + 1) >= 0:
    sys.exit('crafting service list (55 x 349 x 1228) not found exactly once - is this an e344 elements.data? nothing written')
base = pos + 12
types = {}
for k in range(COUNT):
    o = base + k * SIZE
    sid, = struct.unpack_from('<I', d, o)
    typ, = struct.unpack_from('<I', d, o + TYPE_OFF)
    types.setdefault(typ, []).append((sid, o))
name = lambda o: d[o + 4:o + 68].decode('utf-16le', 'ignore').split('\x00')[0]
print('crafting services by production type:', {t: len(v) for t, v in sorted(types.items())})
one = types.get(1, [])
if '--list' in flags:
    for sid, o in one:
        print('  type 1: %5d %s' % (sid, name(o)))
    sys.exit(0)
dst = args[1]
if os.path.abspath(dst) == os.path.abspath(args[0]):
    sys.exit('input and output must be different files')
if not one:
    sys.exit('no type-1 services left - already fixed? nothing written')
if {s for s, _ in one} != STOCK and '--any' not in flags:
    sys.exit('the type-1 services are not the stock 16 (found %d); check with --list, then re-run with --any' % len(one))
orig = bytes(d)
for sid, o in one:
    struct.pack_into('<I', d, o + TYPE_OFF, 0)
    print('  %5d %s: type 1 -> 0' % (sid, name(o)))
check = bytearray(d)
for sid, o in one:
    check[o + TYPE_OFF:o + TYPE_OFF + 4] = orig[o + TYPE_OFF:o + TYPE_OFF + 4]
if len(d) != len(orig) or check != orig:
    sys.exit('unexpected change outside the type fields - nothing written')
changed = sum(1 for sid, o in one for i in range(o + TYPE_OFF, o + TYPE_OFF + 4) if d[i] != orig[i])
open(dst, 'wb').write(d)
print('written %s: %d services changed, %d bytes differ, same size' % (dst, len(one), changed))
