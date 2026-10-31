# Future hooks

Ideas for more `LD_PRELOAD` add-ons built the same way as [`treasure_hook`](../treasure_hook/README.md): a small library loaded beside gs that replaces one missing or broken function, without changing gs itself. Nothing here is built yet.

| Idea | What it would do | Status |
|---|---|---|
| Faction Safe "polite decline" | Answer NPC service 115 with a message instead of freezing the character ([notes](../../docs/research/protocols/faction_safe_5882.md)) | idea; Faction Safe is off the goals |
| Bulk Seeking Treasure | Not possible server-side: the client sends nothing ([notes](../../docs/research/protocols/treasure_protocol.md)) | ruled out |

Rules for any new hook: our own 1.7.3 binaries and client only as sources, a switch to turn it off (like `tools/disable_hook.sh`), tests against a fake gs, and a snapshot before the first live run.

---
[Back to the repository overview](../../README.md)
