#!/bin/bash
# disable_hook.sh - remove the hook from the gs start line in /opt/server.
# Run with sudo. The hook is gone the next time the server starts. gs itself is
# never modified by this project, so this fully reverts it.
#
# Instant off without editing: the library also checks the TREASURE_HOOK_DISABLE
# environment variable - if it is set when gs starts, the library does nothing.
set -e
SERVER=${SERVER:-/opt/server}
[ -w "$SERVER" ] || { echo "cannot write $SERVER (use sudo)"; exit 1; }

if ! grep -q 'libtreasure.so' "$SERVER"; then
    echo "not enabled in $SERVER. Nothing to do."; exit 0
fi
cp -a "$SERVER" "$SERVER.bak_treasure_off.$(date +%Y%m%d_%H%M%S)"
# strip the `env ...libtreasure.so ` words we inserted, leaving ./gs as it was.
# Handles both the current form (env ... LD_PRELOAD=..) and an older bare prefix.
sed -i -E 's#(env )?(TREASURE_HOOK_CONF=[^ ]+ )?(TREASURE_HOOK_LOG=[^ ]+ )?LD_PRELOAD=[^ ]*libtreasure\.so ##g' "$SERVER"
if grep -q 'libtreasure.so' "$SERVER"; then
    echo "WARNING: could not fully remove it automatically. Edit $SERVER by hand;"
    echo "a clean copy is in the newest $SERVER.bak_treasure.* backup."
    exit 1
fi
echo "disabled. The gs line in $SERVER is now:"
grep -nE '\./gs[[:space:]]' "$SERVER"
echo "Restart the server to run without the hook."
