# 1. Setting up the server package on a modern Linux
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

---
[Back to the guide index](README.md)
