# Tooling Semantic Challenger Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Experiment: `TOOLING-038`  
Status: `PASS_KNOWN_FALSE_GREENS_EXPOSED`

## Question and boundary

Does the outcome-blind firewall/authority-packet tooling reject semantically
disguised protected-looking fields and unknown nested packet fields? The test
uses temporary synthetic text, Parquet, and JSON fixtures only. No production,
provider, cloud, canonical, incumbent, target, or outcome artifact was read.

## Results

| Synthetic mutation | Current result | Interpretation |
|---|---|---|
| Text field `future_ret5_value` | `PASS` | false green; token-only scan is not semantic protection |
| Parquet columns `future_ret5_value`, `secret_signal` | `PASS` | false green; schema is not an explicit allowlist |
| Unknown nested field in `candidate_matrix.C1` | `PASS` | false green; nested packet schema is permissive |
| Unknown top-level packet field | `FAIL` | top-level allowlist works |
| Canonical JSON with reordered keys | equal after explicit sorted serialization | deterministic serialization is possible but not enforced by packet schema |
| Expected verifier-version hash pin | absent and recorded | stale verifier-version binding remains a gap |

The challenger therefore confirms the previously suspected limitations with
independent synthetic fixtures. It does not justify changing the firewall
semantics inside this batch because a complete allowlist would need an explicit
schema contract and compatibility review.

## Disposition

Keep the current firewall PASS interpretation bounded: it proves required-path,
hash, and denylist checks, not semantic protected-payload absence. Do not use a
PASS as scientific admission or as proof that arbitrary nested fields are safe.
The next legitimate hardening would be a separately reviewed semantic schema
allowlist, independent formula challenger, and explicit verifier-version pin.

Evidence:

- `research/alpha_tooling_semantic_challenger_v1.py`
- `research_knowledge/tooling_semantic_challenger_v1.json`
- external result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_tooling_semantic_challenger_v1.json`
- code SHA-256:
  `eb171a9209ef1143e939d606e7ea2da5833914083d4b08980f0ceee3920aafa7`
- external result SHA-256:
  `0f389e4fd46795f56e0fed457e101174b8c07fa388c95de27ab90bea6488581d`
