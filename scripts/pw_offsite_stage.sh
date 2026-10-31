#!/bin/bash
# pw_offsite_stage.sh - weekly: packs the newest nightly backup into ~OFFSITE_USER/offsite/ so the PC can pull it.
# Read-only on /var/backups/pw. Keeps the newest 2 packs in offsite/. Log: /var/log/pw_offsite.log
# Install: sudo install -m 700 pw_offsite_stage.sh /usr/local/bin/   (+ pw-offsite.service / pw-offsite.timer)
set -euo pipefail
OFFSITE_USER=youruser   # the normal user the PC logs in as (its ~/offsite is the staging folder)
SRC=/var/backups/pw; OUT=/home/$OFFSITE_USER/offsite; KEEP=2
log(){ echo "$(date '+%F %T') $*" >> /var/log/pw_offsite.log; }
[ -e /run/pw_backup.running ] && { log "nightly backup running, skipped"; exit 0; }
newest=$(ls -1d "$SRC"/2* 2>/dev/null | sort | tail -1)
[ -n "$newest" ] || { log "no backup found in $SRC"; exit 1; }
name=$(basename "$newest")
for f in wm.sql characters.tgz; do [ -s "$newest/$f" ] || { log "$name: $f missing or empty, not staged"; exit 1; }; done
mkdir -p "$OUT"
tmp="$OUT/.pw_backup_$name.tar.part"
tar -cf "$tmp" -C "$SRC" "$name"
mv "$tmp" "$OUT/pw_backup_$name.tar"
( cd "$OUT" && sha256sum "pw_backup_$name.tar" > "pw_backup_$name.tar.sha256" )
ls -1t "$OUT"/pw_backup_*.tar | tail -n +$((KEEP+1)) | while read -r old; do rm -f "$old" "$old.sha256"; done
chown -R "$OFFSITE_USER:$OFFSITE_USER" "$OUT"; chmod 700 "$OUT"
log "staged $name ($(du -h "$OUT/pw_backup_$name.tar" | cut -f1))"
