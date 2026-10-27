"""Backup and restore of the game's per-player settings (the 'userdata' folder).

Backups are zip files kept OUTSIDE the game folder, in
%LOCALAPPDATA%\\PWHomeServer\\userdata_backup, so reinstalling or swapping the game
folder does not take them with it. No window code in here.
"""
import hashlib
import os
import shutil
import subprocess
import time
import zipfile

KEEP = 5                          # newest settings backups to keep
KEEP_UNDO = 3                     # safety copies made just before a restore
SKIP_DIRS = {"userpic"}           # stock pictures from the install, never change
SKIP_FILES = {"dyn_tasks.data"}   # downloaded from the server at login, not a setting
EXE = "elementclient.exe"


def backup_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "PWHomeServer", "userdata_backup")


def _userdata(game_dir):
    return os.path.join(game_dir, "userdata")


def _files(ud):
    """[(relative path with forward slashes, full path)] of everything worth saving."""
    out = []
    for root, dirs, files in os.walk(ud):
        top = root == ud
        if top:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if top and f in SKIP_FILES:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, ud).replace(os.sep, "/")
            out.append((rel, full))
    out.sort()
    return out


def _snapshot(files):
    """Read every file once. Returns (content hash, [(rel, bytes)]); unreadable files are skipped."""
    h = hashlib.sha256()
    data = []
    for rel, full in files:
        try:
            with open(full, "rb") as f:
                b = f.read()
        except OSError:
            continue
        h.update(rel.encode("utf-8") + b"\0" + b + b"\0")
        data.append((rel, b))
    return h.hexdigest()[:8], data


def _write_zip(dest_path, data):
    tmp = dest_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, b in data:
            z.writestr(rel, b)
    os.replace(tmp, dest_path)


def _names(prefix):
    d = backup_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.startswith(prefix) and n.endswith(".zip"))


def _prune(prefix, keep):
    for old in _names(prefix)[:-keep]:
        try:
            os.remove(os.path.join(backup_dir(), old))
        except OSError:
            pass


def backup(game_dir):
    """Save a zip of the settings unless they are identical to the newest backup."""
    ud = _userdata(game_dir)
    if not os.path.isdir(ud):
        return "no userdata folder yet, nothing to back up"
    tag, data = _snapshot(_files(ud))
    if not data:
        return "userdata is empty, nothing to back up"
    names = _names("userdata_")
    if names and names[-1].endswith("_%s.zip" % tag):
        return "settings unchanged since the last backup"
    os.makedirs(backup_dir(), exist_ok=True)
    name = "userdata_%s_%s.zip" % (time.strftime("%Y%m%d_%H%M%S"), tag)
    _write_zip(os.path.join(backup_dir(), name), data)
    _prune("userdata_", KEEP)
    return "saved %d files as %s" % (len(data), name)


def list_backups():
    """Newest first: [{'name','path','size','when'}]."""
    out = []
    for n in reversed(_names("userdata_")):
        p = os.path.join(backup_dir(), n)
        try:
            ts = time.strptime(n[len("userdata_"):len("userdata_") + 15], "%Y%m%d_%H%M%S")
            when = time.strftime("%Y-%m-%d %H:%M", ts)
            out.append({"name": n, "path": p, "size": os.path.getsize(p), "when": when})
        except (ValueError, OSError):
            continue
    return out


def game_running():
    flags = 0x08000000 if os.name == "nt" else 0      # no console flash when packed as a windowed exe
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + EXE, "/NH"],
                             capture_output=True, text=True, timeout=10, creationflags=flags).stdout
        return EXE.lower() in out.lower()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def restore(game_dir, zip_path):
    """Put the settings from a backup zip back. Saves the current settings first (undo copy).
    Files that are not in the zip are left alone. Returns how many files were restored."""
    if game_running():
        raise RuntimeError("The game is running. Close it first, then restore.")
    ud = _userdata(game_dir)
    os.makedirs(ud, exist_ok=True)
    root = os.path.normpath(ud)
    with zipfile.ZipFile(zip_path) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        targets = []
        for i in members:                                   # check every path before touching anything
            parts = i.filename.replace("\\", "/").split("/")
            if i.filename.startswith(("/", "\\")) or ":" in i.filename or any(p in ("", ".", "..") for p in parts):
                raise RuntimeError("The backup has a bad file path: %r" % i.filename)
            full = os.path.normpath(os.path.join(root, *parts))
            if os.path.commonpath([root, full]) != root:
                raise RuntimeError("The backup points outside the settings folder: %r" % i.filename)
            targets.append(full)
        _tag, cur = _snapshot(_files(ud))
        if cur:
            os.makedirs(backup_dir(), exist_ok=True)
            _write_zip(os.path.join(backup_dir(), "undo_%s.zip" % time.strftime("%Y%m%d_%H%M%S")), cur)
            _prune("undo_", KEEP_UNDO)
        for i, full in zip(members, targets):
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with z.open(i) as src, open(full, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return len(members)
