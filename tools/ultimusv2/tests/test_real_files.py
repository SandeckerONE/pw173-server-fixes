"""Runs against real files. Usage: python tests/test_real_files.py <client gshop1.data> <server gshopsev1.data> [<client gshop.data>] [<elements.data copy>]"""
import hashlib, os, struct, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pwedit.shop import ShopFile, ShopPair, ShopError
from pwedit.elements import ItemIndex

ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m) or c
cpath, spath = sys.argv[1], sys.argv[2]
allok = True
# 1 round trip
for p in (cpath, spath):
    f = ShopFile(p)
    allok &= ok(f.to_bytes() == open(p, 'rb').read(), 'round trip unchanged: %s (%s, %d records)' % (os.path.basename(p), f.side, len(f.records)))
pair = ShopPair(cpath, spath)
allok &= ok(not pair.problems, 'pairing clean (%d problems)' % len(pair.problems))
err, warn = pair.validate()
allok &= ok(not err, 'validate: %d errors, %d warnings' % (len(err), len(warn)))
for w in warn[:5]: print('   warning:', w)
print('   tabs:', [(m, s) for m, s in pair.tree])
# 2 edits
tmp = tempfile.mkdtemp()
i = 0
before = pair.row(i)
pair.update(i, price=before['price'] + 100, name='Test Name')
n0 = len(pair)
j = pair.add_copy(i)
pair.update(j, item_id=28297, name="Jones' Blessing Ticket", duration=0, count=1)
pair.delete(1)
co, so = os.path.join(tmp, 'c.data'), os.path.join(tmp, 's.data')
md5c, md5s = pair.save(co, so)
p2 = ShopPair(co, so)
allok &= ok(len(p2) == n0, 'after add+delete count is %d' % len(p2))
allok &= ok(p2.row(0)['price'] == before['price'] + 100 and p2.row(0)['name'] == 'Test Name', 'edit saved on record 0')
allok &= ok(p2.row(len(p2) - 1)['item_id'] == 28297, 'added record saved at the end')
allok &= ok(all(struct.unpack_from('<i', open(co, 'rb').read(), 8 + k * 1448)[0] == k for k in range(len(p2))), 'client lids renumbered')
allok &= ok(not p2.problems, 'saved pair still pairs cleanly')
allok &= ok(open(co, 'rb').read()[:4] == open(cpath, 'rb').read()[:4], 'stamp unchanged')
# 3 safety
try:
    pair.save(cpath, so); allok &= ok(False, 'refused to overwrite opened file')
except ShopError:
    allok &= ok(True, 'refused to overwrite opened file')
pair.update(0, duration=604800, count=5)
e, w = pair.validate()
allok &= ok(any('stop the maps' in x for x in e), 'timed + stacked purchase is blocked')
try:
    pair.update(0, name='x' * 40); allok &= ok(False, 'too-long name rejected')
except ValueError:
    allok &= ok(True, 'too-long name rejected')
# 4 main boutique client file
if len(sys.argv) > 3:
    m = ShopFile(sys.argv[3])
    allok &= ok(m.to_bytes() == open(sys.argv[3], 'rb').read(), 'main boutique round trip (%d records)' % len(m.records))
    bad = [k for k in range(len(m.records)) if m.get(k, 'duration') > 0 and m.get(k, 'count') > 1]
    allok &= ok(not bad, 'stock main boutique has no timed+stacked records (rule is consistent): %s' % bad[:5])
# 5 item index
if len(sys.argv) > 4:
    ix = ItemIndex(); ix.load(sys.argv[4])
    print('   index entries:', len(ix.entries))
    for iid, name, back in ((22198, "Jones' Blessing", 12), (28297, "Jones' Blessing Ticket", 4), (48056, 'Peerless Blessing', 12)):
        hits = [e for e in ix.by_id(iid) if e.name == name]
        allok &= ok(bool(hits) and hits[0].back == back, 'index finds %s (%d) with id at name-%d' % (name, iid, back))
    allok &= ok(ix.best_name(28524) == "O'Malley's Blessing", 'best_name 28524')
    r = ix.search('jones')
    print('   search "jones":', [(e.id, e.name) for e in r[:6]])
    d = ix.dump(ix.by_id(22198)[0])
    allok &= ok('AD_L08' in d, 'dump of Jones shows its stat entry AD_L08')
print('\nALL PASS' if allok else '\nSOME TESTS FAILED')
