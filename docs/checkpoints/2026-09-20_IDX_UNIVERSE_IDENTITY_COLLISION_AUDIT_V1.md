# IDX-Trade — Universe Identity Collision Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Status: `IDENTITY_COLLISION_REPRODUCED / DOWNSTREAM_GUARD_LATE`

This is a read-only synthetic audit of the identity-to-universe boundary. It
uses the exact pinned runtime source from a separate worktree and synthetic
prices/security metadata only. No canonical data, provider, production state,
cloud/capture/telemetry, or incumbent state was accessed or changed.

## 1. Pinned source

- Runtime worktree: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
- Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- `src/idx_trade/universe.py` SHA-256:
  `31A92DB6628C7DE4044240BC06D8F1CE8031D1BF63F8C90285C32175A67464DD`
- `src/idx_trade/security_master.py` SHA-256:
  `4070DF883D340621D8D52D86810E7FC5DDF4A007AD7C858698CCA4674CF21569`

Probe: `research/idx_universe_identity_collision_probe_v1.py`
Test: `tests/test_idx_universe_identity_collision_probe_v1.py`

Focused result: `1 passed`; `py_compile` and `git diff --check` passed.

## 2. Synthetic trigger and observed output

The input contained one security-master identity `ABCD` and two raw price-map
keys: `ABCD` and `ABCD.JK`. Both normalize to `ABCD`. Each alias had 60
complete synthetic active sessions, and `top_n=2` was used.

Observed universe output:

| Result | Value |
|---|---:|
| output rows | 2 |
| unique ticker values | 1 (`ABCD`) |
| selected rows | 2 |
| liquidity ranks | 1 and 2 |
| duplicate ticker key | `true` |

The universe builder normalizes each raw map key but does not assert uniqueness
after normalization. It therefore emits two selected rows for one issuer.

## 3. Boundary containment

The same synthetic duplicate score frame was passed to the pinned V4-X1
Decision rank adapter. That later boundary rejected it with:

`DECISION_V2_V4_X1_DUPLICATE_TICKER`

This is useful containment, but it does not close the origin defect. Any
consumer of the universe output before that adapter, or any structural metric
that counts rows rather than canonical ticker keys, can observe duplicated
liquidity support. The later Decision rejection also means the system has a
late guard rather than one consistent identity invariant across the pipeline.

## 4. Blast radius

- Origin: raw input-key iteration in the universe builder occurs before a
  post-normalization uniqueness check.
- Trigger: aliases or equivalent issuer keys such as `ABCD` and `ABCD.JK`.
- Affected state: duplicate universe rows, duplicated rank slots, inflated
  selected-row counts, and potentially distorted breadth/turnover support.
- Downstream behavior: V4-X1 Decision rank adaptation fails closed if it sees
  the duplicate frame; other row-oriented consumers are not proven safe.
- Existing coverage: the Decision adapter tests normalization and duplicate
  rejection, but the universe tests do not exercise duplicate raw aliases at
  the universe origin.
- Restart/replay: the collision is deterministic on every rebuild; no state
  restart is needed for the defect to recur.
- Hash detection: the observed universe output has no demonstrated
  canonical-identity uniqueness attestation that would catch the collision
  before downstream use.

## 5. Verdict and safe design consequence

`IDENTITY_CONTRACT = INCONSISTENT_ACROSS_BOUNDARIES`

`UNIVERSE_ORIGIN_GUARD = ABSENT`

`DECISION_LATE_GUARD = PRESENT`

The evidence supports a narrow architectural requirement: every identity-
normalizing boundary must reject duplicate canonical keys before ranking,
selection, or persistence. This is a design finding, not authorization to patch
the runtime in this lane.
