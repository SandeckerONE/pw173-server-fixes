# 4. Boutique gold doesn't arrive (`ret=-8`)
✅ *[tested; cause read from the `usecash` procedure]*

**Symptom:** you credit cash with the control script's `server cubi <accountID> <amount>` (100 cash = 1 gold) and the authd log repeats `UseCashTimerTask: ... ret=-8`.

**Cause:** `usecash` needs the account's row in the `point` table, and that row is only created on the account's **first login**.

**Fix:** none needed. Have the player log in once; the gold lands a few minutes later (relog if the Boutique still shows the old balance). Don't re-queue the cash in the meantime, or it may be credited twice.

---
[Back to the guide index](README.md)
