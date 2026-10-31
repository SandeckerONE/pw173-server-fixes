# NPC services (crafting, shops)

How an NPC's services are found in `elements.data` and what this gs does with them. *[tested unless marked]*

- NPC record (list 58, 1,080 B): +740 sell shop id, +744 / +748 other services, **+796 crafting service id**.
- Crafting service (list 55, 1,228 B): +68 craft skill, **+72 production type**, then 8 pages of 32 recipe ids. Layout: [elements](../../layouts/elements/README.md#crafting-services-list-55-tested).
- **Production type 1 is not served by this gs**: every craft answers "Invalid service request", with nothing useful in `gs_main.log`. Type 0 works. 16 services have type 1 in stock 1.7.3 data (Mystical Tomes, Aerogear Forge, Badge of the Cube, Euro Rookie Card, Warsong Exchange, Event Prize, Celestial Exchange (Special), Divine Weapons, three Gear Reforge, Rewards Exchange, Flyer Forge Med. / Adv., Helm Combine, Celestial Reforge).
- The **client** chooses the request type from **its own** `elements.data`: changing only the server's file changes nothing.
- Types 3, 4, 5, 6 (44 services) are untested.
- Shop service: see [NPC shops](../../layouts/npc_shops/README.md). Price comes from the item, not the shop.

Fix: [`forge_type_fix.py`](../../../tools/utility_scripts/README.md) · guide: [Troubleshooting](../../server-guide/troubleshooting.md#forges-answer-invalid-service-request).

---
[Back to research notes](../README.md)
