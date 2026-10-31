# npcgen.data (world, version 11)

The spawn file the server reads from `/opt/gamed/config/world/npcgen.data`. Server-only: clients don't have it. Mapped on our own copy of the stock 1.7.3 file; the editor doesn't load it yet, so there is no JSON table. How it was worked out: [research note](../../research/investigations/npc_spawns/README.md).

## Header *[verified]*
Five u32: version **11**, then four section counts: **21,521** spawn areas, 4,979, 2,610, 4,110 *[only the first count is proven]*.

## Spawn areas *[verified: a walk of all 21,521 areas ends exactly at offset 3,202,699]*
Each area is a **71-byte header** followed by *count* x **64-byte entries**.

| Offset | Field | Notes |
|---|---|---|
| +0 | type | 1 = NPCs, 0 = monsters *[inferred]* |
| +4 | entry count | 0 is allowed (one stock area has it) |
| +8 | position x, y, z (3 f32) | in-game map coordinates ≈ x/10 + 400, z/10 + 550 *[inferred, close enough to find spawns]* |
| +44, +52..+54 | small flag fields | unknown |
| +55 | almost always 12 | unknown |
| **+59** | **switch / controller id** | 0 = always on. Hidden event spawns use a controller nobody switches on (18 on this package). Setting an area to 18 hides it *[tested in game]* |
| +63, +67 | unknown | |

Entry (64 B): +0 NPC or monster id (= elements.data list 58 / 39 id), later fields not mapped.

## Not mapped yet
The data after 3,202,699 (resources, dynamic objects, controllers), entry fields after +4, the area fields marked unknown.

Hide tool: [`tools/utility_scripts/npcgen_hide_spawns.py`](../../../tools/utility_scripts/README.md).

---
[Back to data layouts](../README.md)
