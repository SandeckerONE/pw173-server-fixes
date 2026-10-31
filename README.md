# pw173-server-fixes

Fixes, tools and notes for running the community **Perfect World International 1.7.3 (e344 / t187)** server package on your own Linux VM, with the matching English client. Made for a small private home server; everything here was worked out and tested on one.

> **No game or server files are in this repository**, only instructions and code written for it. Run everything inside a VM and take a snapshot before every change.

## Where to start
- **Setting up a server?** [Setup](docs/server-guide/setup.md), then [authd](docs/server-guide/authd.md) and [Backups](docs/server-guide/backups.md).
- **Something is broken?** The [server guide](docs/server-guide/README.md): one problem per section, with the fix and how sure we are.
- **Want to edit shops, quests or items?** The [in-house editor](tools/ultimusv2/README.md) (Windows, Python).
- **Want the Treasures / Lucky Key window to work?** The [treasure_hook add-on](addons/treasure_hook/README.md).
- **Coming from the old numbered pages?** See [CHANGELOG.md](CHANGELOG.md).

## Folders
| Folder | What it holds |
|---|---|
| [`docs/server-guide/`](docs/server-guide/README.md) | The fix list: setup, authd, gacd, backups, Palette/Treasures, Bless Boxes, troubleshooting |
| [`docs/research/`](docs/research/README.md) | The evidence: per-binary notes, protocols, full investigations, and the method |
| [`docs/layouts/`](docs/layouts/README.md) | Byte layouts: elements, tasks, quest rewards, NPC shops, Boutique, npcgen |
| [`tools/ultimusv2/`](tools/ultimusv2/README.md) | PW173 Editor: Boutique, item lookup, quest rewards, NPC shops, item flow |
| [`tools/launcher/`](tools/launcher/README.md) | Friends' launcher: auto-update, status light, user-data backup |
| [`tools/utility_scripts/`](tools/utility_scripts/README.md) | One-job scripts: item dump, shop edits, forge fix, hide NPC spawns |
| [`addons/`](addons/treasure_hook/README.md) | Server add-ons loaded beside gs (`treasure_hook`, [future ideas](addons/future_hooks/README.md)) |
| [`scripts/`](scripts/README.md) | Server scripts: login watchdog, backups, offline copy, rates, log rotation, pwAdmin lock |
| [`examples/`](examples/README.md) | Worked changes: BH I Event Gold, Bless Box tickets, Palette prizes, NPC shops |
| [`archive/`](archive/README.md) | Old experiments kept for reference |

## Safety rules used everywhere here
- Snapshot the VM first; test risky changes on a copy of the VM.
- Tools never overwrite the file you opened; they write a new file and check it.
- Client and server data files must stay identical (`elements.data`, `tasks.data`).
- Unofficial files from the internet: run them inside the VM only.

## About this repo
Much of the research, code and writing here was done with an AI assistant (Claude) and then tested on a real server. Every claim carries an evidence tag (*tested*, *code*, *inferred*) so you can judge it yourself.

## Contributing
If you fix something listed as ❌ or 🔧 in the guide, open an issue or pull request with what you changed and how you tested it.

License: [MIT](LICENSE).
