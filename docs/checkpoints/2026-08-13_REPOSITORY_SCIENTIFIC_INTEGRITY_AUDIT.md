# Repository-Wide Scientific Integrity and Reproducibility Audit

Date: 2026-08-13 (Asia/Jakarta)
Repository: `samindriano/idx-trade`
Branch: `codex/scientific-integrity-audit-v1`
Audit HEAD before final documentation: `612c11cdde5a942428fe74e3059811480fc0ceb2`
Controlling coordination ref inspected: `origin/main@7436c213c625ea3856b8376e74c5927ff84a7eea`

## Verdict

Overall: `NO-GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE`.

The repository contains coherent frozen model fingerprints and mostly coherent
historical decision boundaries, but its general data/artifact foundation still
has confirmed fail-open paths. A clean pytest result on the current skinny main
line would not establish scientific reproducibility or PIT/data-gate readiness.
The accepted historical model verdicts are not changed by this audit, and no
protected outcome was accessed.

The forward runtime has a separate operational qualification:
`PRIMARY_EOD_CAPTURE_OPERATIONAL; O2.1_RELIABILITY_AUTOMATIC_SIDECAREVIDENCE_NOT_ESTABLISHED`.
The installed task can capture the primary EOD/model path, but the checkout it
executes does not contain the accepted O2.1 sealed-shadow and Reliability V1
modules. This is a coordination blocker for the active forward/runtime lanes,
not an authorization to merge or alter them here.

## Scope and controls

- Read latest `origin/main:coordination/TEAM_STATUS.md` before material work and
  again during final coordination.
- Used the existing isolated audit worktree; no new workers were spawned.
- No research experiment, provider/network call, model fit, scoring run, data
  backfill, panel mutation, or protected-outcome access occurred.
- The apparent `json-voucher-service` observation was a shell-wrapper false
  alarm. Explicit absolute `git -C` commands verified the target repository.
- Existing external model/artifact files were only hash-checked or metadata-
  inspected; no runtime capture was triggered.

## Confirmed high-severity defects

These are engineering/data-integrity defects in the current foundation. They
must remain fail-closed until repaired and tested. Code remediation is not
included here where it overlaps an active ownership lane.

| Severity | Finding | Direct evidence | Disposition |
|---|---|---|---|
| P1 | Textual verification flags fail open. `canonicalize_coverage_windows()` uses `astype(bool)` and `evaluate_data_gate()` uses `bool(...)`; `"False"` becomes true. | Direct isolated call returned `is_complete=np.True_` and `tradability_state=ACTIVE` for `"False"`. | `COORDINATE_WITH_ACTIVE_LANE`; strict parser and regression tests required. |
| P1 | Malformed finite interval ends become open-ended. | Direct isolated security-master call with `listed_to="not-a-date"` returned `LISTED` in 2030. | `COORDINATE_WITH_ACTIVE_LANE`; reject malformed non-null dates. |
| P1 | Conflicting duplicate OHLCV dates are silently last-write-wins. | Direct isolated canonicalization kept the second conflicting close (`3.0`) without a diagnostic. | `COORDINATE_WITH_ACTIVE_LANE`; reject conflicting duplicates, allow only identical duplicates. |
| P1 | Provenance can claim a run with missing source fingerprints and manifests are overwriteable. | Direct call returned a missing source as `None`; `write_manifest_atomic()` replaces an existing path. | Coordinate with provenance registry; require valid fingerprints and immutable publication. |
| P1 | Provider/source authority and expected manifest status are not enforced by the tradability adapter. | `ingest_idx_tradability_manifest()` requires `source_ref`, accepts fetcher-provided hash/status, and the sample manifest's expected parser status is not enforced. | `COORDINATE_WITH_ACTIVE_LANE`; source registry/authority contract owns remediation. |
| P1 | PIT domain is not enforced in warm-up/activity/coverage calculations. | `universe.py` counts observed dates before listing and on non-active states; coverage observes any date set rather than rejecting extras outside official sessions/listing/tradability domain. | `COORDINATE_WITH_ACTIVE_LANE`; do not treat current universe output as PIT-ready. |
| P1 | Price backfill completion is not equivalent to requested official-session completeness. | `price_backfill.py` reports `complete` from `UPDATED` statuses and does not validate requested date/session bounds; provider rows are not independently bounded before completion. | `COORDINATE_WITH_ACTIVE_LANE`; preserve explicit gaps/revisions. |
| P1 | Empty successful month can yield a complete-looking exchange calendar. | `session_backfill.py` records `PARSED` for an empty returned month; no per-month non-empty/domain validation is required. | `COORDINATE_WITH_ACTIVE_LANE`; require validated contribution per requested month or explicit holiday evidence. |
| P1 | Atomic file replacement is not immutable bundle publication. | `storage.py`, `tradability_pipeline.py`, and `provenance.py` replace fixed names without run IDs, write-once refusal, cross-file bundle manifest, or last-pointer publication. | Coordinate with provenance/EOD test-gap lanes. |

## Forward runtime integration finding

The installed `IDXTrade-ForwardEOD` action points to
`C:\Users\Sam\OneDrive\Documents\Project\idx-trade` on
`integration/forward-eod-automation-monitoring@b94b272`. That branch contains
the primary EOD capture and model fan-out, but does not contain
`o2_1_sealed_shadow_runtime.py` or `reliability_v1_forward_shadow.py`.
Those modules are present on accepted sidecar branches. The canonical EOD
runner requests the primary model worker asynchronously; sidecar errors are
collected in a worker result structure, while the scheduled PowerShell action
does not persist/inspect that result as an operator-visible sidecar failure
record. Existing external 2026-08-12 O2.1 and Reliability artifacts prove that
artifacts exist, not that future scheduled sessions will create them.

Actual read-only Windows state observed during this audit:

- `IDXTrade-ForwardEOD`: `Ready`, enabled, daily `18:00 +07:00`, logon
  trigger, `StartWhenAvailable=True`, `MultipleInstances=IgnoreNew`.
- `IDXTrade-ForwardOpenArchive`: disabled.
- Stockbit intraday task: separate task, enabled/Ready; last observed run
  result was `0`.
- Primary external forward runtime contains 2026-08-12 session/model
  artifacts and `eod_automation/latest.json` with
  `status=NO_MISSING_SESSION`, `outcome_access=LOCKED`, and
  `forward_outcomes_accessed=false`.
- Scheduler telemetry still showed the EOD task's sentinel 1999 last-run time
  and result `267011`; this should not be represented as proof of a successful
  scheduled execution merely because an external runtime artifact exists.

This finding is explicitly `COORDINATE_WITH_ACTIVE_LANE` for the Canonical EOD
adversarial audit and Forward-100 evaluator execution review. No runtime code
was patched here.

## Model, hash, outcome-lock, and verdict review

Direct external hash checks matched the frozen runtime contracts:

- V2 model: `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
  model manifest: `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`.
- V3-B model: `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
  feature-order SHA: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
  manifest: `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`.
- O2 model: `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
  feature-order SHA: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
  model manifest: `535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2`.

The Stage-5 global markers were found in both preserved external roots and
record `holdout_consumed=true` / `RANKING_V1_ONLY`; no retry was attempted.
The historical decision chains reviewed remain substantively coherent:
Probability V1 deferred, Expected Payoff V1 no-survivor, O2.1 historical
no-survivor, and Reliability V1 accepted only as an outcome-blind sidecar.
No current verdict reversal was found.

Remaining identity/reproducibility weaknesses:

- O2.1 artifact inventory and O2 forward counter are not fully self-owning or
  independently pinned to model/protocol identity in their loaders.
- O2 forward loading does not enforce the accepted O2 artifact-bundle
  checkpoint/status manifest.
- Reliability status reporting is weaker than sidecar creation validation.
- V2/V3-B verifiers omit parts of feature/population/source/environment
  identity that are recorded in some artifacts but not always enforced.
- `pyproject.toml` uses dependency ranges and no repository lock/hash file is
  tracked; external O2 environment evidence is descriptive, not enforced.

These are `COORDINATE_WITH_ACTIVE_LANE` where they touch forward evaluation or
the provenance registry.

## Documentation and lineage inconsistencies

- `origin/main:coordination/TEAM_STATUS.md` is the current authority, but
  branch-local `CURRENT_STATUS`/`PROJECT_LEDGER` copies are divergent snapshots
  and can present older phases as current.
- The Stockbit row names the data branch but anchors verification at
  `b94b272`, which belongs to the integration EOD branch rather than the
  Stockbit branch. The row should name both implementation and verification
  refs explicitly.
- The earlier EOD `NOT_FOUND`/Access-denied checkpoint is not explicitly linked
  as superseded by the installed checkpoint.
- Accepted broker-margin and Stockbit handoffs still contain pending/non-final
  head placeholders despite later acceptance refs.
- `docs/V2_MIGRATION_AUDIT.md`/README wording overstates implemented immutable
  source authority and future monitoring relative to the current research-only
  root policy.
- The sample tradability snapshot claims `as_of_date=2025-07-30` while its
  references are under a 202508 path and lack publication/validity evidence;
  it cannot establish PIT availability at that as-of date.
- Main has no tracked sector/IDX-IC history adapter/manifest supporting the
  architecture illustration; sector-history modeling remains blocked.

## Safe remediation decision

No source/model/data-contract patch was applied. Every executable P1 finding
touches an active EOD, provenance, or forward-evaluator ownership boundary, so
duplicating a fix here would create competing semantics. This branch adds only
the recovery checkpoint, this factual audit checkpoint, and the handoff. The
smallest safe next engineering actions are strict boolean/date/domain/source
validation, immutable bundle publication, mandatory verified environment/input
manifests, and canonical sidecar integration under the owners listed above.

## Validation and stop condition

The five prior read-only audit outputs were synthesized; they were not
respawned. Direct checks were isolated library reproductions and metadata/hash
verification only. The current repository baseline includes an existing
storage-test expectation mismatch (`39 passed, 1 failed` in the prior targeted
run): the fixture changes both `raw_close` and `vendor_adj_close`, while the
test expects one conflict. This is recorded as a test-contract defect, not
silently changed in this audit because storage/revision semantics are owned by
the active engineering lanes.

Stop after pushing this branch for independent ChatGPT review. Do not run
experiments, providers, models, forward outcomes, bulk repairs, or main merge.
