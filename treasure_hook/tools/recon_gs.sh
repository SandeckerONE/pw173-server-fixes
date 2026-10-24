#!/bin/bash
# recon_gs.sh - READ-ONLY survey of the 1.7.3 game server for the Treasures hook.
# It changes nothing on the server: it only reads files and prints what it finds.
#
#   sudo bash ~/treasure_hook/tools/recon_gs.sh            quick (a few minutes)
#   sudo bash ~/treasure_hook/tools/recon_gs.sh --types    also structure offsets via gdb (slower)
#
# Result: treasure_recon.txt in your home folder. Send that file to Claude.
# Needs python3 (already on Ubuntu). objdump and gdb (packages binutils, gdb) are
# used when installed; without them those sections are skipped.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
GS=${GS:-/opt/gamed/gs}
SERVER=${SERVER:-/opt/server}
TYPES=0
[ "${1:-}" = "--types" ] && TYPES=1
ME=${SUDO_USER:-$(id -un)}
USERHOME=$(getent passwd "$ME" | cut -d: -f6)
OUT=${OUT:-$USERHOME/treasure_recon.txt}
SYM="python3 -I $HERE/gs_symbols.py"

have() { command -v "$1" >/dev/null 2>&1; }
exec 3>&1
step() { echo "[recon] $*" >&3; printf '\n=================== %s ===================\n' "$*"; }

dis() { # dis <mangled name> [max lines]: disassemble one function
    local r
    r=$($SYM range "$GS" "$1" 2>/dev/null) || { echo "(not found: $1)"; return; }
    set -- "$1" "${2:-400}" $r
    echo "----- $1  ($3 .. $4)"
    objdump -d -M intel -C --no-show-raw-insn --start-address="$3" --stop-address="$4" "$GS" |
        sed -n '7,$p' | head -n "$2"
}

main() {
    step "1. system"
    date
    hostname
    uname -a
    grep PRETTY_NAME /etc/os-release
    ldd --version 2>&1 | head -1
    for t in gcc make objdump c++filt gdb python3 file; do
        printf '%-8s %s\n' "$t" "$(command -v "$t" || echo MISSING)"
    done
    if have gcc; then
        if echo 'int main(void){return 0;}' | gcc -m32 -x c -o /dev/null - >/dev/null 2>&1; then
            echo "gcc -m32: works"
        else
            echo "gcc -m32: NOT working (sudo apt install -y gcc-multilib)"
        fi
    fi

    step "2. the gs program"
    ls -la "$GS"
    have file && file "$GS"
    sha256sum "$GS"
    $SYM info "$GS"

    step "3. how the server script starts gs"
    ls -la "$SERVER"
    grep -n -E '\./gs([[:space:]]|$)|LD_PRELOAD|treasure' "$SERVER"
    echo "--- running gs processes:"
    ps -C gs -o pid,ppid,etime,args | head -20

    step "4. Treasures lines in the logs"
    local f c
    find /opt /var/log -xdev -type f \( -name '*.log' -o -name '*log*' -o -path '*/logs/*' \) \
        -size -500M 2>/dev/null | head -300 | while read -r f; do
        c=$(grep -a -c 'Lottery_Notice' "$f" 2>/dev/null)
        [ "${c:-0}" -gt 0 ] && echo "$c lines in $f" && grep -a 'Lottery_Notice' "$f" | tail -12
    done

    step "5. symbols"
    $SYM find "$GS" 'Lottery|Lotery|lottery|lotery|Treasure|treasure|LotInv|lot_inv|DelLot|AddLot|send_lot' 150
    $SYM find "$GS" '^_ZN11gplayer_imp\d+(CheckItem|RemoveItem|TakeOutItem|ObtainItem|DeliverItem|GainItem|GenerateItem|IsItemExist|GetItemCount|CountItem|HasSlot|EmptySlot|TestSafeLock|InventoryHas)' 150
    $SYM find "$GS" '^_ZN18gplayer_dispatcher\d+(error_message|send_lot|lottery|treasure)' 60
    $SYM find "$GS" 'SendClientData|send_ls_msg|GetDataMan|generate_item|DupeItem|CreateItem' 60
    $SYM find "$GS" 'CommandHandler' 40

    step "6. who calls Lottery_Notice1 / Lottery_Notice2 / the lot senders"
    $SYM callers "$GS" 'Lottery_Notice[12]|send_lot|LotInventory'

    step "7. disassembly"
    if have objdump; then
        local n
        for n in $($SYM names "$GS" '^_ZN11gplayer_imp15Lottery_Notice1E'); do dis "$n" 800; done
        for n in $($SYM names "$GS" '^_ZN11gplayer_imp15Lottery_Notice2E'); do dis "$n" 1500; done
        for n in $($SYM names "$GS" 'send_lot|LotInventory|AddLot|DelLot'); do dis "$n" 400; done
        for n in $($SYM names "$GS" '^_ZN11gplayer_imp\d+(ObtainItem|CheckItemExist|RemoveItems?|TakeOutItem|DeliverItem|TestSafeLock)E'); do dis "$n" 300; done
        for n in $($SYM names "$GS" '^_ZN18gplayer_dispatcher13error_messageE|SendClientData'); do dis "$n" 200; done
        echo "----- code around each direct call to Lottery_Notice1"
        local a
        for a in $($SYM callers "$GS" '^_ZN11gplayer_imp15Lottery_Notice1E' | grep -oE 'direct (call|jump) at 0x[0-9a-f]+' | awk '{print $4}'); do
            echo "--- around $a"
            objdump -d -M intel -C --no-show-raw-insn --start-address=$((a - 0x180)) \
                --stop-address=$((a + 0x30)) "$GS" | sed -n '7,$p'
        done
    else
        echo "objdump missing: sudo apt install -y binutils   (then run this again)"
    fi

    step "8. Treasures tables in elements.data"
    # EL= overrides; otherwise try the usual spot, then next to gs, then a search
    local el=${EL:-}
    local gsdir
    gsdir=$(dirname "$GS")
    for cand in "$el" /opt/gamed/config/elements.data "$gsdir/config/elements.data" \
                "$gsdir/elements.data"; do
        [ -n "$cand" ] && [ -f "$cand" ] && { el=$cand; break; } || el=""
    done
    [ -n "$el" ] || el=$(find /opt "$gsdir" -xdev -name elements.data -size +1M 2>/dev/null | head -1)
    if [ -n "$el" ]; then
        python3 -I "$HERE/extract_treasure_cfg.py" "$el"
    else
        echo "elements.data not found (set EL=/path/to/elements.data and re-run step 8)"
    fi

    if [ "$TYPES" = 1 ]; then
        step "9. structure offsets and signatures (gdb; can take several minutes)"
        if have gdb; then
            timeout 1800 gdb -batch -nx -x "$HERE/gdb_types.py" "$GS" 2>&1 |
                grep -v -E '^(warning:|Reading symbols)' | head -3000
        else
            echo "gdb missing: sudo apt install -y gdb   (then run this again with --types)"
        fi
    fi
    step "done"
}

main >"$OUT" 2>&1
chown "$ME": "$OUT" 2>/dev/null
echo "[recon] finished: $OUT ($(du -h "$OUT" | cut -f1)). Send this file to Claude." >&3
