# Faction Safe and faction Loyalty (archived)

> **Archived 2026-10-26.** The Faction Safe was dropped from this project's goals. These notes were section 13 of the old guide and are kept only for reference. Nothing here is being worked on.
❌ → 🔧 *[code + tested]*

**Symptom:** using the Faction Safe Stone at the Faction Base Manager gives "Service unavailable" and **freezes the character** (no walking, flying or skills) until relog. Faction Loyalty never increases. The Guild Base map running doesn't change it.

**Cause:** the server package has no code for it. gs has no NPC service for faction storage; the storage whitelist data is loaded but never used; gfactiond only handles membership, alliances and faction upgrade; no program stores or changes faction Loyalty. Others report the same on 1.7.3.

**What the client expects** *[code, from the 1.7.3 client]*: the client has the whole Faction Safe (window `Win_GuileStorage`: 3 tabs x 96 slots, per-rank deposit/withdraw ticks, sort, log). Every action is sent as NPC service **115** (client command 37) with a sub-code (0x4, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200). The window is opened and filled by GNET protocol **5882** `FactionStoreHouseList_Re`.

**Why it can't simply be added:** `gs` has no service 115 (that is the "Service unavailable" and the freeze), and **no 1.7.3 server program knows protocol 5882, glinkd included** (glinkd logs `Protocol Unknown` for types it doesn't know). A real fix needs server code for the safe **and** a change to glinkd so 5882 can reach the client.

**Workaround:** a shared "bank" character the faction trades items to. Tell players not to use the Safe Stone. A gs-side "polite decline" for service 115 (so nobody freezes) is possible with the same hook technique as [`addons/treasure_hook/`](../../../../addons/treasure_hook/README.md).

Clean summary of what the client expects: [protocols/faction_safe_5882.md](../../protocols/faction_safe_5882.md).

---
[Back to research notes](../../README.md)
