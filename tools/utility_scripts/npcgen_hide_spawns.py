#!/usr/bin/env python3
"""npcgen_hide_spawns.py - hides NPC spawns in world/npcgen.data (PWI 1.7.3, npcgen version 11).

How: each spawn area has a switch field (+59). 0 = always on. Event spawns use a controller that is
never switched on (18 on the 1.7.3 package); giving an area that value hides it. Tested in game:
the NPCs are gone, every other NPC stays. Only the 4-byte switch of each chosen area changes.

Only areas that hold NOTHING but the NPC ids you name are changed; mixed areas are listed and skipped.
Never edits the input; writes a NEW file of the same size and reads it back to check.

Usage:
  python npcgen_hide_spawns.py <npcgen.data> --list <id,id,...>                 show every area holding those ids
  python npcgen_hide_spawns.py <npcgen.data> <output> --hide <id,id,...>         hide them
  python npcgen_hide_spawns.py <npcgen.data> <output> --hide <ids> --switch 18   controller value to use (default 18)
Server-only change: put the output in /opt/gamed/config/world/npcgen.data (keep a backup) and restart.
"""
import os, struct, sys

AREA_HDR, ENTRY, SWITCH = 71, 64, 59
STOCK_AREAS, STOCK_END = 21521, 3202699    # stock 1.7.3 world file; a different file only gives a warning


def walk(d):
    ver, na = struct.unpack_from('<2I', d, 0)
    if ver != 11:
        sys.exit('npcgen version %d, expected 11 - stopping' % ver)
    o, out = 20, []
    for _ in range(na):
        if o + AREA_HDR > len(d):
            sys.exit('file ends inside the spawn areas - not the layout this script knows')
        cnt, = struct.unpack_from('<I', d, o + 4)
        if cnt > 1000 or o + AREA_HDR + ENTRY * cnt > len(d):
            sys.exit('area at offset %d does not read as expected - stopping' % o)
        ids = [struct.unpack_from('<I', d, o + AREA_HDR + ENTRY * j)[0] for j in range(cnt)]
        out.append((o, ids, struct.unpack_from('<3f', d, o + 8), struct.unpack_from('<I', d, o + SWITCH)[0]))
        o += AREA_HDR + ENTRY * cnt
    return na, o, out


def opt(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


if len(sys.argv) < 3:
    sys.exit(__doc__)
src = sys.argv[1]
d = bytearray(open(src, 'rb').read())
na, end, areas = walk(d)
print('%s: %d spawn areas, areas end at %d' % (src, na, end))
if (na, end) != (STOCK_AREAS, STOCK_END):
    print('WARNING: not the stock 1.7.3 world file (%d areas ending at %d); check the --list output carefully' % (STOCK_AREAS, STOCK_END))
ids_arg = opt('--list') or opt('--hide')
if not ids_arg:
    sys.exit(__doc__)
want = {int(x) for x in ids_arg.split(',') if x.strip()}
hits = [a for a in areas if want & set(a[1])]
for n, (o, ids, p, sw) in enumerate(hits, 1):
    mixed = '' if set(ids) <= want else '  MIXED (also holds %s) - will be skipped' % sorted(set(ids) - want)[:6]
    print('%3d  offset %8d  approx. map %4d,%4d  switch %3d  ids %s%s' % (n, o, round(p[0] / 10 + 400), round(p[2] / 10 + 550), sw, sorted(set(ids)), mixed))
if not hits:
    sys.exit('no area holds those ids')
if '--list' in sys.argv:
    sys.exit(0)
dst = sys.argv[2]
if os.path.abspath(dst) == os.path.abspath(src):
    sys.exit('input and output must be different files')
value = int(opt('--switch', '18'))
changed = skipped = 0
for o, ids, p, sw in hits:
    if not set(ids) <= want:
        skipped += 1; continue
    if sw != 0:
        print('  offset %d already has switch %d - left as is' % (o, sw)); skipped += 1; continue
    struct.pack_into('<I', d, o + SWITCH, value); changed += 1
open(dst, 'wb').write(d)
chk = bytearray(open(dst, 'rb').read())
na2, end2, _ = walk(chk)
if len(chk) != len(d) or (na2, end2) != (na, end):
    sys.exit('output does not read back the same way - do not use it')
print('hidden %d areas (switch -> %d), skipped %d; output %s, same size' % (changed, value, skipped, dst))
