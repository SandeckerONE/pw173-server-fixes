#!/usr/bin/env python3
"""run_tests.py - drives fake_gs with treasure_hook preloaded and checks the results.

Used on Claude's side only (64-bit build of the same source). It does not prove the
real gs signatures; it proves the hook machinery and the Treasures logic:
patching (vtable + direct call, PIE and non-PIE, -O0 and -O2), config reload,
seek / open / costs / refusals / Aurum / probe / raw packets / warehouse /
call chains / state persistence / dry run / wrong offsets.

Usage: python3 run_tests.py <out-dir>   (run_tests.sh builds everything first)
"""
import os
import re
import shutil
import subprocess
import sys
import time

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "out")
LIB = os.path.join(OUT, "libtreasure64.so")
KEY = 56274
COSTS = [0, 5, 12, 30, 75, 188, 466, 1166, 2998, 4198]
LOOT_IDS = list(range(90001, 90013))  # 12 rows

failures = []
passes = 0


def check(cond, what):
    global passes
    if cond:
        passes += 1
    else:
        failures.append(what)
        print("   FAIL:", what)


def symbols(binary):
    """demangled name -> mangled name, for the functions the config needs"""
    nm = subprocess.run(["nm", binary], capture_output=True, text=True, check=True).stdout
    mangled = [l.split()[-1] for l in nm.splitlines() if " T " in l or " t " in l or " W " in l]
    dem = subprocess.run(["c++filt"], input="\n".join(mangled), capture_output=True,
                         text=True, check=True).stdout.splitlines()
    return dict(zip(dem, mangled))


def find_sym(table, prefix):
    hits = [m for d, m in table.items() if d.startswith(prefix)]
    assert len(hits) == 1, f"symbol {prefix}: {hits}"
    return hits[0]


class Mock:
    def __init__(self, exe, conf, log, env_extra=None):
        env = dict(os.environ)
        env.update({"LD_PRELOAD": LIB, "TREASURE_HOOK_CONF": conf, "TREASURE_HOOK_LOG": log})
        if env_extra:
            env.update(env_extra)
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, env=env, bufsize=1)

    def send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError(f"fake gs died after '{line}': {out}")
            l = l.rstrip("\n")
            if l == "DONE":
                return out
            out.append(l)

    def close(self):
        try:
            self.p.stdin.write("quit\n")
            self.p.stdin.flush()
        except BrokenPipeError:
            pass
        self.p.wait(timeout=5)


def bag(m, role):
    line = [l for l in m.send(f"bag {role}") if l.startswith("BAG")][0]
    return {int(k): int(v) for k, v in (t.split(":") for t in line.split()[2:])}


INFO_RE = re.compile(r"INFO3 manager=(\d+) score=(\d+) free=(\d+) lots=(\d+) boxes=(\d+) L\[(.*)\] B\[(.*)\]")


def info(lines):
    """parse the last INFO3 line -> dict, or None"""
    rows = [l for l in lines if l.startswith("INFO3")]
    if not rows:
        return None
    m = INFO_RE.match(rows[-1])
    d = dict(zip(["manager", "score", "free", "lots", "boxes"], map(int, m.groups()[:5])))
    d["L"] = [tuple(map(int, re.split("[:x]", t))) for t in m.group(6).split()]       # (lot, id, count)
    d["B"] = [tuple(map(int, re.split("[@:x]", t))) for t in m.group(7).split()]      # (lot, box, id, count)
    return d


_stamp = [time.time_ns()]


def write_conf(path, text):
    with open(path, "w") as f:
        f.write(text)
    _stamp[0] += 10_000_000  # make sure the hook sees a new mtime
    os.utime(path, ns=(_stamp[0], _stamp[0]))


def base_conf(off, syms, state_dir, mode="live", extra=""):
    loot = "\n".join(f"loot = {i}, 0.0833, {1 + (i % 3)}" for i in LOOT_IDS)
    return f"""
mode = {mode}
allow_roles = 1001
off.parent = {off['parent']}
off.runner = {off['runner']}
off.roleid = {off['roleid']}
off.csidx = {off['csidx']}
off.cssid = {off['cssid']}
state_dir = {state_dir}
call.count = {syms['count']} : imp, id, count
ok.count = true
call.remove = {syms['remove']} : imp, id, count
ok.remove = true
call.obtain = {syms['obtain']} : imp, id, count
ok.obtain = true
call.info = {syms['info']} : runner, manager, score, free, nlots, nboxes, lots, boxes
call.msg = {syms['msg']} : runner, err
call.safelock = {syms['safelock']} : imp
ok.safelock = false
err.nokeys = 11
err.bagfull = 12
err.noaurum = 13
err.safelock = 108
{loot}
{extra}
"""


def run_variant(name, exe):
    print(f"== variant {name}")
    work = os.path.join(OUT, "run_" + name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    conf, log, state = (os.path.join(work, n) for n in ("t.conf", "hook.log", "state"))
    t = symbols(exe)
    syms = {
        "count": find_sym(t, "gplayer_imp::CheckItemExist("),
        "remove": find_sym(t, "gplayer_imp::RemoveItems("),
        "obtain": find_sym(t, "gplayer_imp::ObtainItem(int"),
        "obtaindata": find_sym(t, "gplayer_imp::ObtainItemData("),
        "lotadd": find_sym(t, "gplayer_imp::AddLotItem("),
        "safelock": find_sym(t, "gplayer_imp::TestSafeLock("),
        "info": find_sym(t, "gplayer_dispatcher::send_lot_info3("),
        "inv": find_sym(t, "gplayer_dispatcher::send_lot_inv("),
        "msg": find_sym(t, "gplayer_dispatcher::error_message("),
        "raw": find_sym(t, "GMSV::SendClientData("),
        "make": find_sym(t, "MakeItem("),
    }

    # --- A. log mode (pass-through) ---------------------------------------
    write_conf(conf, "mode = log\n")
    m = Mock(exe, conf, log)
    off = dict(kv.split("=") for kv in m.send("offsets")[0].split()[1:])
    off = {k: int(v) for k, v in off.items()}
    out = m.send("cmd 1001 197 3 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1001 3 0") for l in out), "A: log mode passes seek to gs")
    hl = open(log).read()
    check("hook installed" in hl, "A: hook installed")
    mm = re.search(r"hook installed: (\d+) vtable slot\(s\), (\d+) direct call\(s\)/jump\(s\)", hl)
    check(mm and int(mm.group(1)) >= 1 and int(mm.group(2)) >= 1, f"A: vtable and direct call patched ({mm and mm.groups()})")
    check("type=3 param=0 -> seek (mode log)" in hl, "A: command logged")
    # the GCC-style local copy "...Lottery_Notice1Eii.part.0" must never be chosen
    check("candidate" in hl and hl.count("candidate ") == 1, "A: exactly one hook candidate (clone skipped)")
    check(".part.0" not in re.sub(r".*is a local or compiler-made copy.*", "", hl), "A: clone not used as target")
    check(not any("FAKE CLONE" in l for l in out), "A: clone never executed")

    # --- B. live: window, seek, opens, costs ------------------------------
    write_conf(conf, base_conf(off, syms, state))
    m.send(f"give 1001 {KEY} 50")
    out = m.send("cmd 1001 197 0 0")
    i0 = info(out)
    check(i0 and i0["manager"] == 0 and i0["lots"] == 0 and i0["boxes"] == 0, f"B: empty window board {i0}")
    check(not any(l.startswith("Lottery_Notice1") for l in out), "B: gs printf path not used in live mode")

    out = m.send("cmd 1001 197 3 0")
    s = info(out)
    check(s and s["manager"] == 1 and s["lots"] == 10 and s["boxes"] == 0 and s["free"] == 1 and s["score"] == 1,
          f"B: seek shows a 10-chest board {s and {k: s[k] for k in ('manager','lots','boxes','free','score')}}")
    check(s and sorted(e[0] for e in s["L"]) == list(range(10)), "B: lot indexes 0-9")
    check(s and len({e[1] for e in s["L"]}) == 10 and all(e[1] in LOOT_IDS for e in s["L"]), "B: 10 different prizes from the loot table")
    check(bag(m, 1001).get(KEY) == 48, "B: seek took 2 keys")

    out = m.send("cmd 1001 197 1 4")
    o1 = info(out)
    check(o1 and o1["manager"] == 2 and o1["lots"] == 9 and o1["boxes"] == 1 and o1["free"] == 0,
          f"B: first open (free) {o1 and {k: o1[k] for k in ('manager','lots','boxes','free')}}")
    check(o1 and o1["B"][0][1] == 4, "B: opened box is chest 4")
    won = {}
    if o1:
        lot, box, iid, cnt = o1["B"][0]
        check(lot not in [e[0] for e in o1["L"]], "B: won prize left the LOT list")
        won[iid] = won.get(iid, 0) + cnt
    b = bag(m, 1001)
    check(b.get(KEY) == 48, "B: first chest is free")
    check(all(b.get(i) == c for i, c in won.items()), f"B: prize is in the bag {won} {b}")

    out = m.send("cmd 1001 197 1 4")
    again = info(out)
    check(again and again["lots"] == 9 and again["boxes"] == 1, "B: re-opening an open chest only refreshes")
    check(bag(m, 1001).get(KEY) == 48, "B: re-open costs nothing")

    out = m.send("cmd 1001 197 1 7")
    o2 = info(out)
    check(o2 and o2["lots"] == 8 and o2["boxes"] == 2 and [x[1] for x in o2["B"]] == [4, 7], "B: second open, boxes in open order")
    check(bag(m, 1001).get(KEY) == 43, "B: second chest costs 5 keys")
    if o2:
        won[o2["B"][1][2]] = won.get(o2["B"][1][2], 0) + o2["B"][1][3]

    m.send(f"take 1001 {KEY} 40")  # 3 left
    out = m.send("cmd 1001 197 1 1")
    check("ERRMSG 11" in out, "B: not enough keys -> error 11")
    r = info(out)
    check(r and r["lots"] == 8 and r["boxes"] == 2, "B: board unchanged after refusal")
    check(bag(m, 1001).get(KEY) == 3, "B: keys untouched after refusal")

    m.send(f"give 1001 {KEY} 10000")
    last = None
    for pos in [0, 1, 2, 3, 5, 6, 8, 9]:
        last = info(m.send(f"cmd 1001 197 1 {pos}"))
        if last:
            e = last["B"][-1]
            won[e[2]] = won.get(e[2], 0) + e[3]
    check(last and last["lots"] == 0 and last["boxes"] == 10, "B: all 10 chests opened")
    check(bag(m, 1001).get(KEY) == 3 + 10000 - sum(COSTS[2:]), f"B: chest costs follow the table ({bag(m,1001).get(KEY)})")
    b = bag(m, 1001)
    check(all(b.get(i, 0) >= c for i, c in won.items()), "B: every prize reached the bag")
    out = m.send("cmd 1001 197 1 0")
    r = info(out)
    check(r and r["boxes"] == 10 and r["lots"] == 0, "B: open after the board is done only refreshes")
    out = m.send("cmd 1001 197 3 0")
    s2 = info(out)
    check(s2 and s2["manager"] == 1 and s2["lots"] == 10 and s2["boxes"] == 0 and s2["score"] == 2, "B: new seek starts a new board")

    # --- R. relog: the first seek of a login only brings the board back -----
    write_conf(conf, base_conf(off, syms, state, extra="allow_roles = 1001 1003"))
    m.send(f"give 1003 {KEY} 20")
    m.send("cmd 1003 197 0 0")
    s1 = info(m.send("cmd 1003 197 3 0"))
    check(bag(m, 1003).get(KEY) == 18, "R: seek after the window opened is paid")
    m.send("relog 1003 0")
    r1 = info(m.send("cmd 1003 197 3 0"))
    check(bag(m, 1003).get(KEY) == 18, "R: first seek after relog takes no keys")
    check(r1 and s1 and sorted(r1["L"]) == sorted(s1["L"]), "R: first seek after relog resends the same board")
    r2 = info(m.send("cmd 1003 197 3 0"))
    check(bag(m, 1003).get(KEY) == 16, "R: second seek in the same login is paid")
    check(r2 and r2["manager"] == 1 and r2["lots"] == 10, "R: second seek lays out a new board")
    m.send("relog 1003 0")
    m.send("cmd 1003 197 0 0")
    m.send("cmd 1003 197 3 0")
    check(bag(m, 1003).get(KEY) == 14, "R: after relog, a seek that follows a window refresh is paid")
    write_conf(conf, base_conf(off, syms, state, extra="allow_roles = 1001 1003\nseek.clear = empty"))
    out = m.send("cmd 1003 197 3 0")
    infos = [l for l in out if l.startswith("INFO3")]
    check(len(infos) == 2, f"R: seek.clear sends two boards ({len(infos)})")
    first = info(out[:out.index(infos[1])]) if len(infos) == 2 else None
    last = info(out[out.index(infos[1]):]) if len(infos) == 2 else None
    check(first and first["manager"] == 0 and first["lots"] == 0 and first["boxes"] == 0, f"R: first is an empty board {first}")
    check(last and last["manager"] == 1 and last["lots"] == 10, "R: then the new board")

    # --- C. direct call path ----------------------------------------------
    out = m.send("cmd 1001 198 1 0")
    c1 = info(out)
    check(c1 and c1["manager"] == 2 and c1["boxes"] == 1, "C: direct-call path is hooked too")
    check(not any(l.startswith("Lottery_Notice1") for l in out), "C: original not called")

    # --- D. pass-through ----------------------------------------------------
    out = m.send("cmd 1001 197 2 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1001 2 0") for l in out), "D: type 2 (withdraw) goes to gs")
    out = m.send("cmd 1002 197 3 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1002 3 0") for l in out) and info(out) is None, "D: role not in allow_roles goes to gs")

    # --- E. bag full --------------------------------------------------------
    keys = bag(m, 1001)[KEY]
    m.send("full 1001 1")
    out = m.send("cmd 1001 197 1 5")
    e1 = info(out)
    check("ERRMSG 12" in out and e1 and e1["boxes"] == 1, "E: bag full -> error 12, chest stays closed")
    check(bag(m, 1001)[KEY] == keys, "E: nothing taken when the bag is full")
    m.send("full 1001 0")

    # --- F. safety lock -----------------------------------------------------
    m.send("lock 1001 1")
    out = m.send("cmd 1001 197 3 0")
    check("ERRMSG 108" in out and info(out) is None, "F: safety lock -> error 108")
    check(bag(m, 1001)[KEY] == keys, "F: no keys taken while locked")
    m.send("lock 1001 0")

    # --- G. Aurum seek ------------------------------------------------------
    write_conf(conf, base_conf(off, syms, state, extra="aurum_param = 1"))
    out = m.send("cmd 1001 197 3 1")
    check("ERRMSG 13" in out, "G: Aurum seek refused below 20 Aurum")
    check(bag(m, 1001)[KEY] == keys, "G: refused Aurum seek takes no keys")
    for _ in range(18):
        m.send("cmd 1001 197 3 0")
    sc = info(m.send("cmd 1001 197 0 0"))
    check(sc and sc["score"] == 20, f"G: 20 Aurum after 20 key seeks ({sc and sc['score']})")
    keys = bag(m, 1001)[KEY]
    a = info(m.send("cmd 1001 197 3 1"))
    check(a and a["score"] == 0 and a["free"] == 2 and a["lots"] == 10, "G: Aurum seek: -20 Aurum, 2 free chests")
    check(bag(m, 1001)[KEY] == keys - 2, "G: Aurum seek also takes 2 keys")
    m.send("cmd 1001 197 1 0")
    m.send("cmd 1001 197 1 1")
    check(bag(m, 1001)[KEY] == keys - 2, "G: two free opens")
    m.send("cmd 1001 197 1 2")
    check(bag(m, 1001)[KEY] == keys - 2 - 12, "G: third open costs 12")

    # --- H. raw packet ------------------------------------------------------
    write_conf(conf, base_conf(off, syms, state, extra=f"""
info.send = raw
call.raw = {syms['raw']} : csidx, roleid, cssid, buf, len
"""))
    out = m.send("cmd 1001 197 0 0")
    raw = [l for l in out if l.startswith("RAW")]
    check(len(raw) == 1, "H: raw packet sent")
    if raw:
        f = dict(kv.split("=") for kv in raw[0].split()[1:])
        pkt = bytes.fromhex(f["hex"])
        check(f["lid"] == "3" and f["uid"] == "1001" and f["sid"] == "7001", "H: link index / role / session passed")
        op = int.from_bytes(pkt[0:2], "little")
        mgr = pkt[2]
        nl = int.from_bytes(pkt[11:15], "little")
        nb = int.from_bytes(pkt[15:19], "little")
        check(op == 434 and mgr == 2 and nl == 7 and nb == 3, f"H: header fields ({op}, {mgr}, {nl}, {nb})")
        check(len(pkt) == 19 + 9 * nl + 13 * nb, f"H: packet size {len(pkt)}")

    # --- I. probe mode (no items move, state untouched) ---------------------
    keys = bag(m, 1001)[KEY]
    write_conf(conf, base_conf(off, syms, state, mode="probe", extra="probe.fill = 3\nprobe.manager = 1"))
    p = info(m.send("cmd 1001 197 3 0"))
    check(p and p["manager"] == 1 and p["lots"] == 7 and p["boxes"] == 3, "I: probe sends a test board")
    check(bag(m, 1001)[KEY] == keys, "I: probe moves no items")
    write_conf(conf, base_conf(off, syms, state))
    r = info(m.send("cmd 1001 197 0 0"))
    check(r and r["lots"] == 7 and r["boxes"] == 3 and r["manager"] == 2, "I: real board unchanged by probe")

    # --- J. deliver to the Treasure Warehouse + gs withdraw ------------------
    write_conf(conf, base_conf(off, syms, state, extra=f"""
deliver = lotadd
call.lotadd = {syms['lotadd']} : imp, id, count
ok.lotadd = true
call.inv = {syms['inv']} : runner
"""))
    m.send("cmd 1001 197 3 0")
    out = m.send("cmd 1001 197 1 3")
    o = info(out)
    inv = [l for l in out if l.startswith("LOTINV")]
    check(o and inv and str(o["B"][0][2]) in inv[-1], "J: prize went to the warehouse and the list was sent")
    before = bag(m, 1001)
    out = m.send("cmd 1001 197 2 0")
    after = bag(m, 1001)
    check(any(l.startswith("ORIG withdraw") for l in out) and sum(after.values()) > sum(before.values()),
          "J: gs's own withdraw moves it to the bag")

    # --- K. call chain (make item, then give it) + on.open event -------------
    write_conf(conf, base_conf(off, syms, state, extra=f"""
call.aux1 = {syms['make']} : id, count
ok.aux1 = nonzero
call.obtain = {syms['obtaindata']} : imp, ret.aux1
pre.obtain = aux1
call.aux2 = {syms['inv']} : runner
on.open = aux2
"""))
    before = bag(m, 1001)
    out = m.send("cmd 1001 197 1 6")
    o = info(out)
    after = bag(m, 1001)
    check(o and o["B"][-1][1] == 6, "K: chest 6 opened through the call chain")
    if o:
        iid, cnt = o["B"][-1][2], o["B"][-1][3]
        check(after.get(iid, 0) == before.get(iid, 0) + cnt, "K: chained give put the prize in the bag")
    check(any(l.startswith("LOTINV") for l in out), "K: on.open extra call ran")
    board_before_restart = info(m.send("cmd 1001 197 0 0"))
    m.close()

    # --- L. state survives a restart ----------------------------------------
    m = Mock(exe, conf, log)
    r = info(m.send("cmd 1001 197 0 0"))
    check(r and board_before_restart and r["L"] == board_before_restart["L"] and r["B"] == board_before_restart["B"],
          "L: board restored from the state file after restart")

    # --- P. wrong offset does not crash --------------------------------------
    bad = base_conf(off, syms, state).replace(f"off.roleid = {off['roleid']}", "off.roleid = 0x7ffffff0")
    bad = bad.replace(f"off.parent = {off['parent']}", "off.parent = 0x7ffffff0")
    write_conf(conf, bad)
    out = m.send("cmd 1001 197 3 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1001 3 0") for l in out), "P: bad offsets -> passed to gs, no crash")
    check("no role id" in open(log).read(), "P: bad offsets are logged")
    m.close()

    # --- N. dry run -----------------------------------------------------------
    write_conf(conf, base_conf(off, syms, state, extra="hook.patch = no"))
    m = Mock(exe, conf, log)
    out = m.send("cmd 1001 197 3 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1001 3 0") for l in out), "N: dry run patches nothing")
    check("would patch" in open(log).read(), "N: dry run lists the call sites")
    m.close()

    # --- O. other programs are left alone -------------------------------------
    other = os.path.join(work, "notgs")
    shutil.copy(exe, other)
    open(log, "w").close()
    write_conf(conf, base_conf(off, syms, state))
    m = Mock(other, conf, log)
    out = m.send("cmd 1001 197 3 0")
    check(any(l.startswith("Lottery_Notice1 roleid=1001 3 0") for l in out) and open(log).read() == "",
          "O: library does nothing outside a program named gs")
    m.close()

    # --- Q. command-mode hook (plan B: hook CommandHandler, not Lottery_Notice1) ---
    cmd_sym = find_sym(t, "gplayer_controller::CommandHandler(")
    open(log, "w").close()
    write_conf(conf, base_conf(off, syms, state, extra=f"""
hook.mode = command
cmd.id = 197
cmd.type_off = 2
cmd.param_off = 6
off.ctrl_imp = {off['ctrl_imp']}
"""))
    m = Mock(exe, conf, log)
    m.send(f"give 1001 {KEY} 50")
    s = info(m.send("cmd 1001 197 3 0"))
    check(s and s["manager"] == 1 and s["lots"] == 10, "Q: command mode seek shows a board")
    check(bag(m, 1001).get(KEY) == 48, "Q: command mode seek took 2 keys")
    o = info(m.send("cmd 1001 197 1 4"))
    check(o and o["boxes"] == 1, "Q: command mode open works")
    out = m.send("cmd 1001 236 1 0")  # a different command id must pass straight through
    check(any(l.startswith("Lottery_Notice2") for l in out), "Q: other commands pass through in command mode")
    out = m.send("cmd 1002 197 3 0")  # role not allowed -> gs sees the original command
    check(any(l.startswith("Lottery_Notice1 roleid=1002") for l in out), "Q: disallowed role falls through to gs")
    hl = open(log).read()
    check("hook mode command" in hl and "CommandHandler" in hl, "Q: command hook installed on CommandHandler")
    m.close()

    # --- S. command recorder (notice1 mode + cmd.log) ---------------------------
    open(log, "w").close()
    write_conf(conf, base_conf(off, syms, state, extra=f"""
cmd.log = 197
off.ctrl_imp = {off['ctrl_imp']}
"""))
    m = Mock(exe, conf, log)
    m.send(f"give 1001 {KEY} 50")
    s = info(m.send("cmd 1001 197 3 0"))
    check(s and s["manager"] == 1 and s["lots"] == 10, "S: seek still works with the recorder on")
    m.send("cmd 1001 197 5 22")
    hl = open(log).read()
    check("command recorder for command 197 or as set: " in hl and "0 vtable slot" not in hl, "S: recorder installed")
    check("client command 197 from role 1001: type 5" in hl, "S: unknown type 5 recorded with the role id")
    check("type 3," not in hl, "S: normal types are not recorded unless cmd.log_all")
    m.close()
    open(log, "w").close()
    write_conf(conf, base_conf(off, syms, state, extra=f"""
cmd.log = any
off.ctrl_imp = {off['ctrl_imp']}
"""))
    m = Mock(exe, conf, log)
    m.send("cmd 1001 236 1 0")
    for _ in range(5):
        m.send("cmd 1001 236 1 0")
    hl = open(log).read()
    check("command recorder for command any: " in hl, "S: recorder installed for any command")
    check(hl.count("client command 236 from role 1001") == 3, f"S: any-mode records other ids, max 3 per 10 s ({hl.count('client command 236')})")
    m.close()


variants = [(d, os.path.join(OUT, d, "gs")) for d in sorted(os.listdir(OUT))
            if os.path.isfile(os.path.join(OUT, d, "gs"))]
for name, exe in variants:
    run_variant(name, exe)
print(f"\n{passes} checks passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
