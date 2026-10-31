# Quest reward rows (tasks.data t187)

The part of a quest record the Quest rewards tab edits. Quest header: [tasks.data](../tasks/README.md).

Machine-readable version (what the editor loads): [`tasks.json`](../../../tools/ultimusv2/layouts/tasks.json). Edit layouts there, not copies here.

## Reward groups and rows
- Reward group: u8 flag (0 fixed list, 1 list with random rows [inferred]), u32 row count, then rows. Found by scanning the record for [flag<=1][1..60][valid rows].
- Reward row 17 B: item id u32, flag u8 (1 on almost every row), count u32, chance f32 (0..1), period s32 (lifetime in seconds, 0 = permanent).
- Adding/removing a row: insert/remove 17 bytes, update the group's row count, shift every later quest offset. Proof: deleting the 17 BH I ticket rows rebuilds the stock file byte for byte, and adding them back rebuilds the edited file byte for byte; the edited file was tested in game.
- Examples: 22076 "Jones' Blessing" -> 22198 x1 604800 s; 22208 "O'Malley's Serendipity" -> 28524 x1 604800 s; 33836 "Peerless Blessing" -> 48056 x1 3600 s; 18930 "Genie Pack" -> 32 random rows summing to 100%.

---
[Back to data layouts](../README.md)
