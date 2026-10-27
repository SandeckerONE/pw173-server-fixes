# 10. Debug console commands
🟡 *[tested]*

Temporarily set `debug_command_mode = active` ([section 8](08-ctrl-click-teleport.md)), restart, start the client with `console:1`, open the console with **Shift+~**, and send `d_c2scmd <id> <args…>`. Switch it back to `inactive` and restart afterwards, because it opens debug teleport for everyone.

Known IDs (read from gs's DebugCommandHandler):
| Command | Effect |
|---|---|
| `d_c2scmd 10844 <a> <b>` | gives the character `a` Faction Construction points and `b` Faction Contribution points (not Loyalty) *[tested]* |

---
[Back to the guide index](README.md)
