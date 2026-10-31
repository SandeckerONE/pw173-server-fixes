# Data file layouts

Byte-by-byte maps of the 1.7.3 (e344 / t187) data files, worked out on our own files. Each page says how each field was confirmed.

| Page | File | Editor table (`tools/ultimusv2/layouts/`) |
|---|---|---|
| [elements](elements/README.md) | `elements.data`: item index, monsters and drops, recipes, packs, crafting services | `elements_item.json`, `elements_flow.json` |
| [npc_shops](npc_shops/README.md) | `elements.data` lists 41 (shops) and 58 (NPCs) | `elements_npcshops.json` |
| [tasks](tasks/README.md) | `tasks.data` header and quest records | `tasks.json` |
| [quest_rewards](quest_rewards/README.md) | `tasks.data` reward rows | `tasks.json` |
| [gshop](gshop/README.md) | Boutique and Event Boutique, client and server | `gshop_client.json`, `gshop_server.json` |
| [npcgen](npcgen/README.md) | `world/npcgen.data` spawn areas | (none yet) |

The JSON tables live in [`tools/ultimusv2/layouts/`](../../tools/ultimusv2/layouts/) only, so the docs and the program can't drift apart. `known_files.json` there is a template for your own file versions (see the [editor README](../../tools/ultimusv2/README.md)).

---
[Back to the repository overview](../../README.md)
