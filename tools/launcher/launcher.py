"""PW Home Server launcher - step 3: window, GIF, log, Play button, file updater.
Test run:  python launcher.py --game "C:\\path\\to\\PWI_en_1.4.6 (e80_t105)\\element"
"""
import argparse
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.parse
from tkinter import messagebox, ttk

import updater
import userdata_backup

TITLE = "PW Home Server"
SERVERS = [                               # patch server on the Ultimus VM, tried in this order
    "http://100.x.y.z:8088",                # your server VM's Tailscale address (friends)
    "http://192.168.56.x:8088",             # your VM's VirtualBox host-only address (the host PC)
]
SERVER = SERVERS[0]
GAME_EXE = "elementclient.exe"
GAME_ARGS = ["game:cpw", "nocheck", "startbypatcher"]   # same flags as the packaged eStart.bat; without startbypatcher the client opens the dead official launcher
GIF_NAME = "construction.gif"
FRAME_MS = 80
GAME_PORT = 29000          # game link server (glinkd) on the VM
STATUS_EVERY_S = 10        # how often the status light re-checks
GREEN = "#6fcf7a"
BG, PANEL, FG, GOLD, RED = "#14110d", "#1f1a14", "#d8cdb8", "#e8c872", "#e06a5a"


def here():
    """Folder the launcher lives in (works as a script and as a PyInstaller program)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def bundled(name):
    """Path of a file packed inside the program (the GIF)."""
    base = getattr(sys, "_MEIPASS", here())
    return os.path.join(base, name)


def tcp_up(host, port, timeout=2.0):
    """True if something accepts a connection on host:port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pick_server(candidates, timeout=1.5):
    """First patch server address that answers, checked in parallel.
    Falls back to the first one so the error message still makes sense."""
    results = {}

    def probe(url):
        u = urllib.parse.urlparse(url)
        results[url] = tcp_up(u.hostname, u.port or 80, timeout)

    threads = [threading.Thread(target=probe, args=(u,), daemon=True) for u in candidates]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout + 0.5)
    for url in candidates:
        if results.get(url):
            return url
    return candidates[0]


class Launcher(tk.Tk):
    def __init__(self, game_dir, server):
        super().__init__()
        self.game_dir = game_dir
        self.frames = []
        self.frame_no = 0
        self.server = server
        self.server_up = None
        self.q = queue.Queue()
        self.title(TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.build_ui()
        self.load_gif()
        self.log("Launcher started.")
        self.log("Game folder: " + self.game_dir)
        self.check_game()
        self.after(100, self.pump)
        self.start_update()
        self.start_status_watch()

    def build_ui(self):
        left = tk.Frame(self, bg=BG)
        left.grid(row=0, column=0, padx=(14, 8), pady=14, sticky="n")
        right = tk.Frame(self, bg=BG)
        right.grid(row=0, column=1, padx=(8, 14), pady=14, sticky="n")

        self.art = tk.Label(left, bg=BG, bd=0)
        self.art.pack()

        tk.Label(right, text=TITLE, bg=BG, fg=GOLD,
                 font=("Georgia", 20, "bold")).pack(anchor="w")
        tk.Label(right, text="Update and launch", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(right, bg=BG)
        row.pack(anchor="w", pady=(0, 8))
        self.dot = tk.Canvas(row, width=14, height=14, bg=BG, highlightthickness=0)
        self.dot_id = self.dot.create_oval(2, 2, 12, 12, fill="#e8b04a", outline="")
        self.dot.pack(side="left")
        self.srv_label = tk.Label(row, text="Game server: checking...", bg=BG, fg=FG,
                                  font=("Segoe UI", 10))
        self.srv_label.pack(side="left", padx=(6, 0))

        self.status = tk.Label(right, text="Starting...", bg=BG, fg=FG, anchor="w",
                               width=52, font=("Segoe UI", 10))
        self.status.pack(anchor="w")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Gold.Horizontal.TProgressbar", troughcolor=PANEL,
                        background=GOLD, bordercolor=PANEL,
                        lightcolor=GOLD, darkcolor=GOLD)
        self.bar = ttk.Progressbar(right, style="Gold.Horizontal.TProgressbar",
                                   length=400, mode="determinate", maximum=100)
        self.bar.pack(anchor="w", pady=8)

        self.logbox = tk.Text(right, width=56, height=8, bg=PANEL, fg=FG, bd=0,
                              font=("Consolas", 9), state="disabled", wrap="word")
        self.logbox.pack(anchor="w")

        bottom = tk.Frame(right, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))
        self.restore_btn = tk.Button(bottom, text="Restore UI settings...", font=("Segoe UI", 9),
                                     bg=PANEL, fg=FG, activebackground="#2a231a", activeforeground=FG,
                                     bd=0, padx=10, pady=4, command=self.on_restore)
        self.restore_btn.pack(side="left", anchor="s")
        self.play = tk.Button(bottom, text="PLAY", font=("Segoe UI", 12, "bold"),
                              bg=GOLD, fg="#1a1408", activebackground="#f4d98a",
                              bd=0, padx=34, pady=6, command=self.on_play)
        self.play.pack(side="right")

    def load_gif(self):
        path = bundled(GIF_NAME)
        n = 0
        while True:
            try:
                self.frames.append(tk.PhotoImage(file=path, format="gif -index %d" % n))
            except tk.TclError:
                break
            n += 1
        if self.frames:
            self.animate()
        else:
            self.art.config(text="(image missing)", fg=FG, width=32, height=14)

    def animate(self):
        self.art.config(image=self.frames[self.frame_no])
        self.frame_no = (self.frame_no + 1) % len(self.frames)
        self.after(FRAME_MS, self.animate)

    def log(self, msg):
        line = time.strftime("%H:%M:%S  ") + msg
        self.logbox.config(state="normal")
        self.logbox.insert("end", line + "\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")
        try:
            with open(os.path.join(here(), "launcher.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def exe_path(self):
        return os.path.join(self.game_dir, GAME_EXE)

    def check_game(self):
        if not os.path.isfile(self.exe_path()):
            self.status.config(text="%s not found in the game folder." % GAME_EXE, fg=RED)
            self.log("Missing: " + self.exe_path())
            self.play.config(state="disabled")

    # ---- updating: worker thread talks to the window only through a queue ----
    def start_update(self):
        self.play.config(state="disabled")
        self.log("Patch server: " + self.server)
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        q = self.q
        try:                                       # save UI layouts and settings before anything is updated
            q.put(("log", "Settings backup: " + userdata_backup.backup(self.game_dir)))
        except Exception as e:                     # a failed backup must never block updating
            q.put(("log", "Settings backup skipped: %r" % (e,)))
        up = updater.Updater(
            self.server, self.game_dir,
            say=lambda m: q.put(("log", m)),
            status=lambda m: q.put(("status", m)),
            progress=lambda d, t: q.put(("bar", 100.0 * d / max(1, t))))
        try:
            n = up.run()
            q.put(("done", n))
        except updater.UpdateError as e:
            q.put(("fail", str(e)))
        except Exception as e:                     # never let the thread die silently
            q.put(("fail", "Unexpected error: %r" % (e,)))

    # ---- server status light: a thread tries to connect to the game port ----
    def start_status_watch(self):
        host = urllib.parse.urlparse(self.server).hostname
        if not host:
            self.srv_label.config(text="Game server: unknown address")
            return
        self.log("Game server check: %s port %d" % (host, GAME_PORT))
        threading.Thread(target=self.status_worker, args=(host,), daemon=True).start()

    def status_worker(self, host):
        while True:
            self.q.put(("srv", tcp_up(host, GAME_PORT)))
            time.sleep(STATUS_EVERY_S)

    def show_server(self, up):
        if up != self.server_up:
            self.log("Game server is now %s." % ("ONLINE" if up else "OFFLINE"))
            self.server_up = up
        color = GREEN if up else RED
        self.dot.itemconfig(self.dot_id, fill=color)
        self.srv_label.config(text="Game server: " + ("Online" if up else "Offline"), fg=color)

    def pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.log(val)
                elif kind == "status":
                    self.status.config(text=val, fg=FG)
                elif kind == "bar":
                    self.bar["value"] = val
                elif kind == "srv":
                    self.show_server(val)
                elif kind == "done":
                    self.finish(True, None)
                elif kind == "fail":
                    self.finish(False, val)
        except queue.Empty:
            pass
        self.after(100, self.pump)

    def finish(self, ok, err):
        have_exe = os.path.isfile(self.exe_path())
        if ok:
            self.status.config(text="Ready to play.", fg=GOLD)
        else:
            self.status.config(text="Update failed - you can still press Play.", fg=RED)
            self.log(err)
        self.play.config(state="normal" if have_exe else "disabled")

    def on_restore(self):
        items = userdata_backup.list_backups()
        if not items:
            messagebox.showinfo(TITLE, "No settings backups yet.\nOne is saved each time the launcher "
                                "starts, if your settings changed since the last one.")
            return
        win = tk.Toplevel(self)
        win.title("Restore UI settings")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        tk.Label(win, text="Pick a backup (newest first). Close the game first.", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(padx=14, pady=(12, 6))
        box = tk.Listbox(win, width=40, height=min(8, len(items)), bg=PANEL, fg=FG, bd=0,
                         selectbackground=GOLD, selectforeground="#1a1408",
                         font=("Consolas", 10), exportselection=False)
        for it in items:
            box.insert("end", "%s    %d KB" % (it["when"], max(1, it["size"] // 1024)))
        box.selection_set(0)
        box.pack(padx=14)

        def go():
            sel = box.curselection()
            if not sel:
                return
            it = items[sel[0]]
            if not messagebox.askyesno(TITLE, "Restore the settings saved on %s?\n\nYour current settings "
                                       "are saved first, so this can be undone." % it["when"], parent=win):
                return
            try:
                n = userdata_backup.restore(self.game_dir, it["path"])
            except Exception as e:
                messagebox.showerror(TITLE, str(e), parent=win)
                return
            self.log("Restored %d settings files from %s." % (n, it["name"]))
            win.destroy()
            messagebox.showinfo(TITLE, "Settings restored.")

        tk.Button(win, text="Restore selected", font=("Segoe UI", 10, "bold"), bg=GOLD, fg="#1a1408",
                  activebackground="#f4d98a", bd=0, padx=18, pady=4, command=go).pack(pady=12)

    def on_play(self):
        exe = os.path.join(self.game_dir, GAME_EXE)
        try:
            subprocess.Popen([exe] + GAME_ARGS, cwd=self.game_dir)
        except OSError as e:
            self.log("Could not start the game: %s" % e)
            return
        self.log("Game started.")
        self.after(1500, self.destroy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=here(),
                    help="folder that contains elementclient.exe (default: the launcher's own folder)")
    ap.add_argument("--server", default=None,
                    help="patch server address, e.g. http://192.168.56.x:8088 "
                         "(default: the first of SERVERS that answers)")
    args = ap.parse_args()
    server = args.server or pick_server(SERVERS)
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    Launcher(os.path.abspath(args.game), server).mainloop()


if __name__ == "__main__":
    main()
