# PW173 Editor (in-house)

An in-house editor for our Perfect World 1.7.3 (e344 / t187) server, built only from the code and methods we worked out ourselves. No outside editor code is used.

**What it does (stages 1a to 1d):**
- **Shop editor:** edits a Boutique client file and its server file *together* (`gshop.data` + `gshopsev.data` for the main Boutique, `gshop1.data` + `gshopsev1.data` for the Event Boutique).
- **Item lookup:** search `elements.data` by name or id and see the raw record, with stat entries and item names resolved.
- **Quest rewards:** open `tasks.data`, find a quest by id or name, or every quest that gives an item (`item:22198`). See its reward rows (item, count, chance, lifetime), then change a row, add a row (copy of another), or delete one. Load `elements.data` in Item lookup first so item names show.
- **NPC shops:** open a copy of `elements.data`, find a shop by NPC name (`Wang Song`), shop id, or the item it sells (`item:8617`). Each shop has 8 pages of 32 slots: change what a slot sells, clear it, or rename a page. **One shop record is often shared by several NPCs** (the list shows who); a change shows up at all of them.

## Open everything at once (recommended)
Click **Open game data folder...** at the top and pick a client's `element\data` folder (or any folder holding copies of `elements.data` and `tasks.data`). One load gives you:
- item names in every tab,
- the NPC shops and quests from those same files,
- **where-used** in Item lookup: select an item and the top of the panel lists the NPC shops that sell it (and which NPCs), the quests that give it (count, chance, lifetime), and the open Boutique records,
- **double-click** an item anywhere (Boutique record, quest reward row, NPC shop slot) to jump to it in Item lookup.

**Version check:** the editor recognises our known file versions (`layouts/known_files.json`) and labels each file live, old or experiment. Opening an OLD file (for example the friends folder's original `elements.data` or `tasks.data`) shows a warning, because edits made from it would drop later changes such as the Palette swap or the BH1 tickets. When a new version goes live, add its md5 to that file.

## Item flow (where an item comes from and where it goes)
The **Item flow** tab (or **Show item flow** in Item lookup) puts one item in the middle:
- **Comes from:** NPC shops (and which NPCs), quest rewards (with the item that starts or is needed by that quest, e.g. Jones' Blessing <- quest 22076 <- Jones' Blessing Ticket), monster drops (about how often per kill), crafting recipes (with their materials), and the open Boutique pair.
- **Goes to:** quests it opens (packs, vouchers), quests that need or take it (tickets, keys, Bounty Orders), and recipes that use it as a material (with what they make).
- **Double-click** any linked item to move the view to it; **Back** returns.

How sure each link is:
- Shops, quest rewards, recipes, pack -> quest: mapped on our own files and checked across the whole file (see [`docs/layouts/LAYOUTS.md`](../../docs/layouts/LAYOUTS.md)).
- Monster drops: the table layout is checked on all 3,948 monsters that drop something; the "per kill" percentage is *calculated* from it and has not been tested in game. Server-side extra drops (`extra_drops.sev` on the VM) are not included.
- "Needed by quest": read from the quest's needed-items area. An item whose id is an exact multiple of 256 can't be told apart from flag bytes there, so it won't show as needed.

## Run it
- **Without building:** double-click `run_editor.bat` (needs Python, which you already have).
- **As a program:** double-click `build_exe.bat` once. It makes `dist\PW173Editor.exe`, which runs without Python and can be copied anywhere.

## Safety rules (built in)
- Files you open are **never overwritten**. Saving always writes two new files, and refuses if you pick an opened file's name.
- Client and server are checked against each other when you open them and before saving: same stamp, same number of records, same items, counts, prices and durations. Saving is blocked if they don't match.
- The stamp (part of the version check) is never changed.
- Blocked: a timed item (duration > 0) with a count above 1, because stackable items with a duration stop the maps from starting (error -32). There's also a warning when a timed item's name looks stackable (ticket, pack, potion, ...).
- Unknown 1.7.3 fields are copied through untouched.
- `elements.data` is only ever read. Open a copy anyway.
- Quest rewards: chance must be above 0% and at most 100%; the only row of a group can't be deleted; a saved `tasks.data` must load back with the same 20,122 quests or the save is reported as failed. Adding or deleting a row uses the same method as the BH1 script that was tested in game (the editor rebuilds that exact file byte for byte).

## Putting a new elements.data live (NPC shops)
Same as tasks.data: ONE file for the server (`/opt/gamed/config/elements.data`) and every client (`element\data\elements.data`). Snapshot first, back up the live file, restart, check `GS (maps)` is `[UP]`.

## Putting a new tasks.data live
`tasks.data` is ONE file shared by the server and every client: the same new file goes to `/opt/gamed/config/tasks.data` on the VM (after a snapshot and a backup of the live one) and to `element\data\tasks.data` on every client (launcher). Restart the server and check `GS (maps)` is `[UP]`.

## Putting edited shop files live
1. Take a VirtualBox snapshot.
2. Copy the new server file to the VM, back up the live one, and put the new one in `/opt/gamed/config/` under its real name (`gshopsev.data` or `gshopsev1.data`).
3. `sudo server restart`, wait a minute, then `sudo server status`. `GS (maps)` must be `[UP]`. If it isn't, read the log: `sudo tail -n 40 /opt/logs/gs_main.log | iconv -f gbk -t utf-8 -c`
4. Back up your client file and put the new one in `element\data` under its real name. Friends get it through the launcher.

## How it is built
- `layouts/*.json`: the byte layouts. Each field has its offset, type, whether it's editable, and a note saying how it was confirmed ([verified] or [inferred]). To support something new, map it by hand, add it to a table, then add a screen.
- `pwedit/layout.py` reads the tables. `pwedit/shop.py` handles Boutique pairs and the safety checks. `pwedit/elements.py` handles item lookup. `pwedit/tasks.py` handles quest rewards (layout in `layouts/tasks.json`). `pwedit/npcshop.py` handles NPC shops (layout in `layouts/elements_npcshops.json`). `pwedit/known.py` labels file versions from `layouts/known_files.json`. `pwedit/flow.py` builds the Item flow from `layouts/elements_flow.json`. `pwedit/gui.py` is the window.
- Tests run against real files: `py tests\test_real_files.py <gshop1.data> <gshopsev1.data> [<gshop.data>] [<elements.data copy>]` `py tests\test_tasks.py <tasks.data>` (expects the BH1-patched file, md5 17a45032...) `py tests\test_npcshops.py <elements.data copy>`; the window tests (`tests\test_gui_*.py`) use a stand-in for the window toolkit.

## Known limits
- Item lookup finds items by their name field. A few names with unusual characters (Chinese, rare symbols) won't show up in name search. Search by id instead.
- The **Status label** meaning (New / Hot / Sale badge) is inferred.
- The tool can't know an item's real stack limit yet. A count above the stack limit stops the maps from starting, so keep counts to what the item really stacks to.
- Only price slot 0 is edited. All stock 1.7.3 shop records use only slot 0.
- NPC shops: each slot has four extra numbers whose meaning is unknown (values like 600, 2400, 3600 on some slots); they are kept when you change the item and zeroed when you clear a slot (stock empty slots are all zero). Price comes from the item itself, not the shop.
- Quest rewards: only reward rows are edited (not exp, objectives or text). Rewards of nested sub-quests show up as extra groups of their parent quest. The group's first byte (0 fixed list / 1 list with random rows) and the row flag are shown but their meaning is inferred.

## Roadmap
1a Shop editor ✔, 1b Item lookup ✔, 1c Quest reward editor ✔, 1d NPC shop retool ✔.
