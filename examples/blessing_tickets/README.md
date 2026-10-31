# Bless Boxes through their tickets

Jones' Blessing and O'Malley's Blessing sold straight from the Boutique show their bonus on the tooltip but give no stats. Sold as their **tickets**, the ticket's quest creates the blessing and the stats apply. *[tested in game]*

| Sell this ticket | Its quest gives |
|---|---|
| 28297 Jones' Blessing Ticket | 22198 Jones' Blessing, 7 days (Attack Lv +30) |
| 28523 O'Malley's Blessing Ticket | 28524 O'Malley's Blessing, 7 days (Attack Lv +15, Defense Lv +15) |

Steps, with the [utility scripts](../../tools/utility_scripts/README.md) (or the editor's Boutique tab):
```
python shop_swap_item.py gshop1.data    gshop1_new.data    <old id> 28297
python shop_swap_item.py gshopsev1.data gshopsev1_new.data <old id> 28297
python shop_set_duration.py gshop1_new.data    gshop1_new2.data    0 28297
python shop_set_duration.py gshopsev1_new.data gshopsev1_new2.data 0 28297
```
Tickets stack, so their shop duration **must be 0**, or the maps don't start (error -32). Full write-up: [Bless Boxes guide page](../../docs/server-guide/bless-boxes.md). The scripts that did **not** fix it are kept in [`archive/old_notes/blessing-experiments/`](../../archive/old_notes/blessing-experiments/).

---
[Back to examples](../README.md)
