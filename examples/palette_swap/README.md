# Palette of Fortune: replace seasonal prizes

The main Palette table (`elements.data` record 6064) carries seasonal "special" prizes from the original event calendar. `palette_swap.py` replaces five of them with items of our choice and clears their seasonal flag so they count as normal prizes.

```
python palette_swap.py elements.data elements_palette.data
```
- Edit `SWAPS` at the top for your own choice: each line is (offset in the record, old item, new item, label). The script refuses if an entry doesn't hold the old item.
- Patch the server's and the client's `elements.data` the same way, then restart.

Prize entry layout (16 bytes): item id, chance (float), 0, seasonal flag (1 = special). More about the Palette: [guide](../../docs/server-guide/treasures.md#palette-of-fortune) and [research notes](../../docs/research/investigations/palette/README.md).

---
[Back to examples](../README.md)
