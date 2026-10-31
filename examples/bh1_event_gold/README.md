# Bounty Hunter I gives Event Gold

Adds a **10 Event Gold Ticket** (item 30759, x1, permanent) to the reward list of every Bounty Hunter I quest (19949-19964 and 19967), so players earn Event Boutique currency from the daily BH runs. *[tested in game]*

```
python add_bh1_ticket.py tasks.data tasks_bh1.data
```
- Skips quests that already have the ticket, so running it twice is harmless.
- The result must go to the server (`/opt/gamed/config/tasks.data`, keep a backup) **and** every client (`element\data\tasks.data`); a mismatch breaks quests.
- `sudo server restart`, then hand in one BH I quest to check.

How it works: a reward row is 17 bytes (item, flag, count, chance, period). Adding one inserts 17 bytes into the quest, raises that reward group's row count and shifts every later quest's offset in the table at the start of the file. Layout: [tasks.data](../../docs/layouts/tasks/README.md). The [editor's](../../tools/ultimusv2/README.md) Quest rewards tab does the same with a window.

---
[Back to examples](../README.md)
