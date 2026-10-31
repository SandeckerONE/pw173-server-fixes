# Backups

Nightly backup on the VM, a weekly offline copy on a PC, and how to prove a restore works.

**On this page**
- [Nightly backup](#nightly-backup)
- [The backup skips every other night ("another backup is running")](#the-backup-skips-every-other-night-another-backup-is-running)
- [Weekly offline copy on a PC](#weekly-offline-copy-on-a-pc)
- [Restore drill: prove the backup works](#restore-drill-prove-the-backup-works)

## Nightly backup
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

## The backup skips every other night ("another backup is running")
✅ *[tested]*

**Symptom:** `/var/log/pw_backup.log` shows a backup one night and "another backup is running" the next, alternating.

**Cause** *[inferred, strong]*: the script takes its lock with `exec 9>/run/pw_backup.lock; flock -n 9` and then starts the game server itself. Every daemon inherits file 9 and holds the lock until the next manual restart.

**Fix** (already in `scripts/pw_backup.sh`): close file 9 for the server start:
```bash
PW_BACKUP=1 /opt/server start 9>&- > "$OUT/start.txt" 2>&1
```
Check after a run: `sudo fuser -v /run/pw_backup.lock` should print nothing.

## Weekly offline copy on a PC
✅ *[tested]*

A backup that lives only inside the VM dies with the VM. Once a week the VM packs the newest nightly backup, and the PC pulls it over SSH and checks it.

**VM side:** `scripts/pw_offsite_stage.sh` + `scripts/systemd/pw-offsite.service` / `.timer` (Sunday 01:30). It tars the newest `/var/backups/pw/<date>/` into a staging folder of a normal user, writes a `.sha256` next to it and keeps 2. Read-only on the backups; skips if the nightly backup is running.
```bash
sudo nano scripts/pw_offsite_stage.sh        # set OFFSITE_USER at the top
sudo install -m 700 scripts/pw_offsite_stage.sh /usr/local/bin/
sudo install -m 644 scripts/systemd/pw-offsite.service scripts/systemd/pw-offsite.timer /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pw-offsite.timer
sudo systemctl start pw-offsite.service && tail -1 /var/log/pw_offsite.log
```
**PC side:** `scripts/pull_pw_backup.ps1` copies the newest pack, compares the checksum, keeps 8. Give it an SSH key that only this job uses:
```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\pw_backup -N '""'
type $env:USERPROFILE\.ssh\pw_backup.pub | ssh <user>@<vm> "cat >> ~/.ssh/authorized_keys"
powershell -ExecutionPolicy Bypass -File pull_pw_backup.ps1 -Vm <user>@<vm> -Dest D:\PWBackups
```
Then add it to Task Scheduler (weekly, Sunday after the VM's timer, "run as soon as possible after a missed start").

The backups hold your account database including password hashes: keep the copies private.

## Restore drill: prove the backup works
✅ *[tested: characters, gear and items came back as of the backup]*

A backup you never restored is a hope, not a backup. Do this on a **clone**, never the live VM:
1. VirtualBox: clone the server VM (full clone, *new MAC addresses*). On the clone, give the host-only adapter a different IP, and disable everything that talks to the outside or runs on a schedule: `sudo systemctl disable --now tailscaled pw-backup.timer pw-offsite.timer`.
2. Copy one offline pack from the PC into the clone and unpack it: `tar xf pw_backup_<date>.tar -C /tmp`.
3. Move the clone's own character data aside, then restore:
```bash
B=/tmp/<date>
sudo server stop
sudo mv /opt/gamedbd /opt/gamedbd.clone_own; sudo mv /opt/uniquenamed /opt/uniquenamed.clone_own
sudo tar xzf $B/characters.tgz -C /opt
sudo mysql --defaults-extra-file=/root/.pw_db.cnf wm < $B/wm.sql
sudo server start; sleep 120; sudo server status
```
4. Add the clone to your client's `serverlist.txt` as a second line (see [Client won't connect](setup.md#client-wont-connect--stuck-on-connecting-to-server)), log in, and check characters, gear and bags.

`characters.tgz` holds the whole `/opt/gamedbd` and `/opt/uniquenamed` folders (programs, configs and data, without logs), which is why the clone's own folders are moved aside first.

---
[Back to the guide index](README.md)
