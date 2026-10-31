#!/usr/bin/env python3
"""add_bh1_ticket.py - adds a 10 Event Gold Ticket (item 30759, x1, 100%, permanent) to the reward list
of every Bounty Hunter I quest (19949-19964 and 19967) in a PWI 1.7.3 (t187) tasks.data.

Tested in game: each BH I hand-in gives the ticket on top of the normal reward.
Adding a reward row inserts 17 bytes, raises the group's row count and shifts every later quest offset.
Quests that already end with the ticket are skipped, so running it twice changes nothing.
Never edits the input; writes a NEW file and reads it back.

Usage:  python add_bh1_ticket.py <tasks.data in> <tasks.data out>
Patch the server's and the client's tasks.data with the same result (they must be identical).
"""
import os, struct, sys

TICKET_ID = 30759
QUESTS = list(range(19949, 19965)) + [19967]
TICKET = struct.pack('<IBIfi', TICKET_ID, 1, 1, 1.0, 0)   # item, flag, count, chance, period (0 = permanent)


def load(tk):
    magic, ver, count = struct.unpack_from('<3I', tk, 0)
    if ver != 187:
        sys.exit('tasks.data version %d, expected 187 - nothing written' % ver)
    tab = list(struct.unpack_from('<%dI' % count, tk, 12))
    order = sorted(tab)
    recs = {}
    for i, o in enumerate(order):
        e = order[i + 1] if i + 1 < len(order) else len(tk)
        v = struct.unpack_from('<I', tk, o)[0]
        if v & 0xFFFF == 0:                     # u16 prefix 0, then the quest id
            recs[v >> 16 | struct.unpack_from('<H', tk, o + 4)[0] << 16] = (o, e)
    return count, tab, recs


def groups(tk, o, e):
    def row(h):
        it, fl, ct, pr, pe = struct.unpack_from('<IBIfi', tk, h)
        return fl <= 1 and 0 < pr <= 1.0001 and 1 <= ct <= 10000000 and 1 <= it < 100000 and pe >= 0
    out = []
    for h in range(o, e - 5):
        fl = tk[h]; n = struct.unpack_from('<I', tk, h + 1)[0]
        if fl <= 1 and 1 <= n <= 60 and h + 5 + 17 * n <= e and all(row(h + 5 + 17 * k) for k in range(n)):
            out.append((h, n))
    return [g for g in out if not any(g2[0] < g[0] < g2[0] + 5 + 17 * g2[1] for g2 in out if g2 != g)]


if len(sys.argv) != 3:
    sys.exit(__doc__)
src, dst = sys.argv[1], sys.argv[2]
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
tk = open(src, 'rb').read()
count, tab, recs = load(tk)
buf = bytearray(tk); ins = []; skipped = 0
for q in QUESTS:
    if q not in recs:
        sys.exit('quest %d not found - nothing written' % q)
    o, e = recs[q]
    gs = groups(tk, o, e)
    if len(gs) != 1:
        sys.exit('quest %d: expected one reward list, found %d - nothing written' % (q, len(gs)))
    h, n = gs[0]
    if tk[h + 5 + 17 * (n - 1):h + 5 + 17 * n] == TICKET:
        skipped += 1; continue
    struct.pack_into('<I', buf, h + 1, n + 1)
    ins.append((h + 5 + 17 * n, TICKET))
new = bytearray(buf)
for pos, b in sorted(ins, reverse=True):
    new[pos:pos] = b
struct.pack_into('<%dI' % count, new, 12, *[o + sum(len(b) for p, b in ins if p < o) for o in tab])
c2, _, r2 = load(bytes(new))
if c2 != count or len(r2) != len(recs) or len(new) != len(tk) + 17 * len(ins):
    sys.exit('result does not read back as expected - nothing written')
open(dst, 'wb').write(new)
print('written %s: ticket added to %d quests, %d already had it, +%d bytes' % (dst, len(ins), skipped, len(new) - len(tk)))
