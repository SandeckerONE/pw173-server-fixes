# 16. Nightly backup
✅ *[tested]*

`scripts/pw_backup.sh` + `pw-backup.service` + `pw-backup.timer`: at midnight (set your time zone in the timer) it dumps the `wm` database, stops the server for about a minute, archives `/opt/gamedbd` and `/opt/uniquenamed` (characters) and the configs into `/var/backups/pw/<date>/`, starts the server again and keeps the newest 7. **Trap:** the service must have `KillMode=process` (already in the file). Without it, systemd kills every process the backup started when the backup ends, and that includes the game server it just restarted. A test run started by hand doesn't show this; only the timer run does. *[tested the hard way]*

Add the one-line guard from `scripts/server-backup-guard.txt` to `/opt/server` so a manual restart can't collide with it (a collision like that left half the daemons dead on another server).

Restore (snapshot first):
```bash
B=/var/backups/pw/<date>
sudo server stop
sudo tar xzf $B/characters.tgz -C /opt
sudo mysql --defaults-extra-file=/root/.pw_db.cnf wm < $B/wm.sql
sudo server start
```

---
[Back to the guide index](README.md)
