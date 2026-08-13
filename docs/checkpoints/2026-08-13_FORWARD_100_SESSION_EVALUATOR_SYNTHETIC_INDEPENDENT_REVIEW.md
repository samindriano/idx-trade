# IDX Trade — Forward 100-Session Evaluator Synthetic Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT independent review
Reviewed implementation: `1410febf41d653cd6baf135169d31a859e9312ef`
Frozen protocol: `6c05499d01ba644c80f0c6bd6d621aac92ab2813`

## Verdict

`FORWARD_100_SESSION_EVALUATOR_SYNTHETIC_REVIEW_CHANGES_REQUIRED`

The metric and decision core is substantially faithful to the frozen protocol, and the implementation correctly remains synthetic-only with no protected forward outcome access. However, the current synthetic harness does **not yet prove the fail-closed provenance contract required before this evaluator can be accepted**. Four blocking findings must be remediated before engineering acceptance.

No protected outcome was accessed during this review, and no scientific/model/counter semantics were changed.

## What passes review

The following implementation areas are consistent with the frozen protocol:

- exact 100-session inventory length and consecutive session-index checks;
- fixed first-50 / last-50 split;
- O2 `PASS` / `MIXED` / `FAIL` boundaries;
- within-session O2 quintile/decile ranking semantics via the existing ranking utilities;
- Reliability local-pairwise-quality positive/negative/tie semantics;
- Reliability deterministic quartile, top-40%, score-quintile, and conditional-half definitions matching Reliability V0;
- Reliability `80/100` and `40/50` readiness thresholds;
- Reliability `PASS` / `INCONCLUSIVE` / `INCONCLUSIVE_DATA` / `FAIL` semantics;
- Reliability cannot rescue O2;
- O2.1 is excluded;
- synthetic pre-manifest is written before the synthetic marker;
- synthetic marker is written before the outcome loader;
- existing marker and crash-after-marker behavior preserve one-shot consumption;
- output artifacts are deterministic and SHA-inventoried;
- protected runtime loader remains deliberately unwired.

The reported focused `11 passed` and full-suite `289 passed, 0 failed` are credible engineering evidence for the implemented synthetic surface, but the test fixtures currently encode contracts that differ from the accepted real forward artifacts in important ways below.

## Blocking finding 1 — evaluated score/reliability frames are not bound to the hash-pinned artifacts

Severity: **BLOCKER / provenance fail-open**.

`validate_session_inventory()` verifies the files and hashes named by the inventory. But `run_synthetic_forward_evaluation()` then evaluates separately supplied in-memory `o2_scores` and `reliability` DataFrames. There is no cryptographic or semantic binding proving those DataFrames are the contents of the hash-pinned score/sidecar artifacts.

A caller can therefore leave every pinned file/manifest unchanged, alter the in-memory O2 scores or Reliability values, and still pass the artifact-hash preflight. The resulting verdict would be computed from values not pinned by the pre-outcome contract.

This directly conflicts with the frozen protocol requirement that the exact O2 score artifacts and Reliability sidecars be hash-pinned before outcome access and that all input/source/model/sidecar hashes fail closed.

### Required remediation

Preferably make the synthetic runner load the score and Reliability rows from the already hash-verified artifact paths in the session inventory, using synthetic Parquet fixtures that reproduce the accepted runtime schemas. Do not accept an independent unpinned frame as the scientific input.

If a separate normalized frame must exist, its canonical bytes/hash and deterministic derivation from the pinned source artifact must be written and verified **before** the marker, with tests proving a value-only mutation cannot pass while the source hashes remain unchanged.

Add an adversarial test that changes O2 scores and another that changes `score_margin_reliability` while leaving the pinned inventory files/manifests untouched; both must fail before the loader is callable.

## Blocking finding 2 — synthetic Reliability manifest fixture is incompatible with the accepted Reliability V1 contract

Severity: **BLOCKER / real-artifact incompatibility**.

The evaluator currently requires Reliability `runtime_flags` to equal a six-key synthetic dictionary:

- `provider_call`
- `outcome_access`
- `o2_refit`
- `o2_rescore`
- `counter_change`
- `tiering_or_filtering`

The accepted Reliability V1 sidecar uses the frozen `PROTECTED_FLAGS` contract instead, with keys including:

- `provider_calls`
- `source_recapture_or_repair`
- `o2_refit`
- `o2_rescore`
- `reliability_model_fit`
- `composite_reliability_score_created`
- `tier_or_threshold_optimization`
- `trade_filtering`
- `independent_reliability_counter_registration`
- `fresh_forward_outcomes_accessed`
- `forward_outcome_access_marker_written`

and separately uses `outcome_access = LOCKED`.

Therefore an actual accepted Reliability V1 manifest would fail the current evaluator's exact `runtime_flags` equality check. The synthetic tests pass because the fixtures invented a different contract.

The evaluator also does not currently verify the accepted sidecar's `model_id = RELIABILITY-V1-SCORE-MARGIN-SHADOW` and `formula_version = score_margin_reliability_v1`, both of which are part of the accepted immutable sidecar identity.

### Required remediation

Use/import the accepted Reliability V1 constants rather than restating a simplified synthetic contract. Validate at minimum:

- exact `model_id`;
- exact `formula_version`;
- exact accepted `PROTECTED_FLAGS`;
- `outcome_access == LOCKED`;
- existing exact O2 score/manifest/model/feature pins.

Update synthetic fixtures to mirror the real accepted manifest schema. Add a test using a real-schema synthetic manifest and adversarial tests for formula/model/protection drift.

## Blocking finding 3 — missing Reliability sidecars are not declared `INCONCLUSIVE_DATA` before outcome loading

Severity: **BLOCKER / protocol-order violation**.

Frozen vault eligibility rule 5 requires either:

1. every Reliability V1 sidecar exists and validates against its exact O2 source bundle; or
2. Reliability is explicitly declared `INCONCLUSIVE_DATA` **before outcomes are loaded**.

The current runner allows all-empty Reliability declarations for individual sessions, writes the marker, loads outcomes, and only afterwards computes `reliability_complete` and returns `RELIABILITY_FORWARD_INCONCLUSIVE_DATA`.

That is too late. It also computes Reliability metrics from whatever partial sidecar rows are supplied after outcome access even when completeness is false.

### Required remediation

Before writing the marker:

- classify Reliability availability as exactly `COMPLETE_VALIDATED` or `PREDECLARED_INCONCLUSIVE_DATA`;
- write that state into `pre_outcome_contract.json`;
- if incomplete, do not produce a confirmatory Reliability metric evaluation from the partial subset after outcome loading; emit the preregistered `INCONCLUSIVE_DATA` readiness/decision artifact only;
- never rebuild missing sidecars from outcomes.

Add a test proving an incomplete sidecar inventory is declared inconclusive in the pre-contract before the loader event occurs.

## Blocking finding 4 — the frozen protocol hash is caller-overridable

Severity: **HIGH / freeze bypass**.

`run_synthetic_forward_evaluation()` exposes `expected_protocol_sha256` as a caller parameter. The code checks the protocol file against that caller-supplied value rather than requiring it to equal the frozen `PROTOCOL_SHA256` constant.

The current mismatch test proves that a deliberately wrong expected hash blocks, but the opposite path remains possible: a caller can modify the protocol file and pass its new hash as `expected_protocol_sha256`. The runner would accept the modified document while still reporting the frozen protocol status/commit constants.

### Required remediation

The scientific runner must not permit a caller to redefine the frozen protocol identity. Remove the override from the public evaluator path, or explicitly require `expected_protocol_sha256 == PROTOCOL_SHA256` before any artifact/loader action. If a test helper needs arbitrary hashes, isolate that helper from the scientific runner.

Add an adversarial test showing that a modified protocol plus its matching caller-supplied hash is still rejected before the loader.

## Additional required hardening before eventual protected adapter

These are not separate blockers for the synthetic metric core once the four issues above are fixed, but they must be explicit acceptance boundaries:

1. The real protected adapter must validate the canonical O2 counter is exactly `100/100`, official-calendar consecutiveness, and full H10 maturity before any marker.
2. O2 manifest validation at vault time must include the frozen model-manifest pin plus source-snapshot and eligibility provenance required by protocol section 1.4; the current synthetic validator checks model SHA, feature SHA, session identity, score hash, and outcome-clean flags but not the full real source bundle.
3. The real adapter must bind the actual O2 runtime schema (`session_date`, manifest-held official session index) deterministically into the evaluator's normalized `date/session_index` representation without changing row support.
4. The accepted Reliability sidecar contains O2-unscored `NOT_APPLICABLE` rows. The adapter may deterministically restrict evaluation to exact O2-scored support, but must validate the full sidecar artifact first and must not silently rewrite/recompute it.
5. `evaluator_code_commit` in the pre-contract must be resolved/verified from the committed checkout rather than trusted as an arbitrary caller string when the protected adapter is introduced.
6. Shared calendar/security/tradability/corporate-action/source-snapshot roles must be pinned to the exact controlling revisions and cross-linked to the real O2/outcome contract, not merely to arbitrary existing files with self-declared hashes.

These are specifically deferred protected-runtime integration requirements; they do not authorize wiring or accessing the vault now.

## Review decision

Do **not** mark the evaluator accepted yet.

Recommended next action is a bounded engineering remediation on the existing `codex/idx-forward-100-evaluator-v1` branch. Preserve all frozen metric/decision semantics and do not touch protected outcomes. After remediation:

- rerun focused tests;
- rerun full pytest;
- provide a small remediation checkpoint/handoff;
- return for independent re-review.

No model change, threshold change, counter change, provider call, actual forward evaluation, protected outcome access, or O2.1 evaluation is authorized by this review.
