# Handoff — IDX-V4-CA-RESIDUAL-DOCUMENT-SEMANTICS-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-RESIDUAL-DOCUMENT-SEMANTICS-V1`
branch: `data/idx-v4-ca-residual-document-semantics-v1`
scientific/preflight code anchor: `6cced713d13e9933f1c9243695f8e59464c0b407`
scientific parent: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1@c2246e5e82dc642950017e38e57cd97700e15199`

## Mission

Do not design or modify anything. Execute the frozen residual-document semantics lane exactly once, offline only, against the already acquired official KSEI Stage-2 raw corpus. Then execute one frozen continuity replay and STOP.

No provider/network call, redownload, alternate source, target/model/performance/outcome access, or local code patch is authorized.

## Step 0 — coordination hard gate

Before validation/execution:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer ACTIVE lane owns the same residual V4 CA document-semantics scope;
3. add/update exactly one lane `V4 CA residual document semantics V1` to `ACTIVE`, owner `Codex/V4-CA-Residual-Document-Semantics`, branch `data/idx-v4-ca-residual-document-semantics-v1`, boundary `offline reuse of existing Stage-2 KSEI raw corpus; no provider/target/model/outcome`;
4. push only that coordination update to `main` using the repository safe shared-file rule.

If an overlapping active lane now exists, STOP and report the conflict.

## Step 1 — exact branch / validation

Checkout/pull the branch and verify the scientific anchor exists unchanged in history:

`6cced713d13e9933f1c9243695f8e59464c0b407`

Run:

```text
python -m pytest tests/test_v4_ca_residual_document_semantics.py tests/test_v4_ca_residual_document_date_binding.py
```

Then:

```text
python -m py_compile src/idx_trade/v4_ca_residual_document_semantics.py src/idx_trade/v4_ca_residual_document_semantics_hardened.py scripts/verify_v4_ca_stage2_raw_corpus.py scripts/run_v4_ca_residual_document_semantics.py scripts/run_v4_ca_residual_document_semantics_hardened.py scripts/run_v4_ca_residual_document_continuity.py
```

Then:

```text
git diff --check
```

If any validation fails: STOP. Do not patch. Record exact failure in TEAM_STATUS and return to ChatGPT.

## Step 2 — immutable Stage-2 corpus attestation

Run exactly:

```text
python scripts/verify_v4_ca_stage2_raw_corpus.py --stage2-root "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v3"
```

Required status:

`V4_CA_STAGE2_RAW_CORPUS_ATTESTED`

This must account for all 100 prior candidate documents. Every previously successful capture must still exist and hash exactly to the recorded Stage-2 SHA. Provider-failed cases may remain provider-failed.

If attestation fails: STOP. Do not delete/move/redownload/substitute any raw file and do not run Stage A.

## Step 3 — Stage A: one offline residual-document semantic audit

The output root must not already exist:

`D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`

If it exists, STOP and report collision; do not delete/overwrite it.

Run the **hardened launcher only**:

```text
python scripts/run_v4_ca_residual_document_semantics_hardened.py --stage2-root "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v3" --residual-needs "D:\Documents\Project\idx-v4-ca-voluntary-conversion-remediation-20260818-v1\schedule_evidence_needs.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --output-dir "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1"
```

Do not invoke `run_v4_ca_residual_document_semantics.py` directly.

Stage A must report status:

`V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_COMPLETE`

Record, without interpretation/tuning:

- successful Stage-2 raw documents verified;
- event-document candidate rows;
- exact non-blocking events;
- exact-transition events;
- conflict events;
- unresolved events;
- output hashes / manifest SHA.

If Stage A errors or does not produce the exact status/manifest: STOP. Do not patch and do not run Stage B.

## Step 4 — Stage B: exactly one offline frozen continuity replay

No source/config/code edit is allowed after Stage-A result exposure.

The output root must not already exist:

`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v1`

If it exists, STOP; do not delete/overwrite it.

Run exactly:

```text
python scripts/run_v4_ca_residual_document_continuity.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\corporate_action_event_evidence.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --document-root "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1" --output-dir "D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v1"
```

Then STOP regardless of pass/fail.

Record exactly:

- final continuity verdict;
- `corporate_action_continuity_certified`;
- final relevant / exact / schedule-required event counts and tickers;
- H5/H10/consensus dates passing `>=90%`;
- H5/H10/consensus minimum rates;
- Stage-A evidence counts copied by `residual_document_continuity_overlay.json`;
- final small-artifact hashes.

Do not run R5/R10 or any target/model/evaluator after this, even if continuity certifies. ChatGPT review is required first.

## Step 5 — promote only small result artifacts

Keep all Stage-2 raw HTML/PDF/request bytes and the full continuity ledger external.

Promote a compact result bundle under a new `docs/artifacts/` directory. Appropriate files are:

- Stage A `MANIFEST.json`, `summary.json`, `residual_event_document_evidence.csv`, and `residual_document_audit.csv` if reasonably small;
- Stage B `MANIFEST.json`, `summary.json`, `event_semantics_audit.csv`, `schedule_evidence_needs.csv`, `v4_frozen_continuity_per_date_event_window.csv`, and `residual_document_continuity_overlay.json`;
- do **not** commit `v4_frozen_continuity_ledger_event_window.csv`.

Add one factual result checkpoint and one result handoff. No reinterpretation or new hypothesis.

Update the canonical TEAM_STATUS lane to `REVIEW` with branch final HEAD, exact Stage-A counts, Stage-B verdict/rates, provider calls `0`, and explicit statement that target/model/performance/protected outcomes were not accessed. Push branch + coordination update, confirm clean/synced, then STOP for ChatGPT review.

## Immutable scientific restrictions

- Stage-2 provider acquisition is not rerun.
- No provider call is made in this lane.
- No source substitution.
- No generic Record/Distribution -> transition mapping.
- No price-jump inference, adjusted-price rescue, next-session rescue, universe shrink, or gate change.
- Same frozen 610-ticker / 600-date continuity contract and `>=90%` date gate.
- No R5/R10, target rank, fit, prediction, IC, Top30/spread, bootstrap, protected outcome, or fresh-forward access.
