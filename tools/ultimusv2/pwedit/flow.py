"""Item flow: where an item comes from and where it goes, across elements.data, tasks.data and the Boutique.

Every link here was mapped on our own files (layouts/elements_flow.json). Read-only.
"""
import bisect
import json
import os
import struct

from .layout import base_dir
from .tasks import ROW, ROW_SIZE, plain

with open(os.path.join(base_dir(), 'layouts', 'elements_flow.json'), 'r', encoding='utf-8') as _f:
    SPEC = json.load(_f)
MD = SPEC['monster_drops']
RC = SPEC['recipe']
TQ = SPEC['task_item_quest']['offset']
NW_LO, NW_HI = SPEC['quest_needed_window']


def needed_row_ok(it, fl, ct, ch, pe):
    return fl == 1 and 1 <= ct <= 1000000 and ch == 0.0 and 0 <= pe <= 31536000 and 1 <= it < 200000 and it % 256


def period_label(sec):
    if sec == 0:
        return 'permanent'
    for s, lab in ((2592000, '30 days'), (1209600, '14 days'), (604800, '7 days'), (86400, '1 day'), (3600, '1 hour'),
                   (1800, '30 minutes')):
        if sec == s:
            return lab
    return '%d s' % sec


class Node:
    """One line in the flow view. links = [(item_id, text)] shown under it (double-click to follow)."""
    __slots__ = ('kind', 'label', 'detail', 'links')

    def __init__(self, kind, label, detail='', links=None):
        self.kind, self.label, self.detail, self.links = kind, label, detail, links or []


class Flow:
    def __init__(self, index, tasks=None, npcshops=None, pair=None):
        self.ix, self.tasks, self.npcshops, self.pair = index, tasks, npcshops, pair
        self.d = index.data
        self._drops = self._recipes_by_product = self._recipes_by_material = None
        self._quest_of_item = self._items_of_quest = None

    # ------------------------------------------------------------- caches
    def _lst(self, key):
        return self.ix.lists.get(key)

    def _build_drops(self):
        self._drops = {}
        L = self._lst('monsters')
        if not L:
            return
        st, n, R = L
        d = self.d
        for k in range(n):
            o = st + k * R
            rows = [struct.unpack_from('<If', d, o + MD['drops']['offset'] + 8 * j) for j in range(MD['drops']['count'])]
            rows = [(i, p) for i, p in rows if i and p > 0]
            if not rows:
                continue
            mid = struct.unpack_from('<I', d, o)[0]
            pk = struct.unpack_from('<4f', d, o + MD['drop_count_chances']['offset'])
            rolls = struct.unpack_from('<I', d, o + MD['rolls']['offset'])[0]
            for i, p in rows:
                self._drops.setdefault(i, []).append((mid, p, pk, rolls))

    def _build_recipes(self):
        self._recipes_by_product, self._recipes_by_material = {}, {}
        L = self._lst('recipes')
        if not L:
            return
        st, n, R = L
        d = self.d
        for k in range(n):
            o = st + k * R
            rid = struct.unpack_from('<I', d, o)[0]
            prods = [struct.unpack_from('<If', d, o + RC['products']['offset'] + 8 * j) for j in range(RC['products']['count'])]
            prods = [(i, p) for i, p in prods if i and p > 0]
            mats = [struct.unpack_from('<II', d, o + RC['materials']['offset'] + 8 * j) for j in range(RC['materials']['count'])]
            mats = [(i, c) for i, c in mats if i and c]
            coins = struct.unpack_from('<I', d, o + RC['coins']['offset'])[0]
            rec = (rid, prods, mats, coins)
            for i, _ in prods:
                self._recipes_by_product.setdefault(i, []).append(rec)
            for i, _ in mats:
                self._recipes_by_material.setdefault(i, []).append(rec)

    def _build_task_items(self):
        self._quest_of_item, self._items_of_quest = {}, {}
        L = self._lst('task_items')
        if not L or not self.tasks:
            return
        st, n, R = L
        qids = {q.id for q in self.tasks.quests}
        for k in range(n):
            o = st + k * R
            iid, q = struct.unpack_from('<I', self.d, o)[0], struct.unpack_from('<I', self.d, o + TQ)[0]
            if q in qids:
                self._quest_of_item[iid] = q
                self._items_of_quest.setdefault(q, []).append(iid)

    # ------------------------------------------------------------- helpers
    def name(self, iid):
        return self.ix.best_name(iid) or '?'

    def item_text(self, iid, extra=''):
        return '%s (%d)%s' % (self.name(iid), iid, extra)

    @staticmethod
    def per_kill(share, pk, rolls):
        per_roll = sum(pk[k] * (1 - (1 - share) ** k) for k in range(4))
        return 1 - (1 - per_roll) ** max(1, rolls)

    def quest(self, qid):
        if not self.tasks:
            return None
        r = self.tasks.search(str(qid))
        return r[0] if r else None

    def reward_links(self, q):
        out = []
        for g in self.tasks.groups(q):
            for _, iid, _, cnt, ch, per in g.rows:
                out.append((iid, self.item_text(iid, '  x%d, %.4g%%, %s' % (cnt, ch * 100, period_label(per)))))
        return out

    def needed_rows(self, q):
        """chance-0 item rows inside a quest = items it needs or takes (tickets, keys, orders)."""
        d = self.tasks.data
        o, e = self.tasks.extent(q)
        out, h, end = [], o + NW_LO, min(e, o + NW_HI)
        while h + ROW_SIZE <= end:
            it, fl, ct, ch, pe = ROW.unpack_from(d, h)
            if needed_row_ok(it, fl, ct, ch, pe) and self.ix.best_name(it):
                out.append((it, ct))
                h += ROW_SIZE
            else:
                h += 1
        return out

    def quests_needing(self, iid):
        d = self.tasks.data
        p = struct.pack('<I', iid)
        res, seen = [], set()
        tab = self.tasks.table()
        i = d.find(p, tab[0])
        while i != -1:
            if i + ROW_SIZE <= len(d):
                it, fl, ct, ch, pe = ROW.unpack_from(d, i)
                k = bisect.bisect_right(tab, i) - 1
                if needed_row_ok(it, fl, ct, ch, pe) and k >= 0 and NW_LO <= i - tab[k] < NW_HI:
                    q = self.tasks.quests[k]
                    if q.id not in seen:
                        seen.add(q.id)
                        res.append((q, ct))
            i = d.find(p, i + 1)
        return res

    def starters(self, q):
        """Items that start or are needed by a quest: list-75 items pointing at it, plus its needed rows."""
        if self._quest_of_item is None:
            self._build_task_items()
        out = [(i, self.item_text(i, '  (opens this quest)')) for i in self._items_of_quest.get(q.id, [])]
        out += [(i, self.item_text(i, '  (needed x%d)' % c)) for i, c in self.needed_rows(q)]
        return out

    # ------------------------------------------------------------- the two sides
    def comes_from(self, iid, limit=200):
        nodes = []
        if self.npcshops is not None:
            for sh, p, k in self.npcshops.where_sold(iid)[:limit]:
                npcs = ', '.join(n[1] for n in sh.npcs[:5]) + (' +%d more' % (len(sh.npcs) - 5) if len(sh.npcs) > 5 else '')
                nodes.append(Node('shop', 'Sold in NPC shop %d, page "%s"' % (sh.id, self.npcshops.title(sh, p)),
                                  'by ' + (npcs or 'no NPC found')))
        if self.tasks is not None:
            for q in self.tasks.quests_giving(iid)[:limit]:
                rows = [r for g in self.tasks.groups(q) for r in g.rows if r[1] == iid]
                det = '; '.join('x%d, %.4g%%, %s' % (r[3], r[4] * 100, period_label(r[5])) for r in rows[:3])
                nodes.append(Node('quest', 'Quest reward: %d %s' % (q.id, plain(q.name)), det, self.starters(q)))
        if self._drops is None:
            self._build_drops()
        drops = sorted(self._drops.get(iid, []), key=lambda x: -self.per_kill(x[1], x[2], x[3]))
        for mid, p, pk, rolls in drops[:limit]:
            nodes.append(Node('drop', 'Dropped by %s (%d)' % (self.ix.name_in('monster', mid) or 'monster', mid),
                              'about %.3g%% per kill (share %.3g%%, %d roll%s)' % (
                                  self.per_kill(p, pk, rolls) * 100, p * 100, rolls, '' if rolls == 1 else 's')))
        if len(drops) > limit:
            nodes.append(Node('drop', '... %d more monsters' % (len(drops) - limit)))
        if self._recipes_by_product is None:
            self._build_recipes()
        for rid, prods, mats, coins in self._recipes_by_product.get(iid, [])[:limit]:
            ch = sum(p for i, p in prods if i == iid)
            nodes.append(Node('craft', 'Crafted by recipe %d' % rid, '%.3g%% of crafts give this; coins %d (inferred)' % (ch * 100, coins),
                              [(i, self.item_text(i, '  x%d' % c)) for i, c in mats]))
        if self.pair is not None:
            for i in range(len(self.pair)):
                if self.pair.client.get(i, 'item_id') == iid:
                    r = self.pair.row(i)
                    nodes.append(Node('boutique', 'Boutique record %d (%s)' % (i, self.pair.tab_name(r['main_tab'], r['sub_tab'])),
                                      'x%d, price %d, duration %d s' % (r['count'], r['price'], r['duration'])))
        return nodes

    def goes_to(self, iid, limit=200):
        nodes = []
        if self.tasks is not None:
            if self._quest_of_item is None:
                self._build_task_items()
            q_id = self._quest_of_item.get(iid)
            if q_id:
                q = self.quest(q_id)
                if q:
                    nodes.append(Node('opens', 'Opens quest %d %s' % (q.id, plain(q.name)), 'when used', self.reward_links(q)))
            for q, cnt in self.quests_needing(iid)[:limit]:
                nodes.append(Node('needed', 'Needed by quest %d %s' % (q.id, plain(q.name)), 'x%d' % cnt, self.reward_links(q)))
        if self._recipes_by_material is None:
            self._build_recipes()
        for rid, prods, mats, coins in self._recipes_by_material.get(iid, [])[:limit]:
            cnt = sum(c for i, c in mats if i == iid)
            nodes.append(Node('material', 'Material in recipe %d' % rid, 'x%d' % cnt,
                              [(i, self.item_text(i, '  %.3g%%' % (p * 100))) for i, p in prods]))
        return nodes
