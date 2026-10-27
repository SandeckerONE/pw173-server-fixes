# Example patch scripts

Small one-job Python scripts from before the [editor](../tools/ultimusv2/README.md) existed. The editor does all of this with checks and a window; these are kept as short, readable examples of the file formats.

All of them **write a new file and never change the input**, and refuse to run if the file doesn't look exactly as expected.

| Script | Job | Usage |
|---|---|---|
| `dump_item.py` | Read-only: print an item's raw record from `elements.data` | `python dump_item.py elements.data 22198` |
| `shop_swap_item.py` | Change which item one Event Boutique record sells | `python shop_swap_item.py in out <old id> <new id>` |
| `shop_set_duration.py` | Set the shop duration (seconds, 0 = permanent) | `python shop_set_duration.py in out 0 28297` |

The shop scripts work on `gshop1.data` (client) or `gshopsev1.data` (server). **Patch both** with the same change, and never give a stackable item a duration ([guide page 17](../docs/server-guide/17-bless-boxes.md)).

---
[Back to the repository overview](../README.md)
