# IDX-Trade Real Score Validation V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS ON EXPLICIT SHADOW ADAPTER / FULL E2E REPLAY STILL BLOCKED**

## Real score evidence

- Source manifest: D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-09-17\v4_x1_clean_geometry3_prospective_v1\manifest.json
- Source manifest SHA-256: d3e627a4440ca9225617599328bbd12af30b9ba06a3f921fb1ee7710eb834be0
- Source score artifact SHA-256: 909e6e98f576434d8151bc96b30b4208fc76cb30e3fa50cfc472ecc02c47b72c
- Shadow adapter: C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\derived\score_manifest_2026-09-17.shadow-adapter.json
- Shadow adapter SHA-256: 66b8db910bf006bec7a631de56ca804093fa49c3d3bd39dffc96de169e0aa861
- Shadow artifact path: the hash-identical copied score parquet under the
  shadow input root

The adapter preserves the real manifest content and changes only the
artifact_path binding from the absolute source path to the hash-identical
shadow copy. The source manifest was not rewritten. The adapter is derived,
shadow-only, and not promotable as a source artifact.

## Local defect found and fixed

The real manifest represented the freeze boundary as
2026-08-20T19:08:44+07:00. The candidate contract represented the same instant
as 2026-08-20T12:08:44+00:00. The verifier previously compared raw strings and
rejected the real artifact with
DECISION_V1_UPSTREAM_FREEZE_BOUNDARY_CHANGED.

The isolated candidate fix makes the verifier compare timezone-aware instants
in UTC. It still rejects malformed, timezone-naive, or different instants. No
model, feature, scientific blob, alpha formula, rank logic, or score value was
changed.

## Validation results

- Focused verifier/property tests: 26 passed.
- Full candidate suite: 906 collected, reached 100%, exit code 0; three
  pre-existing pandas FutureWarnings remained.
- Shadow score validation: PASS.
- Session date: 2026-09-17.
- Verified score rows: 296.
- Alpha tie diagnostic rows: 82.
- Verified artifact SHA remains
  909e6e98f576434d8151bc96b30b4208fc76cb30e3fa50cfc472ecc02c47b72c.

This validates the real score artifact under an explicitly labelled shadow
path adapter. It does not establish paper state, prepared execution, CA
authority, execution chain, or historical economic equivalence.
