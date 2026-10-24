#!/bin/bash
# enable_hook.sh - add the hook to the gs start line in /opt/server, with a backup.
# Run with sudo. It does NOT start or stop the server; it only edits the script.
# After this, the hook loads the next time the server starts. Take a VirtualBox
# snapshot (server stopped) before you use it for the first time.
set -e
SERVER=${SERVER:-/opt/server}
LIB=${LIB:-/opt/treasure_hook/libtreasure.so}
CONF=${CONF:-/opt/treasure_hook/treasure_hook.conf}
LOG=${LOG:-/opt/treasure_hook/hook.log}

[ -f "$LIB" ]  || { echo "missing $LIB (run: make install)"; exit 1; }
[ -f "$CONF" ] || { echo "missing $CONF"; exit 1; }
[ -w "$SERVER" ] || { echo "cannot write $SERVER (use sudo)"; exit 1; }

if grep -q 'libtreasure.so' "$SERVER"; then
    echo "already enabled in $SERVER. Nothing changed."; exit 0
fi
# find the line that launches gs
if ! grep -nE '(^|[^[:alnum:]_])\./gs[[:space:]]' "$SERVER" >/dev/null; then
    echo "could not find the './gs ...' line in $SERVER. Enable by hand (see README)."; exit 1
fi
cp -a "$SERVER" "$SERVER.bak_treasure.$(date +%Y%m%d_%H%M%S)"
# Insert `env VAR=.. LD_PRELOAD=..` right before ./gs. Using `env` (not a bare
# VAR=val prefix) keeps it correct even when the line starts with `setarch i386
# -X` - there a bare VAR=val would be taken as the program name, but `setarch
# ... env VAR=val ./gs` runs env, which sets the vars and execs gs.
PRE="env TREASURE_HOOK_CONF=$CONF TREASURE_HOOK_LOG=$LOG LD_PRELOAD=$LIB "
sed -i -E "s#(^|[[:space:]])(\./gs[[:space:]])#\1${PRE//#/\\#}\2#" "$SERVER"
echo "enabled. The gs line in $SERVER is now:"
grep -nE 'libtreasure.so' "$SERVER"
echo
echo "Backup: $SERVER.bak_treasure.*"
echo "Next: stop and start the server, then watch $LOG."
