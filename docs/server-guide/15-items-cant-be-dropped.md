# 15. Items can't be dropped on the ground
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

---
[Back to the guide index](README.md)
