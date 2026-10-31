# Faction Safe: NPC service 115 and protocol 5882 (reference only)

> The Faction Safe is **off this project's goals**. Kept so nobody has to rediscover it. Facts from our own 1.7.3 client and server programs. *[code]*

## What the client has
- The full window `Win_GuileStorage`: 3 tabs x 96 slots, per-rank deposit / withdraw ticks, sort, log.
- Every action is sent as NPC service **115** (client command 37) with a sub-code: 0x4, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200.
- The window is opened and filled by GNET protocol **5882** `FactionStoreHouseList_Re`.

## What the server lacks
- gs has no service 115: using the Safe Stone gives "Service unavailable" and freezes the character until relog.
- No 1.7.3 server program knows protocol 5882, glinkd included ([glinkd](../binaries/glinkd.md)).
- No program stores or changes faction Loyalty ([gfactiond](../binaries/gfactiond.md)).

A working safe would need new server code **and** a glinkd change. A gs-side "polite decline" for service 115 (no freeze) is possible with the [treasure_hook](../../../addons/treasure_hook/README.md) technique.

History: [investigation notes](../investigations/faction_safe/README.md).

---
[Back to research notes](../README.md)
