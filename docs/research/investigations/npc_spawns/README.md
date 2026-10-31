# Mapping npcgen.data and hiding stray spawns (investigation)

**Result:** the spawn-area layout of `world/npcgen.data` (version 11) is mapped, and setting an area's switch (+59) from 0 to 18 hides it in game without touching anything else. *[tested in game: hidden "ERR" NPCs gone, every other NPC in place]* Layout: [npcgen](../../../layouts/npcgen/README.md). Tool: [`npcgen_hide_spawns.py`](../../../../tools/utility_scripts/README.md).

Sources: only our own files: the server's `npcgen.data` (copied off the VM, read-only) and our `elements.data`. No outside editors, configs or source code.

## Steps
1. **Start from a known value.** In game, stray "Merchant" NPCs stood around the map. Looking them up in `elements.data` (NPC list 58) and their shops gave NPC id **49452** (they sell Homestead goods).
2. **Find which files mention it.** Counting the id's 4 bytes in every npcgen file pointed at `world` (38 hits). A byte-pattern count can give false hits: another id showed 2 hits in nearly every file, which was noise.
3. **Read the header.** 11, then 21521, 4979, 2610, 4110: version + 4 section counts *[counts after the first inferred]*.
4. **Look at the bytes around a hit** as hex, u32 and float. Positions stand out as three floats in world range (e.g. -2833, 222, 4658). The NPC id sits after a fixed run of header fields.
5. **Find the record size from repeats.** Hits were always a multiple of 135 bytes apart: a 71-byte area header + one 64-byte entry, with the entry count at +4.
6. **Test the guess on the whole file.** Walking all 21,521 areas broke once (an area with 0 entries); allowing 0, the walk ends at **3,202,699** with every count sane. *[verified]*
7. **Profile each field across all records.** Distinct values per header offset: +55 almost always 12; small flag fields at +44, +52..54; about 1,000 different values at **+59**, an id-like field.
8. **Explain a field from behaviour in game.** +59 is 0 on the visible Merchants and 18 on 60 Chinese event NPCs nobody has seen. Reading: switch / controller id, 0 = always on.
9. **Cross-reference names.** Joining entry ids with `elements.data` names: type-1 areas hold NPCs, type-0 monsters *[inferred]*; nearby named NPCs locate each spawn. This also found an untranslated NPC block (ids 70957-71080) whose models are missing from the English client: the floating "ERR" labels.
10. **Smallest possible change, with guards.** Change only +59 of the chosen areas; same size; write a new file; refuse unless version, area count, walk end and the chosen areas all look as expected; compare the output byte by byte.
11. **Confirm in game.** Snapshot, back up, swap the file in, restart: hidden spots empty, other NPCs unchanged, `gs_main.log` clean. *[tested]*

In the end the Merchants were **kept** (they're a Homestead feature), and only the "ERR" block was hidden.

## Still open
The sections after 3,202,699 (resources, dynamic objects, controllers), entry fields after +4, area fields +44 / +48 / +52..54 / +63 / +67, and checking the coordinate formula (x/10 + 400, z/10 + 550) against the map.

---
[Back to research notes](../../README.md)
