# IDX-Trade — Security-Master Revision Collision Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Status: `FAIL — SAME-KEY HISTORY COLLISION NOT FAIL-CLOSED`

This is a read-only synthetic audit of the security-master identity/history
boundary against the pinned runtime. It does not inspect or rewrite canonical
security data and does not call a provider or production path.

## 1. Pinned source and validation

- Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- `src/idx_trade/security_master.py` SHA-256:
  `4070DF883D340621D8D52D86810E7FC5DDF4A007AD7C858698CCA4674CF21569`
- Probe: `research/idx_security_master_revision_collision_probe_v1.py`
- Test: `tests/test_idx_security_master_revision_collision_probe_v1.py`
- Focused result: `1 passed`; `py_compile` and `git diff --check` passed.

## 2. Synthetic collision

Two input rows used the same normalized `(ticker, listed_from)` key:

| Input | Company | Listed-from | Listed-to | Source |
|---|---|---|---|---|
| active | ABCD Active | 2020-01-01 | open | IDX_ACTIVE |
| delisted | ABCD Historical | 2020-01-01 | 2024-12-31 | IDX_DELISTED |

`build_security_master()` returned one row only:

| Output rows | Company retained | Listed-to retained | Source retained |
|---:|---|---|---|
| 1 | ABCD Historical | 2024-12-31 | IDX_DELISTED |

The builder sorts and calls `drop_duplicates(["ticker", "listed_from"],
keep="last")`. It does not emit a typed conflict or preserve both competing
history claims.

## 3. Blast radius

- Origin: security-master canonicalization treats same-key records as a
  replacement-order problem rather than an identity/revision conflict.
- Trigger: duplicate issuer key and listing start with conflicting end/source
  or company metadata.
- Affected state: listing era, existence state, warmup, tradability/universe
  eligibility, and any downstream identity/provenance report derived from the
  master.
- Failure class: silent data-history loss; the output remains syntactically
  valid and can pass later eligibility checks.
- Restart/replay: deterministic for the same input order/sort policy; no
  runtime restart is needed.
- Existing coverage: universe tests cover delisting and IPO warmup separately,
  but not same-key conflicting security-master rows.

This does not establish that the canonical security master currently contains
such a collision. It establishes that the boundary does not fail closed if it
receives one.

## 4. Verdict and safe design consequence

`SECURITY_MASTER_REVISION_CONFLICT = NOT_TYPED`

`IDENTITY_HISTORY_FAIL_CLOSED = NO`

`UNIVERSE_ELIGIBILITY_RESULT = POTENTIALLY_HISTORY_DEPENDENT`

An authorized hardening would need to reject or explicitly version conflicting
same-key records before `drop_duplicates`, with source/revision lineage retained
for adjudication. No runtime fix was applied in this lane.
