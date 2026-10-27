"""Usage: python tests/test_npcshops.py <elements.data copy>"""
import hashlib, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pwedit.npcshop import NpcShops, NpcShopError
from pwedit.elements import ItemIndex
ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m) or c
P = sys.argv[1]; allok = True
t0 = time.time(); ns = NpcShops(P)
allok &= ok(ns.shop_count == 174 and ns.shop_start == 35762472, 'shop list found: %d shops at %d (%.1fs); %d NPCs' % (ns.shop_count, ns.shop_start, time.time() - t0, ns.npc_count))
s = ns.by_id[2673]
allok &= ok(any(n[1] == 'Merchant Wang Song' for n in s.npcs), 'shop 2673 is sold by Merchant Wang Song: %s' % s.npcs[:3])
allok &= ok([ns.title(s, p) for p in range(3)] == ['Jade', 'Misc.', 'Gem'], 'shop 2673 page titles Jade / Misc. / Gem')
allok &= ok(ns.slot(s, 0, 0)[0] == 773, 'page 1 slot 1 = 773')
r = ns.search('wang song'); allok &= ok(s in r, 'search by NPC name finds the shop')
ix = ItemIndex(); ix.load(P)
pots = ns.shops_selling(8617); allok &= ok(len(pots) >= 1, '%d shops sell Small Healing Potion (8617)' % len(pots))
w = ns.validate(s, ix); print('   validate 2673:', len(w), 'warnings, e.g.', w[:1])
orig = bytes(ns.data)
# edits
p1 = ns.slot(s, 1, 0)
ns.set_item(s, 1, 0, 22198)             # replace a used slot (extras kept)
ns.set_item(s, 1, 31, 28297)            # fill an empty slot
ns.set_item(s, 0, 2, 0)                 # clear a slot
ns.set_title(s, 7, 'Blessings')
try: ns.set_title(s, 0, 'x' * 16); allok &= ok(False, 'long title rejected')
except ValueError: allok &= ok(True, 'long title rejected (max 15)')
diff = [i for i in range(len(orig)) if orig[i] != ns.data[i]] if False else None
import numpy as np
a = np.frombuffer(orig, dtype=np.uint8); b = np.frombuffer(bytes(ns.data), dtype=np.uint8)
idx = np.nonzero(a != b)[0]
lo, hi = s.off, s.off + 5448
allok &= ok(len(idx) > 0 and idx.min() >= lo and idx.max() < hi, 'only bytes inside shop 2673 changed (%d bytes)' % len(idx))
out = os.path.join(tempfile.mkdtemp(), 'e.data'); m = ns.save(out)
n2 = NpcShops(out); s2 = n2.by_id[2673]
allok &= ok(n2.slot(s2, 1, 0) == (22198,) + p1[1:] and n2.slot(s2, 1, 31)[0] == 28297 and n2.slot(s2, 0, 2) == (0, 0, 0, 0, 0) and n2.title(s2, 7) == 'Blessings', 'edits saved and reloaded')
allok &= ok(len(n2.data) == len(orig), 'same file size')
try: ns.save(P); allok &= ok(False, 'refuses to overwrite opened file')
except NpcShopError: allok &= ok(True, 'refuses to overwrite opened file')
u = NpcShops(P); allok &= ok(hashlib.md5(u.data).hexdigest() == hashlib.md5(orig).hexdigest(), 'opened file untouched')
print('\nALL PASS' if allok else '\nSOME TESTS FAILED')
