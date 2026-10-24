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
