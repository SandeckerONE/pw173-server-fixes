# 3. Creating accounts
✅ *[tested]*

The `adduser` stored procedure takes **17 arguments**, and this package uses password type 2: **`base64(md5(lowercase(username) + password))`**, passed as a quoted string, not the hex form older guides use.

Two traps:
- `ERROR 1366`: you passed the old hex form; the `passwd` columns are text here.
- `ERROR 1292 Incorrect datetime value: '0' for column birthday`: the 15th argument (`birthday1`) must be a real date, e.g. `'1990-01-01'`.

Working call (MariaDB, database `wm`):
```sql
CALL adduser('name', 'HASH', '0','0','','0.0.0.0','name@example.com',
             '0','0','0','0','0','0', 0, '1990-01-01', '0', 'HASH');
```
Make the hash with Python:
```python
import hashlib, base64
print(base64.b64encode(hashlib.md5((user.lower() + password).encode()).digest()).decode())
```
GM rights: `CALL addGM(<account id>, 1);`. New IDs go 1024, 1040, 1056… (steps of 16).

---
[Back to the guide index](README.md)
