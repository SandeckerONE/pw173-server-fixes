# Friends' launcher (PWLauncher)

A small Windows launcher for a home server's players. It checks the server for updated client files, downloads only what changed, backs up the player's own settings, shows a server status light, and starts the game.

## Files
| File | Job |
|---|---|
| `launcher.py` | The window: update, status light, Play button |
| `updater.py` | Downloads changed files listed in the server's manifest |
| `make_manifest.py` | Run on your patch folder to build that manifest (`python make_manifest.py C:\path\to\patch`) |
| `netcheck.py` | Tells the player when Tailscale isn't connected |
| `userdata_backup.py` | Saves the player's own client settings before an update |
| `PWLauncher.spec` | PyInstaller build file |

## Set it up for your server
1. In `launcher.py`, change the two addresses in `SERVERS` to your VM's Tailscale address and its VirtualBox host-only address (the published copy has placeholders).
2. Put an animated `construction.gif` next to `launcher.py` (not included; the launcher shows "(image missing)" without it).
3. Build: `py -m PyInstaller PWLauncher.spec`. The program lands in `dist\PWLauncher\`.

The patch server is any plain HTTP file server on the VM (port 8088 here) serving the patch folder and its manifest.

---
[Back to the repository overview](../../README.md)
