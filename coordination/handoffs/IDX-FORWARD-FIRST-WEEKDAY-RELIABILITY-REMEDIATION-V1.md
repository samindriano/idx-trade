# Handoff: IDX Forward First-Weekday Reliability Remediation V1

from: Codex
to: MAIN / ChatGPT reviewer
task_id: IDX-FORWARD-FIRST-WEEKDAY-RELIABILITY-REMEDIATION-V1
source_repository: `samindriano/idx-trade`
branch: `fix/forward-first-weekday-reliability-v1`
parent_commit: `d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75`

## Scope

Diagnose and harden the existing Stockbit prospective archive and Official
Open capture after the first weekday 2026-08-24 failures. No historical replay,
model/outcome work, counter mutation, scheduler mutation, or provider data
backfill is included.

## Findings

- Stockbit pre-open run `32684333136`: successful `DATA_READY`, 5,941 rows,
  manifest SHA `94d76d9dc3d60b81ab62f728fcf949fd4bb4f6ec77686ba88df5590bf383e952`.
- Stockbit midday run `32694723874`: Zapi `ReadTimeout`, no final manifest.
- Official Open task: one delayed 15:10 launch, five ignored duplicate
  instances, result `4`; no certified 2026-08-24 Open artifact.
- Isolated post-test probe at 16:13 WIB: `SOURCE_NOT_READY_OR_NO_SESSION`,
  `OFFICIAL_OPEN_RAW_DATA_MISSING`; no production state was touched.

## Changes

- `src/idx_trade/stockbit_stream_capture_v2.py`: bounded request-exception
  retry, explicit partial classification, safe diagnostics, and immutable
  deterministic resume namespace.
- `src/idx_trade/official_open_evidence_v1.py`: accepted warmed curl_cffi
  browser transport, safe direct diagnostics, and bounded Zapi request/5xx
  retry while preserving the exact fallback/certification contract.
- `src/idx_trade/official_open_capture_runtime_v1.py`: allows the default
  browser transport instead of forcing plain `requests.get`.
- `pyproject.toml`: declares the proven `curl_cffi` runtime dependency.
- Focused regression tests cover request timeout recovery/failure, partial
  resume immutability, direct timeout fallback, Zapi retry, and auth failure
  no-retry behavior.

The Stockbit files restored from `origin/main` are part of the intended
integration lineage; they are not a second capture system.

## Validation

- Focused Stockbit/Open/scheduler tests: `36 passed` with isolated temp root.
- Full repository pytest: `706 passed`, `0 failed`, `3 existing FutureWarnings`.
- `py_compile`: PASS.
- `git diff --check`: PASS.

## Explicit policy decisions

- `ttl=30` was reviewed but not adopted because raw Zapi cache-control
  semantics for this endpoint are not proven; bounded retry is the only added
  transient mechanism.
- The live Official Open scheduler was inspected but not mutated. Existing
  triggers remain 09:02/09:07/09:12/09:17/09:22 plus AtLogOn with
  `StartWhenAvailable` and `IgnoreNew`; changing this requires separate
  operational approval and live proof.
- Stockbit archive failure and Official Open evidence failure remain isolated;
  neither path mutates model, PaperState, Decision, counters, or outcomes.

## Boundaries and next action

- No historical E2E replay, model fit/rescore, labels, realized outcomes,
  protected forward outcomes, counter mutation, scheduler mutation, or
  historical backfill.
- Integrator should update the MAIN-owned TEAM_STATUS row, review the
  dependency addition and selective Stockbit lineage import, then push/merge
  according to repository policy.
- Controlled next-session proof is still pending; do not call this a live
  E2E PASS solely from the isolated probe.

Final verdict:
`FORWARD_RELIABILITY_REMEDIATED_NEXT_SESSION_PROOF_PENDING`
