# Handoff — Price / Trend Forward Sidecar V1

from: ChatGPT
to: ChatGPT independent review / Codex local runtime
task_id: IDX-PRICE-TREND-FORWARD-SIDECAR-V1
repository: samindriano/idx-trade
branch: integration/price-trend-state-forward-sidecar-v1
status: REVIEW

## Scientific parent

Accepted Price / Trend / Confirmation State V1:

- implementation: `research/idx-price-trend-confirmation-state-v1@a33863953b4521dd4549a3089f0da2cfdfb6dcd3`
- independent acceptance: `review/idx-price-trend-confirmation-state-v1-acceptance@0c3b221fcecf035add4d0c7ce388ff4b9d6d27da`
- verdict: `PRICE_TREND_CONFIRMATION_STATE_V1_ACCEPTED_PROSPECTIVE_SIDECAR_NEXT`

No state formula or threshold was changed in this sidecar lane.

## Implemented

- `src/idx_trade/forward_price_trend_state.py`
- `src/idx_trade/forward_price_trend_state_verifier.py`
- `tests/test_forward_price_trend_state.py`
- `tests/test_forward_price_trend_state_strict_verifier.py`
- `docs/checkpoints/2026-08-15_PRICE_TREND_FORWARD_SIDECAR_V1.md`
- validation-only draft PR `#27`

## Runtime contract

Completed canonical source `t` is combined with a separately pinned historical H/L/C/Volume warm-up panel. The producer reads canonical forward `model_input.parquet` only, not `session_ohlcv.parquet`, so Open semantics remain outside Price State.

The producer can materialize target `t+1` before a target session directory exists:

`forward_monitoring/prospective/price_trend_confirmation_state_v1/<t+1>/price_trend_confirmation_state_v1.parquet`

with sibling manifest:

`price_trend_confirmation_state_v1.manifest.json`

No provider fallback, scheduler, counter, O2, Foreign Flow merge, model, outcome access, or trade decision exists.

## Provenance gates

Producer verifies:

- pinned historical panel and historical calendar hashes;
- pinned canonical forward calendar hash;
- source `t` is canonical DATA_READY and outcome-blind;
- exact canonical model-input path and snapshot SHA;
- exact parent calendar path/SHA;
- historical/forward overlap agrees exactly on H/L/C/Volume;
- combined calendar preserves exact forward `t -> t+1` identity;
- all input rows used by state calculation are `<= t`.

Output artifact and manifest are immutable and hash-pinned.

## Required verifier

Use only:

`idx_trade.forward_price_trend_state_verifier.verify_prospective_price_trend_state_strict`

for acceptance/runtime verification.

It re-establishes semantics rather than trusting hashes alone:

- exact output schema;
- artifact row/ticker counts;
- state-distribution reconciliation;
- historical/forward calendar hash and exact next-session recomputation;
- combined-calendar metadata reconciliation;
- every canonical parent re-opened through DATA_READY/outcome-blind/path/snapshot/calendar gates;
- deterministic provenance fingerprint recomputation.

The earlier lightweight verifier in `forward_price_trend_state.py` is not the acceptance/runtime authority.

## Validation

Final code validation before documentation-only handoff/checkpoint commits:

- focused Price State + producer + strict verifier: **27 passed**;
- `git diff --check`: **PASS**;
- full repository pytest: **66 passed, 1 failed, 4 warnings**;
- sole failure is the known unrelated pre-existing storage assertion `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` (two independent revision conflicts are emitted while the old test expects one).

Adversarial cases passed for target-session independence, immutable revisions, canonical snapshot mutation, pinned historical mutation, outcome-like schemas, missing next official session, manifest output-schema tamper, state-distribution tamper, consistently re-hashed parent semantic tamper, and calendar semantic tamper.

No sidecar-focused test failed.

## Coordination

Latest canonical `main:coordination/TEAM_STATUS.md` was checked before the lane started. A branch-local claim exists at `coordination/claims/IDX-PRICE-TREND-FORWARD-SIDECAR-V1.md` because the available connector cannot safely append a small row to the large shared canonical ledger without full-file replacement.

Before any local runtime work, refetch canonical TEAM_STATUS and safely record this lane there without overwriting other agents.

## Stop boundary

Do not yet:

- run a real runtime materialization;
- wire the producer into the canonical scheduler/post-capture path;
- create a new scheduler or counter;
- combine Price State with Foreign Flow;
- define WATCH / READY / ENTRY_ELIGIBLE;
- use outcomes or historical performance;
- tune thresholds;
- touch O2 or HSC/free-float.

Next authorized action after independent sidecar acceptance is only controlled zero-provider runtime-hook/materialization verification.