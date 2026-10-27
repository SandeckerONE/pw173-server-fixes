"""Build manifest.json for the patch folder.

Usage:  python make_manifest.py C:\\pwmod\\patch
Expects the files to hand out in  <patch folder>\\files\\...  laid out like the game's
'element' folder (for example files\\data\\gshop.data). Writes <patch folder>\\manifest.json.
"""
import hashlib
import json
import os
import sys
import time

root = sys.argv[1]
files_dir = os.path.join(root, "files")
if not os.path.isdir(files_dir):
    sys.exit("No 'files' folder in %s" % root)
entries = []
for dirpath, dirnames, filenames in os.walk(files_dir):
    for name in filenames:
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, files_dir).replace("\\", "/")
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        entries.append({"path": rel, "size": os.path.getsize(full), "sha256": h.hexdigest()})
entries.sort(key=lambda e: e["path"])
manifest = {"format": 1, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "files": entries}
with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
for e in entries:
    print("%-40s %12s bytes  %s" % (e["path"], format(e["size"], ","), e["sha256"][:16] + "..."))
print("%d file(s) written to %s" % (len(entries), os.path.join(root, "manifest.json")))
