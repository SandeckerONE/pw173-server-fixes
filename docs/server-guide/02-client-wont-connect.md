# 2. Client won't connect / stuck on "Connecting to server"
✅ *[tested]*

**Symptom:** you start `elementclient.exe game:cpw` and get the official launcher panel stuck on "Connecting to server…". It is trying to reach the dead official patch site.

**Fix:** the 1.7.3 client needs `startbypatcher` (and the packaged `eStart.bat` also passes `nocheck`). From the `element` folder:
```
elementclient.exe game:cpw nocheck startbypatcher
```
Add `console:1` if you want the in-game console (Shift+~; see [section 10](10-debug-console.md)).

**Server address:** `patcher\server\serverlist.txt` is **UTF-16LE with a BOM, tab-separated**. Don't edit it in Notepad. PowerShell:
```powershell
$f="...\PWI_en\patcher\server\serverlist.txt"
$t=Get-Content $f -Raw -Encoding Unicode
$t=$t.Replace("OLD.IP.ADDR","YOUR.SERVER.IP")
Set-Content $f $t -Encoding Unicode -NoNewline
```
The line format is `Name<TAB>29000:IP<TAB>10`.

Also check: client `elements.data` and `tasks.data` must be byte-identical to the server's (`md5sum` / `Get-FileHash`).

---
[Back to the guide index](README.md)
