# V4 Corporate-Action Price-Basis Continuity Gate V1 — Result

Date: 2026-08-17 (Asia/Jakarta)
Branch: `data/idx-v4-corporate-action-continuity-gate-v1`
Parent freeze: `research/idx-ranking-v4-3-target-execution-freeze-v1@b536c832730bd0c5e2dd6952b44cf9b11b4573f9`
Status: `BLOCKED`

## Scope and boundary

This was an outcome-blind continuity/support census only. The exact V4
decision universe was rebuilt from the pinned PIT panel/security-master path:
739 decision tickers overall, with 610 of them present on at least one of the
frozen 600 validation dates and 172,395 frozen decision rows. The exact
frozen validation identity remains 600 dates / 6 folds × 100.

No provider call, new CA acquisition, target/return/rank materialization,
model fit, performance metric, protected outcome, or fresh-forward outcome
was accessed.

## Official evidence inventory

The existing official artifact root was reused without modification:
`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2`.
The root is bounded candidate/provenance evidence, not a market-wide no-event
ledger. Its manifest and source-file hashes are pinned in the generated
manifest and summary.

| Event family | Evidence rows | Source | Effective-date result |
|---|---:|---|---|
| Stock split | 7 | IDX `GetIssuedHistory` candidates | unresolved; `TanggalPencatatan` is not admitted as generic effective date |
| Reverse split | 0 | — | no evidence; absence is not a no-event proof |
| Stock dividend | 3 | KSEI registered-security history | unresolved KSEI event-date semantics |
| Bonus shares | 1 | IDX `GetIssuedHistory` candidate | unresolved effective date |
| Rights / HMETD | 10 | 1 IDX candidate + 9 KSEI rows | unresolved linkage/effective date |
| Mandatory conversion | 4 | KSEI registered-security history | unresolved market-effective date |
| Merger | 0 | — | no evidence; absence is not a no-event proof |
| Capital restructuring | 1 | IDX `GetIssuedHistory` candidate | unresolved effective date |

Cash-dividend evidence was not treated as a continuity blocker. The existing
CA source audit still records bounded KSEI/IDX cash-dividend/proxy rows, but
they cannot certify price-basis continuity and are excluded from the
mechanical-event ledger.

## Frozen-600 census

For every frozen decision row and horizon H5/H10, the ledger uses the only
passing state allowed by the frozen V4 generation-1 contract:
`RESOLVED_NO_MECHANICAL_DISCONTINUITY`.

| Metric | Result |
|---|---:|
| Continuity ledger rows | 344,790 (172,395 × H5/H10) |
| `PRICE_CONTINUITY_UNRESOLVED_COVERAGE` | 344,740 |
| `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE` | 50 |
| H5 dates at ≥90% continuity | 0 / 600 |
| H10 dates at ≥90% continuity | 0 / 600 |
| Consensus dates at ≥90% continuity | 0 / 600 |
| Minimum H5/H10/consensus continuity rate | 0.0% |

The 50 effective-date cases are candidate events crossing an individual
forward window without a proven market-effective date. The remaining rows
are explicit coverage failures: no market-wide no-event evidence exists, so
missing rows are not converted into a false “no event” pass.

## Verdict

`BLOCKED`

`corporate_action_continuity_certified` remains false. The existing CA
artifacts are useful for bounded event discovery and provenance, but they do
not establish the market-wide effective-date/no-event evidence required by
V4. No rescue, adjusted endpoint-price shortcut, or V4 contract change was
made.

## Artifacts and hashes

External output root:
`D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3`

- Full continuity ledger: 64,650,811 bytes;
  SHA-256 `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`.
- Event evidence CSV SHA-256:
  `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`.
- Event-family counts CSV SHA-256:
  `6e3f7fa9f8b3e04bb723999d28e4992a31dd1ceb115243f42dd035862d0bd544`.
- Frozen per-date coverage CSV SHA-256:
  `4f246f6f5773e978f177ea786bb8cce8d8e860ce5240818aa0287730ef35f4f8`.
- Output manifest SHA-256:
  `4dd75efc2542082d535b11131b59fcaf5f422d6cc0b567715435d65f6d026bca`.
- Decision-ticker universe SHA-256:
  `700037b38a7202e4c8a58b1068a885f903a568493f379b7fcb3afa88cc620bbe`.

Pinned input hashes are recorded in the promoted summary/manifest, including
calendar `661d3f19...`, panel `67d3d2b5...`, security master `c8efa462...`,
and frozen validation identity `91fe0e5a...`.

## Validation

- Focused continuity tests: `3 passed`.
- Full pytest: `85 passed, 1 failed` out of `86` collected. The only failure
  is the pre-existing unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expectation (`expected 1`, current storage contract returns 2 independent
  raw/vendor conflicts).
- `py_compile`: passed for the continuity runner.
- `git diff --check`: passed.
