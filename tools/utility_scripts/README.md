# Utility scripts

Small one-job Python 3 scripts. The [editor](../ultimusv2/README.md) does the shop and quest jobs with a window and more checks; these stay as short, readable examples of the file formats and for jobs the editor doesn't do yet.

All of them **write a new file and never change the input**, and refuse to run if the file doesn't look as expected. They check the file's **structure** (list headers, record counts, expected values), not a fixed md5, so they work on your own edited files too.

| Script | Job | Usage |
|---|---|---|
| `dump_item.py` | Read-only: print an item's raw record from `elements.data` | `python dump_item.py elements.data 22198` |
| `shop_swap_item.py` | Change which item one Event Boutique record sells | `python shop_swap_item.py in out <old id> <new id>` |
| `shop_set_duration.py` | Set the shop duration (seconds, 0 = permanent) | `python shop_set_duration.py in out 0 28297` |
| `forge_type_fix.py` | Fix "Invalid service request" at forges (crafting type 1 -> 0) | `python forge_type_fix.py elements.data out.data` (`--list` to look first) |
| `npcgen_hide_spawns.py` | Hide NPC spawns (ERR models, unwanted NPCs) by switching their spawn areas off | `python npcgen_hide_spawns.py npcgen.data --list 71014` then `... out.data --hide 71014` |

Notes:
- The shop scripts work on `gshop1.data` (client) or `gshopsev1.data` (server). **Patch both** the same way, and never give a stackable item a duration ([Bless Boxes](../../docs/server-guide/bless-boxes.md)).
- `forge_type_fix.py` must be run on the server's **and** the client's `elements.data` ([Troubleshooting](../../docs/server-guide/troubleshooting.md#forges-answer-invalid-service-request)).
- `npcgen_hide_spawns.py` is server-only ([Troubleshooting](../../docs/server-guide/troubleshooting.md#stray-npcs-floating-err-chinese-names-duplicate-merchants)).
- Patch scripts that were used for a single change on our own server are in [`examples/`](../../examples/README.md).

---
[Back to the repository overview](../../README.md)
