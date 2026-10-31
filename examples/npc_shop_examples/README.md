# NPC shops: find and change what an NPC sells

No script needed: the [editor's](../../tools/ultimusv2/README.md) **NPC shops** tab does this with checks.

1. Open a **copy** of `elements.data` in the editor.
2. NPC shops tab: search the NPC by name (e.g. "Merchant Wang Song") or the item by name or id. The tab shows which shop the NPC uses and every other NPC that shares that shop: a change hits all of them.
3. Change or clear a slot, save as a new file.
4. Put the new file on the server and the clients (both must match), `sudo server restart`, and check the shop in game.

Good to know:
- Price comes from the item itself, not the shop.
- Each slot has four extra numbers whose meaning is unknown; the editor keeps them when you change the item.
- Before hiding or changing an odd NPC, check what it sells: the scattered "Merchant" NPCs on the 1.7.3 map sell Homestead goods.

Layout: [NPC shops](../../docs/layouts/npc_shops/README.md).

---
[Back to examples](../README.md)
