# NPC shops (elements.data lists 41 and 58)

Which NPC sells what.

Machine-readable version (what the editor loads): [`elements_npcshops.json`](../../../tools/ultimusv2/layouts/elements_npcshops.json). Edit layouts there, not copies here.

## NPC shops in elements.data (e344), used by the NPC shops tab
Confirmed 2026-10-26 on our elements.data.
- Every list we found starts with a header `[list id][record count][record size]` right before its first record.
- **Shop list = list 41**: 174 records x 5,448 B, first record at 35,762,472. Record: +0 id, +4 name (64 B UTF-16, mostly "Goods"), +68 8 pages x 672 B, +5444 trailing u32 (0 everywhere).
- **Page** (672 B): +0 title (32 B UTF-16, max 15 characters), +32 32 slots x 20 B.
- **Slot** (20 B): +0 item id (0 = empty), +4..+16 four extra u32 (unknown; values like 8, 20, 40, 600, 2400, 3600, 24000 on some slots).
- **NPC list = list 58**: 7,406 records x 1,080 B. +0 id, +4 name, **+740 shop id** (set on 860 NPCs). Example: Merchant Wang Song (2165) -> shop 2673 (pages Jade / Misc. / Gem; Jade sells 771-779 Broken/Orange/Red/Verdant/Black/Yellow Jade), shared with Merchant Li Er, Merchant Fu and others.
- Old low-id items (e.g. 36 "☆Mother and Son Blades", 259 "☆Beast Bone Necklace", 771 "Broken Orange Jade") have small type pairs; the item index accepts them (id, type a < type b < 1000, name).

---
[Back to data layouts](../README.md)
