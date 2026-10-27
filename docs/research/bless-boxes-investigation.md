# Bless Boxes bought from the Boutique give no stats (investigation)

**Result:** Jones' Blessing and O'Malley's Blessing work when a **Ticket quest** hands them out, with the original, unedited `elements.data` and `tasks.data`. Copies sold straight from the Boutique give nothing. *[tested]* The how-to is [guide page 17](../server-guide/17-bless-boxes.md).

Sources: our own `elements.data` (e344), `tasks.data` (t187), Event Boutique files, server logs and in-game tests. No outside code.

## Symptom
Bought from the Event Boutique and equipped in the Blessing slot, the tooltip shows the bonus but the character sheet does not change (Attack Lv and Defense Lv stay the same). A damage test on a training mob confirmed the bonus was not just hidden. *[tested]*

## What we ruled out *[tested]*
- **The Blessing slot.** Peerless Blessing (from the daily sign-in) works in the same slot: Attack Lv +8, Defense Lv +8, Spirit +100, Physical/Magic Penetration +300.
- **The effect type.** Peerless uses an effect from the same old family as ours, and it works.
- **Permanent vs timed.** Giving the shop copies a 7-day duration changed the tooltip ("Duration: 6 day(s) 23 hour(s)") and nothing else.
- **The item record.** Peerless differs from ours in item level (+368: 16 vs 0), quality (+400: 3 vs 1), flags (+1124) and a second, filled effect list (+820). We copied all of these onto O'Malley's and only the second list onto Jones'. With the server confirmed to have loaded the edited file, shop-bought copies still gave nothing. The edit was reverted; it was not needed.

## What worked *[tested]*
| Ticket | Quest | Gives | Result |
|---|---|---|---|
| Jones' Blessing Ticket 28297 | 22076 "Jones' Blessing" | 22198 x1, 7 days | Attack Lv 1 -> 31 |
| O'Malley's Blessing Ticket 28523 | 22208 "O'Malley's Serendipity" *[quest id inferred]* | 28524 x1, 7 days | Attack Lv and Defense Lv +15 |

Peerless itself also comes from a quest (33836, opened by voucher 48060), which fits the pattern.

**Likely reason** *[inferred]*: items created by the quest reward code get their effects set up; items created by the Boutique purchase path do not, for this item type.

## Found on the way: stackable items can't have a shop duration *[tested, server log]*
If a stackable item (tickets stack) has a shop duration, the maps refuse to start (error -32, "Event Boutique data failed to initialize"). The log names the item id and the record index. Tickets must be sold with duration 0. The blessings themselves don't stack and can carry a duration.

## Useful layout: Bless Box record (e344, 1164 bytes) *[code, our file]*
`+0` id · `+4/+8` type pair · `+12` name (64 B) · `+368` item level · `+388` class mask · `+392` required level · `+400` quality · `+492/+496` prices · `+564` effect list (32 x [id, chance]) · `+820` second effect list · `+1124` flags (0x1 no drop on death, 0x2 no discard, 0x4 no sell, 0x10 no trade, 0x4000 no account stash).

Effect entries are 84 bytes: `[id][name 64 B][1][value][0][0]`.

The scripts used for the failed experiments are in [`archive/blessing-experiments/`](../../archive/blessing-experiments/).

---
[Back to research notes](README.md)
