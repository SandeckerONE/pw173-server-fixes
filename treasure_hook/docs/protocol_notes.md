# How the Treasures chest board is brought up (protocol notes)
> **Update after testing (2026-10-23):** these were the design notes written before the hook ran on a real server. The confirmed answers are in `../README.md` ("Things we learned the hard way"): the board is opcode 434 with the 1.7.6 layout, sent raw; `send_lot_info3/4` are the main Palette draw, not the board; prizes go to the Treasure Warehouse.


This is the "why" behind the hook. It is the current best understanding, with
each point labelled. Confirm the [infer] / [agent] ones against your own recon
before trusting them in live mode.

## The question the user asked
"Bring up the secondary chest item screen where you pick the treasure chests."
That screen is the row of 10 chests in the Treasures (Lucky Key) window. On the
1.7.3 server it never appears because the server never answers the
command that should produce it.

## The command path (verified by disassembly, 2026-10-17)
- The client sends the Treasures command; the server receives it in
  `gplayer_controller::CommandHandler`, which calls
  `gplayer_imp::Lottery_Notice1(type, param)`. [verified]
- `type` is the action, `param` is its argument:
  - `3` = Seek Treasures (lay out a new board) [verified from the `3 0` log line]
  - `1` = open chest number `param` [verified from the `1 n` log line]
  - `0` = window opened / refresh [verified from the `0 0` log line]
  - `2` = withdraw item `param` from the Treasure Warehouse [verified]
- gs implements ONLY type 2. Types 0/1/3 run a `printf("Lottery_Notice1 ...")`
  and return. So a Seek does nothing: no board, no keys taken, no message.
  [verified]
- The main Palette of Fortune draw is a different function,
  `gplayer_imp::Lottery_Notice2`, and it works. [verified]

## What makes the board show (the reply packet)
The client shows the 10 chests when the server sends it the "treasure info"
packet. We do not have the 1.7.3 client's own name for it, but the public
DeadRaky rewrite in the 1.7.4 / 1.7.6 sources defines it, and the 1.7.3 gs has
three unused senders with matching names: `send_lot_info3`, `send_lot_info4`,
`send_lot_inv`. [verified names; [infer] that one of info3/info4 is this packet]

Packet `get_treasure_info`, opcode **434** in the 1.7.6 source
(`s2c_source.h` / `s2c_header.h`, read 2026-10-19): [agent/verified from source]

```
u16  cmd            # 434 (GET_TREASURE_INFO)
u8   manager        # 0 = just info, 1 = seek just happened, 2 = a chest was opened
u32  score          # Aurum
u32  free_count     # free opens left
u32  lot_count      # chests still closed  (= number of LOT entries)
u32  box_count      # chests opened so far (= number of BOX entries)
LOT  lot[lot_count]      # { u32 id; u32 count; u8 lot; }         prizes not yet won
BOX  box[box_count]      # { u32 id; u32 box; u32 count; u8 lot; } opened chests, in order
```

In that source the `BOX box[]` line is commented out, so some builds send only
the LOT array. The hook can send either; `box.layout` controls the BOX entry and
you can drop it by removing `boxes` from `raw.info` (or leaving the box sender
out). [verified from source comment]

### The sequence that opens the board
1. Client sends Seek (type 3). Server draws 10 prizes, hides them in 10 chests,
   and replies with `manager = 1, lot_count = 10, box_count = 0`. The client
   switches to the chest-picking screen. **This reply is the missing piece.**
2. Client sends open-chest `n` (type 1). Server gives the prize and replies with
   `manager = 2`, one more BOX entry, one fewer LOT entry.
3. Window open / refresh (type 0) just re-sends the current board.

`InitLot` in the DeadRaky source confirms the seek sets `manager = 1`,
`lot_count = 10`, `box_count = 0`; `OpenLot` sets `manager = 2` and moves a chest
from closed to open. [agent]

## Two ways to deliver that reply, and why the hook is configurable
We do not yet know, for the 1.7.3 gs:
- the exact S2C opcode the 1.7.3 **client** expects (434 is from the 1.7.6
  source; client opcodes can shift between versions),
- the argument order of `send_lot_info3`,
- the struct offsets of `_parent` / `_runner` / the role id.

So the hook does not hard-code them. It can either:
- **native**: call gs's own `send_lot_info3` (set `call.info` to its symbol and
  argument order) — preferred, because gs then frames and encrypts the packet
  exactly as the client expects; or
- **raw**: build the 434 packet itself (the `raw.info` layout) and send it with a
  generic client-data sender.

`probe` mode is how you find out which values light up the board without moving
any items: it sends a chosen `manager` / counts / chest list for your GM
character only. Flip the numbers, watch the client.

## Recommended path to a working board
1. **log** mode: open the Treasures window and press each button. The log shows
   the real `type`/`param` the client sends — confirm 3/1/0 and find what the
   Aurum seek sends.
2. **probe** mode: get gs's `send_lot_info3` argument order from recon, set
   `call.info`, send `manager=1, lot_count=10, box_count=0`. If the 10 chests
   appear, the packet is right. If not, try `send_lot_info4`, or `raw` with the
   434 layout.
3. **live** mode for the GM role only: real seek/open with keys and prizes.
4. Widen `allow_roles` once it behaves.

## Open points to close with recon
- Which of `send_lot_info3` / `info4` is opcode 434, and its arguments. [open]
- The real S2C opcode the 1.7.3 client wants (compare client + server). [open]
- Whether the client needs the BOX array or only LOT. [open]
- Whether opened prizes go to the bag or the Treasure Warehouse on this build
  (the official game uses the warehouse; `deliver = lotadd` matches that). [open]
