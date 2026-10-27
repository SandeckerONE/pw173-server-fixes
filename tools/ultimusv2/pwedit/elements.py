"""Item lookup in elements.data (read-only).

elements.data is not parsed list by list (most record types are not mapped yet). Items are found by their
name field: the item id sits 4, 8 or 12 bytes before the name (see layouts/elements_item.json).
The file is only ever opened for reading.
"""
import bisect
import json
import os
import re
import struct

from .layout import base_dir

with open(os.path.join(base_dir(), 'layouts', 'elements_flow.json'), 'r', encoding='utf-8') as _f:
    LISTS = json.load(_f)['lists']
NON_ITEM = ('stats', 'monsters', 'shops', 'npcs', 'recipes')   # lists whose records are not items


def find_list(d, list_id, size):
    """Find a list by its header [list id][count][size]; returns (start, count) or None."""
    pat = struct.pack('<I', size)
    i = d.find(pat)
    while i != -1:
        if i >= 8 and struct.unpack_from('<I', d, i - 8)[0] == list_id:
            cnt = struct.unpack_from('<I', d, i - 4)[0]
            start = i + 4
            if 0 < cnt < 200000 and start + cnt * size <= len(d):
                rid = struct.unpack_from('<I', d, start)[0]
                if 1 <= rid < 200000:
                    return start, cnt
        i = d.find(pat, i + 1)
    return None

# UTF-16LE names: ASCII, middle dot, and the star symbols used in item names; 2 to 31 characters, then a 00 00 end
NAME_RE = re.compile(rb'(?:[\x20-\x7e\xb7]\x00|[\x05\x06]\x26){2,31}\x00\x00')
ID_MIN, ID_MAX = 1000, 200000


def name_ok(d, s):
    """At least two letters in the name (keeps short codes and junk out of the old-equipment rule)."""
    nm = d[s:s + 64].decode('utf-16le', 'ignore').split('\x00')[0]
    return sum(ch.isalpha() for ch in nm) >= 2


class Entry:
    __slots__ = ('id', 'name', 'name_off', 'back', 'kind')

    def __init__(self, id_, name, name_off, back, kind=None):
        self.id, self.name, self.name_off, self.back, self.kind = id_, name, name_off, back, kind

    @property
    def rec_off(self):
        return self.name_off - self.back


class ItemIndex:
    def __init__(self):
        self.ready = False
        self.path = None
        self.data = b''
        self.entries = []
        self._by_id = {}
        self._stat_cache = {}
        self.lists = {}   # name -> (start, count, size)

    def load(self, path, progress=None):
        with open(path, 'rb') as f:
            data = f.read()
        self.build(data, path, progress)

    def build(self, data, path, progress=None):
        """Index an elements.data already in memory (bytes or bytearray; a bytearray is shared, not copied)."""
        self.data = data
        self.path = path
        d, out = self.data, []
        u = struct.Struct('<I').unpack_from
        step = max(1, len(d) // 50)
        nextp = step
        for m in NAME_RE.finditer(d):
            s = m.start()
            if progress and s >= nextp:
                progress(s / len(d))
                nextp += step
            if s < 12 or d[s - 2] | d[s - 1]:
                continue  # not the start of a name field
            a, b, c = u(d, s - 12)[0], u(d, s - 8)[0], u(d, s - 4)[0]
            ok = lambda v: ID_MIN <= v <= ID_MAX  # noqa: E731
            if ok(a) and ok(b) and ok(c) and b < c:
                back = 12          # id, major type, sub type, name
            elif 1 <= a <= ID_MAX and 1 <= b < c < ID_MIN and name_ok(d, s):
                back = 12          # old equipment: small id and small type pair (e.g. 36, type 1/35, ☆Mother and Son Blades)
            elif ok(b) and not ok(c):
                back = 8
            elif ok(c):
                back = 4
            else:
                continue
            name = d[s:m.end() - 2].decode('utf-16le', 'replace')
            out.append(Entry(u(d, s - back)[0], name, s, back))
        # mark entries that sit in known non-item lists, and take their id from the record start
        self.lists = {}
        for key, spec in LISTS.items():
            f = find_list(d, spec['list_id'], spec['record_size'])
            if f:
                self.lists[key] = (f[0], f[1], spec['record_size'])
        ranges = sorted((st, st + c * sz, sz, key) for key, (st, c, sz) in self.lists.items() if key in NON_ITEM)
        starts = [r[0] for r in ranges]
        for e in out:
            k = bisect.bisect_right(starts, e.name_off) - 1
            if k >= 0 and e.name_off < ranges[k][1]:
                st, en, sz, key = ranges[k]
                rec = st + ((e.name_off - st) // sz) * sz
                into = e.name_off - rec
                e.kind = key[:-1] if into in (4, 8, 12) else 'text'
                if into in (4, 8, 12):
                    e.back = into
                    e.id = u(d, rec)[0]
        self.entries = out
        self._by_id = {}
        for e in out:
            self._by_id.setdefault(e.id, []).append(e)
        self.ready = True
        if progress:
            progress(1.0)

    def by_id(self, item_id):
        return self._by_id.get(item_id, [])

    def search(self, text, limit=500):
        text = text.strip()
        if not text:
            return []
        if text.isdigit():
            return self.by_id(int(text))[:limit]
        t = text.lower()
        exact = [e for e in self.entries if e.name.lower() == t]
        part = [e for e in self.entries if t in e.name.lower() and e.name.lower() != t]
        return (exact + part)[:limit]

    def best_name(self, item_id):
        """The most likely ITEM name for an id: entries in non-item lists (stats, monsters, NPCs, recipes) are skipped."""
        hits = [e for e in self.by_id(item_id) if e.kind is None]
        for e in hits:
            if e.back in (12, 4):
                return e.name
        return hits[0].name if hits else None

    def name_in(self, kind, rec_id):
        """Name of a record in a non-item list, e.g. name_in('monster', 17359)."""
        for e in self.by_id(rec_id):
            if e.kind == kind:
                return e.name
        return None

    def stat_entry(self, v):
        """If v is the id of an 84-byte stat entry ([id][name 64 B][1][value][0][0]), return (name, values)."""
        if v in self._stat_cache:
            return self._stat_cache[v]
        d, res = self.data, None
        p = struct.pack('<I', v)
        i, tries = d.find(p), 0
        while i != -1 and tries < 400 and i + 84 <= len(d):
            nm = d[i + 4:i + 68].decode('utf-16le', 'ignore').split('\x00')[0]
            first = struct.unpack_from('<I', d, i + 68)[0]
            if len(nm) >= 2 and nm.isprintable() and first in (1, 2, 3):
                res = (nm, list(struct.unpack_from('<4I', d, i + 68)))
                break
            i, tries = d.find(p, i + 1), tries + 1
        self._stat_cache[v] = res
        return res

    def dump(self, e, length=1200):
        """Readable dump of the bytes after an item's id: every non-zero 4-byte value, floats, stat entries."""
        d = self.data
        o = e.rec_off
        end = min(o + length, len(d))
        lines = ['%s  (id %d)' % (e.name, e.id),
                 'record starts at file offset %d; name field at id+%d' % (o, e.back),
                 'offsets below are from the id; only non-zero 4-byte values are shown', '']
        ns, ne = e.name_off, e.name_off + 64
        for r in range(o, end - 3, 4):
            if ns <= r < ne:
                continue
            v = struct.unpack_from('<I', d, r)[0]
            if not v:
                continue
            extra = ''
            f = struct.unpack_from('<f', d, r)[0]
            if f == f and 1e-6 < abs(f) < 1e7 and v > 0x30000000:
                extra += '  float=%g' % f
            if ID_MIN <= v <= ID_MAX:
                s = self.stat_entry(v)
                if s:
                    extra += '  <- stat entry %r %s' % (s[0], s[1])
                else:
                    nm = self.best_name(v)
                    if nm:
                        extra += '  <- item %r' % nm
            lines.append('  +%-5d %-12d%s' % (r - o, v, extra))
        return '\n'.join(lines)
