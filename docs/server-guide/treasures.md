# Palette of Fortune and Treasures

The two gacha windows: what works out of the box and what needs the add-on.

**On this page**
- [Palette of Fortune](#palette-of-fortune)
- [Treasures / Lucky Key system](#treasures--lucky-key-system)

## Palette of Fortune
✅ the **main draw** (Color Burst, Free-in-a-row, Ticket of Magnificence) works *[tested]*.
- If it does nothing, the character's **Safety Lock** is probably still active (default about one minute after login); gs refuses with error 108. *[code]*
- The highlighted empty box at the top of "Treasure Display" is a legend for the season's special items, not a missing prize. *[inferred from the window]*
- Odds from the data: Legendary 0.00618% per draw, about 1 in 16,200 tickets. Worth knowing when you price tickets.

## Treasures / Lucky Key system
✅ seek / open / warehouse work with the add-on in `addons/treasure_hook/` · ❌ Bulk Seeking and Aurum seek *[code + tested in game]*

**Symptom:** the Treasures window opens and the loot list shows, but "Seek Treasures: 2 Keys" does nothing; no keys are taken and no chests appear.

**Cause:** the client sends `Lottery_Notice1(type, param)` (3 = seek, 1 = open chest n, 0 = window, 2 = withdraw from the Treasure Warehouse). **The 1.7.3 gs only implements type 2.** The loot table (elements.data list 232), costs (list 233) and bonus event (list 234) are loaded but never used. No other program contains the logic. It's not a config or date problem.

**Fix:** the add-on library in [`addons/treasure_hook/`](../../addons/treasure_hook/) (install steps in its README), loaded beside gs with `LD_PRELOAD` (gs itself is not changed) that answers seek and open:
- Board packet: the add-on builds the Treasures board itself and sends it raw with gs's `send_ls_msg(gplayer const*, void const*, unsigned)`. *[tested: the 1.7.3 client draws it]* The byte layout is deliberately not written out here: it was first taken from an outside server source tree whose licence turned out to be restrictive, and it is being re-documented from our own 1.7.3 client.
- Keys: `CheckItemExist` + `RemoveItems(id, count, 11, true)` (Lucky Key 56274, 2 per seek; chest costs 0, 5, 12, 30...). Prizes: `AddLotInventory(id, count)` into the Treasure Warehouse, then `GetLotInventory` + `send_lot_inv` to refresh the warehouse list (opcode 433). Withdraw is gs's own. *[tested]*
- **Trap:** the first time the window opens after a login, the client sends type 3, the same as the Seek button, to get its board back. Treat the first seek of each login as "resend the saved board" (tell logins apart by the player's link session id at `gplayer + 0xb0 / 0xb4`), or every relog costs 2 keys and a new board. *[tested]*
- The client itself refuses opens and Aurum seeks you can't afford, and blocks Seek: Aurum below 20 Aurum. Aurum is +1 per board sought. *[tested]*
- Boards are saved per character in a small file, so they survive relogs and restarts. *[tested]*
- **gs must be told "handled":** gs's CommandHandler sends error 3 ("Critical error: invalid action") whenever `Lottery_Notice1` returns false, so a replacement must return true. *[code + tested]*
- The Treasures command is client command **197**. gs accepts only action types 0-3 for it and refuses anything else before `Lottery_Notice1` is called. *[code]*
- **Not working:** *Bulk Seeking Treasure* sends nothing to the server on this client (every client command was recorded during bulk runs; nothing carried the count or ticked items). The client fakes the run locally, so no server-side fix is possible. *Seek Treasures: Aurum* (higher odds for rare items) looks the same and is left out. *[tested]*

---
[Back to the guide index](README.md)
