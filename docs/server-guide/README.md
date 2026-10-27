# Server guide: known problems and fixes

A living fix list for people running the community **PWI 1.7.3 (elements v344, tasks v187)** server package on their own Linux VM, with the matching English **PWI_en_1.7.3 (e344_t187)** client. Every fix here was found on a real home server and tested in game unless it says otherwise.

One problem per page. Start with 1 and 2 if you are setting up a new server; otherwise jump to the symptom you have.

**Status tags:** ✅ fixed and tested · 🟡 workaround · 🔧 in progress · ❌ not fixable yet (code missing from the server package)

**Evidence tags:** *[tested]* confirmed in game or by command output · *[code]* read from the server programs (they ship with debug symbols) · *[inferred]* best reading, not proven

> Scope and etiquette: this guide contains **no game or server files**, only instructions and small scripts written for it. Get the server package and client from wherever you got them; this only helps you make them work. Run everything inside a VM, take a snapshot before every change, and test risky changes on a copy of the VM first.

| # | Problem | Status |
|---|---|---|
| 1 | [Setting up the server package on a modern Linux](01-setup-modern-linux.md) | ✅ |
| 2 | [Client won't connect / stuck on "Connecting to server"](02-client-wont-connect.md) | ✅ |
| 3 | [Creating accounts](03-creating-accounts.md) | ✅ |
| 4 | [Boutique gold doesn't arrive (`ret=-8`)](04-boutique-gold-ret-8.md) | ✅ |
| 5 | [GACD (anti-cheat) keeps dying](05-gacd-anti-cheat.md) | ✅ |
| 6 | [Severe lag, login bounces, followers not updating](06-lag-and-login-bounces.md) | ✅ |
| 7 | [Instances that won't open](07-instances-wont-open.md) | ✅ |
| 8 | [Every player can Ctrl+click teleport](08-ctrl-click-teleport.md) | ✅ |
| 9 | [Character export/import](09-character-export-import.md) | ⚠️ read first |
| 10 | [Debug console commands](10-debug-console.md) | 🟡 |
| 11 | [Palette of Fortune](11-palette-of-fortune.md) | ✅ main draw works |
| 12 | [Treasures / Lucky Key system](12-treasures-lucky-keys.md) | ✅ with the add-on · ❌ Bulk / Aurum seek |
| 13 | [Small notes](13-small-notes.md) | tips |
| 14 | [All logins suddenly refused](14-logins-refused.md) | ✅ |
| 15 | [Items can't be dropped on the ground](15-items-cant-be-dropped.md) | ✅ |
| 16 | [Nightly backup](16-nightly-backup.md) | ✅ |
| 17 | [Adding Bless Box items (Jones' Blessing, O'Malley's Blessing, ...)](17-bless-boxes.md) | ✅ |

Not in this list any more: the Faction Safe notes (old section 13) moved to [`archive/`](../../archive/faction-safe-notes.md) when that goal was dropped.

---
[Back to the repository overview](../../README.md)
