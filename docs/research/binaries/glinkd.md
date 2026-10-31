# glinkd (link server)

Very little mapped so far. *[code]*
- Players connect to it on 29000; it forwards between client and gdeliveryd / gs.
- Logs `Protocol Unknown` for protocol types it doesn't know. **No 1.7.3 server program knows protocol 5882** (`FactionStoreHouseList_Re`), glinkd included, so a Faction Safe can't reach the client without changing glinkd ([faction safe](../protocols/faction_safe_5882.md)).

To do (horizon): list the protocol ids glinkd accepts, as part of a g-binary index.

---
[Back to research notes](../README.md)
