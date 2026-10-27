"""Known versions of our data files (layouts/known_files.json), so the editor can say which version you opened."""
import json
import os

from .layout import base_dir

with open(os.path.join(base_dir(), 'layouts', 'known_files.json'), 'r', encoding='utf-8') as _f:
    KNOWN = json.load(_f)['files']


def identify(path, md5):
    """Returns (status, label): status is live / old / experiment / unknown."""
    name = os.path.basename(path).lower()
    for fname, versions in KNOWN.items():
        if name == fname.lower() or name.startswith(os.path.splitext(fname)[0].lower() + '_'):
            v = versions.get(md5)
            if v:
                return v['status'], v['label']
    for versions in KNOWN.values():   # renamed copies (e.g. elements_copy.data): match by md5 alone
        v = versions.get(md5)
        if v:
            return v['status'], v['label']
    return 'unknown', 'not a known version (edited or new)'


def describe(path, md5):
    status, label = identify(path, md5)
    warn = ''
    if status == 'old':
        warn = '  <-- OLD VERSION: edits made from it would drop later changes'
    elif status == 'experiment':
        warn = '  <-- EXPERIMENT FILE: do not use'
    return '%s: %s%s' % (os.path.basename(path), label, warn), status
