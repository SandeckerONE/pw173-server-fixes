import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_tk
from pwedit import gui
from pwedit.known import describe
el, tasks, c1, s1 = sys.argv[1:5]
fd, mb = fake_tk.fd, fake_tk.mb
folder = tempfile.mkdtemp()
os.symlink(el, os.path.join(folder, 'elements.data')); os.symlink(tasks, os.path.join(folder, 'tasks.data'))
app = gui.App(fake_tk.Tk())
fd.answers = [folder]; app.open_folder()
t0 = time.time()
while app.tasks is None and time.time() - t0 < 90: time.sleep(0.2); app.poll()
app.poll()
assert app.index.ready and app.npcshops and app.tasks
assert app.index.data is app.npcshops.data, 'index and NPC shops share one copy of elements.data'
info = app.data_info['text']; print('   info:', info)
assert 'live UltimusV2 (Palette' in info and 'BH1' in info and 'OLD' not in info
assert not any(x[0] == 'showwarning' for x in mb.shown), 'no warning for live files'
# where-used for Jones' Blessing Ticket (quests? no; NPC? no) and Small Healing Potion (NPC shops) and Jones' Blessing (quest 22076)
w = app.where_used(22198); print('\n'.join('   ' + l for l in w.splitlines()[:6]))
assert "quest 22076 Jones' Blessing" in w
w2 = app.where_used(8617); assert 'Sold in NPC shops: ' in w2 and 'sold by' in w2
print('\n'.join('   ' + l for l in w2.splitlines()[:4]))
# double-click jump from a quest reward
app.qsearch_var.set('22208'); app.quest_search(); app.qtv.selection_set('0'); app.rtv.selection_set('0:0'); app._dbl_reward()
assert "O'Malley's Blessing" in app.dumpbox.t.splitlines()[0], app.dumpbox.t[:200]
# jump from NPC slot
app.nsearch_var.set('2673'); app.npc_search(); app.stv.selection_set('0'); app.sltv.selection_set('0'); app._dbl_slot()
assert 'Broken Red Jade' in app.dumpbox.t
# Boutique pair + where-used includes Boutique
fd.answers = [c1, s1]; app.open_pair(); app.tv.selection_set('149'); app._dbl_shoprec()
assert 'In the open Boutique pair: 1 record' in app.dumpbox.t, app.dumpbox.t[:600]
# known-version tags
assert describe('x/tasks.data', '9abe2781e0373d25ca5a9a2b4f915b1d')[1] == 'old'
assert describe('x/elements.data', 'f67769d87bcc00c0c00e58fc8fcfca31')[1] == 'old'
assert describe('x/elements_copy.data', 'c89984b59b8372a794a0e5c9da9f9f33')[1] == 'live'
assert describe('x/whatever.data', '0' * 32)[1] == 'unknown'
print('FOLDER / CROSS-INTEGRATION: ALL PASS')
