# elements.data (e344)

How items are found, and the lists we have mapped. NPC shops have [their own page](../npc_shops/README.md).

Machine-readable version (what the editor loads): [`elements_item.json`](../../../tools/ultimusv2/layouts/elements_item.json), [`elements_flow.json`](../../../tools/ultimusv2/layouts/elements_flow.json). Edit layouts there, not copies here.

## elements.data (partial)
- Item id sits 4, 8 or 12 bytes before the 64-byte UTF-16 name: 12 for equipment-like records (id, major type, sub type, name), 8 for monsters and stones, 4 for tickets, packs and vouchers.
- Stat entries: 84 B `[id][name 64 B][1][value][0][0]`.
- Bless Box records (type pair 21213/21285, 1164 B): see [Bless Box record](../../research/investigations/blessing_system/README.md#useful-layout-bless-box-record-e344-1164-bytes-code-our-file).

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

## Crafting services (list 55) *[tested]*
349 records x 1,228 B; header `[55][349][1228]` right before the first record.

| Offset | Field |
|---|---|
| +0 | service id |
| +4 (64 B) | name, UTF-16 |
| +68 | craft skill id (160 = Craftsman; 158 / 159 / 161 others) |
| +72 | **production type**: 0 / 1 / 3 / 4 / 5 / 6. The 1.7.3 gs refuses type 1 ("Invalid service request") *[tested]*; 3-6 untested |
| +76 | 8 pages x 144 B: 16 B title + 32 recipe ids |

NPC record (list 58): +740 sell shop, +744 / +748 other services, **+796 crafting service id**.

Recipe record (list 70) extra fields: +80 skill id, +84 skill level, +88 flag 0/1/2 (meaning unknown; not the cause of the forge error) *[tested]*.

## Monster EXP and spirit (list 39)
+588 EXP, +592 spirit (both match the in-game encyclopedia). Changing them changes the reward in game. *[tested]*

---
[Back to data layouts](../README.md)
