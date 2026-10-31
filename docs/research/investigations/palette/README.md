# Palette of Fortune (notes)

**Result:** the main draw (Color Burst, Free-in-a-row, Ticket of Magnificence) works on stock 1.7.3. *[tested]* The how-to is on the [guide page](../../../server-guide/treasures.md#palette-of-fortune).

- "Does nothing": the character's Safety Lock is still active (about a minute after login); gs refuses with error 108. *[code]*
- The highlighted empty box at the top of Treasure Display is a legend for the season's special items. *[inferred from the window]*
- Odds from the data: Legendary 0.00618% per draw, about 1 in 16,200 tickets.
- The prize table is `elements.data` record 6064 (`彩票配置表`). Prize entry: 16 bytes = item id, chance (f32), 0, seasonal flag (1 = special). Seasonal specials can be swapped for normal prizes: [`examples/palette_swap`](../../../../examples/palette_swap/README.md). *[tested in game]*

---
[Back to research notes](../../README.md)
