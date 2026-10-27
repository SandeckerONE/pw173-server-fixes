# Server scripts

Run on the server VM. Install steps are at the top of each file and in the guide pages.

| File | Job | Guide page |
|---|---|---|
| `pw_authcheck.sh` | Read-only check: is the login server (authd) healthy? | [14](../docs/server-guide/14-logins-refused.md) |
| `pw-authwatch.cron` | Runs the check every 5 minutes and restarts the server if authd is broken | [14](../docs/server-guide/14-logins-refused.md) |
| `pw_backup.sh` | Nightly backup: accounts, characters, configs; keeps 7 | [16](../docs/server-guide/16-nightly-backup.md) |
| `pw-backup.service` / `pw-backup.timer` | systemd units that run the backup at midnight | [16](../docs/server-guide/16-nightly-backup.md) |
| `server-backup-guard.txt` | One line for `/opt/server` so a manual restart can't collide with the backup | [16](../docs/server-guide/16-nightly-backup.md) |

---
[Back to the repository overview](../README.md)
