# gdeliveryd

The hub between link, game, database and pwAdmin. Notes from our 1.7.3 binary and pwAdmin's protocol config. *[code + tested]*

## Server attributes (rates and switches)
- Held in memory only (`ServerAttr`), set at runtime by `GMSetGameAttri` and pushed to every gs (`OnReportAttr`, see [gs](gs.md)). **They reset on every restart**; nothing reads them from a config file.
- pwAdmin's Server Configuration page and `AA/cmd.jsp?cmd_opt=dblDrops` send `GMSetGameAttri`. `scripts/pw_rates_apply.sh` uses that to re-apply rates after each start.
- "Lambda" is stored by gdeliveryd but no gs code reads it: no gameplay effect.

## Protocol ids
The ids in pwAdmin's `config.xml` match this gdeliveryd, e.g. `SetMaxOnlineNum` 373, `GMControlGame` 380.

## Ports
29100 (pwAdmin and the other daemons connect here). pwAdmin needs `/etc/iweb.conf` pointing at `127.0.0.1` to reach it ([setup](../../server-guide/setup.md#pwadmin-status-offline--1-values-saving-rates-failed)).

---
[Back to research notes](../README.md)
