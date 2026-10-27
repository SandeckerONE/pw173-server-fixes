"""NPC shops (what an NPC sells) in elements.data, 1.7.3 e344.

Layout from layouts/elements_npcshops.json, mapped on our own file: the shop list (list 41, 5448-byte records,
8 pages x 32 slots) and the NPC list (list 58, 1080-byte records, shop id at +740).
Only slot item ids and page titles are edited; every other byte is copied untouched. Same file size in and out.
"""
import hashlib
import json
import os
import struct

from .layout import base_dir

with open(os.path.join(base_dir(), 'layouts', 'elements_npcshops.json'), 'r', encoding='utf-8') as _f:
    SPEC = json.load(_f)

SHOP = SPEC['shop_list']
NPC = SPEC['npc_list']
_f = {f['name']: f for f in SHOP['fields']}
PAGES_OFF, N_PAGES, PAGE_SIZE = _f['pages']['offset'], _f['pages']['count'], _f['pages']['size']
_p = {f['name']: f for f in SHOP['page']['fields']}
TITLE_LEN = _p['title']['length']
SLOTS_OFF, N_SLOTS, SLOT_SIZE = _p['slots']['offset'], _p['slots']['count'], _p['slots']['size']
NPC_SELL = next(f['offset'] for f in NPC['fields'] if f['name'] == 'sell_service')


class NpcShopError(Exception):
    pass


def _text(d, o, n):
    return bytes(d[o:o + n]).decode('utf-16le', 'replace').split('\x00')[0]


def find_list(d, list_id, size, check):
    """Find a list by its header [list id][count][record size]; check(first_record_offset, count) confirms it."""
    pat = struct.pack('<I', size)
    i = d.find(pat)
    while i != -1:
        if i >= 8 and struct.unpack_from('<I', d, i - 8)[0] == list_id:
            cnt = struct.unpack_from('<I', d, i - 4)[0]
            start = i + 4
            if 0 < cnt < 100000 and start + cnt * size <= len(d) and check(start, cnt):
                return start, cnt
        i = d.find(pat, i + 1)
    return None


class Shop:
    __slots__ = ('index', 'off', 'id', 'name', 'npcs')

    def __init__(self, index, off, id_, name):
        self.index, self.off, self.id, self.name, self.npcs = index, off, id_, name, []


class NpcShops:
    def __init__(self, path, data=None):
        self.path = path
        if data is None:
            with open(path, 'rb') as f:
                data = bytearray(f.read())
        self.data = data if isinstance(data, bytearray) else bytearray(data)
        self.md5_loaded = hashlib.md5(self.data).hexdigest()
        d = self.data
        R = SHOP['record_size']

        def shop_ok(start, cnt):
            for k in (0, cnt - 1):
                o = start + k * R
                if not 1 <= struct.unpack_from('<I', d, o)[0] < 200000:
                    return False
                for p in range(N_PAGES):
                    t = _text(d, o + PAGES_OFF + p * PAGE_SIZE, TITLE_LEN)
                    if t and not t.isprintable():
                        return False
            return True
        found = find_list(d, SHOP['list_id'], R, shop_ok)
        if not found:
            raise NpcShopError('NPC shop list (list %d, %d-byte records) not found - not a 1.7.3 e344 elements.data?'
                               % (SHOP['list_id'], R))
        self.shop_start, self.shop_count = found
        self.shops = []
        for k in range(self.shop_count):
            o = self.shop_start + k * R
            self.shops.append(Shop(k, o, struct.unpack_from('<I', d, o)[0], _text(d, o + 4, 64)))
        self.by_id = {}
        for s in self.shops:
            self.by_id.setdefault(s.id, s)
        # NPC -> shop links
        NR = NPC['record_size']
        npcs = find_list(d, NPC['list_id'], NR, lambda st, c: 1 <= struct.unpack_from('<I', d, st)[0] < 200000)
        self.npc_count = 0
        if npcs:
            st, c = npcs
            self.npc_count = c
            for k in range(c):
                o = st + k * NR
                sid = struct.unpack_from('<I', d, o + NPC_SELL)[0]
                if sid in self.by_id:
                    self.by_id[sid].npcs.append((struct.unpack_from('<I', d, o)[0], _text(d, o + 4, 64)))
        self.dirty = False

    # ------------------------------------------------------------- reading
    def page_off(self, shop, page):
        return shop.off + PAGES_OFF + page * PAGE_SIZE

    def slot_off(self, shop, page, slot):
        return self.page_off(shop, page) + SLOTS_OFF + slot * SLOT_SIZE

    def title(self, shop, page):
        return _text(self.data, self.page_off(shop, page), TITLE_LEN)

    def slot(self, shop, page, slot):
        return struct.unpack_from('<5I', self.data, self.slot_off(shop, page, slot))

    def items(self, shop):
        return [it for p in range(N_PAGES) for s in range(N_SLOTS) for it in [self.slot(shop, p, s)[0]] if it]

    def search(self, text, limit=500):
        t = text.strip()
        if not t:
            return list(self.shops)[:limit]
        if t.isdigit():
            v = int(t)
            return [s for s in self.shops if s.id == v or any(n[0] == v for n in s.npcs)]
        tl = t.lower()
        return [s for s in self.shops if tl in s.name.lower() or any(tl in n[1].lower() for n in s.npcs)][:limit]

    def where_sold(self, item_id):
        """Every (shop, page, slot) that sells this item."""
        out = []
        for sh in self.shops:
            for p in range(N_PAGES):
                for k in range(N_SLOTS):
                    if self.slot(sh, p, k)[0] == item_id:
                        out.append((sh, p, k))
        return out

    def shops_selling(self, item_id):
        return [s for s in self.shops if item_id in self.items(s)]

    # ------------------------------------------------------------- editing
    def set_item(self, shop, page, slot, item_id):
        if not 0 <= item_id < 200000:
            raise ValueError('item id must be 0 (empty) to 199999')
        o = self.slot_off(shop, page, slot)
        if item_id == 0:
            struct.pack_into('<5I', self.data, o, 0, 0, 0, 0, 0)   # empty slot: all zero, like stock empty slots
        else:
            struct.pack_into('<I', self.data, o, item_id)           # extra fields kept as they are
        self.dirty = True

    def set_title(self, shop, page, text):
        raw = text.encode('utf-16le')
        if len(raw) > TITLE_LEN - 2:
            raise ValueError('page title is too long (max %d characters)' % (TITLE_LEN // 2 - 1))
        o = self.page_off(shop, page)
        self.data[o:o + TITLE_LEN] = raw + b'\x00' * (TITLE_LEN - len(raw))
        self.dirty = True

    def validate(self, shop, item_index=None):
        warnings = []
        if item_index is not None and item_index.ready:
            for p in range(N_PAGES):
                for s in range(N_SLOTS):
                    it = self.slot(shop, p, s)[0]
                    if it and not item_index.by_id(it):
                        warnings.append('page %d slot %d: item %d has no named item record (the slot may show empty in game)' % (p + 1, s + 1, it))
        return warnings

    def save(self, out_path):
        if os.path.normcase(os.path.abspath(out_path)) == os.path.normcase(os.path.abspath(self.path)):
            raise NpcShopError('refusing to overwrite the file that is open; save under a new name')
        with open(out_path, 'wb') as f:
            f.write(self.data)
        check = NpcShops(out_path)
        if (check.shop_start, check.shop_count, len(check.data)) != (self.shop_start, self.shop_count, len(self.data)):
            raise NpcShopError('saved file does not read back the same way - do not use it')
        self.dirty = False
        return check.md5_loaded
