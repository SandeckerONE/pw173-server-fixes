# Verified layouts (reference)

Every layout the editor uses, and how it was confirmed. The JSON tables in [`tools/ultimusv2/layouts/`](../../tools/ultimusv2/layouts/) are the machine-readable version (the editor reads them; edit them there, not copies).

## Boutique client file (gshop.data, gshop1.data): header 8 B, records 1448 B, then the category list
Confirmed 2026-10-26 on the user's client: main Boutique 3,103 records, Event Boutique 158; unchanged load/save is byte-identical.

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

## elements.data (partial)
- Item id sits 4, 8 or 12 bytes before the 64-byte UTF-16 name: 12 for equipment-like records (id, major type, sub type, name), 8 for monsters and stones, 4 for tickets, packs and vouchers.
- Stat entries: 84 B `[id][name 64 B][1][value][0][0]`.
- Bless Box records (type pair 21213/21285, 1164 B): see `claude/blessing_boxes_173.md`.

## tasks.data (t187), used by the Quest rewards tab
Confirmed 2026-10-26 on the user's file (md5 17a45032, BH1-patched).
- Header: +0 magic 0x93858361, +4 version 187, +8 quest count (20,122), +12 table of quest record offsets (sorted; a record runs to the next offset).
- Quest record: +0 u16 prefix (0, or 1 on 52 records), +2 quest id u32, +6 name: 30 UTF-16 units XORed with (id & 0xFFFF), may start with a ^rrggbb colour. Records are not 4-byte aligned. Sub-quests are nested inside their parent's record.
- Reward group: u8 flag (0 fixed list, 1 list with random rows [inferred]), u32 row count, then rows. Found by scanning the record for [flag<=1][1..60][valid rows].
- Reward row 17 B: item id u32, flag u8 (1 on almost every row), count u32, chance f32 (0..1), period s32 (lifetime in seconds, 0 = permanent).
- Adding/removing a row: insert/remove 17 bytes, update the group's row count, shift every later quest offset. Proof: deleting the 17 BH1 ticket rows rebuilds the original file (md5 9abe2781) exactly, and adding them back rebuilds the BH1 file (md5 17a45032) exactly; the BH1 file was tested in game.
- Examples: 22076 "Jones' Blessing" -> 22198 x1 604800 s; 22208 "O'Malley's Serendipity" -> 28524 x1 604800 s; 33836 "Peerless Blessing" -> 48056 x1 3600 s; 18930 "Genie Pack" -> 32 random rows summing to 100%.

## NPC shops in elements.data (e344), used by the NPC shops tab
Confirmed 2026-10-26 on the user's file (md5 c89984b5).
- Every list we found starts with a header `[list id][record count][record size]` right before its first record.
- **Shop list = list 41**: 174 records x 5,448 B, first record at 35,762,472. Record: +0 id, +4 name (64 B UTF-16, mostly "Goods"), +68 8 pages x 672 B, +5444 trailing u32 (0 everywhere).
- **Page** (672 B): +0 title (32 B UTF-16, max 15 characters), +32 32 slots x 20 B.
- **Slot** (20 B): +0 item id (0 = empty), +4..+16 four extra u32 (unknown; values like 8, 20, 40, 600, 2400, 3600, 24000 on some slots).
- **NPC list = list 58**: 7,406 records x 1,080 B. +0 id, +4 name, **+740 shop id** (set on 860 NPCs). Example: Merchant Wang Song (2165) -> shop 2673 (pages Jade / Misc. / Gem; Jade sells 771-779 Broken/Orange/Red/Verdant/Black/Yellow Jade), shared with Merchant Li Er, Merchant Fu and others.
- Old low-id items (e.g. 36 "☆Mother and Son Blades", 259 "☆Beast Bone Necklace", 771 "Broken Orange Jade") have small type pairs; the item index accepts them (id, type a < type b < 1000, name).

## Lists used by Item flow (elements.data e344), verified 2026-10-26
Every list found by its header `[list id][count][record size]`.

| List | Id | Records x size | Used for |
|---|---|---|---|
| stat entries | 1 | 3,559 x 84 | not items (index skips them) |
| monsters | 39 | 12,623 x 1,748 | drops |
| NPC shops | 41 | 174 x 5,448 | sold by |
| NPCs | 58 | 7,406 x 1,080 | who uses a shop |
| recipes | 70 | 10,787 x 440 | crafting |
| packs / vouchers / task items | 75 | 4,053 x 600 | opens quest |

- **Monster** record: +0 id, +4 type, +8 name. Drops: +1268 four chances that one roll drops 0/1/2/3 items (sum 1.0), +1284 number of rolls, +1292 32 x (item u32, share f32), shares sum 1.0. Checked on all 3,948 monsters with drops. Example: Skeleton Legion Marshal (17359): 8 rolls of 3 items from Big Golden Sculpture 11.5%, Big Luminostone 12.0%, Tear of Heaven 10.9%, Leaf of Unicorn Forest 32.8%, Stone of the Scarred 27.3%, Desert Tower Miniature 5.5%.
- **Recipe** record: +0 id, +4/+8 category, +12 name (debug name), +92 4 x (product, chance) summing to 1.0 (checked on 10,720 recipes), +128 coins [inferred], +148 32 x (material, count), at most 8 used. Example: ☆Battle Falchion = 5 Purified Oil + 3 Orange Jade + 1 Copper Bar -> 67% 1-star, 30% 2-star, 3% 3-star.
- **Pack/voucher** (list 75): +328 quest started on use (Genie Pack 23965 -> 18930, Anniversary Pack 25148 -> 20191, Peerless voucher 48060 -> 33836); set on 3,820 of 4,053.
- **Needed-by-quest rows** (tasks.data): reward-row format with chance 0.0, in the quest's needed-items area (quest offset 1560-1700, usually +1576, +1585 on Bounty Hunter II/III), row flag 1, id not a multiple of 256. +1576 holds 2,013 different items across the file.
