#!/usr/bin/env python3
"""extract_treasure_cfg.py - READ-ONLY. Reads the Treasures tables out of the
server's elements.data and prints lines to paste into treasure_hook.conf.

  python3 -I extract_treasure_cfg.py /opt/gamed/config/elements.data

What it looks for (1.7.3, elements e344; verified 2026-10-17 by byte reading):
  LOTTORY_TICKET_COST_CONFIG  record 2313: key item 56274, 2 keys per seek,
                              extra-chest costs 0,5,12,30,75,188,466,1166,2998,4198
  LOTTORY_TICKET_STORAGE_CONFIG record 2312: 100 loot rows
                              (u32 item id, f32 chance, u32 tier, u32 count),
                              rows start at offset 88628828 in the e344 file
If the file is a different version, it searches for the same patterns instead.
"""
import hashlib
import struct
import sys

COSTS = (0, 5, 12, 30, 75, 188, 466, 1166, 2998, 4198)
E344_MD5_PREFIX = "f67769d8"
E344_ROWS_AT = 88628828
NROWS = 100


def rows_at(data, off):
    """return the 100 rows at off if they look like a loot table, else None"""
    if off < 0 or off + NROWS * 16 > len(data):
        return None
    rows = [struct.unpack_from("<IfII", data, off + 16 * i) for i in range(NROWS)]
    used = [r for r in rows if r[0]]
    if len(used) < 10 or rows[0][0] == 0:  # a real table starts with a used row
        return None
    for iid, p, tier, cnt in rows:
        if iid == 0:
            continue
        if not (1 <= iid <= 400000 and 0.0 <= p <= 1.0 and tier <= 1000 and 1 <= cnt <= 100000):
            return None
    total = sum(r[1] for r in used)
    if not 0.5 <= total <= 1.5:
        return None
    return rows


def find_costs(data):
    pat = struct.pack("<10I", *COSTS)
    hits = []
    o = data.find(pat)
    while o >= 0:
        hits.append(o)
        o = data.find(pat, o + 1)
    return hits


def find_loot(data):
    """look for record id 2312 followed (within 300 bytes) by a valid table"""
    pat = struct.pack("<I", 2312)
    o = data.find(pat)
    while o >= 0:
        for start in range(o + 4, o + 300, 4):
            rows = rows_at(data, start)
            if rows:
                return start, rows
        o = data.find(pat, o + 1)
    return None, None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()
    md5 = hashlib.md5(data).hexdigest()
    print(f"# elements.data: {path}")
    print(f"# md5 {md5}, {len(data)} bytes, header {data[:4].hex(' ')}")

    costs = find_costs(data)
    if costs:
        o = costs[0]
        key, per = struct.unpack_from("<II", data, o - 8)
        print(f"# cost table found at offset {o} (record 2313); the two numbers before it: {key}, {per}")
        if 1 <= key <= 400000 and 1 <= per <= 100:
            print(f"key_item = {key}")
            print(f"keys_per_seek = {per}")
        else:
            print("# (they do not look like key item / keys per seek; keep the defaults)")
        print("cost = " + ", ".join(str(c) for c in COSTS))
    else:
        print("# WARNING: cost table 0,5,12,...,4198 not found; keep the default cost line")

    rows, where = None, None
    if md5.startswith(E344_MD5_PREFIX):
        rows, where = rows_at(data, E344_ROWS_AT), E344_ROWS_AT
    if not rows:
        where, rows = find_loot(data)
    if not rows:
        print("# WARNING: loot table (record 2312) not found; add loot lines by hand")
        return 1
    used = [r for r in rows if r[0]]
    total = sum(r[1] for r in used)
    print(f"# loot table at offset {where}: {len(used)} rows, chances add up to {total:.6f}")
    print("# loot = item id, chance, count   (tier from the data, for reference)")
    for iid, p, tier, cnt in used:
        print(f"loot = {iid}, {p:.9g}, {cnt}   # tier {tier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
