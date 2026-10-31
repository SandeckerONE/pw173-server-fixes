# Boutique files (gshop*.data, gshopsev*.data)

Main Boutique (`gshop.data` / `gshopsev.data`) and Event Boutique (`gshop1.data` / `gshopsev1.data`), 1.7.3 e344.

Machine-readable version (what the editor loads): [`gshop_client.json`](../../../tools/ultimusv2/layouts/gshop_client.json), [`gshop_server.json`](../../../tools/ultimusv2/layouts/gshop_server.json). Edit layouts there, not copies here.

## Boutique client file (gshop.data, gshop1.data): header 8 B, records 1448 B, then the category list
Confirmed 2026-10-26 on our client: main Boutique 3,103 records, Event Boutique 158; unchanged load/save is byte-identical.

| Offset | Field | Notes |
|---|---|---|
| +0 | lid | = record index |
| +4 / +8 | main tab / sub tab | indexes into the category list |
| +12 (128 B) | icon path | GBK text |
| +140 | item id | |
| +144 | count | |
| +148..+275 | 4 price slots x 32 B | slot 0: +148 price (x100), +152 0, **+156 duration (s)**, +160 0, +164 -1, +168 0, **+172 status label**, +176 0. Slots 1-3 unused in stock files (a few small values at +180 are carried through) |
| +276 (16 B) | block A | new in 1.7.3, unknown, kept |
| +292 (1024 B) | description | UTF-16; literal `\r` = line break; `^rrggbb` = colour |
| +1316 (64 B) | name | UTF-16, max 31 characters |
| +1380 (68 B) | block B | new in 1.7.3 (item ids and small numbers seen, probably gift/bonus fields), kept; last u32 is -1 |

**Category list** (after the last record): per main tab, a 128 B UTF-16 name, a u32 sub count, then that many 128 B sub names. Main Boutique: Shop, Fashion, Star, Flyers, Ride, Chat, Utility, Craft. Event Boutique: Shop (E.Gold), Fashion, Firework, Flyers, Ride, Chat, Utility, Craft.

## Boutique server file (gshopsev.data, gshopsev1.data): header 8 B, records 232 B, no trailer
Confirmed on the Event Boutique pair, which matches the client record for record.

| Offset | Field |
|---|---|
| +0..+16 | lid, main tab, sub tab, item id, count (= client) |
| +20..+147 | 4 price slots (= client +148..+275): +20 price, +28 duration, +44 status label |
| +148 (16 B) | = client block A [inferred pairing] |
| +164 (68 B) | = client block B [inferred; last u32 -1 on both sides, verified] |

## Rules confirmed in the server log
- A stackable item with a shop duration stops the maps: `...可堆叠但存在有效期的物品<id>，无法进行初始化操作 索引<n>`, error -32.
- (1.4.6, likely the same here) a count above the item's stack limit stops the maps ("exceeds the stack limit").

---
[Back to data layouts](../README.md)
