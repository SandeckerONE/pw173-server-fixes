# 6. Severe lag, login bounces, followers not updating
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

---
[Back to the guide index](README.md)
