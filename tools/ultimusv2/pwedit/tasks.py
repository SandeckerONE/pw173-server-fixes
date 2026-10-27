"""Quest reward editing in tasks.data (1.7.3, t187).

Layout comes from layouts/tasks.json (mapped on our own file; the add-row method is the one add_bh1_ticket.py used,
tested in game). Only reward rows are edited. Everything else is copied untouched.
"""
import bisect
import hashlib
import json
import os
import re
import struct

from .layout import base_dir

with open(os.path.join(base_dir(), 'layouts', 'tasks.json'), 'r', encoding='utf-8') as _f:
    SPEC = json.load(_f)


def _off(section, name):
    return next(f['offset'] for f in SPEC[section]['fields'] if f['name'] == name)


H_COUNT = _off('header', 'count')
H_TABLE = _off('header', 'offsets')
Q_ID = _off('quest_record', 'quest_id')
Q_NAME = _off('quest_record', 'name')
ROW = struct.Struct('<IBIfi')          # item, flag, count, chance, period  (layouts/tasks.json reward_row)
ROW_SIZE = SPEC['reward_row']['size']
assert ROW.size == ROW_SIZE
G_HEAD = 5                              # flag u8 + rows u32
COLOUR = re.compile(r'\^[0-9A-Fa-f]{6}')
MAX_ROWS = 60


class TasksError(Exception):
    pass


def plain(name):
    return COLOUR.sub('', name)


class Quest:
    __slots__ = ('slot', 'id', 'name')

    def __init__(self, slot, qid, name):
        self.slot, self.id, self.name = slot, qid, name


class Group:
    def __init__(self, pos, flag, rows):
        self.pos, self.flag, self.rows = pos, flag, rows   # rows: list of (row_pos, item, rflag, count, chance, period)


class TasksFile:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = bytearray(f.read())
        self.md5_loaded = hashlib.md5(self.data).hexdigest()
        d = self.data
        if len(d) < 16:
            raise TasksError('file too small to be tasks.data')
        self.magic, self.version = struct.unpack_from('<II', d, 0)
        n = struct.unpack_from('<I', d, H_COUNT)[0]
        if not 1 <= n <= 200000 or H_TABLE + 4 * n > len(d):
            raise TasksError('quest count %d does not fit this file - not a 1.7.3 tasks.data?' % n)
        self.count = n
        tab = self.table()
        if tab != sorted(tab) or tab[0] < H_TABLE + 4 * n or tab[-1] >= len(d):
            raise TasksError('quest offset table is not in the expected shape - not a 1.7.3 tasks.data?')
        self.quests = []
        for slot, o in enumerate(tab):
            qid = struct.unpack_from('<I', d, o + Q_ID)[0]
            self.quests.append(Quest(slot, qid, self._name(o, qid)))
        self.dirty = False

    # ---------------------------------------------------------------- reading
    def table(self):
        return list(struct.unpack_from('<%dI' % self.count, self.data, H_TABLE))

    def _name(self, o, qid):
        k = qid & 0xFFFF
        units = struct.unpack_from('<30H', self.data, o + Q_NAME)
        return ''.join(chr(u ^ k) for u in units).split('\x00')[0]

    def extent(self, q):
        tab = self.table()
        start = tab[q.slot]
        end = tab[q.slot + 1] if q.slot + 1 < len(tab) else len(self.data)
        return start, end

    def _row_ok(self, h):
        it, fl, ct, pr, pe = ROW.unpack_from(self.data, h)
        return fl <= 1 and 0 < pr <= 1.0001 and 1 <= ct <= 10000000 and 1 <= it < 200000 and pe >= 0

    def groups(self, q):
        """Reward groups inside a quest record (and its nested sub-quests)."""
        d = self.data
        o, e = self.extent(q)
        found = []
        for h in range(o, e - G_HEAD):
            fl = d[h]
            if fl > 1:
                continue
            n = struct.unpack_from('<I', d, h + 1)[0]
            if 1 <= n <= MAX_ROWS and h + G_HEAD + ROW_SIZE * n <= e and \
                    all(self._row_ok(h + G_HEAD + ROW_SIZE * k) for k in range(n)):
                found.append((h, n))
        found = [g for g in found if not any(g2[0] < g[0] < g2[0] + G_HEAD + ROW_SIZE * g2[1] for g2 in found if g2 != g)]
        out = []
        for h, n in found:
            rows = []
            for k in range(n):
                p = h + G_HEAD + ROW_SIZE * k
                rows.append((p,) + ROW.unpack_from(d, p))
            out.append(Group(h, d[h], rows))
        return out

    def search(self, text, limit=1000):
        t = text.strip()
        if not t:
            return []
        if t.isdigit():
            return [q for q in self.quests if q.id == int(t)]
        tl = t.lower()
        exact = [q for q in self.quests if plain(q.name).lower() == tl]
        part = [q for q in self.quests if tl in plain(q.name).lower() and plain(q.name).lower() != tl]
        return (exact + part)[:limit]

    def quests_giving(self, item_id, limit=500):
        """Quests with a reward row for this item (fast byte search, then confirmed against the quest's groups)."""
        d, tab = self.data, self.table()
        p = struct.pack('<I', item_id)
        hits, i = set(), d.find(p, tab[0])
        while i != -1:
            if i + ROW_SIZE <= len(d) and self._row_ok(i):
                slot = bisect.bisect_right(tab, i) - 1
                if slot >= 0:
                    hits.add(slot)
            i = d.find(p, i + 1)
        out = []
        for slot in sorted(hits):
            q = self.quests[slot]
            if any(r[1] == item_id for g in self.groups(q) for r in g.rows):
                out.append(q)
            if len(out) >= limit:
                break
        return out

    # ---------------------------------------------------------------- editing
    def set_row(self, row_pos, item, rflag, count, chance, period):
        if not (1 <= item < 200000):
            raise ValueError('item id out of range')
        if rflag not in (0, 1):
            raise ValueError('row flag must be 0 or 1')
        if not (1 <= count <= 10000000):
            raise ValueError('count must be 1 to 10,000,000')
        if not (0 < chance <= 1.0):
            raise ValueError('chance must be above 0% and at most 100%')
        if period < 0:
            raise ValueError('period cannot be negative')
        ROW.pack_into(self.data, row_pos, item, rflag, count, chance, period)
        self.dirty = True

    def _shift_table(self, pos, delta, current_slot):
        tab = self.table()
        for k, o in enumerate(tab):
            if k != current_slot and o >= pos:
                tab[k] = o + delta
        struct.pack_into('<%dI' % self.count, self.data, H_TABLE, *tab)

    def add_row(self, q, group, copy_index):
        """Append a copy of row copy_index at the end of the group. Shifts every later quest by 17 bytes."""
        n = len(group.rows)
        if n >= MAX_ROWS:
            raise ValueError('a group can hold at most %d rows' % MAX_ROWS)
        src = group.rows[copy_index][0]
        row = bytes(self.data[src:src + ROW_SIZE])
        pos = group.pos + G_HEAD + ROW_SIZE * n
        struct.pack_into('<I', self.data, group.pos + 1, n + 1)
        self.data[pos:pos] = row
        self._shift_table(pos, ROW_SIZE, q.slot)
        self.dirty = True

    def delete_row(self, q, group, index):
        n = len(group.rows)
        if n <= 1:
            raise ValueError('cannot delete the only row of a group (an empty group is untested); change the row instead')
        pos = group.rows[index][0]
        struct.pack_into('<I', self.data, group.pos + 1, n - 1)
        del self.data[pos:pos + ROW_SIZE]
        self._shift_table(pos + ROW_SIZE, -ROW_SIZE, q.slot)
        self.dirty = True

    # ---------------------------------------------------------------- checks / save
    def validate(self, quests, item_index=None):
        errors, warnings = [], []
        tab = self.table()
        if tab != sorted(tab):
            errors.append('quest offset table is no longer sorted')
        for q in quests:
            for g in self.groups(q):
                rnd = [r for r in g.rows if r[4] < 0.99999]
                s = sum(r[4] for r in rnd)
                if rnd and s > 1.0005:
                    warnings.append('quest %d %s: random rows in one group add up to %.2f%% (over 100%%)' % (q.id, plain(q.name), s * 100))
                if g.flag == 1 and rnd and abs(s - 1) > 0.0005 and len(rnd) == len(g.rows):
                    warnings.append('quest %d %s: random-pick group adds up to %.2f%% (stock tables add up to 100%%)' % (q.id, plain(q.name), s * 100))
                if item_index is not None and item_index.ready:
                    for r in g.rows:
                        if not item_index.by_id(r[1]):
                            warnings.append('quest %d: item %d not found by name in elements.data (check it)' % (q.id, r[1]))
        return errors, warnings

    def save(self, out_path):
        if os.path.normcase(os.path.abspath(out_path)) == os.path.normcase(os.path.abspath(self.path)):
            raise TasksError('refusing to overwrite the file that is open; save under a new name')
        tab = self.table()
        if tab != sorted(tab):
            raise TasksError('quest offset table is not sorted - not saved')
        with open(out_path, 'wb') as f:
            f.write(self.data)
        check = TasksFile(out_path)  # must load back as a valid tasks.data with the same quests
        if [q.id for q in check.quests] != [q.id for q in self.quests]:
            raise TasksError('saved file does not read back with the same quests - do not use it')
        self.dirty = False
        return check.md5_loaded
