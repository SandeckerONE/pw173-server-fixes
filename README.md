# Perfect World 1.7.3 (e344 / t187) server: known problems and fixes

A living fix list for people running the community **PWI 1.7.3 (elements v344, tasks v187)** server package on their own Linux VM, with the matching English **PWI_en_1.7.3 (e344_t187)** client. Every fix here was found on a real home server and tested in game unless it says otherwise.

**Status tags:** ✅ fixed and tested · 🟡 workaround · 🔧 in progress · ❌ not fixable yet (code missing from the server package)

**Evidence tags:** *[tested]* confirmed in game or by command output · *[code]* read from the server programs (they ship with debug symbols) · *[inferred]* best reading, not proven

**In this repository:** this guide (`README.md`), the Treasures add-on (`treasure_hook/`) and helper scripts (`scripts/`: login check + watchdog, nightly backup).

> Scope and etiquette: this guide contains **no game or server files**, only instructions and small scripts written for it. Get the server package and client from wherever you got them; this only helps you make them work. Run everything inside a VM, take a snapshot before every change, and test risky changes on a copy of the VM first.

---

## Contents
1. [Setting up the server package on a modern Linux](#1-setting-up-the-server-package-on-a-modern-linux)
2. [Client won't connect / stuck on "Connecting to server"](#2-client-wont-connect--stuck-on-connecting-to-server)
3. [Creating accounts (and why the obvious way fails)](#3-creating-accounts)
4. [Boutique gold doesn't arrive (`ret=-8`)](#4-boutique-gold-doesnt-arrive-ret-8)
5. [GACD (anti-cheat) keeps dying](#5-gacd-anti-cheat-keeps-dying)
6. [Severe lag, login bounces, followers not updating](#6-severe-lag-login-bounces-followers-not-updating)
7. [Instances that won't open ("Can't enter instance")](#7-instances-that-wont-open)
8. [Every player can Ctrl+click teleport](#8-every-player-can-ctrlclick-teleport)
9. [Character export/import (and how it can corrupt your database)](#9-character-exportimport)
10. [Debug console commands (careful)](#10-debug-console-commands)
11. [Palette of Fortune: what works and what doesn't](#11-palette-of-fortune)
12. [Treasures / Lucky Key system](#12-treasures--lucky-key-system)
13. [Faction Safe and faction Loyalty](#13-faction-safe-and-faction-loyalty)
14. [Small notes](#14-small-notes)
15. [All logins suddenly refused (authd loses the database)](#15-all-logins-suddenly-refused)
16. [Items can't be dropped on the ground](#16-items-cant-be-dropped-on-the-ground)
17. [Nightly backup](#17-nightly-backup)

---

## 1. Setting up the server package on a modern Linux
✅ *[tested on Ubuntu Server 26.04, VirtualBox, 8 vCPU / 24 GB RAM]*

The package expects `/opt/{authd,gacd,gamed,gamedbd,gdeliveryd,gfactiond,glinkd,logservice,uniquenamed,...}`, a control script `/opt/server` (link it to `/sbin/server`), a map list `/opt/maps`, and a MariaDB database named **`wm`** (not `pw`).

**32-bit libraries.** The server programs are 32-bit and old. Enable i386 and install what your distro still has:
```bash
sudo dpkg --add-architecture i386 && sudo apt update
sudo apt install -y libc6:i386 zlib1g:i386 liblzma5:i386
```
Some libraries no longer exist in current distros and must be copied from a system that has them (for example the Debian 12 VM the package came on), into e.g. `/usr/local/lib/pw32/`, then registered:
- `libstdc++.so.5`, `libpcre.so.0`, `libtask.so`, `libxml2.so.2`
- `libicuuc.so.72` and `libicudata.so.72` (ICU 72; needed by gacd)
- `libcrypto.so.4`: on the source system this name is a link to an OpenSSL library; copy what it points to and keep the `.so.4` name. Programs look it up by file name, so also link it into a default path: `sudo ln -s /usr/local/lib/pw32/libcrypto.so.4 /usr/lib/i386-linux-gnu/libcrypto.so.4`
```bash
echo /usr/local/lib/pw32 | sudo tee /etc/ld.so.conf.d/pw32.conf && sudo ldconfig
for b in /opt/*/[a-z]*d /opt/gamed/gs; do echo "== $b"; ldd "$b" 2>&1 | grep "not found"; done   # should print no "not found"
```
**Host names.** The configs use internal names. Add them to `/etc/hosts`:
```
127.0.0.1 manager aumanager auth audb link1 link2 game1 game2 game3 game4 delivery database backup gmserver
```
**Database.** Import the package's `wm` dump. If you set a MariaDB root password, plain `sudo mysql` stops working and every tool must use the password (control script, authd config, your own scripts).

Check: `sudo server start`, then `sudo server status` should show every daemon `[UP]` and the game port listening: `sudo ss -ltnp | grep 29000`.

## 2. Client won't connect / stuck on "Connecting to server"
✅ *[tested]*

**Symptom:** you start `elementclient.exe game:cpw` and get the official launcher panel stuck on "Connecting to server…". It is trying to reach the dead official patch site.

**Fix:** the 1.7.3 client needs `startbypatcher` (and the packaged `eStart.bat` also passes `nocheck`). From the `element` folder:
```
elementclient.exe game:cpw nocheck startbypatcher
```
Add `console:1` if you want the in-game console (Shift+~; see section 10).

**Server address:** `patcher\server\serverlist.txt` is **UTF-16LE with a BOM, tab-separated**. Don't edit it in Notepad. PowerShell:
```powershell
$f="...\PWI_en\patcher\server\serverlist.txt"
$t=Get-Content $f -Raw -Encoding Unicode
$t=$t.Replace("OLD.IP.ADDR","YOUR.SERVER.IP")
Set-Content $f $t -Encoding Unicode -NoNewline
```
The line format is `Name<TAB>29000:IP<TAB>10`.

Also check: client `elements.data` and `tasks.data` must be byte-identical to the server's (`md5sum` / `Get-FileHash`).

## 3. Creating accounts
✅ *[tested]*

The `adduser` stored procedure takes **17 arguments**, and this package uses password type 2: **`base64(md5(lowercase(username) + password))`**, passed as a quoted string, not the hex form older guides use.

Two traps:
- `ERROR 1366`: you passed the old hex form; the `passwd` columns are text here.
- `ERROR 1292 Incorrect datetime value: '0' for column birthday`: the 15th argument (`birthday1`) must be a real date, e.g. `'1990-01-01'`.

Working call (MariaDB, database `wm`):
```sql
CALL adduser('name', 'HASH', '0','0','','0.0.0.0','name@example.com',
             '0','0','0','0','0','0', 0, '1990-01-01', '0', 'HASH');
```
Make the hash with Python:
```python
import hashlib, base64
print(base64.b64encode(hashlib.md5((user.lower() + password).encode()).digest()).decode())
```
GM rights: `CALL addGM(<account id>, 1);`. New IDs go 1024, 1040, 1056… (steps of 16).

## 4. Boutique gold doesn't arrive (`ret=-8`)
✅ *[tested; cause read from the `usecash` procedure]*

**Symptom:** you credit cash with the control script's `server cubi <accountID> <amount>` (100 cash = 1 gold) and the authd log repeats `UseCashTimerTask: ... ret=-8`.

**Cause:** `usecash` needs the account's row in the `point` table, and that row is only created on the account's **first login**.

**Fix:** none needed. Have the player log in once; the gold lands a few minutes later (relog if the Boutique still shows the old balance). Don't re-queue the cash in the meantime, or it may be credited twice.

## 5. GACD (anti-cheat) keeps dying
✅ *[tested over several days]*

**Symptom:** `server status` shows `[DOWN] GACD` some time after start; gdeliveryd logs `connect to GACD failed!`; `dmesg` shows `gacd[...]: segfault at X ip X ... error 15` with **the same address twice**.

**Cause** *[inferred from the crash signature]*: the old 32-bit gacd jumps into its own data memory, which modern kernels block (no-execute protection).

**Fix:** start gacd with "read implies exec" for that one process. In `/opt/server`, change the gacd start line:
```bash
sudo cp /opt/server /opt/server.bak_gacd
sudo sed -i 's|^\(\s*\)\./gacd gamesys\.conf|\1setarch i386 -X ./gacd gamesys.conf|' /opt/server
grep -n "gacd gamesys.conf" /opt/server      # should show: setarch i386 -X ./gacd gamesys.conf
sudo server restart
```

## 6. Severe lag, login bounces, followers not updating
✅ *[tested]*

**Symptom:** logging into the world sometimes disconnects (relog works), characters on follow behave as if the leader isn't updating, general rubber-banding.

**Cause:** every `yes` line in `/opt/maps` is a separate map process that ticks even when empty. With ~93 maps on 4 vCPUs: load average ~260, 85% "system" CPU, ~240,000 context switches per second, and the main world (gs01) got under 10% of a core. Each empty map costs about 4% CPU and ~100 MB RAM.

**Fix:** run only the maps your players use, and give the VM enough cores.
```bash
sudo cp /opt/maps /opt/maps.bak
KEEP="gs01 is61 is62 is02 is05 is06 is07 is08 is09 is10 is11"     # world + level 1-59 dungeons; edit to taste
sudo awk -F, -v OFS=, -v keep="$KEEP" 'BEGIN{n=split(keep,k," ");for(i=1;i<=n;i++)K[k[i]]=1} {$1=($2 in K)?"yes":"no"; print}' /opt/maps > /tmp/maps.new && sudo cp /tmp/maps.new /opt/maps
sudo server restart
uptime; vmstat 2 3      # load should be in single digits, "sy" low
```
Result here: load ~7 on 8 cores, 94% idle. Add maps back as players level. `is77` and `ms01` never start (cross-server maps; leave them off).

## 7. Instances that won't open
✅ *[tested]*

The package ships with only `gs01` and `is61` set to `yes` in `/opt/maps`, so most dungeons give "Can't enter instance". Set the ones you need to `yes` (see section 6 for the CPU cost) and restart. Secret Passage is `is02`, Hall of Deception `is08`.

## 8. Every player can Ctrl+click teleport
✅ *[tested; mechanism read from gs]*

**Cause:** `/opt/gamed/ptemplate.conf` ships with `debug_command_mode = active`. That turns on gs's debug command handler, which has **no GM check**: anyone can Ctrl+click the map to teleport and use other test commands (including item and cash ones). gs treats only the exact value `active` as on.

**Fix:**
```bash
sudo sed -i 's/^debug_command_mode *= *active/debug_command_mode = inactive/' /opt/gamed/ptemplate.conf
sudo server restart
```
Real GM accounts keep their GM commands; those go through a separate, checked handler.

## 9. Character export/import
⚠️ *[tested the hard way]*

The control script's `exportrole <id> <file.xml>` / `importrole <file.xml>` run the gamedbd program **directly on the database files**.

1. **Never run `importrole` while the server is running.** The live gamedbd caches the data, and the second program writing the same files left the character database so that `listrole` segfaulted even after stopping the server. Only a snapshot restore fixed it. Untested whether importing with the server fully stopped is safe; snapshot first either way.
2. **Export/import mismatch:** the export writes `reserved1`…`reserved10` at the end of `<status>`, but import stops reading at `lottery_data` and fails with `error member (reserved1, 0) in GRoleStatus` / `decode roleidfile error.` Delete those ten lines inside `<status>` only (the `reserved` lines in other sections are expected):
```bash
sudo sed -i '/<status>/,/<\/status>/{/<variable name="reserved[0-9]*"/d}' role.xml
```
Prefer the server's own debug commands (section 10) for small character changes.

## 10. Debug console commands
🟡 *[tested]*

Temporarily set `debug_command_mode = active` (section 8), restart, start the client with `console:1`, open the console with **Shift+~**, and send `d_c2scmd <id> <args…>`. Switch it back to `inactive` and restart afterwards, because it opens debug teleport for everyone.

Known IDs (read from gs's DebugCommandHandler):
| Command | Effect |
|---|---|
| `d_c2scmd 10844 <a> <b>` | gives the character `a` Faction Construction points and `b` Faction Contribution points (not Loyalty) *[tested]* |

## 11. Palette of Fortune
✅ the **main draw** (Color Burst, Free-in-a-row, Ticket of Magnificence) works *[tested]*.
- If it does nothing, the character's **Safety Lock** is probably still active (default about one minute after login); gs refuses with error 108. *[code]*
- The highlighted empty box at the top of "Treasure Display" is a legend for the season's special items, not a missing prize. *[inferred from the window]*
- Odds from the data: Legendary 0.00618% per draw, about 1 in 16,200 tickets. Worth knowing when you price tickets.

## 12. Treasures / Lucky Key system
✅ seek / open / warehouse work with the add-on in `treasure_hook/` · ❌ Bulk Seeking and Aurum seek *[code + tested in game]*

**Symptom:** the Treasures window opens and the loot list shows, but "Seek Treasures: 2 Keys" does nothing; no keys are taken and no chests appear.

**Cause:** the client sends `Lottery_Notice1(type, param)` (3 = seek, 1 = open chest n, 0 = window, 2 = withdraw from the Treasure Warehouse). **The 1.7.3 gs only implements type 2.** The loot table (elements.data list 232), costs (list 233) and bonus event (list 234) are loaded but never used. No other program contains the logic. It's not a config or date problem.

**Fix:** the add-on library in [`treasure_hook/`](treasure_hook/) (install steps in its README), loaded beside gs with `LD_PRELOAD` (gs itself is not changed) that answers seek and open:
- Board packet = **opcode 434**, the same layout as the public 1.7.6 source: `u16 434, u8 manager (0 info / 1 new board / 2 chest opened), u32 Aurum, u32 free opens, u32 closed count, u32 opened count`, then closed chests `{u32 id, u32 count, u8 prize}` and opened chests `{u32 id, u32 chest, u32 count, u8 prize}`. Sent raw with gs's `send_ls_msg(gplayer const*, void const*, unsigned)`. *[tested: the 1.7.3 client draws it]*
- Keys: `CheckItemExist` + `RemoveItems(id, count, 11, true)` (Lucky Key 56274, 2 per seek; chest costs 0, 5, 12, 30...). Prizes: `AddLotInventory(id, count)` into the Treasure Warehouse, then `GetLotInventory` + `send_lot_inv` to refresh the warehouse list (opcode 433). Withdraw is gs's own. *[tested]*
- **Trap:** the first time the window opens after a login, the client sends type 3, the same as the Seek button, to get its board back. Treat the first seek of each login as "resend the saved board" (tell logins apart by the player's link session id at `gplayer + 0xb0 / 0xb4`), or every relog costs 2 keys and a new board. *[tested]*
- The client itself refuses opens and Aurum seeks you can't afford, and blocks Seek: Aurum below 20 Aurum. Aurum is +1 per board sought. *[tested]*
- Boards are saved per character in a small file, so they survive relogs and restarts. *[tested]*
- **gs must be told "handled":** gs's CommandHandler sends error 3 ("Critical error: invalid action") whenever `Lottery_Notice1` returns false, so a replacement must return true. *[code + tested]*
- The Treasures command is client command **197**. gs accepts only action types 0-3 for it and refuses anything else before `Lottery_Notice1` is called. *[code]*
- **Not working:** *Bulk Seeking Treasure* sends nothing to the server on this client (every client command was recorded during bulk runs; nothing carried the count or ticked items). The client fakes the run locally, so no server-side fix is possible. *Seek Treasures: Aurum* (higher odds for rare items) looks the same and is left out. *[tested]*


## 13. Faction Safe and faction Loyalty
❌ → 🔧 *[code + tested]*

**Symptom:** using the Faction Safe Stone at the Faction Base Manager gives "Service unavailable" and **freezes the character** (no walking, flying or skills) until relog. Faction Loyalty never increases. The Guild Base map running doesn't change it.

**Cause:** the server package has no code for it. gs has no NPC service for faction storage; the storage whitelist data is loaded but never used; gfactiond only handles membership, alliances and faction upgrade; no program stores or changes faction Loyalty. Others report the same on 1.7.3.

**What the client expects** *[code, from the 1.7.3 client]*: the client has the whole Faction Safe (window `Win_GuileStorage`: 3 tabs x 96 slots, per-rank deposit/withdraw ticks, sort, log). Every action is sent as NPC service **115** (client command 37) with a sub-code (0x4, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200). The window is opened and filled by GNET protocol **5882** `FactionStoreHouseList_Re`.

**Why it can't simply be added:** `gs` has no service 115 (that is the "Service unavailable" and the freeze), and **no 1.7.3 server program knows protocol 5882, glinkd included** (glinkd logs `Protocol Unknown` for types it doesn't know). A real fix needs server code for the safe **and** a change to glinkd so 5882 can reach the client.

**Workaround:** a shared "bank" character the faction trades items to. Tell players not to use the Safe Stone. A gs-side "polite decline" for service 115 (so nobody freezes) is possible with the same hook technique as `treasure_hook/`.

## 14. Small notes
- **Class mask:** `allow_login_class_mask = 32767` in `ptemplate.conf` allows all 15 classes.
- **Root `/opt` permissions:** the stock control script runs `chmod 777 -R /opt` on every start; consider removing that once everything works.
- **Database password:** the package uses MariaDB `root`/`root`. Change it before letting anyone else near the VM, and keep the database on localhost only. Places that hold the login on this package: `/opt/authd/table.xml` (authd), pwAdmin's `webapps/pwadmin/WEB-INF/.pwadminconf.jsp` plus a few add-on pages (clear `pwadmin/work/Catalina` afterwards so the pages recompile), and any scripts of your own. A separate game user with rights on `wm` only works fine for authd. *[tested]*
- **`chmod 777 -R /opt`:** the stock `/opt/server` makes everything world-writable on every start. Comment that line out and run `sudo chmod -R go-w /opt`; all daemons run as root, so nothing breaks. *[tested]*
- **Friends can't connect but it works for you (VM lost internet):** after restoring a *running* VirtualBox snapshot, the VM's NAT adapter can lose its IPv4 address while the host-only adapter keeps working. Your own client still connects; Tailscale on the VM goes `offline` ("Unable to connect to the Tailscale coordination server") and friends' launchers time out. Check with `ping -c2 1.1.1.1` and `ip route | grep default` on the VM. Fix: in the running VM window, Devices > Network > untick and re-tick the NAT adapter, then `sudo networkctl reconfigure <nat-interface>`; or do a cold power-off and start. Then `sudo systemctl restart tailscaled`. *[tested]*
- **Remote friends:** a mesh VPN such as Tailscale inside the VM works well; only the game port (29000) needs to be reachable. Block everything else on the VPN interface.


## 15. All logins suddenly refused
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

**Checker + watchdog** (files in [`scripts/`](scripts/)). `pw_authcheck.sh` (read-only) says BROKEN if MariaDB started after authd, or if authd logged database errors since it started:
```bash
#!/bin/bash
# pw_authcheck.sh - is authd healthy? Read-only.
echo "=== authd check $(date '+%F %T') ==="
p=$(pgrep -f authd | head -1)
if [ -z "$p" ]; then echo "VERDICT: BROKEN - authd not running. Fix: sudo server restart"; exit; fi
a=$(date -d "$(ps -o lstart= -p $p)" +%s)
m=$(date -d "$(systemctl show mariadb -p ActiveEnterTimestamp --value)" +%s)
echo "authd started:   $(date -d @$a '+%F %T')"
echo "MariaDB started: $(date -d @$m '+%F %T')"
s=$(date -d @$a '+%F %T')
bad=$(grep -a -E "Connection must be Open|acquireIdPasswd exception" /opt/logs/authd.log | awk -v s="$s" '/^20[0-9][0-9]-/ && substr($0,1,19)>=s' | wc -l)
echo "DB errors since authd started: $bad"
if [ "$m" -gt "$a" ]; then echo "VERDICT: BROKEN - MariaDB restarted after authd. Fix: sudo server restart"
elif [ "$bad" -gt 0 ]; then echo "VERDICT: BROKEN - authd logged DB errors. Fix: sudo server restart"
else echo "VERDICT: OK"; fi
```
Two traps we hit writing it: don't judge by "last error vs last good login" (no logins after a restart looks broken forever), and only count log lines that start with a date (the error's detail lines don't, and slip through a time filter). Watchdog every 5 minutes (`scripts/pw-authwatch.cron`, expects the checker in `/usr/local/bin/`):
```bash
sudo tee /etc/cron.d/pw-authwatch >/dev/null <<'EOF'
*/5 * * * * root [ ! -e /run/pw_backup.running ] && /usr/local/bin/pw_authcheck.sh | grep -q "VERDICT: BROKEN" && { echo "$(date) authd broken, restarting" >> /var/log/pw_authwatch.log; /sbin/server restart >> /var/log/pw_authwatch.log 2>&1; }
EOF
```
`/var/log/pw_authwatch.log` records every restart it does.

## 16. Items can't be dropped on the ground
✅ *[code + tested]*

**Symptom:** dropping an item from the bag does nothing, even for items that are not marked "cannot be dropped", with the Safety Lock off.

**Cause:** in `/opt/gamed/gs.conf` the main world's section has `nothrow` in its `limit =` line. `gplayer_imp::PlayerDropInvItem` refuses every drop on a map with that flag (error 44). The same line holds other per-map rules (`nofly`, `clear-ap`, ...).

**Fix:** remove only the word `nothrow;` from the main world's (`gs01`) `limit =` line, then restart. Instance and battle maps also have it; leave those unless you want drops there.
```bash
sudo cp /opt/gamed/gs.conf /opt/gamed/gs.conf.bak_nothrow
grep -n "^ *limit" /opt/gamed/gs.conf          # find the gs01 section's line
sudo sed -i '<LINE>s/nothrow;//' /opt/gamed/gs.conf   # <LINE> = that line number
sudo server restart
```

## 17. Nightly backup
✅ *[tested]*

`scripts/pw_backup.sh` + `pw-backup.service` + `pw-backup.timer`: at midnight (set your time zone in the timer) it dumps the `wm` database, stops the server for about a minute, archives `/opt/gamedbd` and `/opt/uniquenamed` (characters) and the configs into `/var/backups/pw/<date>/`, starts the server again and keeps the newest 7. Add the one-line guard from `scripts/server-backup-guard.txt` to `/opt/server` so a manual restart can't collide with it (a collision like that left half the daemons dead on another server).

Restore (snapshot first):
```bash
B=/var/backups/pw/<date>
sudo server stop
sudo tar xzf $B/characters.tgz -C /opt
sudo mysql --defaults-extra-file=/root/.pw_db.cnf wm < $B/wm.sql
sudo server start
```

---

*Contributions welcome. If you fix something listed as ❌ or 🔧, open an issue or pull request with what you changed and how you tested it.*
