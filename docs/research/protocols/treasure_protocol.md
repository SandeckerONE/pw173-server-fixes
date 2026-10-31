# Treasures / Lucky Key protocol (1.7.3)

What the 1.7.3 client and gs exchange for the Treasures window. Only facts from our own client and gs. *[code + tested]*

## Client -> server
- Client command **197**, handled by `Lottery_Notice1(type, param)`. gs accepts action types 0-3 only and refuses anything else before the call.
- Types: **0** = window opened, **1** = open chest `param`, **2** = withdraw from the Treasure Warehouse, **3** = seek a new board.
- The first window open after each login sends **3**, the same as the Seek button, to get the current board back.
- *Bulk Seeking Treasure* and *Seek: Aurum* send nothing to the server on this client (recorded every client command during bulk runs).

## Server -> client
- **Board**: sent raw with gs's `send_ls_msg(gplayer const*, void const*, unsigned)`. The 1.7.3 client draws a board built this way *[tested]*. **The byte layout is not written here yet:** it was first taken from an outside source tree with a restrictive licence, and has to be re-derived from our own 1.7.3 client before it is published.
- **Warehouse list**: `GetLotInventory` + `send_lot_inv` (opcode 433).
- If `Lottery_Notice1` returns false, `CommandHandler` sends error 3 ("Critical error: invalid action").

## gs functions used by the add-on
`CheckItemExist`, `RemoveItems(id, count, 11, true)`, `AddLotInventory(id, count)`, `GetLotInventory`, `send_lot_inv`, `send_ls_msg`. Player link session id at `gplayer + 0xb0 / 0xb4` (tells logins apart).

Data: loot table `elements.data` list 232, costs list 233, bonus event list 234 (loaded by gs, never used).

How-to: [Treasures guide](../../server-guide/treasures.md#treasures--lucky-key-system) · add-on: [`addons/treasure_hook`](../../../addons/treasure_hook/README.md).

---
[Back to research notes](../README.md)
