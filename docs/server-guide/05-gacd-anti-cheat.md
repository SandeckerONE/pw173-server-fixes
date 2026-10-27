# 5. GACD (anti-cheat) keeps dying
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

---
[Back to the guide index](README.md)
