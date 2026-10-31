# Examples

Worked changes we made on our own server, each with its script and the steps around it. They show the method; change the ids for your own server. For general tools see [`tools/utility_scripts/`](../tools/utility_scripts/README.md) and the [editor](../tools/ultimusv2/README.md).

| Folder | What it does | Files changed |
|---|---|---|
| [`bh1_event_gold/`](bh1_event_gold/README.md) | Bounty Hunter I hand-ins also give a 10 Event Gold Ticket | `tasks.data` (server + client) |
| [`blessing_tickets/`](blessing_tickets/README.md) | Sell Jones' / O'Malley's Blessing so the stats really apply | Event Boutique pair |
| [`palette_swap/`](palette_swap/README.md) | Replace 5 seasonal Palette of Fortune prizes | `elements.data` (server + client) |
| [`npc_shop_examples/`](npc_shop_examples/README.md) | Find and change what an NPC sells | `elements.data` (server + client) |

Every script writes a new file and never changes its input. Snapshot the VM first, and keep the server and client copies of a file identical.

---
[Back to the repository overview](../README.md)
