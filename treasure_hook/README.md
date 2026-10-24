# treasure_hook: Treasures (Lucky Key) for the PWI 1.7.3 server

A small add-on library for the community **PWI 1.7.3 (e344 / t187)** server package. It supplies the missing server half of the **Treasures / Lucky Key** window (the 10-chest "seek and pick" board, reached from the Palette of Fortune).

The stock 1.7.3 `gs` receives the Treasures clicks but only implements "withdraw from the Treasure Warehouse". Seek, open-chest and window-refresh are logged and ignored, so the chests never appear and no keys are taken. This library answers them using `gs`'s own item and packet functions.

**`gs` itself is not changed.** The library is loaded next to `gs` with `LD_PRELOAD` from the start script. Take that out again and the server is exactly as before.

## Status
| Feature | State |
|---|---|
| Seek Treasures (2 Lucky Keys, new 10-chest board, +1 Aurum) | works (tested in game) |
| Open chest (first free, then 5, 12, 30, ... keys; client refuses opens you can't afford) | works |
| Prize into the Treasure Warehouse, warehouse list refreshes, withdraw to bag | works |
| Board survives relog and server restart (saved per character) | works |
| Relog does not cost keys | works (see "relog trap" below) |
| Bulk Seeking Treasure | **not possible server-side**: the 1.7.3 client never sends a request for it |
| Seek Treasures: Aurum | **not working**: handled by the client alone, same as Bulk |

Tested on: `gs` md5 `70207fa25a0a0d83a92dc7a62da1fb4c`, elements.data e344, English client PWI_en_1.7.3 (e344_t187), Ubuntu Server 26.04 in VirtualBox. The shipped config has the function names, structure offsets and loot table for exactly that build. **Another gs build needs its own values** (see `tools/recon_gs.sh`).

## Install
Do this on a **VirtualBox snapshot** or a copy of your server VM first.

```bash
# 1. copy this folder to the server (from your PC), e.g. into ~/treasure_hook
# 2. build (gs is 32-bit, so the library must be too)
sudo apt install -y gcc-multilib make
cd ~/treasure_hook/src && make && sudo make install       # -> /opt/treasure_hook/
# 3. put your GM character's role id in allow_roles (see below)
sudo nano /opt/treasure_hook/treasure_hook.conf
# 4. add the preload to the gs line of /opt/server (keeps a backup), then restart
sudo bash ~/treasure_hook/tools/enable_hook.sh
sudo server restart
grep -E "hook installed|command recorder" /opt/treasure_hook/hook.log
```

The `grep` should show `hook installed: 0 vtable slot(s), 1 direct call(s)/jump(s)` and `command recorder ...: 1 vtable slot(s) patched`.

## Bring it up one mode at a time
The config is re-read a second or two after you save it. No restart is needed for these changes.

1. `mode = log`: open Treasures and press Seek. `hook.log` shows a line like `Lottery_Notice1 role=1234 type=3 param=0`. That number is your **role id**.
2. `mode = probe` with `allow_roles = <your role id>`: the hook sends you a test board and moves no items. You should see the 10 chests.
3. `mode = live`, still just your role: real seeks and opens with keys and prizes. Check that keys go down by 2 per seek and by the chest cost per open, and that prizes land in the Treasure Warehouse.
4. `allow_roles = all` when you are happy.

Back to safe at any time: `mode = log`.

## Things we learned the hard way (useful if you write your own)
- **Board packet:** S2C opcode **434**, same layout as the public 1.7.6 source (`get_treasure_info`): `u16 434, u8 manager (0 info / 1 new board / 2 chest opened), u32 Aurum, u32 free opens, u32 closed count, u32 opened count`, then closed chests `{u32 id, u32 count, u8 prize}` and opened chests `{u32 id, u32 chest, u32 count, u8 prize}`. `gs`'s own `send_lot_info3/4` are the main Palette draw (523/524), not this. Sent raw with `send_ls_msg(gplayer const*, void const*, unsigned)`.
- **Warehouse:** `AddLotInventory(id, count)`, then `GetLotInventory(unsigned&)` + `gplayer_dispatcher::send_lot_inv(n, ptr)` (opcode 433) so the client's list updates.
- **Return true:** if `Lottery_Notice1` returns false, `CommandHandler` sends error 3, which shows as "Critical error: invalid action". Hence `hook.ret = 1`.
- **Relog trap:** the first time the window opens after a login, the client sends type 3, the same as the Seek button, to get its board back. If you treat that as a seek, every relog costs 2 keys and deals a new board. The hook treats the first seek of each login (told apart by the link session id at `gplayer + 0xb0 / 0xb4`) as "resend the saved board".
- **Stale pictures:** a new board does not clear the client's old opened-chest pictures. Sending an empty board first fixes it (`seek.clear = empty`).
- The Treasures command is client command **197**. `gs` accepts only action types 0-3 for it and refuses anything else before `Lottery_Notice1` runs. The recorder (`cmd.log = 197`, or `any` for every command) writes refused or unknown commands to `hook.log`. That is how we found out Bulk Seeking sends nothing.

## Turn it off
- Instantly: `mode = log` in the config.
- Completely: `sudo bash ~/treasure_hook/tools/disable_hook.sh && sudo server restart`. `gs` was never modified, so this is a full revert.

## Files
```
src/treasure_hook.c      the library        src/Makefile   32-bit build + install
conf/treasure_hook.conf  settings for the tested 1.7.3 build (loot table included)
tools/enable_hook.sh     add LD_PRELOAD to /opt/server (with backup)
tools/disable_hook.sh    remove it again
tools/recon_gs.sh        read-only scan of another gs build (symbols, offsets)
tools/extract_treasure_cfg.py  print key/cost/loot lines from your elements.data
docs/protocol_notes.md   early design notes (the findings above supersede them)
test/                    mock gs + 252 automated checks (developer use)
```

## Safety
- Unofficial, home-made code. Run it only on your own server VM, from a snapshot.
- It only acts inside a program named `gs`, only for roles in `allow_roles`, and refuses to act if a function or offset it needs is missing.
- A board is saved before any item moves. If giving the prize fails, the board is put back and no keys are taken.
- No network access of its own; it only writes `/opt/treasure_hook/hook.log` and the per-character board files in `/opt/treasure_hook/state/`.
