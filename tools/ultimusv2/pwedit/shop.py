"""Boutique files: a client file (gshop.data / gshop1.data) and its server twin (gshopsev.data / gshopsev1.data).

The two files must stay in step: same stamp, same number of records, same order, same item/count/price data.
This module only edits the fields marked editable in the layout tables and copies everything else untouched.
"""
import hashlib
import os
import re
import struct

from .layout import load_layout

CLIENT = load_layout('gshop_client.json')
SERVER = load_layout('gshop_server.json')

# fields that exist on both sides and must match
SHARED = ('main_tab', 'sub_tab', 'item_id', 'count', 'price', 'duration', 'status_label')

# words that usually mean the item stacks (tickets, packs ...). A duration on a stackable item stops the maps (error -32).
STACK_HINTS = ('ticket', 'pack', 'pill', 'potion', 'scroll', 'stone', 'chest', 'key', 'coupon', 'token', 'box', 'shard',
               'charm', 'firework', 'dye', 'pigment', 'herb', 'essence', 'gold', 'note', 'card')

def looks_stackable(name):
    words = re.findall(r'[a-z]+', (name or '').lower())
    return any(w in STACK_HINTS or w.rstrip('s') in STACK_HINTS for w in words)


DURATIONS = [('permanent', 0), ('1 day', 86400), ('3 days', 259200), ('7 days', 604800), ('15 days', 1296000),
             ('30 days', 2592000)]


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class ShopError(Exception):
    pass


class ShopFile:
    """One boutique file, either side."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) < 8:
            raise ShopError('%s is too small to be a boutique file' % path)
        self.stamp, n = struct.unpack_from('<II', data, 0)
        if len(data) - 8 == n * SERVER.record_size:
            self.side, self.lay, self.trailer = 'server', SERVER, b''
        elif len(data) - 8 > n * CLIENT.record_size:
            self.side, self.lay = 'client', CLIENT
            self.trailer = data[8 + n * CLIENT.record_size:]
            self.tree = parse_tree(self.trailer)
            if self.tree is None:
                raise ShopError('%s: the category list after the records does not parse - not a 1.7.3 client boutique file?' % path)
        else:
            raise ShopError('%s: size %d does not fit %d records of a 1.7.3 client (1448 B) or server (232 B) boutique file'
                            % (path, len(data), n))
        R = self.lay.record_size
        self.records = [bytearray(data[8 + i * R: 8 + (i + 1) * R]) for i in range(n)]
        self.md5_loaded = hashlib.md5(data).hexdigest()

    def get(self, i, name):
        return self.lay.get(self.records[i], name)

    def set(self, i, name, value):
        self.lay.set(self.records[i], name, value)

    def to_bytes(self):
        out = [struct.pack('<II', self.stamp, len(self.records))]
        for i, r in enumerate(self.records):
            struct.pack_into('<i', r, 0, i)  # lid = index
            out.append(bytes(r))
        out.append(self.trailer)
        return b''.join(out)


def parse_tree(trailer):
    """Category list: per main tab 128 B UTF-16 name, u32 sub count, sub count x 128 B names."""
    tree, o = [], 0
    try:
        while o < len(trailer):
            name = trailer[o:o + 128].decode('utf-16le', 'replace').split('\x00')[0].strip()
            o += 128
            c = struct.unpack_from('<I', trailer, o)[0]
            o += 4
            if c > 64:
                return None
            subs = [trailer[o + 128 * k:o + 128 * (k + 1)].decode('utf-16le', 'replace').split('\x00')[0].strip()
                    for k in range(c)]
            o += 128 * c
            tree.append((name, subs))
    except struct.error:
        return None
    return tree if o == len(trailer) else None


class ShopPair:
    """Client + server boutique files edited together."""

    def __init__(self, client_path, server_path):
        c, s = ShopFile(client_path), ShopFile(server_path)
        if c.side == 'server' and s.side == 'client':
            c, s = s, c
        if c.side != 'client' or s.side != 'server':
            raise ShopError('Pick one client file (gshop*.data) and one server file (gshopsev*.data).')
        self.client, self.server = c, s
        self.problems = self.check_pairing()

    def __len__(self):
        return len(self.client.records)

    @property
    def tree(self):
        return self.client.tree

    def check_pairing(self):
        p = []
        if self.client.stamp != self.server.stamp:
            p.append('stamps differ: client %08x, server %08x' % (self.client.stamp, self.server.stamp))
        if len(self.client.records) != len(self.server.records):
            p.append('record counts differ: client %d, server %d' % (len(self.client.records), len(self.server.records)))
            return p
        for i in range(len(self)):
            for f in SHARED:
                a, b = self.client.get(i, f), self.server.get(i, f)
                if a != b:
                    p.append('record %d: %s differs (client %s, server %s)' % (i, f, a, b))
            if self.client.lay.slice(self.client.records[i], 'block_a') != self.server.lay.slice(self.server.records[i], 'block_a') or \
               self.client.lay.slice(self.client.records[i], 'block_b') != self.server.lay.slice(self.server.records[i], 'block_b'):
                p.append('record %d: extra 1.7.3 fields differ between client and server' % i)
            if len(p) > 50:
                p.append('... (more)')
                break
        return p

    def row(self, i):
        c = self.client
        return {k: c.get(i, k) for k in ('main_tab', 'sub_tab', 'item_id', 'count', 'price', 'duration', 'status_label',
                                          'name', 'description')}

    def tab_name(self, main, sub):
        t = self.tree
        if 0 <= main < len(t):
            m, subs = t[main]
            s = subs[sub] if 0 <= sub < len(subs) else '?%d' % sub
            return '%s > %s' % (m, s)
        return '?%d > ?%d' % (main, sub)

    def update(self, i, **vals):
        """Set fields on both sides. Raises ValueError on bad input (nothing is changed then)."""
        c_rec, s_rec = bytearray(self.client.records[i]), bytearray(self.server.records[i])
        for k, v in vals.items():
            if k in ('name', 'description'):
                self.client.lay.set(c_rec, k, v)
            elif k in SHARED:
                self.client.lay.set(c_rec, k, v)
                self.server.lay.set(s_rec, k, v)
            else:
                raise ValueError('field %s cannot be edited' % k)
        self.client.records[i], self.server.records[i] = c_rec, s_rec

    def add_copy(self, i):
        """Append a copy of record i at the end of both files; returns the new index."""
        self.client.records.append(bytearray(self.client.records[i]))
        self.server.records.append(bytearray(self.server.records[i]))
        return len(self) - 1

    def delete(self, i):
        del self.client.records[i]
        del self.server.records[i]

    def move(self, i, j):
        for side in (self.client, self.server):
            r = side.records.pop(i)
            side.records.insert(j, r)

    def validate(self, item_index=None):
        """Returns (errors, warnings). Errors block saving."""
        errors, warnings = [], []
        errors += self.check_pairing()
        for i in range(len(self)):
            r = self.row(i)
            tag = 'record %d (%s, item %d)' % (i, r['name'] or '?', r['item_id'])
            if r['count'] < 1:
                errors.append('%s: count must be at least 1' % tag)
            if r['price'] < 0:
                errors.append('%s: price is negative' % tag)
            if r['duration'] < 0:
                errors.append('%s: duration is negative' % tag)
            if r['duration'] > 0 and r['count'] > 1:
                errors.append('%s: count %d with a duration: a stacked purchase of a timed item will stop the maps from starting' % (tag, r['count']))
            elif r['duration'] > 0 and looks_stackable(r['name']):
                warnings.append('%s: has a duration and looks like a stackable item. If it stacks, the maps will not start (error -32). Set duration 0.' % tag)
            m, s = r['main_tab'], r['sub_tab']
            if not (0 <= m < len(self.tree)) or not (0 <= s < max(1, len(self.tree[m][1]))):
                warnings.append('%s: tab %d/%d is not in this file\'s category list' % (tag, m, s))
            if item_index is not None and item_index.ready and not item_index.by_id(r['item_id']):
                warnings.append('%s: item id not found by name in the loaded elements.data (may still be real; check it)' % tag)
        return errors, warnings

    def save(self, client_out, server_out):
        """Writes two NEW files. Never overwrites the files that were opened."""
        opened = {os.path.normcase(os.path.abspath(p)) for p in (self.client.path, self.server.path)}
        outs = [os.path.normcase(os.path.abspath(p)) for p in (client_out, server_out)]
        if outs[0] == outs[1]:
            raise ShopError('client and server output must be different files')
        for o in outs:
            if o in opened:
                raise ShopError('refusing to overwrite a file that is open in the editor: %s\nSave under a new name, then swap files by hand after a snapshot.' % o)
        errors, _ = self.validate()
        if errors:
            raise ShopError('not saved, fix these first:\n' + '\n'.join(errors[:20]))
        cb, sb = self.client.to_bytes(), self.server.to_bytes()
        # re-read check: the bytes we are about to write must load back cleanly
        with open(client_out, 'wb') as f:
            f.write(cb)
        with open(server_out, 'wb') as f:
            f.write(sb)
        ShopPair(client_out, server_out)  # raises if what we wrote does not load as a valid pair
        return md5_file(client_out), md5_file(server_out)
