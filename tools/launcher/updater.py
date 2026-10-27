"""Update logic for the PW Home Server launcher (no window code in here).

The patch server publishes:
    <server>/manifest.json        list of files: path, size, sha256
    <server>/files/<path>         the files themselves
Paths are relative to the game's 'element' folder and use forward slashes.
"""
import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

import netcheck


class UpdateError(Exception):
    """Something went wrong that the user should be told about in plain words."""


def safe_target(game_dir, rel):
    """Turn a manifest path into a full path, refusing anything outside the game folder."""
    if not isinstance(rel, str) or not rel or os.path.isabs(rel) or ":" in rel:
        raise UpdateError("The manifest has a bad file path: %r" % (rel,))
    parts = rel.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise UpdateError("The manifest has a bad file path: %r" % (rel,))
    root = os.path.normpath(game_dir)
    full = os.path.normpath(os.path.join(root, *parts))
    if os.path.commonpath([root, full]) != root:
        raise UpdateError("The manifest points outside the game folder: %r" % (rel,))
    return full


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Updater:
    def __init__(self, server, game_dir, say=None, status=None, progress=None):
        self.server = server.rstrip("/")
        self.game_dir = game_dir
        self.say = say or (lambda m: None)            # one line for the log box
        self.status = status or (lambda m: None)      # the big status line
        self.progress = progress or (lambda d, t: None)   # bytes done, bytes total
        # An opener with no proxy: the patch server is a direct Tailscale/LAN address.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _get(self, url, timeout):
        req = urllib.request.Request(url, headers={"User-Agent": "PWHomeLauncher/2"})
        return self.opener.open(req, timeout=timeout)

    def fetch_manifest(self):
        url = self.server + "/manifest.json?t=%d" % time.time()
        try:
            with self._get(url, 8) as r:
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise UpdateError("Can't reach the patch server (%s). %s" % (e, netcheck.hint(self.server)))
        if not isinstance(data, dict) or data.get("format") != 1 or not isinstance(data.get("files"), list):
            raise UpdateError("The patch server's manifest is not in a format this launcher understands.")
        return data

    def run(self):
        """Check every file in the manifest, download what is missing or different.
        Returns how many files were downloaded. Raises UpdateError on any problem."""
        self.status("Checking for updates...")
        data = self.fetch_manifest()
        todo = []
        for e in data["files"]:
            try:
                rel, size, want = e["path"], int(e["size"]), str(e["sha256"]).lower()
            except (KeyError, TypeError, ValueError):
                raise UpdateError("A manifest entry is malformed.")
            target = safe_target(self.game_dir, rel)
            ok = os.path.isfile(target) and os.path.getsize(target) == size and sha256_file(target) == want
            self.say(("ok            " if ok else "needs update  ") + rel)
            if not ok:
                todo.append((rel, size, want, target))
        if not todo:
            self.progress(1, 1)
            self.status("Up to date.")
            return 0
        total = max(1, sum(t[1] for t in todo))
        done = 0
        for n, (rel, size, want, target) in enumerate(todo, 1):
            self.status("Downloading %s (%d of %d)" % (rel, n, len(todo)))
            done = self._download(rel, size, want, target, done, total)
        self.progress(1, 1)
        self.status("Updated %d file(s)." % len(todo))
        return len(todo)

    def _download(self, rel, size, want, target, done, total):
        url = self.server + "/files/" + urllib.parse.quote(rel)
        part = target + ".part"
        os.makedirs(os.path.dirname(target), exist_ok=True)
        h = hashlib.sha256()
        got = 0
        try:
            with self._get(url, 20) as r, open(part, "wb") as out:
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
                    self.progress(done + got, total)
        except (urllib.error.URLError, OSError) as e:
            self._drop(part)
            raise UpdateError("Download of %s failed: %s" % (rel, e))
        if got != size or h.hexdigest() != want:
            self._drop(part)
            raise UpdateError("%s arrived damaged (size or hash mismatch). Nothing was changed." % rel)
        try:
            if os.path.isfile(target):
                shutil.copy2(target, target + ".old")     # one-step undo
            os.replace(part, target)
        except OSError as e:
            self._drop(part)
            raise UpdateError("Could not replace %s (is the game running?): %s" % (rel, e))
        self.say("downloaded    " + rel)
        return done + got

    @staticmethod
    def _drop(path):
        try:
            os.remove(path)
        except OSError:
            pass
