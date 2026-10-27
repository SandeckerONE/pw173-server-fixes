# 9. Character export/import
⚠️ *[tested the hard way]*

The control script's `exportrole <id> <file.xml>` / `importrole <file.xml>` run the gamedbd program **directly on the database files**.

1. **Never run `importrole` while the server is running.** The live gamedbd caches the data, and the second program writing the same files left the character database so that `listrole` segfaulted even after stopping the server. Only a snapshot restore fixed it. Untested whether importing with the server fully stopped is safe; snapshot first either way.
2. **Export/import mismatch:** the export writes `reserved1`…`reserved10` at the end of `<status>`, but import stops reading at `lottery_data` and fails with `error member (reserved1, 0) in GRoleStatus` / `decode roleidfile error.` Delete those ten lines inside `<status>` only (the `reserved` lines in other sections are expected):
```bash
sudo sed -i '/<status>/,/<\/status>/{/<variable name="reserved[0-9]*"/d}' role.xml
```
Prefer the server's own debug commands ([section 10](10-debug-console.md)) for small character changes.

---
[Back to the guide index](README.md)
