# authd (logins)

The login server. Its one known failure mode and the watchdog that fixes it by itself.

**On this page**
- [All logins suddenly refused](#all-logins-suddenly-refused)

## All logins suddenly refused
✅ *[tested; recurred twice before the fix]*

**Symptom:** accounts that worked minutes ago are refused ("wrong account/password"), then every account is. The authd log (`/opt/logs/authd.log`) shows `Connection must be Open; current state is Closed`, `acquireIdPasswd exception`, then `GQueryPasswd:can not find user <name>`.

**Cause:** authd opens its MariaDB connection once and **never reconnects**. Anything that restarts MariaDB breaks all logins until authd is restarted. Here it was Ubuntu's daily automatic update (~06:30 UTC): one day a MariaDB package upgrade, the next day only a **zlib** update, after which MariaDB was restarted anyway (most likely by `needrestart`, which restarts services using an updated library *[inferred]*). MariaDB's 8-hour idle timeout (`wait_timeout = 28800`) can cause the same on a quiet server.

**Quick fix:** `sudo server restart`

**Prevention:**
```bash
# 1) don't auto-upgrade MariaDB
sudo tee /etc/apt/apt.conf.d/51pw-no-auto-db >/dev/null <<'EOF'
Unattended-Upgrade::Package-Blacklist { "mariadb-"; "libmariadb"; "galera-"; };
EOF
# 2) don't let needrestart restart MariaDB after other library updates
sudo mkdir -p /etc/needrestart/conf.d
echo '$nrconf{override_rc}{qr(^mariadb)} = 0;' | sudo tee /etc/needrestart/conf.d/50-pw-keep-mariadb.conf
# 3) never drop idle connections
printf '[mysqld]\nwait_timeout = 31536000\ninteractive_timeout = 31536000\n' | sudo tee /etc/mysql/mariadb.conf.d/99-pw-timeouts.cnf
sudo systemctl restart mariadb && sudo server restart
```
Still apply security updates to MariaDB yourself now and then, followed by `sudo server restart`.

**Checker + watchdog** (files in [`scripts/`](../../scripts/)). `pw_authcheck.sh` (read-only) says BROKEN if nothing listens on authd's port 29200, if MariaDB started after authd, or if authd logged database errors since it started. Same as [`scripts/pw_authcheck.sh`](../../scripts/pw_authcheck.sh):
```bash
#!/bin/bash
# pw_authcheck.sh - is the login server (authd) healthy? Read-only.
# authd never reconnects to MariaDB after MariaDB restarts; this spots that.
# authd is found by the port it listens on (29200), not by name: a name search
# also matches any command line that merely contains "authd" (e.g. the watchdog's own cron line).
# Install: sudo install -m 755 pw_authcheck.sh /usr/local/bin/
echo "=== authd check $(date '+%F %T') ==="
p=$(ss -ltnpH 'sport = :29200' 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
[ -z "$p" ] && p=$(sudo -n ss -ltnpH 'sport = :29200' 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
if [ -z "$p" ]; then echo "VERDICT: BROKEN - nothing listening on 29200 (authd down). Fix: sudo server restart"; exit; fi
a=$(date -d "$(ps -o lstart= -p $p)" +%s)
m=$(date -d "$(systemctl show mariadb -p ActiveEnterTimestamp --value)" +%s)
echo "authd pid $p started: $(date -d @$a '+%F %T')"
echo "MariaDB started:      $(date -d @$m '+%F %T')"
s=$(date -d @$a '+%F %T')
# only lines that start with a date: the exception's detail lines don't, and would slip through
bad=$(grep -a -E "Connection must be Open|acquireIdPasswd exception" /opt/logs/authd.log | awk -v s="$s" '/^20[0-9][0-9]-/ && substr($0,1,19)>=s' | wc -l)
echo "DB errors since authd started: $bad"
if [ "$m" -gt "$a" ]; then echo "VERDICT: BROKEN - MariaDB restarted after authd. Fix: sudo server restart"
elif [ "$bad" -gt 0 ]; then echo "VERDICT: BROKEN - authd logged DB errors. Fix: sudo server restart"
else echo "VERDICT: OK"; fi
```
Three traps we hit writing it: find authd by its port, not with `pgrep -f authd` (that also matches the watchdog's own cron line, which contains the word "authd", so a dead authd looked alive); don't judge by "last error vs last good login" (no logins after a restart looks broken forever), and only count log lines that start with a date (the error's detail lines don't, and slip through a time filter). Watchdog every 5 minutes (`scripts/pw-authwatch.cron`, expects the checker in `/usr/local/bin/`):
```bash
sudo tee /etc/cron.d/pw-authwatch >/dev/null <<'EOF'
*/5 * * * * root [ ! -e /run/pw_backup.running ] && /usr/local/bin/pw_authcheck.sh | grep -q "VERDICT: BROKEN" && { echo "$(date) authd broken, restarting" >> /var/log/pw_authwatch.log; /sbin/server restart >> /var/log/pw_authwatch.log 2>&1; }
EOF
```
`/var/log/pw_authwatch.log` records every restart it does.

---
[Back to the guide index](README.md)
