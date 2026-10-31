# Server scripts

Run on the server VM unless it says PC. Install steps are at the top of each file and in the guide pages.

| File | Job | Guide |
|---|---|---|
| `pw_authcheck.sh` | Read-only check: is the login server (authd) healthy? | [authd](../docs/server-guide/authd.md) |
| `pw-authwatch.cron` | Runs the check every 5 minutes and restarts the server if authd is broken | [authd](../docs/server-guide/authd.md) |
| `pw_backup.sh` | Nightly backup: accounts, characters, configs; keeps 7 (lock bug fixed) | [Backups](../docs/server-guide/backups.md) |
| `server-backup-guard.txt` | One line for `/opt/server` so a manual restart can't collide with the backup | [Backups](../docs/server-guide/backups.md) |
| `pw_offsite_stage.sh` | Weekly: packs the newest backup for the PC to pull (set `OFFSITE_USER`) | [Backups](../docs/server-guide/backups.md#weekly-offline-copy-on-a-pc) |
| `pull_pw_backup.ps1` | **PC:** pulls that pack over SSH, checks sha256, keeps 8 | [Backups](../docs/server-guide/backups.md#weekly-offline-copy-on-a-pc) |
| `pw_rates_apply.sh` | Re-applies EXP/SP and double drops/coins through pwAdmin after every start | [Setup](../docs/server-guide/setup.md#rates-exp-spirit-drops-and-coins) |
| `logrotate/pw-logs` | Rotates `/opt/logs` (7 days, 30 for cash/chat) | [Setup](../docs/server-guide/setup.md#log-rotation-logs-filling-the-disk) |
| `nftables/pwadmin-lock.nft` | Drops pwAdmin/Tomcat ports on the VPN interface | [Setup](../docs/server-guide/setup.md#security-checklist) |
| `systemd/pw-backup.service`, `.timer` | Run the backup at midnight | [Backups](../docs/server-guide/backups.md) |
| `systemd/pw-offsite.service`, `.timer` | Run the offline staging on Sundays | [Backups](../docs/server-guide/backups.md#weekly-offline-copy-on-a-pc) |
| `systemd/pwadmin-lock.service` | Loads `pwadmin-lock.nft` at boot | [Setup](../docs/server-guide/setup.md#security-checklist) |

Timers use `America/Chicago` as an example time zone: change it to yours.

---
[Back to the repository overview](../README.md)
