import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_tk
from pwedit import gui
el, tasks = sys.argv[1:3]
fd, mb = fake_tk.fd, fake_tk.mb
folder = tempfile.mkdtemp()
os.symlink(el, os.path.join(folder, 'elements.data')); os.symlink(tasks, os.path.join(folder, 'tasks.data'))
app = gui.App(fake_tk.Tk())
fd.answers = [folder]; app.open_folder()
t0 = time.time()
while app.tasks is None and time.time() - t0 < 90: time.sleep(0.2); app.poll()
app.poll()
def texts(side): return [r[2] for r in app.flow_trees[side].rows]
app.flow_var.set("Jones' Blessing"); app.flow_go()
assert "Jones' Blessing (22198)" in app.flow_title['text'], app.flow_title['text']
f = texts('from'); assert any('Quest reward: 22076' in x for x in f) and any("Jones' Blessing Ticket (28297)" in x for x in f), f[:6]
# follow the ticket link
tv = app.flow_trees['from']; lk = [r[0] for r in tv.rows if r[0].startswith('L28297_')][0]
tv.sel = (lk,); app.flow_follow(tv)
assert app.flow_var.get() == '28297' and any('Needed by quest 22076' in x for x in texts('to'))
app.flow_back(); assert app.flow_var.get() == '22198'
app.flow_var.set('20449'); app.flow_go()
assert any('Material in recipe' in x for x in texts('to')) and any('End of Elysium' in x for x in texts('to'))
app.flow_var.set('8617'); app.flow_go(); assert any('Sold in NPC shop' in x for x in texts('from'))
# a monster drop
app.flow_var.set('20943'); app.flow_go()
assert any('Dropped by Skeleton Legion Marshal' in x for x in texts('from')), texts('from')[:5]
# from Item lookup button
app.search_var.set('Nirvana Palace Key'); app.search(); app.itv.selection_set('0'); app.flow_from_lookup()
assert any('Enter the Palace of Nirvana' in x for x in texts('to'))
print('ITEM FLOW TAB LOGIC: ALL PASS')
