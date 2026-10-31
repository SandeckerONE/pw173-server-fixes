# Troubleshooting

Everything else: one problem per section, with the fix.

**On this page**
- [Boutique gold doesn't arrive (`ret=-8`)](#boutique-gold-doesnt-arrive-ret-8)
- [Severe lag, login bounces, followers not updating](#severe-lag-login-bounces-followers-not-updating)
- [Instances that won't open](#instances-that-wont-open)
- [Every player can Ctrl+click teleport](#every-player-can-ctrlclick-teleport)
- [Character export/import](#character-exportimport)
- [Debug console commands](#debug-console-commands)
- [Items can't be dropped on the ground](#items-cant-be-dropped-on-the-ground)
- [Forges answer "Invalid service request"](#forges-answer-invalid-service-request)
- [Stray NPCs: floating "ERR", Chinese names, duplicate merchants](#stray-npcs-floating-err-chinese-names-duplicate-merchants)
- [Chinese text in logs and data files](#chinese-text-in-logs-and-data-files)

## Boutique gold doesn't arrive (`ret=-8`)
✅ *[tested; cause read from the `usecash` procedure]*

**Symptom:** you credit cash with the control script's `server cubi <accountID> <amount>` (100 cash = 1 gold) and the authd log repeats `UseCashTimerTask: ... ret=-8`.

**Cause:** `usecash` needs the account's row in the `point` table, and that row is only created on the account's **first login**.

**Fix:** none needed. Have the player log in once; the gold lands a few minutes later (relog if the Boutique still shows the old balance). Don't re-queue the cash in the meantime, or it may be credited twice.

## Severe lag, login bounces, followers not updating
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

## Instances that won't open
✅ *[tested]*

The package ships with only `gs01` and `is61` set to `yes` in `/opt/maps`, so most dungeons give "Can't enter instance". Set the ones you need to `yes` (see [map CPU cost](#severe-lag-login-bounces-followers-not-updating) for the CPU cost) and restart. Secret Passage is `is02`, Hall of Deception `is08`.

## Every player can Ctrl+click teleport
✅ *[tested; mechanism read from gs]*

**Cause:** `/opt/gamed/ptemplate.conf` ships with `debug_command_mode = active`. That turns on gs's debug command handler, which has **no GM check**: anyone can Ctrl+click the map to teleport and use other test commands (including item and cash ones). gs treats only the exact value `active` as on.

**Fix:**
```bash
sudo sed -i 's/^debug_command_mode *= *active/debug_command_mode = inactive/' /opt/gamed/ptemplate.conf
sudo server restart
```
Real GM accounts keep their GM commands; those go through a separate, checked handler.

## Character export/import
⚠️ *[tested the hard way]*

The control script's `exportrole <id> <file.xml>` / `importrole <file.xml>` run the gamedbd program **directly on the database files**.

1. **Never run `importrole` while the server is running.** The live gamedbd caches the data, and the second program writing the same files left the character database so that `listrole` segfaulted even after stopping the server. Only a snapshot restore fixed it. Untested whether importing with the server fully stopped is safe; snapshot first either way.
2. **Export/import mismatch:** the export writes `reserved1`…`reserved10` at the end of `<status>`, but import stops reading at `lottery_data` and fails with `error member (reserved1, 0) in GRoleStatus` / `decode roleidfile error.` Delete those ten lines inside `<status>` only (the `reserved` lines in other sections are expected):
```bash
sudo sed -i '/<status>/,/<\/status>/{/<variable name="reserved[0-9]*"/d}' role.xml
```
Prefer the server's own debug commands ([debug console](#debug-console-commands)) for small character changes.

## Debug console commands
🟡 *[tested]*

Temporarily set `debug_command_mode = active` ([Ctrl+click teleport](#every-player-can-ctrlclick-teleport)), restart, start the client with `console:1`, open the console with **Shift+~**, and send `d_c2scmd <id> <args…>`. Switch it back to `inactive` and restart afterwards, because it opens debug teleport for everyone.

Known IDs (read from gs's DebugCommandHandler):
| Command | Effect |
|---|---|
| `d_c2scmd 10844 <a> <b>` | gives the character `a` Faction Construction points and `b` Faction Contribution points (not Loyalty) *[tested]* |

## Items can't be dropped on the ground
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

## Forges answer "Invalid service request"
✅ *[tested in game]*

**Symptom:** some crafting NPCs refuse every craft with "Invalid service request" (e.g. Nature Forge: Tomes, Aerogear Forge), while others (e.g. Forge: Item Exchange) work. `gs_main.log` shows nothing useful.

**Cause** *[tested]*: each crafting service in `elements.data` (list 55) has a **production type** at +72. This gs doesn't serve type 1. The client builds its request from its own `elements.data`, so **both** the server's and the client's file must change.

**Fix:** set the 16 type-1 services to type 0 with [`tools/utility_scripts/forge_type_fix.py`](../../tools/utility_scripts/README.md), on the server and the client file, then restart the server and update the clients. Test without the auto-updating launcher (see [Small notes](setup.md#small-notes)).

Ruled out on the way: the recipes' flag at +88. Untested: services of type 3-6 (44 of them) may fail the same way. With type 0, reforge-style services behave as plain crafting *[inferred]*.

## Stray NPCs: floating "ERR", Chinese names, duplicate merchants
✅ *[tested in game]*

**What "ERR" means:** a floating "ERR" label is the client's placeholder for a **missing model**. The package spawns some untranslated Chinese NPC blocks whose models aren't in the English client (we found 慧昕 in Archosaur North District).

**How to hide a spawn without deleting anything:** in `/opt/gamed/config/world/npcgen.data`, every spawn area has a *switch* field (+59). 0 = always on. Hidden event spawns use a controller that is never switched on (18 on this package). Setting an area's switch from 0 to 18 hides it; the file stays the same size and nothing else changes. *[tested]* [`tools/utility_scripts/npcgen_hide_spawns.py`](../../tools/utility_scripts/README.md) does that for areas that hold only the NPC ids you name. The npcgen layout and how it was mapped: [npcgen layout](../layouts/npcgen/README.md).
```bash
sudo cp /opt/gamed/config/world/npcgen.data /opt/gamed/config/world/npcgen.data.bak
# on a copy, on your PC or the VM:
python3 npcgen_hide_spawns.py npcgen.data --list 71013,71014,71031
python3 npcgen_hide_spawns.py npcgen.data npcgen_new.data --hide 71013,71014,71031
# put npcgen_new.data in place as npcgen.data, then: sudo server restart
```
Undo: copy the `.bak` back and restart. This is a server-only change; clients need nothing.

**Not every odd NPC is a bug.** The extra "Merchant" NPCs scattered around the map sell Homestead goods. Check what an NPC sells (the [editor's](../../tools/ultimusv2/README.md) NPC shops tab) before hiding it.

## Chinese text in logs and data files
- `gs_main.log` is GBK: read it with `sudo tail -n 40 /opt/logs/gs_main.log | iconv -f gbk -t utf-8 -c`.
- Chinese inside `*.sev` files, `auctionid.txt`, `webtradeid.txt` and config comments is not shown to players (the client uses its own English text). *[checked on this package]*
- Items players can get from shops, the Boutique, quests and drops all have English names in the e344 English client data. About 1,100 of the 20,122 quests have Chinese names; they only matter if an NPC offers one. *[checked on our data]*

---
[Back to the guide index](README.md)
