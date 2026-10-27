# Data file layouts

Byte-by-byte maps of the 1.7.3 (e344 / t187) data files, worked out on our own files.

- **[LAYOUTS.md](LAYOUTS.md)**: the readable reference, with how each field was confirmed.
- **The JSON tables** the editor uses live in [`tools/ultimusv2/layouts/`](../../tools/ultimusv2/layouts/). They are kept in one place only, so the docs and the program can't drift apart.

| File | What it maps |
|---|---|
| `gshop_client.json` / `gshop_server.json` | Boutique records (client 1448 B, server 232 B) |
| `elements_item.json` | How items are found in `elements.data` |
| `elements_npcshops.json` | NPC shops (list 41) and NPCs (list 58) |
| `elements_flow.json` | Monsters and drops, recipes, packs -> quests |
| `tasks.json` | `tasks.data` header, quest records, reward rows |
| `known_files.json` | md5 of our known file versions (live / old / experiment) |

---
[Back to the repository overview](../../README.md)
