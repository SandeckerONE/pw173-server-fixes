# gdb_types.py - READ-ONLY. Run by recon_gs.sh --types as:
#   gdb -batch -nx -x gdb_types.py /opt/gamed/gs
# gdb only opens the gs FILE (its debug info); it does not attach to the running server.
# Prints the structure offsets and function signatures the Treasures hook config needs.
import re

import gdb


def run(cmd, filt=None, limit=150):
    print("### " + cmd)
    try:
        out = gdb.execute(cmd, to_string=True)
    except Exception as e:  # keep going: one missing name must not stop the rest
        msg = str(e).splitlines()
        print("  (failed: %s)" % (msg[0] if msg else "error"))
        return ""
    lines = out.splitlines()
    if filt:
        lines = [l for l in lines if re.search(filt, l)]
    for l in lines[:limit]:
        print("  " + l)
    if len(lines) > limit:
        print("  ... %d more lines" % (len(lines) - limit))
    return out


for setting in ("pagination off", "width 0", "print demangle on", "print asm-demangle on"):
    gdb.execute("set " + setting)

# 1. offsets for treasure_hook.conf (off.parent / off.runner / off.roleid / off.csidx / off.cssid)
for expr in ("&((gplayer_imp*)0)->_parent", "&((gplayer_imp*)0)->_runner",
             "&((gplayer_imp*)0)->_commander", "&((gplayer_imp*)0)->_plane",
             "&((gobject*)0)->ID", "&((gobject*)0)->ID.id", "&((gplayer*)0)->ID.id",
             "&((gplayer*)0)->cs_index", "&((gplayer*)0)->cs_sid", "sizeof(XID)"):
    run("print/d (long)(" + expr + ")")

# 2. the classes involved (filtered to the interesting members)
run("ptype /o XID")
run("ptype /o gobject_imp", limit=80)
run("ptype /o gobject", limit=120)
run("ptype /o gplayer", filt=r"cs_|ID|offset|size|/\*", limit=200)
run("ptype /o gplayer_imp",
    filt=r"(?i)lot|treasure|_parent|_runner|_commander|_plane|inventory|safe|class gplayer_imp|total size",
    limit=150)

# 3. full signatures (return types included) of the functions the hook may call.
#    gdb takes POSIX basic regexes here: alternation is \| and grouping is \( \).
for rx in (r"^gplayer_imp::Lottery_Notice", r"send_lot", r"LotInventory\|AddLot\|DelLot",
           r"^gplayer_imp::\(ObtainItem\|CheckItemExist\|RemoveItem\|TakeOutItem\|DeliverItem\|TestSafeLock\|GainItem\|GetItemCount\|HasEmptySlot\|InventoryHasSlot\)",
           r"^gplayer_dispatcher::error_message", r"SendClientData", r"send_ls_msg",
           r"^gplayer_controller::CommandHandler"):
    run("info functions " + rx, filt=r"\(|File ", limit=60)

# 4. packet structures with lottery/treasure in the name (S2C command layouts)
out = run(r"info types [Ll]otter\?y\|[Tt]reasure\|lot_\|_lot\|Lot_", limit=120)
names = []
for l in out.splitlines():
    m = re.search(r"(?:struct|class|union)?\s*([A-Za-z_][\w:]*(?:[Ll]ot|[Tt]reasure)\w*)\s*;", l)
    if m and m.group(1) not in names:
        names.append(m.group(1))
for n in names[:25]:
    run("ptype /o " + n, limit=60)
