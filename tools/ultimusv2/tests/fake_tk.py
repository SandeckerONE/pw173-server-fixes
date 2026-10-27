"""Minimal stand-in for tkinter so the GUI logic can be exercised without a display. Test use only."""
import sys, types

class Var:
    def __init__(self, value=''): self._v = value; self._cb = []
    def get(self): return self._v
    def set(self, v):
        self._v = v
        for cb in self._cb: cb()
    def trace_add(self, mode, cb): self._cb.append(cb)

class W:
    def __init__(self, *a, **k): self._cfg = dict(k); self._items = {}
    def __getattr__(self, n):
        if n.startswith('__'): raise AttributeError(n)
        return lambda *a, **k: None
    def __setitem__(self, k, v): self._cfg[k] = v
    def __getitem__(self, k): return self._cfg.get(k)
    def config(self, **k): self._cfg.update(k)
    configure = config

class Text(W):
    def __init__(self, *a, **k): super().__init__(*a, **k); self.t = ''
    def insert(self, idx, s): self.t = (self.t + s) if idx == 'end' else (s + self.t)
    def delete(self, a, b=None): self.t = ''
    def get(self, a, b=None): return self.t

class Treeview(W):
    def __init__(self, *a, **k): super().__init__(*a, **k); self.rows = []; self.sel = ()
    def insert(self, parent, idx, iid=None, values=(), text='', **k): self.rows.append((iid, values, text, parent))
    def delete(self, *iids): self.rows = [r for r in self.rows if r[0] not in iids and (len(r) < 4 or r[3] not in iids)]
    def get_children(self): return [r[0] for r in self.rows]
    def selection(self): return self.sel
    def selection_set(self, iid): self.sel = (iid,); self._on_select()
    def bind(self, ev, fn):
        if ev == '<<TreeviewSelect>>': self._on_select = fn
    def _on_select(self, *a): pass

class Tk(W):
    def after(self, ms, fn): pass

class TclError(Exception): pass

tk = types.ModuleType('tkinter')
tk.Tk, tk.Text, tk.StringVar, tk.TclError = Tk, Text, Var, TclError
ttk = types.ModuleType('tkinter.ttk')
for n in ('Notebook', 'Frame', 'Button', 'Label', 'PanedWindow', 'Entry', 'Scrollbar', 'LabelFrame', 'Combobox', 'Progressbar', 'Style'):
    setattr(ttk, n, type(n, (W,), {}))
ttk.Treeview = Treeview
fd = types.ModuleType('tkinter.filedialog'); fd.answers = []
fd.askopenfilename = lambda **k: fd.answers.pop(0)
fd.asksaveasfilename = lambda **k: fd.answers.pop(0)
fd.askdirectory = lambda **k: fd.answers.pop(0)
mb = types.ModuleType('tkinter.messagebox'); mb.shown = []
for n in ('showinfo', 'showerror', 'showwarning'):
    setattr(mb, n, (lambda n: lambda *a, **k: mb.shown.append((n, a)))(n))
mb.askyesno = lambda *a, **k: True
tk.ttk, tk.filedialog, tk.messagebox = ttk, fd, mb
sys.modules.update({'tkinter': tk, 'tkinter.ttk': ttk, 'tkinter.filedialog': fd, 'tkinter.messagebox': mb})
