# Handoff — Forward CA Zapi Dividends Audit Result

from: `Codex`
to: `ChatGPT/Forward-CA-Attestation`
task_id: `FORWARD-CA-ATTESTATION-V1-ZAPI-DIVIDENDS-AUDIT`
model_used: `Luna xhigh`
reasoning_level: `xhigh`
source_repository: `samindriano/idx-trade`
source_commit: `8e3be9f937f1ec7315b822d2f1c686042187b24a`
branch: `integration/forward-ca-attestation-v1`

## Result

Final verdict:
`AUDIT_HARNESS_BUG_FIXED_REVIEW_EXISTING_ARTIFACT_AGAIN`

The existing Zapi capture is not sufficient to decide endpoint admission. It
is a valid HTTP-200 nested empty `data` envelope, but the request omitted the
catalog-declared `search` filter and was not ticker-scoped. Forward CA V1.1
remains blocked and was not created.

## Files changed

- `scripts/probe_zapi_idx_dividends_v1.py`
- `scripts/review_zapi_idx_dividends_probe_v1.py`
- `tests/test_zapi_idx_dividends_harness.py`
- `docs/checkpoints/2026-08-21_ZAPI_IDX_DIVIDENDS_BOUNDED_AUDIT_RESULT.md`
- this handoff

External output written without changing existing raw artifacts:

`D:\Documents\Project\idx-zapi-dividends-probe-20260821-v1-r2\PROBE_REVIEW_OFFLINE_REMEDIATED.json`

## Evidence

- raw response SHA:
  `963a2bd8a0599bf63ead4c517165ade688de72144584356ce646cf9e714bf3fa`
- catalog SHA:
  `72cecf672a3635868c30b38d0b5a4908ef28cd5817b686065c2cc9820f24efbd`
- offline remediation review SHA:
  `32e15d083211e85f1de4608a1b688357748ca40457f7ac1f231989edecdbab7a`
- raw shape: object → `data` object → `items=[]`, `count=0`, `total=0`,
  `hasMore=false`; provider/dataset are `idx`/`dividends`.
- existing request params: `page=1&length=20`; scope mode recorded global.
- catalog also exposes `search`, so the existing request is audit-incomplete.

## Validation

- focused harness tests: `2 passed`
- full pytest: `416 passed, 0 failed, 3 warnings`
- py_compile: PASS for both probe/reviewer scripts
- `git diff --check`: PASS
- authenticated Zapi requests in this task: `0`

## Decisions and boundaries

- no V1.1 setup or promotion;
- no V4-X1 alpha/Decision/frozen identity change;
- no provider, model, outcome, or historical backfill access;
- no existing raw/manifest/review artifact overwrite;
- one future request is required only after authorization, using
  `search=BBCA` plus a known non-empty year/month and the existing page bound.

recommended_next_action: independently authorize one corrected ticker-scoped,
known-nonempty-period request; then rerun the offline semantic gate. Do not
label the endpoint permanent NO_GO from the current empty unscoped page.

