# 13. Small notes
- **Class mask:** `allow_login_class_mask = 32767` in `ptemplate.conf` allows all 15 classes.
- **Root `/opt` permissions:** the stock control script runs `chmod 777 -R /opt` on every start; consider removing that once everything works.
- **Database password:** the package uses MariaDB `root`/`root`. Change it before letting anyone else near the VM, and keep the database on localhost only. Places that hold the login on this package: `/opt/authd/table.xml` (authd), pwAdmin's `webapps/pwadmin/WEB-INF/.pwadminconf.jsp` plus a few add-on pages (clear `pwadmin/work/Catalina` afterwards so the pages recompile), and any scripts of your own. A separate game user with rights on `wm` only works fine for authd. *[tested]*
- **`chmod 777 -R /opt`:** the stock `/opt/server` makes everything world-writable on every start. Comment that line out and run `sudo chmod -R go-w /opt`; all daemons run as root, so nothing breaks. *[tested]*
- **Friends can't connect but it works for you (VM lost internet):** after restoring a *running* VirtualBox snapshot, the VM's NAT adapter can lose its IPv4 address while the host-only adapter keeps working. Your own client still connects; Tailscale on the VM goes `offline` ("Unable to connect to the Tailscale coordination server") and friends' launchers time out. Check with `ping -c2 1.1.1.1` and `ip route | grep default` on the VM. Fix: in the running VM window, Devices > Network > untick and re-tick the NAT adapter, then `sudo networkctl reconfigure <nat-interface>`; or do a cold power-off and start. Then `sudo systemctl restart tailscaled`. *[tested]*
- **Remote friends:** a mesh VPN such as Tailscale inside the VM works well; only the game port (29000) needs to be reachable. Block everything else on the VPN interface.

---
[Back to the guide index](README.md)
