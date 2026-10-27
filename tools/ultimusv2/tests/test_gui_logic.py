import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_tk
from pwedit import gui
from pwedit.shop import ShopPair
c, s, el = sys.argv[1:4]
fd, mb = fake_tk.fd, fake_tk.mb
app = gui.App(fake_tk.Tk())
fd.answers = [c, s]; app.open_pair()
assert app.pair and len(app.tv.rows) == len(app.pair), 'list filled'
app.tv.selection_set('149')                      # Jones' ticket record
assert app.v['item_id'].get() == '28297', app.v['item_id'].get()
app.v['price'].set('700'); app.apply()
assert app.pair.row(149)['price'] == 700
assert app.pair.row(149)['description'] == ShopPair(c, s).row(149)['description'], 'description round-trips through the text box'
app.add_copy(); new = len(app.pair) - 1
assert app.selected() == new
app.v['duration'].set('7 days (604800)'); app.v['count'].set('5'); app.apply()
assert mb.shown and mb.shown[-1][0] == 'showerror', 'timed+stacked refused in the form'
app.v['count'].set('1'); app.apply()
assert app.pair.row(new)['duration'] == 604800
app.move(-1); assert app.selected() == new - 1
app.delete(); assert len(app.pair) == 158
app.validate()
tmp = tempfile.mkdtemp()
fd.answers = [os.path.join(tmp, 'c.data'), os.path.join(tmp, 's.data')]; app.save_pair()
assert os.path.exists(os.path.join(tmp, 'c.data')) and not app.dirty, mb.shown[-1]
p2 = ShopPair(os.path.join(tmp, 'c.data'), os.path.join(tmp, 's.data'))
assert p2.row(149)['price'] == 700 and not p2.problems
fd.answers = [c, s]  # saving over the opened files must be refused
app.pair.update(0, price=1); app.dirty = True; app.save_pair()
assert mb.shown[-1][0] == 'showerror' and 'refusing' in str(mb.shown[-1][1])
# item tab
fd.answers = [el]; app.open_elements()
t0 = time.time()
while not app.index.ready and time.time() - t0 < 60: time.sleep(0.2); app.poll()
app.poll()
assert app.index.ready
app.search_var.set("O'Malley"); app.search()
assert any(r[1][0] == 28524 for r in app.itv.rows), app.itv.rows[:5]
k = [r[0] for r in app.itv.rows if r[1][0] == 28524][0]
app.itv.selection_set(k); app.on_item_select()
assert 'AD_L05' in app.dumpbox.t
app.tv.selection_set('10'); app.use_in_shop()
assert app.v['item_id'].get() == '28524'
app.v['item_id'].set('22198'); app.fill_name(); assert app.v['name'].get() == "Jones' Blessing"
print('GUI LOGIC: ALL PASS')
print('--- log tail ---'); print('\n'.join(app.logbox.t.splitlines()[-6:]))
