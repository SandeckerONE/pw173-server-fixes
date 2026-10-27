# pw173-server-fixes

Fixes, tools and notes for running the community **Perfect World International 1.7.3 (e344 / t187)** server package on your own Linux VM, with the matching English client. Made for a small private home server; everything here was worked out and tested on one.

> **No game or server files are in this repository**, only instructions and code written for it. Run everything inside a VM and take a snapshot before every change.

## Where to start
- **Something is broken on your server?** Open the [server guide](docs/server-guide/README.md). One problem per page, with the fix and how sure we are.
- **Want to edit shops, quests or items?** Use the [in-house editor](tools/ultimusv2/README.md) (Windows, Python).
- **Want the Treasures / Lucky Key window to work?** See the [treasure_hook add-on](addons/treasure_hook/README.md).

## What is in each folder
| Folder | What it holds |
|---|---|
| [`docs/server-guide/`](docs/server-guide/README.md) | The fix list: setup, connecting, accounts, Boutique, lag, instances, backups, Bless Boxes ... |
| [`docs/research/`](docs/research/README.md) | How we found things out: investigation write-ups with the evidence |
| [`docs/layouts/`](docs/layouts/README.md) | Byte layouts of the data files (Boutique, elements.data, tasks.data) |
| [`tools/ultimusv2/`](tools/ultimusv2/README.md) | PW173 Editor: Boutique, item lookup, quest rewards, NPC shops, item flow |
| [`tools/launcher/`](tools/launcher/README.md) | Friends' launcher: auto-update, server status light, user-data backup |
| [`addons/treasure_hook/`](addons/treasure_hook/README.md) | Server add-on (LD_PRELOAD) that adds the missing Treasures logic |
| [`scripts/`](scripts/README.md) | Server scripts: login watchdog, nightly backup |
| [`examples/`](examples/README.md) | Small one-job patch scripts (shop item swap, shop duration, item dump) |
| [`archive/`](archive/README.md) | Old notes and experiments kept for reference only |

## Safety rules used everywhere here
- Snapshot the VM first; test risky changes on a copy of the VM.
- Tools never overwrite the file you opened; they write a new file.
- Unofficial files from the internet: run them inside the VM only.

## Contributing
If you fix something listed as ❌ or 🔧 in the guide, open an issue or pull request with what you changed and how you tested it.

License: [MIT](LICENSE).
