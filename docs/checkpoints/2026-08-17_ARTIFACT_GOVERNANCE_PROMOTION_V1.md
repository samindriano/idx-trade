# Artifact Governance V1 — actual Git promotion

Date: 2026-08-17
Branch: `codex/artifact-governance-v1`
Source main snapshot: `d3f49a61ff51fe9075f3cfca12956a976219b8b2`
Accepted source checkpoint: `ed13ee0812e8db21d580e922f4e346873aa7b3cd`

## Decision

`ARTIFACT_GOVERNANCE_V1_PROMOTION_COMPLETE_EXTERNAL_PAYLOADS_RETAINED`

The accepted 126-session IDX data-gate snapshot was promoted selectively.
Thirteen small artifacts are now tracked in Git, with exact source/promoted
SHA-256 values in `docs/artifact_governance/ARTIFACT_PROMOTION_V1.csv` and
`artifacts/registry/ARTIFACT_REGISTRY_V1.json`.

## Promoted scope

- six `PUSH_TO_GIT` canonical/reference tables: official sessions, security
  master, scope exclusions, merged and curated tradability intervals, and
  official split/reverse actions;
- six `PUSH_SUMMARY_OR_MANIFEST_ONLY` summaries: action summary, exchange
  source report, exchange summary, full-universe gate summary, certification
  ladder, and certification summary;
- one scrubbed pointer to the certified snapshot manifest.

Promotion source: logical root `IDX_TRADE_EXTERNAL_ROOT`, snapshot
`idx-trade-data-gate-20260808u/certification`. The `p` snapshot was checked;
exact duplicate security-master, scope-exclusion, and split-action files were
not copied again.

## Explicitly retained external

The original certified manifest remains external because it contains absolute
local paths. The model-safe Parquet panel, 21 MB tradability-anchor table,
raw/provider files, attachments, full OHLCV/Financial PIT/Foreign Flow panels,
model binaries, runtime state, credentials, and outcomes were not promoted.

## Verification

- registry/promotion focused tests: `4 passed`;
- source-vs-Git SHA/size verification: PASS for all exact copies;
- scrubbed pointer source-manifest SHA verification: PASS;
- `git diff --check`: PASS;
- full pytest: `1 failed` pre-existing unrelated storage expectation; the
  failure is `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  (2 independent conflicts are returned, while the old test expects 1).

No source artifact, scientific result, model, outcome, provider, or runtime
was changed.
