import os, sys, tempfile, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_tk
from pwedit import gui
from pwedit.tasks import TasksFile
tasks, el = sys.argv[1:3]
fd, mb = fake_tk.fd, fake_tk.mb
app = gui.App(fake_tk.Tk())
def wait(cond):
    t0 = time.time()
    while not cond() and time.time() - t0 < 90: time.sleep(0.2); app.poll()
fd.answers = [el]; app.open_elements(); wait(lambda: app.index.ready)
fd.answers = [tasks]; app.open_tasks(); wait(lambda: app.tasks is not None)
assert app.tasks and len(app.tasks.quests) == 20122
app.qsearch_var.set('item:22198'); app.quest_search()
ids = [r[1][0] for r in app.qtv.rows]; assert 22076 in ids, ids
k = [r[0] for r in app.qtv.rows if r[1][0] == 22076][0]
app.qtv.selection_set(k)
assert app.rtv.rows and app.rtv.rows[0][1][3] == "Jones' Blessing", app.rtv.rows
app.rtv.selection_set('0:0')
assert app.qv['item'].get() == '22198' and app.qv['period'].get().startswith('7 days')
app.qv['period'].set('14 days (1209600)'); app.apply_reward()
assert app.tasks.groups(app.cur_quest)[0].rows[0][5] == 1209600
app.add_reward(); assert len(app.tasks.groups(app.cur_quest)[0].rows) == 2
# item from lookup
app.search_var.set("O'Malley's Blessing"); app.search()
kk = [r[0] for r in app.itv.rows if r[1][0] == 28524][0]; app.itv.selection_set(kk)
app.rtv.selection_set('0:1'); app.item_from_lookup(); app.qv['count'].set('2'); app.apply_reward()
g = app.tasks.groups(app.cur_quest)[0]; assert g.rows[1][1] == 28524 and g.rows[1][3] == 2
app.qv['chance'].set('150'); app.apply_reward(); assert mb.shown[-1][0] == 'showerror'
app.rtv.selection_set('0:1'); app.delete_reward(); assert len(app.tasks.groups(app.cur_quest)[0].rows) == 1
app.validate_quest()
out = os.path.join(tempfile.mkdtemp(), 't.data'); fd.answers = [out]; app.save_tasks()
t2 = TasksFile(out); r = t2.groups(t2.search('22076')[0])[0].rows[0]
assert r[1] == 22198 and r[5] == 1209600 and len(t2.data) == len(app.tasks.data)
fd.answers = [tasks]; app.save_tasks(); assert mb.shown[-1][0] == 'showerror', 'overwrite refused'
app.qsearch_var.set('genie pack'); app.quest_search(); assert app.qtv.rows
print('QUEST TAB LOGIC: ALL PASS')
print('\n'.join(app.qlogbox.t.splitlines()[-5:]))
