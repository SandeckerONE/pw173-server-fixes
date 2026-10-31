# Server guide: known problems and fixes

A living fix list for people running the community **PWI 1.7.3 (elements v344, tasks v187)** server package on their own Linux VM, with the matching English **PWI_en_1.7.3 (e344_t187)** client. Every fix here was found on a real home server and tested in game unless it says otherwise.

**Status tags:** ✅ fixed and tested · 🟡 workaround · 🔧 in progress · ❌ not fixable yet (code missing from the server package)

**Evidence tags:** *[tested]* confirmed in game or by command output · *[code]* read from the server programs (they ship with debug symbols) · *[inferred]* best reading, not proven

> Scope and etiquette: this guide contains **no game or server files**, only instructions and small scripts written for it. Run everything inside a VM, take a snapshot before every change, and test risky changes on a copy of the VM first.

| Page | What's in it |
|---|---|
| [Setup](setup.md) | Modern Linux, client won't connect, accounts, pwAdmin, rates, log rotation, security checklist, small notes |
| [authd (logins)](authd.md) | All logins suddenly refused + a watchdog that fixes it |
| [gacd (anti-cheat)](gacd.md) | gacd keeps dying |
| [Backups](backups.md) | Nightly backup, the every-other-night lock bug, weekly offline copy, restore drill |
| [Palette and Treasures](treasures.md) | Palette of Fortune; Treasures / Lucky Keys (with the add-on) |
| [Bless Boxes](bless-boxes.md) | Adding Jones' / O'Malley's Blessing so the stats actually apply |
| [Troubleshooting](troubleshooting.md) | Boutique gold `ret=-8`, lag, instances, Ctrl+click teleport, export/import, debug console, item drops, forges, stray NPCs, Chinese text |

New server? Read [Setup](setup.md) top to bottom, then [authd](authd.md) and [Backups](backups.md).

## Old page names (before the v2 layout)
Links to the old numbered pages now land here. Where each one went:

| Old page | Now |
|---|---|
| `01-setup-modern-linux.md` | [`setup.md#setting-up-the-server-package-on-a-modern-linux`](setup.md#setting-up-the-server-package-on-a-modern-linux) |
| `02-client-wont-connect.md` | [`setup.md#client-wont-connect--stuck-on-connecting-to-server`](setup.md#client-wont-connect--stuck-on-connecting-to-server) |
| `03-creating-accounts.md` | [`setup.md#creating-accounts`](setup.md#creating-accounts) |
| `04-boutique-gold-ret-8.md` | [`troubleshooting.md#boutique-gold-doesnt-arrive-ret-8`](troubleshooting.md#boutique-gold-doesnt-arrive-ret-8) |
| `05-gacd-anti-cheat.md` | [`gacd.md`](gacd.md) |
| `06-lag-and-login-bounces.md` | [`troubleshooting.md#severe-lag-login-bounces-followers-not-updating`](troubleshooting.md#severe-lag-login-bounces-followers-not-updating) |
| `07-instances-wont-open.md` | [`troubleshooting.md#instances-that-wont-open`](troubleshooting.md#instances-that-wont-open) |
| `08-ctrl-click-teleport.md` | [`troubleshooting.md#every-player-can-ctrlclick-teleport`](troubleshooting.md#every-player-can-ctrlclick-teleport) |
| `09-character-export-import.md` | [`troubleshooting.md#character-exportimport`](troubleshooting.md#character-exportimport) |
| `10-debug-console.md` | [`troubleshooting.md#debug-console-commands`](troubleshooting.md#debug-console-commands) |
| `11-palette-of-fortune.md` | [`treasures.md#palette-of-fortune`](treasures.md#palette-of-fortune) |
| `12-treasures-lucky-keys.md` | [`treasures.md#treasures--lucky-key-system`](treasures.md#treasures--lucky-key-system) |
| `13-small-notes.md` | [`setup.md#small-notes`](setup.md#small-notes) |
| `14-logins-refused.md` | [`authd.md`](authd.md) |
| `15-items-cant-be-dropped.md` | [`troubleshooting.md#items-cant-be-dropped-on-the-ground`](troubleshooting.md#items-cant-be-dropped-on-the-ground) |
| `16-nightly-backup.md` | [`backups.md`](backups.md) |
| `17-bless-boxes.md` | [`bless-boxes.md`](bless-boxes.md) |

The Faction Safe notes (old section 13 of the first guide) are in [research/investigations/faction_safe](../research/investigations/faction_safe/README.md).

---
[Back to the repository overview](../../README.md)
