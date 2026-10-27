"""PW173 Editor window: Shop editor (client + server boutique pair) and Item lookup (elements.data, read-only)."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .elements import ItemIndex
from .shop import DURATIONS, ShopError, ShopPair
from .tasks import TasksError, TasksFile, plain
from .npcshop import N_PAGES, N_SLOTS, NpcShopError, NpcShops
from .known import describe
from .flow import Flow

PERIODS = [('permanent', 0), ('30 minutes', 1800), ('1 hour', 3600), ('1 day', 86400), ('7 days', 604800),
           ('14 days', 1209600), ('30 days', 2592000)]


def period_text(sec):
    for label, v in PERIODS:
        if v == sec:
            return '%s (%d)' % (label, v)
    return str(sec)

APP = 'PW173 Editor (in-house, 1.7.3 e344)'


def dur_text(sec):
    for label, v in DURATIONS:
        if v == sec:
            return '%s (%d)' % (label, v)
    return str(sec)


def parse_int(text, what):
    t = str(text).strip()
    if '(' in t and t.endswith(')'):
        t = t[t.rfind('(') + 1:-1]
    try:
        return int(t)
    except ValueError:
        raise ValueError('%s must be a whole number (got %r)' % (what, text))


class App:
    def __init__(self, root):
        self.root = root
        self.pair = None
        self.dirty = False
        self.tasks = None
        self.npcshops = None
        self.index = ItemIndex()
        self.q = queue.Queue()
        self.view_rows = []  # record indexes shown in the list, in order
        root.title(APP)
        root.geometry('1250x780')
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        bar = ttk.Frame(root)
        bar.pack(fill='x', padx=6, pady=(6, 0))
        ttk.Button(bar, text='Open game data folder...', command=self.open_folder).pack(side='left')
        self.data_info = ttk.Label(bar, text='Tip: open the element\\data folder of a client to load elements.data and '
                                             'tasks.data together (item names everywhere, where-used lookups).')
        self.data_info.pack(side='left', padx=10)
        self.data_folder = None
        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True)
        self.nb = nb
        self.shop_tab = ttk.Frame(nb)
        self.item_tab = ttk.Frame(nb)
        self.quest_tab = ttk.Frame(nb)
        nb.add(self.shop_tab, text='Shop editor')
        nb.add(self.item_tab, text='Item lookup')
        nb.add(self.quest_tab, text='Quest rewards')
        self.npc_tab = ttk.Frame(nb)
        nb.add(self.npc_tab, text='NPC shops')
        self.flow_tab = ttk.Frame(nb)
        nb.add(self.flow_tab, text='Item flow')
        self._flow = None
        self._flow_key = None
        self.flow_hist = []
        self.tasks = None
        self.npcshops = None
        self.build_shop_tab()
        self.build_item_tab()
        self.build_quest_tab()
        self.build_npc_tab()
        self.build_flow_tab()
        self.log('Ready. Open a boutique pair (client gshop*.data + server gshopsev*.data). '
                 'Files you open are never overwritten: saving always writes new files.')
        root.after(150, self.poll)

    # ---------------------------------------------------------------- shop tab
    def build_shop_tab(self):
        f = self.shop_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Button(top, text='Open pair...', command=self.open_pair).pack(side='left')
        ttk.Button(top, text='Validate', command=self.validate).pack(side='left', padx=4)
        ttk.Button(top, text='Save pair as...', command=self.save_pair).pack(side='left')
        self.info = ttk.Label(top, text='No files open')
        self.info.pack(side='left', padx=10)

        body = ttk.PanedWindow(f, orient='horizontal')
        body.pack(fill='both', expand=True, padx=6)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        flt = ttk.Frame(left)
        flt.pack(fill='x')
        ttk.Label(flt, text='Filter (name or item id):').pack(side='left')
        self.filter_var = tk.StringVar()
        e = ttk.Entry(flt, textvariable=self.filter_var)
        e.pack(side='left', fill='x', expand=True, padx=4)
        e.bind('<Return>', lambda ev: self.refresh_list())
        ttk.Button(flt, text='Apply filter', command=self.refresh_list).pack(side='left')

        cols = ('rec', 'tab', 'item', 'name', 'count', 'price', 'duration', 'label')
        heads = ('#', 'Tab', 'Item id', 'Name', 'Count', 'Price', 'Duration', 'Label')
        widths = (50, 150, 70, 260, 55, 70, 120, 50)
        tv = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse')
        for c, h, w in zip(cols, heads, widths):
            tv.heading(c, text=h)
            tv.column(c, width=w, anchor='w')
        sb = ttk.Scrollbar(left, orient='vertical', command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        tv.bind('<<TreeviewSelect>>', self.on_select)
        tv.bind('<Double-1>', self._dbl_shoprec)
        self.tv = tv

        form = ttk.LabelFrame(right, text='Selected record (changes apply to client AND server)')
        form.pack(fill='both', expand=True, padx=4)
        self.v = {k: tk.StringVar() for k in ('item_id', 'name', 'count', 'price', 'duration', 'label', 'main', 'sub')}
        r = 0

        def row(label, widget, extra=None):
            nonlocal r
            ttk.Label(form, text=label).grid(row=r, column=0, sticky='w', padx=4, pady=2)
            widget.grid(row=r, column=1, sticky='we', padx=4, pady=2)
            if extra is not None:
                extra.grid(row=r, column=2, sticky='w', padx=4)
            r += 1

        form.columnconfigure(1, weight=1)
        row('Item id', ttk.Entry(form, textvariable=self.v['item_id']),
            ttk.Button(form, text='Name from elements', command=self.fill_name))
        row('Shop name (max 31)', ttk.Entry(form, textvariable=self.v['name']))
        row('Count per purchase', ttk.Entry(form, textvariable=self.v['count']))
        self.price_hint = ttk.Label(form, text='')
        row('Price (x100)', ttk.Entry(form, textvariable=self.v['price']), self.price_hint)
        self.v['price'].trace_add('write', lambda *a: self.update_price_hint())
        dur = ttk.Combobox(form, textvariable=self.v['duration'], values=[dur_text(s) for _, s in DURATIONS])
        row('Duration (seconds)', dur)
        self.main_cb = ttk.Combobox(form, textvariable=self.v['main'], state='readonly')
        self.main_cb.bind('<<ComboboxSelected>>', lambda ev: self.fill_subs())
        row('Main tab', self.main_cb)
        self.sub_cb = ttk.Combobox(form, textvariable=self.v['sub'], state='readonly')
        row('Sub tab', self.sub_cb)
        row('Status label', ttk.Entry(form, textvariable=self.v['label']),
            ttk.Label(form, text='badge, probably New/Hot/Sale (inferred)'))
        ttk.Label(form, text='Description\n(^rrggbb = colour)').grid(row=r, column=0, sticky='nw', padx=4)
        self.desc = tk.Text(form, height=10, wrap='word')
        self.desc.grid(row=r, column=1, columnspan=2, sticky='nsew', padx=4, pady=2)
        form.rowconfigure(r, weight=1)
        r += 1
        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=3, sticky='we', pady=4)
        ttk.Button(btns, text='Apply changes', command=self.apply).pack(side='left', padx=2)
        ttk.Button(btns, text='Add copy at end', command=self.add_copy).pack(side='left', padx=2)
        ttk.Button(btns, text='Delete', command=self.delete).pack(side='left', padx=2)
        ttk.Button(btns, text='Move up', command=lambda: self.move(-1)).pack(side='left', padx=2)
        ttk.Button(btns, text='Move down', command=lambda: self.move(1)).pack(side='left', padx=2)

        self.logbox = tk.Text(f, height=8, wrap='word')
        self.logbox.pack(fill='x', padx=6, pady=4)

    def log(self, msg):
        self.logbox.insert('end', msg + '\n')
        self.logbox.see('end')

    def open_pair(self):
        if self.dirty and not messagebox.askyesno(APP, 'You have unsaved changes. Open another pair anyway?'):
            return
        c = filedialog.askopenfilename(title='1 of 2: CLIENT boutique file (gshop.data or gshop1.data)',
                                       initialdir=self.data_folder or '',
                                       filetypes=[('Boutique data', '*.data'), ('All files', '*.*')])
        if not c:
            return
        s = filedialog.askopenfilename(title='2 of 2: SERVER boutique file (gshopsev.data or gshopsev1.data)',
                                       filetypes=[('Boutique data', '*.data'), ('All files', '*.*')])
        if not s:
            return
        try:
            pair = ShopPair(c, s)
        except (ShopError, OSError) as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.pair, self.dirty = pair, False
        self.info.config(text='%s + %s | %d records | stamp %08x' % (
            os.path.basename(pair.client.path), os.path.basename(pair.server.path), len(pair), pair.client.stamp))
        self.main_cb['values'] = ['%d %s' % (i, m) for i, (m, _) in enumerate(pair.tree)]
        self.log('Opened %s (md5 %s) and %s (md5 %s).' % (pair.client.path, pair.client.md5_loaded,
                                                         pair.server.path, pair.server.md5_loaded))
        for pth, m in ((pair.client.path, pair.client.md5_loaded), (pair.server.path, pair.server.md5_loaded)):
            txt, st = describe(pth, m)
            self.log('  ' + txt)
        if pair.problems:
            self.log('WARNING: the two files do not match each other:\n  ' + '\n  '.join(pair.problems[:20]))
            messagebox.showwarning(APP, 'The client and server files do not match each other (see the log). '
                                        'Saving is blocked until they do. Did you pick files from the same pair?')
        else:
            self.log('Client and server files match record for record.')
        self.refresh_list()

    def refresh_list(self, select=None):
        tv = self.tv
        tv.delete(*tv.get_children())
        self.view_rows = []
        if not self.pair:
            return
        flt = self.filter_var.get().strip().lower()
        for i in range(len(self.pair)):
            r = self.pair.row(i)
            if flt and flt not in r['name'].lower() and flt != str(r['item_id']):
                continue
            self.view_rows.append(i)
            tv.insert('', 'end', iid=str(i), values=(i, self.pair.tab_name(r['main_tab'], r['sub_tab']), r['item_id'],
                                                      r['name'], r['count'], r['price'], dur_text(r['duration']),
                                                      r['status_label']))
        if select is not None and str(select) in tv.get_children():
            tv.selection_set(str(select))
            tv.see(str(select))

    def selected(self):
        sel = self.tv.selection()
        return int(sel[0]) if sel else None

    def on_select(self, ev=None):
        i = self.selected()
        if i is None or not self.pair:
            return
        r = self.pair.row(i)
        self.v['item_id'].set(str(r['item_id']))
        self.v['name'].set(r['name'])
        self.v['count'].set(str(r['count']))
        self.v['price'].set(str(r['price']))
        self.v['duration'].set(dur_text(r['duration']))
        self.v['label'].set(str(r['status_label']))
        tree = self.pair.tree
        m = r['main_tab']
        self.v['main'].set('%d %s' % (m, tree[m][0]) if 0 <= m < len(tree) else str(m))
        self.fill_subs(keep=r['sub_tab'])
        self.desc.delete('1.0', 'end')
        self.desc.insert('1.0', r['description'].replace('\\r', '\n'))  # the game writes line breaks as a literal backslash-r

    def fill_subs(self, keep=None):
        if not self.pair:
            return
        try:
            m = int(self.v['main'].get().split()[0])
        except (ValueError, IndexError):
            return
        subs = self.pair.tree[m][1] if 0 <= m < len(self.pair.tree) else []
        vals = ['%d %s' % (k, s) for k, s in enumerate(subs)] or ['0 (none)']
        self.sub_cb['values'] = vals
        k = keep if keep is not None else 0
        self.v['sub'].set(vals[k] if 0 <= k < len(vals) else str(k))

    def update_price_hint(self):
        try:
            p = int(self.v['price'].get())
            self.price_hint.config(text='= %.2f gold / Event Gold' % (p / 100.0))
        except ValueError:
            self.price_hint.config(text='')

    def fill_name(self):
        if not self.index.ready:
            messagebox.showinfo(APP, 'Load an elements.data copy in the Item lookup tab first.')
            return
        try:
            iid = parse_int(self.v['item_id'].get(), 'Item id')
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        nm = self.index.best_name(iid)
        if nm:
            self.v['name'].set(nm[:31])
            self.log('Item %d is "%s" in elements.data.' % (iid, nm))
        else:
            self.log('Item %d not found by name in elements.data (it may still be real; check it in Item lookup).' % iid)

    def form_values(self):
        vals = {
            'item_id': parse_int(self.v['item_id'].get(), 'Item id'),
            'count': parse_int(self.v['count'].get(), 'Count'),
            'price': parse_int(self.v['price'].get(), 'Price'),
            'duration': parse_int(self.v['duration'].get(), 'Duration'),
            'status_label': parse_int(self.v['label'].get(), 'Status label'),
            'main_tab': parse_int(self.v['main'].get().split()[0] if self.v['main'].get() else '', 'Main tab'),
            'sub_tab': parse_int(self.v['sub'].get().split()[0] if self.v['sub'].get() else '0', 'Sub tab'),
            'name': self.v['name'].get(),
            'description': self.desc.get('1.0', 'end-1c').replace('\n', '\\r'),
        }
        if vals['count'] < 1:
            raise ValueError('Count must be at least 1')
        if vals['duration'] > 0 and vals['count'] > 1:
            raise ValueError('A timed item (duration > 0) bought several at a time must stack, and stackable items with '
                             'a duration stop the maps from starting. Use count 1 or duration 0.')
        return vals

    def apply(self):
        i = self.selected()
        if i is None or not self.pair:
            messagebox.showinfo(APP, 'Select a record first.')
            return
        try:
            vals = self.form_values()
            self.pair.update(i, **vals)
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.dirty = True
        self.log('Record %d updated (item %d, %s).' % (i, vals['item_id'], vals['name']))
        self.refresh_list(select=i)

    def add_copy(self):
        i = self.selected()
        if i is None or not self.pair:
            messagebox.showinfo(APP, 'Select the record to copy first (a similar item in the right tab works best).')
            return
        j = self.pair.add_copy(i)
        self.dirty = True
        self.filter_var.set('')
        self.log('Record %d copied to the end as record %d. Change its item id, name, price and description, then Apply.' % (i, j))
        self.refresh_list(select=j)
        self.on_select()

    def delete(self):
        i = self.selected()
        if i is None or not self.pair:
            return
        r = self.pair.row(i)
        if not messagebox.askyesno(APP, 'Delete record %d (%s, item %d) from both files?' % (i, r['name'], r['item_id'])):
            return
        self.pair.delete(i)
        self.dirty = True
        self.log('Record %d deleted; later records moved up by one.' % i)
        self.refresh_list(select=min(i, len(self.pair) - 1))

    def move(self, step):
        i = self.selected()
        if i is None or not self.pair:
            return
        j = i + step
        if not 0 <= j < len(self.pair):
            return
        self.pair.move(i, j)
        self.dirty = True
        self.refresh_list(select=j)

    def validate(self):
        if not self.pair:
            return
        errors, warnings = self.pair.validate(self.index)
        self.log('Validate: %d errors, %d warnings.' % (len(errors), len(warnings)))
        for e in errors[:30]:
            self.log('  ERROR: ' + e)
        for w in warnings[:30]:
            self.log('  warning: ' + w)
        if not errors and not warnings:
            self.log('  all good.')

    def save_pair(self):
        if not self.pair:
            return
        p = self.pair
        c_dir, c_name = os.path.split(p.client.path)
        s_dir, s_name = os.path.split(p.server.path)
        co = filedialog.asksaveasfilename(title='Save CLIENT file as (new name)', initialdir=c_dir,
                                          initialfile=os.path.splitext(c_name)[0] + '_new.data')
        if not co:
            return
        so = filedialog.asksaveasfilename(title='Save SERVER file as (new name)', initialdir=s_dir,
                                          initialfile=os.path.splitext(s_name)[0] + '_new.data')
        if not so:
            return
        try:
            mc, ms = p.save(co, so)
        except (ShopError, OSError, ValueError) as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.dirty = False
        self.log('Saved:\n  client %s  md5 %s\n  server %s  md5 %s' % (co, mc, so, ms))
        self.log('Next: snapshot the VM, put the server file in /opt/gamed/config/ under its real name, restart, '
                 'check "server status" shows GS (maps) UP after a minute, then swap the client file.')
        messagebox.showinfo(APP, 'Saved both files.\n\nClient md5 %s\nServer md5 %s\n\nSee the log for the next steps.' % (mc, ms))

    # ---------------------------------------------------------------- item tab
    def build_item_tab(self):
        f = self.item_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Button(top, text='Open elements.data (a copy)...', command=self.open_elements).pack(side='left')
        self.prog = ttk.Progressbar(top, length=200, mode='determinate')
        self.prog.pack(side='left', padx=6)
        self.item_info = ttk.Label(top, text='Not loaded (read-only; nothing is ever written to it)')
        self.item_info.pack(side='left')

        srch = ttk.Frame(f)
        srch.pack(fill='x', padx=6)
        ttk.Label(srch, text='Search (name part, or exact item id):').pack(side='left')
        self.search_var = tk.StringVar()
        e = ttk.Entry(srch, textvariable=self.search_var)
        e.pack(side='left', fill='x', expand=True, padx=4)
        e.bind('<Return>', lambda ev: self.search())
        ttk.Button(srch, text='Search', command=self.search).pack(side='left')
        ttk.Button(srch, text='Use in Shop editor', command=self.use_in_shop).pack(side='left', padx=4)
        ttk.Button(srch, text='Show item flow', command=self.flow_from_lookup).pack(side='left')

        body = ttk.PanedWindow(f, orient='horizontal')
        body.pack(fill='both', expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)
        cols = ('id', 'name', 'at', 'off')
        tv = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse')
        for c, h, w in zip(cols, ('Item id', 'Name', 'Id at', 'File offset'), (70, 260, 60, 100)):
            tv.heading(c, text=h)
            tv.column(c, width=w, anchor='w')
        sb = ttk.Scrollbar(left, orient='vertical', command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        tv.bind('<<TreeviewSelect>>', self.on_item_select)
        self.itv = tv
        self.hits = []
        self.dumpbox = tk.Text(right, wrap='none', font=('Consolas', 9))
        self.dumpbox.pack(fill='both', expand=True)

    def open_elements(self):
        p = filedialog.askopenfilename(title='elements.data (open a COPY, not the live server file)',
                                       filetypes=[('elements.data', '*.data'), ('All files', '*.*')])
        if not p:
            return
        self.item_info.config(text='Building the name index (about 5-10 seconds)...')
        self.prog['value'] = 0
        idx = ItemIndex()

        def work():
            try:
                idx.load(p, progress=lambda x: self.q.put(('prog', x)))
                self.q.put(('loaded', idx))
            except OSError as ex:
                self.q.put(('error', str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == 'prog':
                    self.prog['value'] = val * 100
                elif kind == 'loaded':
                    self.index = val
                    self.prog['value'] = 100
                    self.item_info.config(text='%s: %d named entries' % (os.path.basename(val.path), len(val.entries)))
                    self.log('elements.data loaded for lookups: %s' % val.path)
                elif kind == 'error':
                    self.item_info.config(text='Could not load: ' + val)
                elif kind == 'tasks_loaded':
                    self.tasks = val
                    self.cur_quest = None
                    self.quest_info.config(text='%d quests | %s' % (len(val.quests), describe(val.path, val.md5_loaded)[0]))
                    self.qlog('Loaded %s. Search by quest id, part of the name, or item:<id> to find the quests that give an item.' % val.path)
                    if val.version != 187:
                        self.qlog('WARNING: version %d, this editor was mapped on version 187 files.' % val.version)
                elif kind == 'npc_loaded':
                    self.npcshops = val
                    self.cur_shop = None
                    self.npc_info.config(text='%d NPC shops, %d NPCs | %s' % (
                        val.shop_count, val.npc_count, describe(val.path, val.md5_loaded)[0]))
                    self.nlog('Loaded %s. Search by NPC name, shop id, or item:<id> to find the shops that sell an item.' % val.path)
                    self.npc_search()
                elif kind == 'folder_loaded':
                    self.folder_loaded(val)
                elif kind == 'folder_error':
                    self.data_info.config(text='Could not load the folder: ' + val)
                    messagebox.showerror(APP, val)
                elif kind == 'npc_error':
                    self.npc_info.config(text='Could not load: ' + val)
                elif kind == 'tasks_error':
                    self.quest_info.config(text='Could not load: ' + val)
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def search(self):
        if not self.index.ready:
            messagebox.showinfo(APP, 'Open an elements.data copy first.')
            return
        self.hits = self.index.search(self.search_var.get())
        self.itv.delete(*self.itv.get_children())
        for k, e in enumerate(self.hits):
            self.itv.insert('', 'end', iid=str(k), values=(e.id, e.name, '-%d' % e.back, e.rec_off))
        self.dumpbox.delete('1.0', 'end')
        self.dumpbox.insert('1.0', '%d results%s' % (len(self.hits), ' (first 500 shown)' if len(self.hits) >= 500 else ''))

    def on_item_select(self, ev=None):
        sel = self.itv.selection()
        if not sel:
            return
        e = self.hits[int(sel[0])]
        self.dumpbox.delete('1.0', 'end')
        self.dumpbox.insert('1.0', self.where_used(e.id, e.name) + '\n\n' + self.index.dump(e))

    def use_in_shop(self):
        sel = self.itv.selection()
        if not sel:
            messagebox.showinfo(APP, 'Select an item in the results first.')
            return
        e = self.hits[int(sel[0])]
        self.v['item_id'].set(str(e.id))
        self.v['name'].set(e.name[:31])
        self.nb.select(self.shop_tab)
        if self.selected() is None:
            self.log('Item %d "%s" put in the form, but no shop record is selected: select a record (or Add copy) '
                     'first, then use this button again.' % (e.id, e.name))
        else:
            self.log('Item %d "%s" put in the form for record %d. Check price, count and description, then Apply changes.'
                     % (e.id, e.name, self.selected()))

    # ---------------------------------------------------------------- quest tab
    def build_quest_tab(self):
        f = self.quest_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Button(top, text='Open tasks.data (a copy)...', command=self.open_tasks).pack(side='left')
        ttk.Button(top, text='Validate quest', command=self.validate_quest).pack(side='left', padx=4)
        ttk.Button(top, text='Save as...', command=self.save_tasks).pack(side='left')
        self.quest_info = ttk.Label(top, text='Not loaded')
        self.quest_info.pack(side='left', padx=10)

        srch = ttk.Frame(f)
        srch.pack(fill='x', padx=6)
        ttk.Label(srch, text='Quest id, name part, or item:<id>:').pack(side='left')
        self.qsearch_var = tk.StringVar()
        e = ttk.Entry(srch, textvariable=self.qsearch_var)
        e.pack(side='left', fill='x', expand=True, padx=4)
        e.bind('<Return>', lambda ev: self.quest_search())
        ttk.Button(srch, text='Search', command=self.quest_search).pack(side='left')

        body = ttk.PanedWindow(f, orient='horizontal')
        body.pack(fill='both', expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)
        qtv = ttk.Treeview(left, columns=('id', 'name'), show='headings', selectmode='browse')
        qtv.heading('id', text='Quest id')
        qtv.column('id', width=70, anchor='w')
        qtv.heading('name', text='Quest name')
        qtv.column('name', width=280, anchor='w')
        sb = ttk.Scrollbar(left, orient='vertical', command=qtv.yview)
        qtv.configure(yscrollcommand=sb.set)
        qtv.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        qtv.bind('<<TreeviewSelect>>', self.on_quest_select)
        self.qtv = qtv
        self.qhits = []

        cols = ('grp', 'row', 'item', 'iname', 'count', 'chance', 'period', 'flag')
        heads = ('Group', 'Row', 'Item id', 'Item name', 'Count', 'Chance %', 'Period', 'Flag')
        widths = (50, 40, 65, 220, 60, 75, 120, 40)
        rtv = ttk.Treeview(right, columns=cols, show='headings', selectmode='browse', height=14)
        for c, h, w in zip(cols, heads, widths):
            rtv.heading(c, text=h)
            rtv.column(c, width=w, anchor='w')
        rtv.pack(fill='both', expand=True)
        rtv.bind('<<TreeviewSelect>>', self.on_reward_select)
        rtv.bind('<Double-1>', self._dbl_reward)
        self.rtv = rtv
        self.cur_quest = None
        self.cur_groups = []

        form = ttk.LabelFrame(right, text='Selected reward row')
        form.pack(fill='x', pady=4)
        self.qv = {k: tk.StringVar() for k in ('item', 'count', 'chance', 'period', 'flag')}
        r = 0
        for label, key in (('Item id', 'item'), ('Count', 'count'), ('Chance %', 'chance')):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky='w', padx=4, pady=2)
            ttk.Entry(form, textvariable=self.qv[key]).grid(row=r, column=1, sticky='we', padx=4, pady=2)
            r += 1
        self.qname_lbl = ttk.Label(form, text='')
        self.qname_lbl.grid(row=0, column=2, sticky='w', padx=4)
        ttk.Button(form, text='Item from Item lookup', command=self.item_from_lookup).grid(row=1, column=2, sticky='w', padx=4)
        ttk.Label(form, text='100 = always; random rows in a pack add up to 100').grid(row=2, column=2, sticky='w', padx=4)
        ttk.Label(form, text='Period (item lifetime)').grid(row=r, column=0, sticky='w', padx=4, pady=2)
        ttk.Combobox(form, textvariable=self.qv['period'], values=[period_text(v) for _, v in PERIODS]).grid(
            row=r, column=1, sticky='we', padx=4, pady=2)
        r += 1
        ttk.Label(form, text='Row flag (0/1)').grid(row=r, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(form, textvariable=self.qv['flag']).grid(row=r, column=1, sticky='we', padx=4, pady=2)
        ttk.Label(form, text='1 on almost every stock row; leave as is').grid(row=r, column=2, sticky='w', padx=4)
        r += 1
        form.columnconfigure(1, weight=1)
        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=3, sticky='we', pady=4)
        ttk.Button(btns, text='Apply to row', command=self.apply_reward).pack(side='left', padx=2)
        ttk.Button(btns, text='Add row (copy of selected)', command=self.add_reward).pack(side='left', padx=2)
        ttk.Button(btns, text='Delete row', command=self.delete_reward).pack(side='left', padx=2)

        self.qlogbox = tk.Text(f, height=6, wrap='word')
        self.qlogbox.pack(fill='x', padx=6, pady=4)

    def qlog(self, msg):
        self.qlogbox.insert('end', msg + '\n')
        self.qlogbox.see('end')

    def open_tasks(self):
        if self.tasks is not None and self.tasks.dirty and \
                not messagebox.askyesno(APP, 'Unsaved quest changes. Open another tasks.data anyway?'):
            return
        p = filedialog.askopenfilename(title='tasks.data (open a COPY, not the live file)',
                                       filetypes=[('tasks.data', '*.data'), ('All files', '*.*')])
        if not p:
            return
        self.quest_info.config(text='Loading...')

        def work():
            try:
                self.q.put(('tasks_loaded', TasksFile(p)))
            except (TasksError, OSError, ValueError) as ex:
                self.q.put(('tasks_error', str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def item_name(self, item_id):
        if self.index.ready:
            return self.index.best_name(item_id) or '?'
        return '(load elements.data in Item lookup for names)'

    def quest_search(self):
        if not self.tasks:
            messagebox.showinfo(APP, 'Open a tasks.data copy first.')
            return
        t = self.qsearch_var.get().strip()
        if t.lower().startswith('item:'):
            try:
                iid = int(t[5:].strip())
            except ValueError:
                messagebox.showerror(APP, 'Use item:<number>, for example item:22198')
                return
            self.qhits = self.tasks.quests_giving(iid)
            self.qlog('%d quests give item %d (%s).' % (len(self.qhits), iid, self.item_name(iid)))
        else:
            self.qhits = self.tasks.search(t)
        self.qtv.delete(*self.qtv.get_children())
        for k, q in enumerate(self.qhits):
            self.qtv.insert('', 'end', iid=str(k), values=(q.id, plain(q.name)))
        if not self.qhits:
            self.qlog('No quests found for "%s".' % t)

    def on_quest_select(self, ev=None):
        sel = self.qtv.selection()
        if not sel:
            return
        self.cur_quest = self.qhits[int(sel[0])]
        self.show_rewards()

    def show_rewards(self, select=None):
        self.rtv.delete(*self.rtv.get_children())
        q = self.cur_quest
        if q is None:
            return
        self.cur_groups = self.tasks.groups(q)
        for gi, g in enumerate(self.cur_groups):
            for ri, row in enumerate(g.rows):
                _, item, rflag, count, chance, period = row
                self.rtv.insert('', 'end', iid='%d:%d' % (gi, ri), values=(
                    gi + 1, ri + 1, item, self.item_name(item), count, '%.4g' % (chance * 100), period_text(period), rflag))
        if not self.cur_groups:
            self.qlog('Quest %d %s: no reward list found in its data.' % (q.id, plain(q.name)))
        if select and select in self.rtv.get_children():
            self.rtv.selection_set(select)

    def cur_reward(self):
        sel = self.rtv.selection()
        if not sel or self.cur_quest is None:
            return None
        gi, ri = (int(x) for x in sel[0].split(':'))
        return gi, ri

    def on_reward_select(self, ev=None):
        cr = self.cur_reward()
        if cr is None:
            return
        gi, ri = cr
        _, item, rflag, count, chance, period = self.cur_groups[gi].rows[ri]
        self.qv['item'].set(str(item))
        self.qv['count'].set(str(count))
        self.qv['chance'].set('%.6g' % (chance * 100))
        self.qv['period'].set(period_text(period))
        self.qv['flag'].set(str(rflag))
        self.qname_lbl.config(text=self.item_name(item))

    def item_from_lookup(self):
        sel = self.itv.selection()
        if not sel:
            messagebox.showinfo(APP, 'Select an item in the Item lookup tab first.')
            return
        e = self.hits[int(sel[0])]
        self.qv['item'].set(str(e.id))
        self.qname_lbl.config(text=e.name)

    def apply_reward(self):
        cr = self.cur_reward()
        if cr is None:
            messagebox.showinfo(APP, 'Select a reward row first.')
            return
        gi, ri = cr
        try:
            item = parse_int(self.qv['item'].get(), 'Item id')
            count = parse_int(self.qv['count'].get(), 'Count')
            try:
                chance = float(self.qv['chance'].get()) / 100.0
            except ValueError:
                raise ValueError('Chance must be a number (percent)')
            period = parse_int(self.qv['period'].get(), 'Period')
            rflag = parse_int(self.qv['flag'].get(), 'Row flag')
            self.tasks.set_row(self.cur_groups[gi].rows[ri][0], item, rflag, count, chance, period)
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.qlog('Quest %d group %d row %d set to item %d (%s) x%d, %.4g%%, period %s.' % (
            self.cur_quest.id, gi + 1, ri + 1, item, self.item_name(item), count, chance * 100, period_text(period)))
        self.show_rewards(select='%d:%d' % (gi, ri))

    def add_reward(self):
        cr = self.cur_reward()
        if cr is None:
            messagebox.showinfo(APP, 'Select the row to copy first.')
            return
        gi, ri = cr
        try:
            self.tasks.add_row(self.cur_quest, self.cur_groups[gi], ri)
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        n = len(self.cur_groups[gi].rows)
        self.qlog('Row copied to the end of group %d (file grows by 17 bytes). Select it, change it, then Apply to row.' % (gi + 1))
        self.show_rewards(select='%d:%d' % (gi, n))
        self.on_reward_select()

    def delete_reward(self):
        cr = self.cur_reward()
        if cr is None:
            return
        gi, ri = cr
        row = self.cur_groups[gi].rows[ri]
        if not messagebox.askyesno(APP, 'Delete row %d (item %d) from group %d?' % (ri + 1, row[1], gi + 1)):
            return
        try:
            self.tasks.delete_row(self.cur_quest, self.cur_groups[gi], ri)
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.qlog('Row deleted (file shrinks by 17 bytes).')
        self.show_rewards()

    def validate_quest(self):
        if not self.tasks or self.cur_quest is None:
            messagebox.showinfo(APP, 'Select a quest first.')
            return
        errors, warnings = self.tasks.validate([self.cur_quest], self.index)
        self.qlog('Validate quest %d: %d errors, %d warnings.' % (self.cur_quest.id, len(errors), len(warnings)))
        for x in errors:
            self.qlog('  ERROR: ' + x)
        for x in warnings:
            self.qlog('  warning: ' + x)

    def save_tasks(self):
        if not self.tasks:
            return
        d, n = os.path.split(self.tasks.path)
        out = filedialog.asksaveasfilename(title='Save tasks.data as (new name)', initialdir=d,
                                           initialfile=os.path.splitext(n)[0] + '_new.data')
        if not out:
            return
        try:
            m = self.tasks.save(out)
        except (TasksError, OSError) as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.qlog('Saved %s  md5 %s' % (out, m))
        self.qlog('Next: snapshot the VM; this ONE file goes to the server (/opt/gamed/config/tasks.data) AND to every '
                  'client (element\\data\\tasks.data, via the launcher). Restart the server, check GS (maps) is UP.')
        messagebox.showinfo(APP, 'Saved.\n\nmd5 %s\n\nThe same file goes to the server and every client. See the log.' % m)

    # ---------------------------------------------------------------- NPC shop tab
    def build_npc_tab(self):
        f = self.npc_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Button(top, text='Open elements.data (a copy)...', command=self.open_npcshops).pack(side='left')
        ttk.Button(top, text='Validate shop', command=self.validate_shop).pack(side='left', padx=4)
        ttk.Button(top, text='Save as...', command=self.save_npcshops).pack(side='left')
        self.npc_info = ttk.Label(top, text='Not loaded')
        self.npc_info.pack(side='left', padx=10)

        srch = ttk.Frame(f)
        srch.pack(fill='x', padx=6)
        ttk.Label(srch, text='NPC name, shop id, NPC id, or item:<id>:').pack(side='left')
        self.nsearch_var = tk.StringVar()
        e = ttk.Entry(srch, textvariable=self.nsearch_var)
        e.pack(side='left', fill='x', expand=True, padx=4)
        e.bind('<Return>', lambda ev: self.npc_search())
        ttk.Button(srch, text='Search', command=self.npc_search).pack(side='left')

        body = ttk.PanedWindow(f, orient='horizontal')
        body.pack(fill='both', expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)
        stv = ttk.Treeview(left, columns=('id', 'name', 'npcs'), show='headings', selectmode='browse')
        for c, h, w in (('id', 'Shop id', 60), ('name', 'Shop', 90), ('npcs', 'Sold by (NPCs)', 260)):
            stv.heading(c, text=h)
            stv.column(c, width=w, anchor='w')
        sb = ttk.Scrollbar(left, orient='vertical', command=stv.yview)
        stv.configure(yscrollcommand=sb.set)
        stv.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        stv.bind('<<TreeviewSelect>>', self.on_shop_select)
        self.stv = stv
        self.shits = []
        self.cur_shop = None

        pg = ttk.Frame(right)
        pg.pack(fill='x')
        ttk.Label(pg, text='Page:').pack(side='left')
        self.page_var = tk.StringVar()
        self.page_cb = ttk.Combobox(pg, textvariable=self.page_var, state='readonly', width=24)
        self.page_cb.pack(side='left', padx=4)
        self.page_cb.bind('<<ComboboxSelected>>', lambda ev: self.show_slots())
        ttk.Label(pg, text='Page title (max 15):').pack(side='left', padx=(12, 0))
        self.ptitle_var = tk.StringVar()
        ttk.Entry(pg, textvariable=self.ptitle_var, width=18).pack(side='left', padx=4)
        ttk.Button(pg, text='Rename page', command=self.rename_page).pack(side='left')

        cols = ('slot', 'item', 'iname', 'e1', 'e2', 'e3', 'e4')
        heads = ('Slot', 'Item id', 'Item name', 'Extra 1', 'Extra 2', 'Extra 3', 'Extra 4')
        widths = (40, 65, 260, 60, 55, 55, 55)
        sltv = ttk.Treeview(right, columns=cols, show='headings', selectmode='browse', height=16)
        for c, h, w in zip(cols, heads, widths):
            sltv.heading(c, text=h)
            sltv.column(c, width=w, anchor='w')
        sltv.pack(fill='both', expand=True, pady=4)
        sltv.bind('<<TreeviewSelect>>', self.on_slot_select)
        sltv.bind('<Double-1>', self._dbl_slot)
        self.sltv = sltv

        form = ttk.LabelFrame(right, text='Selected slot (extra fields are unknown and kept as they are)')
        form.pack(fill='x')
        ttk.Label(form, text='Item id').grid(row=0, column=0, sticky='w', padx=4, pady=2)
        self.sitem_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.sitem_var).grid(row=0, column=1, sticky='we', padx=4, pady=2)
        self.sname_lbl = ttk.Label(form, text='')
        self.sname_lbl.grid(row=0, column=2, sticky='w', padx=4)
        form.columnconfigure(1, weight=1)
        btns = ttk.Frame(form)
        btns.grid(row=1, column=0, columnspan=3, sticky='we', pady=4)
        ttk.Button(btns, text='Apply to slot', command=self.apply_slot).pack(side='left', padx=2)
        ttk.Button(btns, text='Item from Item lookup', command=self.slot_from_lookup).pack(side='left', padx=2)
        ttk.Button(btns, text='Clear slot', command=self.clear_slot).pack(side='left', padx=2)

        self.nlogbox = tk.Text(f, height=6, wrap='word')
        self.nlogbox.pack(fill='x', padx=6, pady=4)

    def nlog(self, msg):
        self.nlogbox.insert('end', msg + '\n')
        self.nlogbox.see('end')

    def open_npcshops(self):
        if self.npcshops is not None and self.npcshops.dirty and \
                not messagebox.askyesno(APP, 'Unsaved NPC shop changes. Open another file anyway?'):
            return
        p = filedialog.askopenfilename(title='elements.data to edit (open a COPY, not the live file)',
                                       filetypes=[('elements.data', '*.data'), ('All files', '*.*')])
        if not p:
            return
        self.npc_info.config(text='Loading...')

        def work():
            try:
                self.q.put(('npc_loaded', NpcShops(p)))
            except (NpcShopError, OSError, ValueError) as ex:
                self.q.put(('npc_error', str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def npc_search(self):
        if not self.npcshops:
            messagebox.showinfo(APP, 'Open an elements.data copy in this tab first.')
            return
        t = self.nsearch_var.get().strip()
        if t.lower().startswith('item:'):
            try:
                iid = int(t[5:].strip())
            except ValueError:
                messagebox.showerror(APP, 'Use item:<number>, for example item:8617')
                return
            self.shits = self.npcshops.shops_selling(iid)
            self.nlog('%d shops sell item %d (%s).' % (len(self.shits), iid, self.item_name(iid)))
        else:
            self.shits = self.npcshops.search(t)
        self.stv.delete(*self.stv.get_children())
        for k, s in enumerate(self.shits):
            npcs = ', '.join(n[1] for n in s.npcs[:3]) + (' +%d more' % (len(s.npcs) - 3) if len(s.npcs) > 3 else '')
            self.stv.insert('', 'end', iid=str(k), values=(s.id, s.name, npcs or '(no NPC found)'))

    def on_shop_select(self, ev=None):
        sel = self.stv.selection()
        if not sel:
            return
        self.cur_shop = self.shits[int(sel[0])]
        ns = self.npcshops
        self.page_cb['values'] = ['%d %s' % (p + 1, ns.title(self.cur_shop, p) or '(no title)') for p in range(N_PAGES)]
        self.page_var.set(self.page_cb['values'][0])
        self.show_slots()

    def cur_page(self):
        try:
            return int(self.page_var.get().split()[0]) - 1
        except (ValueError, IndexError):
            return 0

    def show_slots(self, select=None):
        self.sltv.delete(*self.sltv.get_children())
        if self.cur_shop is None:
            return
        ns, p = self.npcshops, self.cur_page()
        self.ptitle_var.set(ns.title(self.cur_shop, p))
        for k in range(N_SLOTS):
            it, e1, e2, e3, e4 = ns.slot(self.cur_shop, p, k)
            self.sltv.insert('', 'end', iid=str(k), values=(k + 1, it or '', self.item_name(it) if it else '(empty)',
                                                           e1, e2, e3, e4))
        if select is not None:
            self.sltv.selection_set(str(select))

    def cur_slot(self):
        sel = self.sltv.selection()
        return int(sel[0]) if sel and self.cur_shop is not None else None

    def on_slot_select(self, ev=None):
        k = self.cur_slot()
        if k is None:
            return
        it = self.npcshops.slot(self.cur_shop, self.cur_page(), k)[0]
        self.sitem_var.set(str(it) if it else '')
        self.sname_lbl.config(text=self.item_name(it) if it else '(empty)')

    def slot_from_lookup(self):
        sel = self.itv.selection()
        if not sel:
            messagebox.showinfo(APP, 'Select an item in the Item lookup tab first.')
            return
        e = self.hits[int(sel[0])]
        self.sitem_var.set(str(e.id))
        self.sname_lbl.config(text=e.name)

    def apply_slot(self):
        k = self.cur_slot()
        if k is None:
            messagebox.showinfo(APP, 'Select a slot first.')
            return
        try:
            it = parse_int(self.sitem_var.get() or '0', 'Item id')
            self.npcshops.set_item(self.cur_shop, self.cur_page(), k, it)
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.nlog('Shop %d page %d slot %d now sells %s (%s). This shop is used by %d NPC(s): %s' % (
            self.cur_shop.id, self.cur_page() + 1, k + 1, it or 'nothing', self.item_name(it) if it else 'empty',
            len(self.cur_shop.npcs), ', '.join(n[1] for n in self.cur_shop.npcs[:6]) or 'none found'))
        self.show_slots(select=k)

    def clear_slot(self):
        k = self.cur_slot()
        if k is None:
            return
        self.npcshops.set_item(self.cur_shop, self.cur_page(), k, 0)
        self.nlog('Shop %d page %d slot %d cleared.' % (self.cur_shop.id, self.cur_page() + 1, k + 1))
        self.show_slots(select=k)

    def rename_page(self):
        if self.cur_shop is None:
            return
        try:
            self.npcshops.set_title(self.cur_shop, self.cur_page(), self.ptitle_var.get())
        except ValueError as ex:
            messagebox.showerror(APP, str(ex))
            return
        p = self.cur_page()
        self.page_cb['values'] = ['%d %s' % (i + 1, self.npcshops.title(self.cur_shop, i) or '(no title)') for i in range(N_PAGES)]
        self.page_var.set(self.page_cb['values'][p])
        self.nlog('Shop %d page %d renamed to "%s".' % (self.cur_shop.id, p + 1, self.ptitle_var.get()))

    def validate_shop(self):
        if self.cur_shop is None:
            messagebox.showinfo(APP, 'Select a shop first.')
            return
        w = self.npcshops.validate(self.cur_shop, self.index)
        if not self.index.ready:
            self.nlog('Load elements.data in Item lookup too, so item ids can be checked.')
        self.nlog('Validate shop %d: %d warnings.' % (self.cur_shop.id, len(w)))
        for x in w[:30]:
            self.nlog('  warning: ' + x)

    def save_npcshops(self):
        if not self.npcshops:
            return
        d, n = os.path.split(self.npcshops.path)
        out = filedialog.asksaveasfilename(title='Save elements.data as (new name)', initialdir=d,
                                           initialfile=os.path.splitext(n)[0] + '_new.data')
        if not out:
            return
        try:
            m = self.npcshops.save(out)
        except (NpcShopError, OSError) as ex:
            messagebox.showerror(APP, str(ex))
            return
        self.nlog('Saved %s  md5 %s' % (out, m))
        self.nlog('Next: snapshot the VM; this ONE elements.data goes to the server (/opt/gamed/config/elements.data) AND '
                  'every client (element\\data\\elements.data, via the launcher). Restart and check GS (maps) is UP.')
        messagebox.showinfo(APP, 'Saved.\n\nmd5 %s\n\nThe same file goes to the server and every client. See the log.' % m)

    # ---------------------------------------------------------------- cross-integration
    def open_folder(self):
        dirty = [n for n, x in (('quest', self.tasks), ('NPC shop', self.npcshops)) if x is not None and x.dirty]
        if dirty and not messagebox.askyesno(APP, 'Unsaved %s changes will be dropped. Open a folder anyway?' % ' and '.join(dirty)):
            return
        folder = filedialog.askdirectory(title='Game data folder (a client\'s element\\data, or a folder with copies)')
        if not folder:
            return
        ep, tp = os.path.join(folder, 'elements.data'), os.path.join(folder, 'tasks.data')
        if not os.path.exists(ep):
            messagebox.showerror(APP, 'No elements.data in that folder.')
            return
        self.data_info.config(text='Loading %s ...' % folder)
        self.item_info.config(text='Building the name index...')
        self.prog['value'] = 0

        def work():
            try:
                with open(ep, 'rb') as f:
                    data = bytearray(f.read())
                ns = NpcShops(ep, data)
                ix = ItemIndex()
                ix.build(ns.data, ep, progress=lambda x: self.q.put(('prog', x)))
                tf = TasksFile(tp) if os.path.exists(tp) else None
                self.q.put(('folder_loaded', {'folder': folder, 'index': ix, 'npc': ns, 'tasks': tf}))
            except (NpcShopError, TasksError, OSError, ValueError) as ex:
                self.q.put(('folder_error', str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def folder_loaded(self, v):
        self.data_folder = v['folder']
        self.index, self.npcshops, self.tasks = v['index'], v['npc'], v['tasks']
        self.cur_shop = self.cur_quest = None
        self.prog['value'] = 100
        lines, bad = [], []
        el, st = describe(self.npcshops.path, self.npcshops.md5_loaded)
        lines.append(el)
        if st in ('old', 'experiment'):
            bad.append(el)
        self.item_info.config(text='%d named entries | %s' % (len(self.index.entries), el))
        self.npc_info.config(text='%d NPC shops, %d NPCs | %s' % (self.npcshops.shop_count, self.npcshops.npc_count, el))
        if self.tasks:
            tl, ts = describe(self.tasks.path, self.tasks.md5_loaded)
            lines.append(tl)
            if ts in ('old', 'experiment'):
                bad.append(tl)
            self.quest_info.config(text='%d quests | %s' % (len(self.tasks.quests), tl))
        else:
            lines.append('tasks.data: not in this folder')
            self.quest_info.config(text='Not loaded (no tasks.data in the folder)')
        self.data_info.config(text='Folder %s  |  %s' % (self.data_folder, '  |  '.join(lines)))
        self.log('Game data folder loaded: %s' % self.data_folder)
        for x in lines:
            self.log('  ' + x)
        self.npc_search()
        if bad:
            messagebox.showwarning(APP, 'Heads up:\n\n' + '\n'.join(bad) +
                                   '\n\nYou can look around, but make edits from the live version.')

    def where_used(self, item_id, name=None):
        out = ['WHERE ID %d (%s) IS USED AS AN ITEM' % (item_id, name or self.item_name(item_id))]
        if self.npcshops is not None:
            ws = self.npcshops.where_sold(item_id)
            out.append('Sold in NPC shops: %d slot(s)' % len(ws))
            for sh, p, k in ws[:25]:
                npcs = ', '.join(n[1] for n in sh.npcs[:4]) + (' +%d more' % (len(sh.npcs) - 4) if len(sh.npcs) > 4 else '')
                out.append('  shop %d page %d "%s" slot %d  - sold by %s' % (sh.id, p + 1, self.npcshops.title(sh, p), k + 1, npcs or 'no NPC found'))
        else:
            out.append('NPC shops: (open the game data folder to see)')
        if self.tasks is not None:
            qs = self.tasks.quests_giving(item_id)
            out.append('Given by quests: %d' % len(qs))
            for q in qs[:25]:
                rows = [r for g in self.tasks.groups(q) for r in g.rows if r[1] == item_id]
                desc = '; '.join('x%d, %.4g%%, %s' % (r[3], r[4] * 100, period_text(r[5])) for r in rows[:3])
                out.append('  quest %d %s  - %s' % (q.id, plain(q.name), desc))
        else:
            out.append('Quests: (open the game data folder or a tasks.data to see)')
        if self.pair is not None:
            recs = [i for i in range(len(self.pair)) if self.pair.client.get(i, 'item_id') == item_id]
            out.append('In the open Boutique pair: %d record(s)' % len(recs))
            for i in recs[:10]:
                r = self.pair.row(i)
                out.append('  record %d %s  - x%d, price %d, %s' % (i, self.pair.tab_name(r['main_tab'], r['sub_tab']),
                                                                   r['count'], r['price'], dur_text(r['duration'])))
        out.append('(The same id number can also belong to an NPC, monster or skill in another list; '
                   'these lookups only count it where an item is expected.)')
        return '\n'.join(out)

    def goto_item(self, item_id):
        if not item_id:
            return
        if not self.index.ready:
            messagebox.showinfo(APP, 'Load elements.data first (Open game data folder, or Item lookup).')
            return
        self.nb.select(self.item_tab)
        self.search_var.set(str(item_id))
        self.search()
        if self.hits:
            best = next((k for k, e in enumerate(self.hits) if e.back in (12, 4)), 0)
            self.itv.selection_set(str(best))
            self.on_item_select()
        else:
            self.dumpbox.delete('1.0', 'end')
            self.dumpbox.insert('1.0', self.where_used(item_id) + '\n\n(no named record for this id)')

    def _dbl_reward(self, ev=None):
        cr = self.cur_reward()
        if cr:
            self.goto_item(self.cur_groups[cr[0]].rows[cr[1]][1])

    def _dbl_slot(self, ev=None):
        k = self.cur_slot()
        if k is not None:
            self.goto_item(self.npcshops.slot(self.cur_shop, self.cur_page(), k)[0])

    def _dbl_shoprec(self, ev=None):
        i = self.selected()
        if i is not None and self.pair:
            self.goto_item(self.pair.client.get(i, 'item_id'))

    # ---------------------------------------------------------------- item flow tab
    def build_flow_tab(self):
        f = self.flow_tab
        top = ttk.Frame(f)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Label(top, text='Item id or name:').pack(side='left')
        self.flow_var = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.flow_var, width=40)
        e.pack(side='left', padx=4)
        e.bind('<Return>', lambda ev: self.flow_go())
        ttk.Button(top, text='Show', command=self.flow_go).pack(side='left')
        ttk.Button(top, text='Back', command=self.flow_back).pack(side='left', padx=4)
        self.flow_title = ttk.Label(top, text='Open the game data folder, then enter an item. Double-click any linked item to follow it.')
        self.flow_title.pack(side='left', padx=10)
        body = ttk.PanedWindow(f, orient='horizontal')
        body.pack(fill='both', expand=True, padx=6, pady=4)
        self.flow_trees = {}
        for side, title in (('from', 'COMES FROM  (shops, quest rewards, drops, crafting, Boutique)'),
                            ('to', 'GOES TO  (opens quest, needed by quest, crafting material)')):
            fr = ttk.LabelFrame(body, text=title)
            body.add(fr, weight=1)
            tv = ttk.Treeview(fr, columns=('detail',), show='tree headings', selectmode='browse')
            tv.heading('#0', text='Where')
            tv.column('#0', width=360, anchor='w')
            tv.heading('detail', text='Detail')
            tv.column('detail', width=260, anchor='w')
            sb = ttk.Scrollbar(fr, orient='vertical', command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            tv.pack(side='left', fill='both', expand=True)
            sb.pack(side='left', fill='y')
            tv.bind('<Double-1>', lambda ev, t=tv: self.flow_follow(t))
            self.flow_trees[side] = tv
        ttk.Label(f, text='Drop chance per kill is calculated from the monster table (not tested in game). '
                          'Server-side extra drops (extra_drops.sev on the VM) are not included.').pack(fill='x', padx=6, pady=(0, 4))

    def flow(self):
        key = (id(self.index), id(self.tasks), id(self.npcshops))
        if self._flow is None or self._flow_key != key:
            self._flow = Flow(self.index, self.tasks, self.npcshops, self.pair)
            self._flow_key = key
        self._flow.pair = self.pair
        return self._flow

    def flow_go(self, push=True):
        if not self.index.ready:
            messagebox.showinfo(APP, 'Open the game data folder first (or load elements.data in Item lookup).')
            return
        t = self.flow_var.get().strip()
        if not t:
            return
        if t.isdigit():
            iid = int(t)
        else:
            hits = [e for e in self.index.search(t) if e.kind is None]
            if not hits:
                messagebox.showinfo(APP, 'No item named like "%s".' % t)
                return
            iid = hits[0].id
        self.flow_show(iid, push)

    def flow_show(self, iid, push=True):
        fl = self.flow()
        if push and (not self.flow_hist or self.flow_hist[-1] != iid):
            self.flow_hist.append(iid)
        self.flow_var.set(str(iid))
        missing = [n for n, x in (('tasks.data', self.tasks), ('NPC shops', self.npcshops)) if x is None]
        self.flow_title.config(text='%s%s' % (fl.item_text(iid), ('   (not loaded: %s)' % ', '.join(missing)) if missing else ''))
        for side, nodes in (('from', fl.comes_from(iid)), ('to', fl.goes_to(iid))):
            tv = self.flow_trees[side]
            tv.delete(*tv.get_children())
            if not nodes:
                tv.insert('', 'end', iid='none', text='(nothing found)', values=('',))
            for k, n in enumerate(nodes):
                pid = 'n%d' % k
                tv.insert('', 'end', iid=pid, text=n.label, values=(n.detail,), open=True)
                for j, (lid, txt) in enumerate(n.links):
                    tv.insert(pid, 'end', iid='L%d_%d_%d' % (lid, k, j), text='   -> ' + txt, values=('double-click to follow',))
        self.nb.select(self.flow_tab)

    def flow_follow(self, tv):
        sel = tv.selection()
        if sel and sel[0].startswith('L'):
            self.flow_show(int(sel[0][1:].split('_')[0]))

    def flow_back(self):
        if len(self.flow_hist) > 1:
            self.flow_hist.pop()
            self.flow_show(self.flow_hist[-1], push=False)

    def flow_from_lookup(self):
        sel = self.itv.selection()
        if not sel:
            messagebox.showinfo(APP, 'Select an item in the results first.')
            return
        self.flow_show(self.hits[int(sel[0])].id)

    def on_close(self):
        if self.npcshops is not None and self.npcshops.dirty and \
                not messagebox.askyesno(APP, 'You have unsaved NPC shop changes. Quit anyway?'):
            return
        if self.tasks is not None and self.tasks.dirty and \
                not messagebox.askyesno(APP, 'You have unsaved quest changes. Quit anyway?'):
            return
        if self.dirty and not messagebox.askyesno(APP, 'You have unsaved changes. Quit anyway?'):
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use('vista')
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
