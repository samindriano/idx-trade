# IDX-Trade — Security-Master Revision Collision Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Status: `FAIL — SAME-KEY REVISION COLLISION IS ORDER-SENSITIVE`

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
- Adjacent pinned-runtime baseline: universe + Decision V2 + sizing adapter
  suite `11 passed`.

## 2. Historical intent and synthetic collision

Historical archaeology found that the original introduction commit
`65233e195128d542457693643b3faba5546e6173` explicitly documented the policy
“Prefer a delisted row when active+delisted sources describe the same listing
interval.” The earlier active-versus-delisted example is therefore an intended
policy case, not by itself a defect.

The remaining question is whether conflicting same-key revisions are also
disambiguated. They are not.

Two delisted input rows used the same normalized `(ticker, listed_from)` key but
different end dates and sources:

| Input | Company | Listed-from | Listed-to | Source |
|---|---|---|---|---|
| revision A | History A | 2020-01-01 | 2024-12-31 | ARCHIVE_A |
| revision B | History B | 2020-01-01 | 2025-12-31 | ARCHIVE_B |

`build_security_master()` returned one row, and reversing input order changed
which revision survived:

| Input order | Company retained | Listed-to retained | Source retained |
|---|---|---|---|
| A then B | History B | 2025-12-31 | ARCHIVE_B |
| B then A | History A | 2024-12-31 | ARCHIVE_A |

The builder sorts and calls `drop_duplicates(["ticker", "listed_from"],
keep="last"). It does not emit a typed conflict, preserve both competing
history claims, or select by a declared revision authority/date.

## 3. Blast radius

- Origin: security-master canonicalization applies the documented
  active-vs-delisted preference, but applies the same deduplication to
  conflicting same-class revisions without an authority rule.
- Trigger: duplicate issuer key and listing start with conflicting end/source
  or company metadata.
- Affected state: listing era, existence state, warmup, tradability/universe
  eligibility, and any downstream identity/provenance report derived from the
  master.
- Failure class: order-dependent data-history loss; the output remains
  syntactically valid and can pass later eligibility checks.
- Restart/replay: deterministic for the same input order/sort policy; no
  runtime restart is needed.
- Existing coverage: universe tests cover delisting and IPO warmup separately,
  but not same-key conflicting security-master rows.

This does not establish that the canonical security master currently contains
such a collision. It establishes that the boundary does not fail closed if it
receives one.

## 4. Verdict and safe design consequence

`ACTIVE_VS_DELISTED_PREFERENCE = INTENTIONAL_HISTORICAL_POLICY`

`SAME_CLASS_REVISION_CONFLICT = NOT_TYPED`

`IDENTITY_HISTORY_FAIL_CLOSED = NO`

`UNIVERSE_ELIGIBILITY_RESULT = POTENTIALLY_HISTORY_DEPENDENT`

An authorized hardening would need to reject or explicitly version conflicting
same-key records before `drop_duplicates`, with source/revision lineage retained
for adjudication. No runtime fix was applied in this lane.
