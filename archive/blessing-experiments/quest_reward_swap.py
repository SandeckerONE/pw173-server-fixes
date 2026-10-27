#!/usr/bin/env python3
# quest_reward_swap.py - EXPERIMENT on a COPY of tasks.data. Same size in, same size out.
# In quest 33836 ("Peerless Blessing") the reward item 48056 (Peerless Blessing, 3600 s) is replaced by another item id.
# Refuses unless the quest and its reward row are exactly as expected. Never edits the input; writes a NEW file.
# Usage: python quest_reward_swap.py <tasks.data copy> <output file> <new item id>      e.g. 22198
import struct, sys, hashlib, os
if len(sys.argv) != 4:
    sys.exit('usage: python quest_reward_swap.py <tasks.data copy> <output file> <new item id>')
src, dst, new = sys.argv[1], sys.argv[2], int(sys.argv[3])
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit('input and output must be different files')
d = bytearray(open(src, 'rb').read()); N = len(d)
print('input size', N, 'md5', hashlib.md5(d).hexdigest())
QID, OLD = 33836, 48056
p = struct.pack('<I', QID); k = QID & 0xFFFF; quests = []; i = d.find(p)
while i != -1:
    raw = struct.unpack_from('<30H', d, i + 4)
    nm = ''.join(chr(x ^ k) if (x ^ k) else '\0' for x in raw).split('\0')[0]
    if nm == 'Peerless Blessing':
        quests.append(i)
    i = d.find(p, i + 1)
if len(quests) != 1:
    sys.exit('expected exactly one quest %d named Peerless Blessing, found %d - nothing done' % (QID, len(quests)))
q = quests[0]
row = struct.pack('<IBIfi', OLD, 1, 1, 1.0, 3600)
j = d.find(row, q, q + 8000)
if j == -1 or d.find(row, j + 1, q + 8000) != -1:
    sys.exit('reward row (48056 x1, 3600 s) not found exactly once inside the quest - nothing done')
print('quest at', q, '| reward row at', j, '(%d bytes into the quest)' % (j - q))
struct.pack_into('<I', d, j, new)
assert len(d) == N
open(dst, 'wb').write(d)
print('reward item changed:', OLD, '->', new, '| bytes changed: 4')
print('wrote', dst, '| md5 out:', hashlib.md5(d).hexdigest())
