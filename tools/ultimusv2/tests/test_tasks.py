"""Usage: python tests/test_tasks.py <tasks.data>   (any t187 tasks.data: stock or edited)"""
import hashlib, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pwedit.tasks import TasksFile, TasksError, plain
ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m) or c
P = sys.argv[1]; allok = True
t0 = time.time(); tf = TasksFile(P)
allok &= ok(len(tf.quests) == 20122, 'loaded %d quests, version %d (%.1fs)' % (len(tf.quests), tf.version, time.time() - t0))
md5 = lambda: hashlib.md5(tf.data).hexdigest()
IN = md5()
q = tf.search('22076')[0]; g = tf.groups(q)
allok &= ok(plain(q.name) == "Jones' Blessing" and len(g) == 1 and g[0].rows[0][1:] == (22198, 1, 1, 1.0, 604800), "quest 22076 reward = Jones' 22198 x1, 7 days")
allok &= ok(any(x.id == 22208 for x in tf.quests_giving(28524)), "quests_giving(28524) finds O'Malley's Serendipity 22208")
# round trip on a stock quest: delete the last reward row of the Genie Pack (18930), add it back -> same bytes as the input
q = tf.search('18930')[0]; g = tf.groups(q)[0]; last = g.rows[-1]
n = len(tf.data); tf.delete_row(q, g, len(g.rows) - 1)
allok &= ok(len(tf.data) == n - 17, 'deleting a reward row removes 17 bytes')
tf.add_row(q, tf.groups(q)[0], 0); g = tf.groups(q)[0]
tf.set_row(g.rows[-1][0], *last[1:])
allok &= ok(md5() == IN, 'adding the same row back gives the input file byte for byte')
# same-size edit + save + reload
q = tf.search('22208')[0]; g = tf.groups(q)[0]
tf.set_row(g.rows[0][0], 28524, 1, 1, 1.0, 1209600)
out = os.path.join(tempfile.mkdtemp(), 't.data'); m = tf.save(out)
t2 = TasksFile(out); r = t2.groups(t2.search('22208')[0])[0].rows[0]
allok &= ok(r[5] == 1209600 and len(t2.data) == len(tf.data), "O'Malley's period changed to 14 days, saved and reloaded")
try: tf.save(P); allok &= ok(False, 'refuses to overwrite opened file')
except TasksError: allok &= ok(True, 'refuses to overwrite opened file')
try: tf.set_row(r[0], 28524, 1, 1, 1.5, 0); allok &= ok(False, 'chance > 100% rejected')
except ValueError: allok &= ok(True, 'chance > 100% rejected')
q = tf.search('22076')[0]; g = tf.groups(q)[0]
try: tf.delete_row(q, g, 0); allok &= ok(False, 'deleting the only row refused')
except ValueError: allok &= ok(True, 'deleting the only row refused')
e, w = tf.validate([tf.search('18930')[0]]); allok &= ok(not e and not w, 'Genie Pack table validates clean (sums to 100%%): %s' % w)
print('\nALL PASS' if allok else '\nSOME TESTS FAILED')
