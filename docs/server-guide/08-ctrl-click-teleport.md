# 8. Every player can Ctrl+click teleport
✅ *[tested; mechanism read from gs]*

**Cause:** `/opt/gamed/ptemplate.conf` ships with `debug_command_mode = active`. That turns on gs's debug command handler, which has **no GM check**: anyone can Ctrl+click the map to teleport and use other test commands (including item and cash ones). gs treats only the exact value `active` as on.

**Fix:**
```bash
sudo sed -i 's/^debug_command_mode *= *active/debug_command_mode = inactive/' /opt/gamed/ptemplate.conf
sudo server restart
```
Real GM accounts keep their GM commands; those go through a separate, checked handler.

---
[Back to the guide index](README.md)
