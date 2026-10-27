import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_tk
from pwedit import gui
from pwedit.npcshop import NpcShops
el = sys.argv[1]
fd, mb = fake_tk.fd, fake_tk.mb
app = gui.App(fake_tk.Tk())
def wait(cond):
    t0 = time.time()
    while not cond() and time.time() - t0 < 90: time.sleep(0.2); app.poll()
fd.answers = [el]; app.open_elements(); wait(lambda: app.index.ready)
fd.answers = [el]; app.open_npcshops(); wait(lambda: app.npcshops is not None)
assert len(app.stv.rows) == 174, len(app.stv.rows)
app.nsearch_var.set('Wang Song'); app.npc_search()
k = [r[0] for r in app.stv.rows if r[1][0] == 2673][0]; app.stv.selection_set(k)
assert app.page_cb['values'][:3] == ['1 Jade', '2 Misc.', '3 Gem'], app.page_cb['values']
assert app.sltv.rows[0][1][2] == 'Broken Red Jade', app.sltv.rows[0]
app.page_var.set('2 Misc.'); app.show_slots()
app.sltv.selection_set('31'); app.sitem_var.set('28297'); app.apply_slot()
assert app.npcshops.slot(app.cur_shop, 1, 31)[0] == 28297
app.search_var.set("Jones' Blessing"); app.search()
kk = [r[0] for r in app.itv.rows if r[1][0] == 22198][0]; app.itv.selection_set(kk)
app.sltv.selection_set('30'); app.slot_from_lookup(); app.apply_slot()
assert app.npcshops.slot(app.cur_shop, 1, 30)[0] == 22198
app.sltv.selection_set('30'); app.clear_slot(); assert app.npcshops.slot(app.cur_shop, 1, 30) == (0, 0, 0, 0, 0)
app.page_var.set('8 (no title)'); app.show_slots(); app.ptitle_var.set('Blessings'); app.rename_page()
assert app.npcshops.title(app.cur_shop, 7) == 'Blessings' and app.page_cb['values'][7] == '8 Blessings'
app.ptitle_var.set('x' * 20); app.rename_page(); assert mb.shown[-1][0] == 'showerror'
app.nsearch_var.set('item:28297'); app.npc_search(); assert any(r[1][0] == 2673 for r in app.stv.rows)
app.validate_shop()
out = os.path.join(tempfile.mkdtemp(), 'e.data'); fd.answers = [out]; app.save_npcshops()
n2 = NpcShops(out); s2 = n2.by_id[2673]
assert n2.slot(s2, 1, 31)[0] == 28297 and n2.title(s2, 7) == 'Blessings'
fd.answers = [el]; app.npcshops.dirty = True; app.save_npcshops(); assert mb.shown[-1][0] == 'showerror'
print('NPC SHOP TAB LOGIC: ALL PASS')
print('\n'.join(app.nlogbox.t.splitlines()[-5:]))
