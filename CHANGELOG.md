# Changelog

## v2: 2026-10-31, topic layout
The guide moved from 17 numbered pages to topic pages, research got its own sections, and the fixes from 2026-10-27 to 10-31 were added.

### New fixes and tools
- **pwAdmin connects again** (`/etc/iweb.conf` points at 127.0.0.1 / 29400): [Setup](docs/server-guide/setup.md#pwadmin-status-offline--1-values-saving-rates-failed)
- **Rates through pwAdmin**, re-applied after every restart (`scripts/pw_rates_apply.sh`); why `exp_bonus` does nothing: [Setup](docs/server-guide/setup.md#rates-exp-spirit-drops-and-coins)
- **Log rotation** (`scripts/logrotate/pw-logs`): [Setup](docs/server-guide/setup.md#log-rotation-logs-filling-the-disk)
- **pwAdmin blocked on the VPN** (`scripts/nftables/`, `scripts/systemd/pwadmin-lock.service`): [Security checklist](docs/server-guide/setup.md#security-checklist)
- **Backup lock bug** (backup skipped every other night) fixed in `scripts/pw_backup.sh`: [Backups](docs/server-guide/backups.md#the-backup-skips-every-other-night-another-backup-is-running)
- **Weekly offline copy on a PC** (`scripts/pw_offsite_stage.sh`, `scripts/pull_pw_backup.ps1`) and a **restore drill**: [Backups](docs/server-guide/backups.md)
- **Forges "Invalid service request"** (`tools/utility_scripts/forge_type_fix.py`): [Troubleshooting](docs/server-guide/troubleshooting.md#forges-answer-invalid-service-request)
- **Hide stray / ERR NPC spawns** (`tools/utility_scripts/npcgen_hide_spawns.py`) and the npcgen layout: [Troubleshooting](docs/server-guide/troubleshooting.md#stray-npcs-floating-err-chinese-names-duplicate-merchants)
- Editor: item index fix (stones, pets and other `[id][type][name]` records now resolve to the right id); `known_files.json` is now an empty template, with your own list in `known_files.local.json`; tests no longer need our own file versions.
- Examples: `bh1_event_gold/`, `palette_swap/`, `blessing_tickets/`, `npc_shop_examples/`. Their scripts check the file's structure instead of a fixed md5.
- Research: per-binary notes (`binaries/`), protocol notes (`protocols/`), the npcgen and Palette investigations, and the mapping method.

### Where the old pages went
| Old page | Now |
|---|---|
| `01-setup-modern-linux.md` | [`setup.md#setting-up-the-server-package-on-a-modern-linux`](docs/server-guide/setup.md#setting-up-the-server-package-on-a-modern-linux) |
| `02-client-wont-connect.md` | [`setup.md#client-wont-connect--stuck-on-connecting-to-server`](docs/server-guide/setup.md#client-wont-connect--stuck-on-connecting-to-server) |
| `03-creating-accounts.md` | [`setup.md#creating-accounts`](docs/server-guide/setup.md#creating-accounts) |
| `04-boutique-gold-ret-8.md` | [`troubleshooting.md#boutique-gold-doesnt-arrive-ret-8`](docs/server-guide/troubleshooting.md#boutique-gold-doesnt-arrive-ret-8) |
| `05-gacd-anti-cheat.md` | [`gacd.md`](docs/server-guide/gacd.md) |
| `06-lag-and-login-bounces.md` | [`troubleshooting.md#severe-lag-login-bounces-followers-not-updating`](docs/server-guide/troubleshooting.md#severe-lag-login-bounces-followers-not-updating) |
| `07-instances-wont-open.md` | [`troubleshooting.md#instances-that-wont-open`](docs/server-guide/troubleshooting.md#instances-that-wont-open) |
| `08-ctrl-click-teleport.md` | [`troubleshooting.md#every-player-can-ctrlclick-teleport`](docs/server-guide/troubleshooting.md#every-player-can-ctrlclick-teleport) |
| `09-character-export-import.md` | [`troubleshooting.md#character-exportimport`](docs/server-guide/troubleshooting.md#character-exportimport) |
| `10-debug-console.md` | [`troubleshooting.md#debug-console-commands`](docs/server-guide/troubleshooting.md#debug-console-commands) |
| `11-palette-of-fortune.md` | [`treasures.md#palette-of-fortune`](docs/server-guide/treasures.md#palette-of-fortune) |
| `12-treasures-lucky-keys.md` | [`treasures.md#treasures--lucky-key-system`](docs/server-guide/treasures.md#treasures--lucky-key-system) |
| `13-small-notes.md` | [`setup.md#small-notes`](docs/server-guide/setup.md#small-notes) |
| `14-logins-refused.md` | [`authd.md`](docs/server-guide/authd.md) |
| `15-items-cant-be-dropped.md` | [`troubleshooting.md#items-cant-be-dropped-on-the-ground`](docs/server-guide/troubleshooting.md#items-cant-be-dropped-on-the-ground) |
| `16-nightly-backup.md` | [`backups.md`](docs/server-guide/backups.md) |
| `17-bless-boxes.md` | [`bless-boxes.md`](docs/server-guide/bless-boxes.md) |
### Other moves
| Old | New |
|---|---|
| `docs/layouts/LAYOUTS.md` | split into `docs/layouts/{elements,npc_shops,tasks,quest_rewards,gshop}/README.md`, plus new `npcgen/` |
| `docs/research/bless-boxes-investigation.md` | `docs/research/investigations/blessing_system/README.md` |
| `archive/faction-safe-notes.md` | `docs/research/investigations/faction_safe/README.md` |
| `archive/blessing-experiments/` | `archive/old_notes/blessing-experiments/` |
| `examples/*.py` (dump_item, shop_swap_item, shop_set_duration) | `tools/utility_scripts/` |
| `scripts/pw-backup.service`, `.timer` | `scripts/systemd/` |

## v1: 2026-10-26
Split the single README into `docs/`, `tools/`, `addons/`, `scripts/`, `examples/`, `archive/` (commit 72a7f67).
