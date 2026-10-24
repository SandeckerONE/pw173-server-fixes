#!/bin/bash
# pw_backup.sh - nightly backup: accounts (MariaDB wm), characters (gamedbd, uniquenamed), configs.
# The server is stopped for about a minute so the character files are consistent. Keeps the newest 7.
# Needs /root/.pw_db.cnf (mode 600):  [client] / user="root" / password="..."
# Install: sudo install -m 700 pw_backup.sh /root/   (+ pw-backup.service / pw-backup.timer)
DEST=/var/backups/pw; KEEP=7; OUT=$DEST/$(date +%Y-%m-%d_%H%M)
log(){ echo "$(date '+%F %T') $*"; }
exec 9>/run/pw_backup.lock; flock -n 9 || { log "another backup is running"; exit 1; }
for i in $(seq 60); do pgrep -f "server (start|stop|restart)$" >/dev/null || break; log "waiting for a manual start/stop"; sleep 5; done
touch /run/pw_backup.running; trap 'rm -f /run/pw_backup.running' EXIT
mkdir -p "$OUT"; log "backup to $OUT"
mysqldump --defaults-extra-file=/root/.pw_db.cnf --single-transaction --routines --triggers wm > "$OUT/wm.sql"
grep -q "Dump completed" "$OUT/wm.sql" && log "accounts ok" || log "WARNING: accounts dump incomplete"
PW_BACKUP=1 /opt/server stop > "$OUT/stop.txt" 2>&1
for i in $(seq 60); do pgrep -x gamedbd >/dev/null || break; sleep 1; done
if pgrep -x gamedbd >/dev/null; then log "ERROR: gamedbd did not stop - no character backup"; else
  tar czf "$OUT/characters.tgz" --exclude='*.log' -C /opt gamedbd uniquenamed && log "characters ok"; fi
(cd /opt && tar czf "$OUT/configs.tgz" gamed/*.conf maps server treasure_hook/treasure_hook.conf treasure_hook/state 2>/dev/null) && log "configs ok"
PW_BACKUP=1 /opt/server start > "$OUT/start.txt" 2>&1
sleep 20; log "after start: $(/usr/local/bin/pw_authcheck.sh | tail -1)"
ls -1d $DEST/20*/ 2>/dev/null | head -n -$KEEP | xargs -r rm -rf
log "done, size $(du -sh "$OUT" | cut -f1)"
