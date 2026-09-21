# IDX-Trade Shadow Recovery Matrix V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **SYNTHETIC RECOVERY PASS / REAL RECOVERY BLOCKED**

## Recovery surfaces

| Surface | Synthetic candidate evidence | Real retained evidence | Verdict |
|---|---|---|---|
| verified ancestor selection | tested in adoption packet | no real snapshot chain | real BLOCKED |
| tampered/latest quarantine | tested in adoption packet | no real latest state | real BLOCKED |
| fork rejection | tested in adoption packet | no real competing chain | real BLOCKED |
| restart after preparation | selected synthetic rehearsal | no prepared parent | real BLOCKED |
| restart after partial execution | selected synthetic rehearsal | no fill vector | real BLOCKED |
| CA settlement restart | selected synthetic rehearsal | no CA ledger | real BLOCKED |
| controller recovery fence | candidate focus tests | active root ended without prepared execution | real BLOCKED |

The active runtime's no-prepared-execution record is a terminal operational
metadata observation. It is not a recovery chain and was not converted into
one.

`RECOVERY = PASS_SYNTHETIC / BLOCKED_REAL`.
