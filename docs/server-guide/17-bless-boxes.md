# 17. Adding Bless Box items (Jones' Blessing, O'Malley's Blessing, ...)
✅ *[tested on the 1.7.3 e344 / t187 package, Ubuntu 26.04 VM]*

**Short version:** do not sell a Bless Box straight from the Boutique. Sell the item's **Ticket** and let the ticket's quest hand out the blessing. Shop-bought copies look fine but give no stats. Quest-delivered copies work, with the original, unedited `elements.data` and `tasks.data`.

### What goes wrong
You add Jones' Blessing (22198) or O'Malley's Blessing (28524) to the Event Boutique. You can buy it, equip it in the Blessing slot, and the tooltip lists the bonus ("Atk. Level +30"). The character sheet doesn't change: Attack Lv and Defense Lv stay where they were, and a damage test on a dummy confirms nothing is applied. It isn't a display problem.

### What to avoid
Everything in this list was tried on **shop-bought copies** and made no difference. Skip it.

1. **Selling the blessing itself from the shop.** This is the actual problem. *[tested]*
2. **Giving the shop entry a duration.** The real items are 7-day items, so a 7-day shop duration looks like the obvious fix. The tooltip then shows "Duration: 6 day(s) 23 hour(s)", but the stats still don't apply. *[tested]*
3. **Editing the item record in `elements.data`.** We made the record match a working blessing: item level, quality, flags, and the second effect list. No change. *[tested, with the server confirmed to have loaded the edited file]* Don't put your friends through a 100 MB client update for this.
4. **Blaming the server or the Blessing slot.** Another blessing that comes from a quest (Peerless Blessing, from the daily sign-in) works in the very same slot and gives all its stats. The slot and the effect types are fine. *[tested]*
5. **Putting a shop duration on a stackable item** (see the next section). This one is a trap for the fix, not for the problem.

### The shop refuses stackable items with a duration
If you sell a ticket with a shop duration, the game server starts, then the maps (`GS`) never come up, and `server status` shows `[DOWN] GS (maps)`.

`/opt/logs/gs_main.log` is in Chinese (GBK). Read it with:
```bash
sudo tail -n 40 /opt/logs/gs_main.log | iconv -f gbk -t utf-8 -c
```
The line that matters ends the log:
```
百宝阁中物品存在可堆叠但存在有效期的物品28297，无法进行初始化操作 索引149
初始化鸿利商城数据失败
第一步初始化失败，错误号:-32
```
Meaning: "Boutique item 28297 is stackable but has an expiry, cannot initialize, index 149", then "Event Boutique data failed to initialize", error -32. *[tested]*

The long run of lines above it (`百宝阁中物品68755(1个)超过了堆叠上限0` and similar) is "stack limit 0": items that aren't in this data version. They were there while the shop worked as well and are not what stops the start. *[inferred from the log, not proven]*

**Rule:** a stackable item (tickets, packs) must have shop duration **0**. The 7 days come from the quest reward, not the shop.

### The way that works
Sell the ticket. The ticket starts a quest, and the quest's reward row creates the blessing.

| Blessing | Ticket (sell this) | Quest | Reward | Result in game |
|---|---|---|---|---|
| Jones' Blessing | 28297 | 22076 "Jones' Blessing" | item 22198, 7 days | Attack Lv +30 |
| O'Malley's Blessing | 28523 | 22208 "O'Malley's Serendipity" *[quest inferred, see below]* | item 28524, 7 days | Attack Lv +15, Defense Lv +15 |

Jones' also appears as a reward in quest 17027 "Jones' Secret Power" (not used here).

How to add them:
1. In the Event Boutique files, add two shop records for the **tickets** (28297 and 28523), with duration **0**. Keep the client file (`gshop1.data`, 1448-byte records) and the server file (`gshopsev1.data`, 232-byte records) in step: same items, same order.
2. Put the server file in `/opt/gamed/config/`, restart with `sudo server restart`, then check `sudo server status` shows `[UP] GS (maps)` after about a minute.
3. Give your players the new `gshop1.data` (through your launcher or by hand).
4. Buy a ticket, use it, equip the blessing, and check the character sheet.

You do **not** need to touch `elements.data` or `tasks.data`. We tested this twice: once after editing the item records, and once after restoring the original files. Both blessings work on the original files, using freshly bought tickets. (Blessings that were created while the edited file was loaded are not a valid test, so buy new ones after any change.)

### How we worked it out
1. **Control:** find a blessing that does work. Peerless Blessing (quest reward) applied all five of its stats in the same slot, which ruled out the server and the slot.
2. **Compare the records:** we read the raw item records (a short script that dumps the record for an item id from a *copy* of `elements.data`) and compared Peerless against Jones' and O'Malley's. Effect entries looked the same kind; the differences were level, quality, flags and a second effect list. Changing those did nothing.
3. **Look at how Peerless is delivered:** a search of `tasks.data` for the item id found a **quest reward row** (item, count, chance, period). The row sets a 3600-second life (that's the "Time Remaining" on its tooltip). So Peerless doesn't come from the shop at all.
4. **Look for the same thing for ours:** searching `tasks.data` for 22198 and 28524 found reward rows with a 604800-second period (7 days) inside quests named after the blessings. Their tickets trigger those quests.
5. **Test the real path:** sell the tickets, use them. Both blessings worked on the first try. Then restore the original data files and repeat: still working.

### Finding the quest behind an item (for other items)
- **Reward rows in `tasks.data`** are 17 bytes: `item id (4)`, `flag (1)`, `count (4)`, `chance (float, 4)`, `period in seconds (4)`. Search the file for the item id as a 4-byte little-endian number, and look for a row whose next fields look like `1, 1, 1.0, <period>`.
- **Quest headers** are the quest id (4 bytes) followed by 30 UTF-16 characters XORed with `quest id & 0xFFFF`. Quest records are **not** 4-byte aligned, so scan every byte, not every 4. Verify a candidate by decoding the name and checking that it reads like text.
- **The enclosing quest:** the nearest header *before* the reward row is the quest it belongs to. Be careful: an aligned-only scan picked the wrong quest for us the first time ("Starter Kit" instead of "Jones' Blessing"). Check the decoded name makes sense.
- **Which item triggers a quest:** look the ticket up on a database such as PWDatabase (for example https://www.pwdatabase.com/my/items/28297 for Jones' ticket). For O'Malley's ticket (28523) we did not find the quest id listed, so quest 22208 is inferred from the name and from its identical structure to quest 22076 (reward row exactly 1912 bytes into the quest in both). It matched in game.

### Quick reference (e344)
- Boutique file records: client 1448 bytes (item id at +140, first price slot at +148: price, ?, **duration in seconds**, ...), server 232 bytes (item id at +12, first price slot at +20). 0 = permanent. *[read from our own files]*
- Bless Box item record (1164 bytes): id, then item type pair, then a 64-byte name at +12. Level at +368, required level at +392, quality at +400, effect list at +564 (32 x `[id, chance]`), second list at +820, flags at +1124. *[our own files; only the effect lists and level fields were varied in testing]*
- Effect entries (84 bytes each, near the start of the effect table): for example `Attack Level +8`, `D_L08`, `AD_L08` (= +30). *[our own files]*

> **Provenance:** every id, offset and observation above comes from our own client and server files, logs and game screenshots. No code or data was taken from other servers or tools. Item and quest ids come from our own `elements.data` / `tasks.data`; the PWDatabase link is a lookup aid only.

---
[Back to the guide index](README.md)
