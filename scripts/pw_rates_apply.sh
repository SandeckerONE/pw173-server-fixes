#!/bin/bash
# pw_rates_apply.sh - sets the server's event rates through pwAdmin after every (re)start.
# The rates (EXP/SP multiplier, double drops, double coins) live in gdeliveryd memory only and
# reset on every restart, so this re-applies them. Same as pressing SAVE in pwAdmin.
# Change the two values below to change the standing rates.
EXP=2          # EXP/SP multiplier: 1 to 10 (1 = normal)
DOUBLE=true    # true = double drops + double coins, false = off
LOG=/var/log/pw_rates.log
log(){ echo "$(date '+%F %T') $*" >> "$LOG"; }
# wait (max 5 min) until the game maps run and pwAdmin is linked to gdeliveryd
for i in $(seq 60); do
  if pgrep -x gs >/dev/null && ss -tnp 2>/dev/null | grep ':29100' | grep -q java; then break; fi
  sleep 5
done
if ! ss -tnp 2>/dev/null | grep ':29100' | grep -q java; then log "pwAdmin not linked to gdeliveryd after 5 min - rates NOT set"; exit 1; fi
sleep 30   # let the maps finish loading
/usr/bin/wget -q -O /dev/null "http://127.0.0.1:8080/pwadmin/AA/cmd.jsp?cmd_opt=dblDrops&val_1=${DOUBLE}&val_2=${EXP}" \
  && log "rates set: EXP/SP x${EXP}, double drops+coins ${DOUBLE}" || log "wget to pwAdmin failed - rates NOT set"
