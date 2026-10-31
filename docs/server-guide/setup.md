# Setup

Getting the 1.7.3 package running on a modern Linux VM, letting the client in, accounts, pwAdmin, rates, logs and basic security.

**On this page**
- [Setting up the server package on a modern Linux](#setting-up-the-server-package-on-a-modern-linux)
- [Client won't connect / stuck on "Connecting to server"](#client-wont-connect--stuck-on-connecting-to-server)
- [Creating accounts](#creating-accounts)
- [pwAdmin: status "Offline", -1 values, "Saving Rates Failed"](#pwadmin-status-offline--1-values-saving-rates-failed)
- [Rates: EXP, spirit, drops and coins](#rates-exp-spirit-drops-and-coins)
- [Log rotation (logs filling the disk)](#log-rotation-logs-filling-the-disk)
- [Security checklist](#security-checklist)
- [Small notes](#small-notes)

## Setting up the server package on a modern Linux
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

## Client won't connect / stuck on "Connecting to server"
✅ *[tested]*

**Symptom:** you start `elementclient.exe game:cpw` and get the official launcher panel stuck on "Connecting to server…". It is trying to reach the dead official patch site.

**Fix:** the 1.7.3 client needs `startbypatcher` (and the packaged `eStart.bat` also passes `nocheck`). From the `element` folder:
```
elementclient.exe game:cpw nocheck startbypatcher
```
Add `console:1` if you want the in-game console (Shift+~; see [debug console](troubleshooting.md#debug-console-commands)).

**Server address:** `patcher\server\serverlist.txt` is **UTF-16LE with a BOM, tab-separated**. Don't edit it in Notepad. PowerShell:
```powershell
$f="...\PWI_en\patcher\server\serverlist.txt"
$t=Get-Content $f -Raw -Encoding Unicode
$t=$t.Replace("OLD.IP.ADDR","YOUR.SERVER.IP")
Set-Content $f $t -Encoding Unicode -NoNewline
```
The line format is `Name<TAB>29000:IP<TAB>10`.

Also check: client `elements.data` and `tasks.data` must be byte-identical to the server's (`md5sum` / `Get-FileHash`).

## Creating accounts
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

## pwAdmin: status "Offline", -1 values, "Saving Rates Failed"
✅ *[tested]*

The package ships pwAdmin in `/opt/pwadmin` (Tomcat 7 with its own Java 7, port 8080; `server pwAdmin start|stop`). It holds two web apps: `pwadmin` (`http://<vm>:8080/pwadmin/`: accounts, characters, server configuration, server control) and `iweb` (`http://<vm>:8080/iweb/`, an official-style GM web).

**Symptom:** the pages load, but the server shows Offline, numbers show `-1`, and saving rates gives "Saving Rates Failed".

**Cause** *[tested]*: both apps share one protocol library, and iweb's start-up code reads **`/etc/iweb.conf`** first. That file doesn't exist, so the bundled `iweb/WEB-INF/classes/iweb.conf` is used, and it points to the original builder's network (`172.16.2.109`) and GameDB port `39400`. So nothing ever connects to gdeliveryd.

**Fix:**
```bash
C=/opt/pwadmin/webapps/iweb/WEB-INF/classes/iweb.conf
sudo cp $C $C.bak_orig
sudo sed -i 's/172\.16\.2\.109/127.0.0.1/g; s/39400/29400/g' $C    # the file uses tabs, so match the numbers only
grep -n "127.0.0.1\|29400" $C
sudo cp $C /etc/iweb.conf
sudo server pwAdmin stop; sleep 5; sudo server pwAdmin start
sleep 60; sudo ss -tnp | grep java | grep -E ':29100|:29400'   # Java should now hold both connections
```
After that the status is Online and rates save. A `NullPointerException in protocol.JioConfig` at start-up is still logged and is harmless. iweb's own account list says "Failed to connect to MySQL" (its database login is separate); use pwAdmin for accounts.

**Avoid** iweb's *Server Settings* "Change" button: its checkboxes are pre-ticked, and pressing it turns the trade / auction / mail / faction **bans on**. Use pwAdmin's *Server Configuration* page instead.

**Lock it down:** `pwadmin/AA/cmd.jsp` (broadcasts, NPC generator, rates) has **no login check**. Never expose port 8080 beyond your own PC. See [Security checklist](#security-checklist).

## Rates: EXP, spirit, drops and coins
✅ *[tested in game; mechanism read from gs and gdeliveryd]*

**What doesn't work:** `exp_bonus` / `sp_bonus` in `ptemplate.conf` are read but have no effect (the gs function that should apply them is empty). The `[MESMD_ADJUST]` level table didn't change solo kills either. `money_bonus` does work (coins x (1 + value)). *[code + tested]*

**What works:** the server's runtime switches, set through pwAdmin's *Server Configuration* page (once [pwAdmin is fixed](#pwadmin-status-offline--1-values-saving-rates-failed)):
- EXP multiplier 1-10. It multiplies spirit too.
- Double drops (drop table rolled twice) and double coins.
- Also there: no-trade / no-mail / no-auction / no-faction switches and PvP.
- "Lambda" is stored by gdeliveryd but gs never reads it; leave it 0.

When on, the client's server list shows it under Event Info (e.g. "2x Exp, 2x Drop").

**Trap:** these switches live in gdeliveryd's memory only. **Every restart resets them**, including the nightly backup. `scripts/pw_rates_apply.sh` re-applies your standing values after each start:
```bash
sudo install -m 755 pw_rates_apply.sh /usr/local/bin/     # edit EXP= and DOUBLE= at the top first
sudo cp /opt/server /opt/server.bak_rates
grep -n "pwAdmin #2 STARTED" /opt/server                  # find the line after which pwAdmin is up
# add this line right after it (in the start section):
#   /usr/local/bin/pw_rates_apply.sh &
sudo server restart; sleep 240; tail -2 /var/log/pw_rates.log
```
It waits until gs runs and pwAdmin is linked to gdeliveryd, then calls the same pwAdmin page the SAVE button uses. For a one-off event, change the rate in pwAdmin; the next restart goes back to the script's values.

*Data route (works, but needs a client update):* monster records in `elements.data` list 39 hold EXP at +588, spirit at +592 and the number of drop rolls at +1284 ([layout](../layouts/elements/README.md)). Doubling those stacks with the switches.

## Log rotation (logs filling the disk)
✅ *[tested]*

Nothing rotates `/opt/logs`, and `world2.*` / `statinfom` grow by hundreds of MB. `scripts/logrotate/pw-logs` keeps 7 days (30 for the cash and chat logs), compressed, max 100 MB per file before a forced rotate. It uses `copytruncate` because the daemons keep their log files open.
```bash
sudo install -m 644 scripts/logrotate/pw-logs /etc/logrotate.d/pw-logs
sudo logrotate -d /etc/logrotate.d/pw-logs 2>&1 | tail -20     # dry run: check every file is matched once
sudo logrotate -f /etc/logrotate.d/pw-logs && ls -la /opt/logs | head
```
Don't add `delaycompress`: with `maxsize` it leaves one uncompressed copy of the biggest log (we got a 736 MB `.1` file). Logrotate runs daily from its own timer; add `maxsize` checks more often by running it hourly if your logs grow fast.

## Security checklist
- **Database password:** the package uses MariaDB `root`/`root`. Change it before anyone else can reach the VM, and keep MariaDB on localhost. Places that hold the login: `/opt/authd/table.xml` (authd), pwAdmin's `webapps/pwadmin/WEB-INF/.pwadminconf.jsp` plus a few add-on pages (clear `pwadmin/work/Catalina` afterwards so the pages recompile), and your own scripts. A separate user with rights on `wm` only works fine for authd. *[tested]*
- **`chmod 777 -R /opt`:** the stock `/opt/server` makes everything world-writable on every start. Comment that line out and run `sudo chmod -R go-w /opt`; all daemons run as root, so nothing breaks. *[tested]*
- **Remote friends:** a mesh VPN such as Tailscale inside the VM works well; only the game port (29000) and your patch server need to be reachable. Block everything else on the VPN interface.
- **pwAdmin over the VPN:** at the very least block 8080 (pwAdmin), 5001 and 8005 (Tomcat) on the VPN interface. `scripts/nftables/pwadmin-lock.nft` + `scripts/systemd/pwadmin-lock.service` do that for `tailscale0`; the host-only address keeps working:
```bash
sudo install -m 644 scripts/nftables/pwadmin-lock.nft /etc/pwadmin-lock.nft
sudo install -m 644 scripts/systemd/pwadmin-lock.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pwadmin-lock
sudo nft list table inet pwadmin_lock
```
  Test from a friend's PC (should time out) and from yours over the host-only address (should load).

## Small notes
- **Class mask:** `allow_login_class_mask = 32767` in `ptemplate.conf` allows all 15 classes.
- **Friends can't connect but it works for you (VM lost internet):** after restoring a *running* VirtualBox snapshot, the VM's NAT adapter can lose its IPv4 address while the host-only adapter keeps working. Your own client still connects; Tailscale on the VM goes `offline` and friends' launchers time out. Check with `ping -c2 1.1.1.1` and `ip route | grep default` on the VM. Fix: in the running VM window, Devices > Network > untick and re-tick the NAT adapter, then `sudo networkctl reconfigure <nat-interface>`; or do a cold power-off and start. Then `sudo systemctl restart tailscaled`. *[tested]*
- **Testing client data changes:** a launcher that auto-updates (like [ours](../../tools/launcher/README.md)) puts its own copy of `elements.data` back. Start the game with `eStart.bat` / `elementclient.exe game:cpw nocheck startbypatcher` while testing, or the test runs on the old file. *[tested the hard way]*

---
[Back to the guide index](README.md)
