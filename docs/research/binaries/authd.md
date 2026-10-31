# authd (login server)

*[tested unless marked]*
- Opens its MariaDB connection once and **never reconnects**. Any MariaDB restart (package update, `needrestart`, idle timeout) breaks every login until authd restarts. Log signature: `Connection must be Open; current state is Closed`, `acquireIdPasswd exception`, `GQueryPasswd:can not find user`. Fix and watchdog: [authd guide](../../server-guide/authd.md).
- Listens on 29200. Find it by port, not by name (`pgrep -f authd` also matches command lines that merely contain the word).
- Passwords: type 2, `base64(md5(lowercase(username) + password))` ([accounts](../../server-guide/setup.md#creating-accounts)).
- Boutique cash: `UseCashTimerTask ... ret=-8` means the account has no row in `point` yet; it is created on first login (read from the `usecash` procedure).
- Database login lives in `/opt/authd/table.xml`.

---
[Back to research notes](../README.md)
