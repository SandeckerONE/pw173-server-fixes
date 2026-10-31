#!/usr/bin/env python3
# dump_item.py - READ-ONLY. Shows the raw record of items in a COPY of elements.data.
# Usage: python dump_item.py <path to elements.data copy> <item id> [<item id> ...]
# Opens the file in 'rb' mode only. Writes nothing.
import struct, sys, math

if len(sys.argv) < 3:
    sys.exit('usage: python dump_item.py <elements.data copy> <id> [<id> ...]')

d = open(sys.argv[1], 'rb').read()
N = len(d)
print('file size', N)


def find_all(p, limit=5000):
    out = []
    i = d.find(p)
    while i != -1 and len(out) < limit:
        out.append(i)
        i = d.find(p, i + 1)
    return out


def u32(o):
    return struct.unpack_from('<I', d, o)[0] if 0 <= o and o + 4 <= N else None


def text_at(o, units=32):
    if o < 0 or o + units * 2 > N:
        return None
    s = d[o:o + units * 2].decode('utf-16le', 'ignore').split('\x00')[0]
    return s if len(s) >= 3 and s.isprintable() else None


def addon_entry(v):
    # stat entry shape from earlier notes: [id][name 64 B UTF-16][u32 a][u32 b][u32 c][u32 d]
    for o in find_all(struct.pack('<I', v), 400):
        nm = text_at(o + 4)
        if nm is not None and u32(o + 68) in (1, 2, 3):
            return o, nm, struct.unpack_from('<4I', d, o + 68)
    return None


def fl(v):
    f = struct.unpack('<f', struct.pack('<I', v))[0]
    if f == f and 1e-6 < abs(f) < 1e7 and v > 0x3f000000 - 0x10000000:
        return ' float=%g' % f
    return ''


for want in sys.argv[2:]:
    item = int(want)
    hits = find_all(struct.pack('<I', item))
    print('\n' + '=' * 70)
    print('ID %d: %d raw hits in the file' % (item, len(hits)))
    shown = 0
    for o in hits:
        for back in (4, 8, 12):
            nm = text_at(o + back)
            if nm:
                shown += 1
                print('\n-- record candidate at offset %d, name at id+%d: %r' % (o, back, nm))
                end = min(o + 1000, N)
                # name field is 64 bytes: skip it
                nstart, nend = o + back, o + back + 64
                for r in range(o, end, 4):
                    if nstart <= r < nend:
                        continue
                    v = u32(r)
                    if v:
                        extra = ''
                        if 1000 <= v <= 200000:
                            a = addon_entry(v)
                            if a:
                                extra = '  <- stat entry %r %s' % (a[1], list(a[2]))
                        print('  +%-4d %-12d%s%s' % (r - o, v, fl(v), extra))
                break
    if not shown:
        print('  no record-looking hit (no name next to the id).')
print('\nDone. Nothing was written.')
