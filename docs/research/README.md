# Research notes

How we worked things out: the evidence behind the [server guide](../server-guide/README.md). Every claim is tagged *[tested]* (in game or by command output), *[code]* (read from our own 1.7.3 programs or client) or *[inferred]* (best reading, not proven). **Only our own 1.7.3 files are used as sources.**

## binaries/: what each server program does
[gs](binaries/gs.md) · [gdeliveryd](binaries/gdeliveryd.md) · [authd](binaries/authd.md) · [glinkd](binaries/glinkd.md) · [gfactiond](binaries/gfactiond.md)

## protocols/: what client and server send each other
| Note | Short version |
|---|---|
| [Treasures](protocols/treasure_protocol.md) | Command 197, types 0-3; gs only does type 2. Board layout still to be re-derived |
| [Faction Safe (5882)](protocols/faction_safe_5882.md) | Client has it all; no server program knows service 115 or protocol 5882 |
| [NPC services](protocols/npc_services.md) | Crafting production type 1 = "Invalid service request" |

## investigations/: full write-ups
| Note | Short version |
|---|---|
| [Bless Boxes](investigations/blessing_system/README.md) | Sell the Ticket, let its quest give the blessing |
| [npcgen spawns](investigations/npc_spawns/README.md) | Spawn areas mapped; switch +59 = 18 hides a spawn |
| [Palette of Fortune](investigations/palette/README.md) | Works; Safety Lock error 108; prize table record 6064 |
| [Faction Safe](investigations/faction_safe/README.md) | Archived: dropped from the goals |

## The method we keep using
Every data format here was mapped the same way:
1. Start from something known (an item id, a value seen in game).
2. Find its bytes in the file.
3. Guess the record size from how far apart the repeats are.
4. Walk the **whole** file with that guess; it must end exactly at a sane place.
5. Profile each field across all records (constant? flag? id-like?).
6. Explain fields with small in-game tests, on a snapshot.
7. Patch with a guarded, same-size script that writes a new file and checks itself.
8. Confirm in game, and write down which claims are tested and which are inferred.

---
[Back to the repository overview](../../README.md)
