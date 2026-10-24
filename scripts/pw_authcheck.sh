#!/bin/bash
# pw_authcheck.sh - is the login server (authd) healthy? Read-only.
# authd never reconnects to MariaDB after MariaDB restarts; this spots that.
# Install: sudo install -m 755 pw_authcheck.sh /usr/local/bin/
echo "=== authd check $(date '+%F %T') ==="
p=$(pgrep -f authd | head -1)
if [ -z "$p" ]; then echo "VERDICT: BROKEN - authd not running. Fix: sudo server restart"; exit; fi
a=$(date -d "$(ps -o lstart= -p $p)" +%s)
m=$(date -d "$(systemctl show mariadb -p ActiveEnterTimestamp --value)" +%s)
echo "authd started:   $(date -d @$a '+%F %T')"
echo "MariaDB started: $(date -d @$m '+%F %T')"
ss -ltn | grep -q ":29200 " && echo "port 29200: listening" || echo "port 29200: NOT listening"
s=$(date -d @$a '+%F %T')
# only lines that start with a date: the exception's detail lines don't, and would slip through
bad=$(grep -a -E "Connection must be Open|acquireIdPasswd exception" /opt/logs/authd.log | awk -v s="$s" '/^20[0-9][0-9]-/ && substr($0,1,19)>=s' | wc -l)
echo "DB errors since authd started: $bad"
if [ "$m" -gt "$a" ]; then echo "VERDICT: BROKEN - MariaDB restarted after authd. Fix: sudo server restart"
elif [ "$bad" -gt 0 ]; then echo "VERDICT: BROKEN - authd logged DB errors. Fix: sudo server restart"
else echo "VERDICT: OK"; fi
