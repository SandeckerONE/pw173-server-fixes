# gs (game server / map processes)

Notes on the 1.7.3 `gs` binary, read from our copy (it ships with debug symbols, so function names are readable) and checked in game where marked. Only facts from our own files.

## Config switches that matter
| Setting | What gs does with it | Source |
|---|---|---|
| `ptemplate.conf` `debug_command_mode` | Only the exact value `active` turns on `DebugCommandHandler`, which has **no GM check** (Ctrl+click teleport, item/cash test commands) | [code + tested] |
| `ptemplate.conf` `exp_bonus`, `sp_bonus` | Read, but `AdjustGlobalExpSp` is an empty function: no effect | [code + tested] |
| `ptemplate.conf` `money_bonus` | Coins x (1 + value) | [code + tested] |
| `ptemplate.conf` `[MESMD_ADJUST]` | Level-difference table; no visible effect on solo kills | [tested] |
| `gs.conf` `limit = ... nothrow;` | `gplayer_imp::PlayerDropInvItem` refuses every drop on that map (error 44) | [code + tested] |

## Runtime switches (`OnReportAttr`)
gdeliveryd pushes these to every gs ([gdeliveryd](gdeliveryd.md)); pwAdmin's Server Configuration page sets them. *[code + tested]*
- `SetDoubleExp`: value 10-100, multiplier = value / 10 (1x-10x). Spirit follows it.
- `SetDoubleMoney`, `SetDoubleObject` (drop table rolled twice), `SetDoubleSP`.
- `SetNoTrade`, `SetNoMail`, `SetNoAuction`, `SetNoFaction`, `SetNoSellPoint`, `SetPVP`.

## Drops *[code]*
The number of drop rolls comes from the monster record (+1284, `elements.data` list 39). One kill drops at most 44 items.

## Missing or half-done features
- **Treasures (`Lottery_Notice1`)**: only type 2 (warehouse withdraw) is implemented; seek/open are missing. Returning false makes `CommandHandler` send error 3. Client command 197 accepts action types 0-3 only. *[code + tested]* See [treasure protocol](../protocols/treasure_protocol.md).
- **Faction Safe**: no NPC service 115. *[code]* See [faction safe](../protocols/faction_safe_5882.md).
- **Crafting**: services with production type 1 answer "Invalid service request". *[tested]* See [NPC services](../protocols/npc_services.md).
- **Palette of Fortune**: works; refuses with error 108 while the Safety Lock is active. *[code]*

## Debug commands (`DebugCommandHandler`)
| Command | Effect |
|---|---|
| `d_c2scmd 10844 <a> <b>` | `a` Faction Construction and `b` Faction Contribution points *[tested]* |

---
[Back to research notes](../README.md)
