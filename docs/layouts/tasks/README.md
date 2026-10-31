# tasks.data (t187)

Quest file header and quest records. Reward rows: [quest rewards](../quest_rewards/README.md).

Machine-readable version (what the editor loads): [`tasks.json`](../../../tools/ultimusv2/layouts/tasks.json). Edit layouts there, not copies here.

## tasks.data (t187), used by the Quest rewards tab
Confirmed 2026-10-26 on our tasks.data (stock file and the BH I edit from [`examples/bh1_event_gold`](../../../examples/bh1_event_gold/README.md)).
- Header: +0 magic 0x93858361, +4 version 187, +8 quest count (20,122), +12 table of quest record offsets (sorted; a record runs to the next offset).
- Quest record: +0 u16 prefix (0, or 1 on 52 records), +2 quest id u32, +6 name: 30 UTF-16 units XORed with (id & 0xFFFF), may start with a ^rrggbb colour. Records are not 4-byte aligned. Sub-quests are nested inside their parent's record.

---
[Back to data layouts](../README.md)
