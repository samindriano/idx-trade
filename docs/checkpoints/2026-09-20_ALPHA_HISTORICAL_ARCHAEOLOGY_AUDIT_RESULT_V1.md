# Historical Alpha Archaeology Audit V1

Date: 2026-09-20 (Asia/Jakarta)  
Experiment: `ARCHAEOLOGY-037`  
Status: `SUPPORTED_BOUNDED_MAP_WITH_REPLAY_GAPS`

## Question and boundary

Is the existing historical failure/lineage map complete enough at family level,
and which older implementations remain source-level replayable? This was a
read-only, outcome-blind metadata/tree audit. It inspected current archaeology,
failure-taxonomy, tombstone, and retained-lineage documents plus Git tree names
on six retained refs. It did not read historical target/outcome payloads,
forward-return arrays, incumbent score arrays, provider data, or cloud state.

## Result

The family-level map is supported and sufficiently complete for current
research prioritization. Exact old implementation replayability is only
partial. The retained refs and safe relevant tree-name counts are:

| Lineage | Commit | Safe relevant paths | Protected-looking paths read |
|---|---|---:|---:|
| Ranking V2/V3/V4-A:C | `9378943bde44b33e311bec1e1daf38ca5cd9b5d3` | 131 | 0 |
| V4 CA/identity | `806895880e262641820dbe30e85a1faf7f26b87f` | 160 | 0 |
| V4-X1/O2 | `bfe40f69090c2cc3550bf4d00335643fba70fc5c` | 224 | 0 |
| Alpha frontier | `1537ba35e79c73e64fee19d499190f529122403b` | 14 | 0 |
| Financial representation | `f2f401e3e68893426858a60e1093832cf122bd41` | 16 | 0 |
| Foreign-flow representation | `10a72f25b840d3689e39352c779d95ca33c40f77` | 8 | 0 |

Protected-looking paths were counted by the audit but deliberately not read;
the external result records counts of 25, 46, 46, 10, 1, and 0 respectively.

## Family classification

- Ranking V1/V2 and V3-A:E: family map supported; retained specs/checkpoints and
  source references provide bounded replayability. Historical headlines are not
  reopened.
- V4-A:C: family map supported; participation, price-path, and
  cross-sectional first-pass records are retained at reference level.
- V4-D sector: source-admission blocked, not mechanism-rejected; no daily PIT
  sector authority was admitted.
- V4-E/F/G: family map supported, but exact old implementation replayability is
  partial. Financial and foreign-flow retained refs exist, while not every
  historical formulation is present in the active lane.
- V4-X1/O2: lineage and integrity conclusions are supported; incumbent/target
  material remains protected or lineage-only.
- Auxiliary payoff, reliability, path-risk, and execution-source work:
  tombstones/source-blocked conclusions are durable; recreating deleted
  implementations without new evidence would be redundant.

## Historical interpretation locked by this audit

The latest PIT/integrity adjudication controls older promotion headlines. In
particular, the early V3-B Structure-Lite promotion is not current survivor
evidence because later KOCI pre-listing contamination and a failed late paired
gate changed its interpretation to `PIT_FAIL / OOS_FAIL`; clean V2 remains the
trusted historical parent/control. This is a reinterpretation of evidence, not
a new predictive run.

## Red-team and limitations

The audit verified that current source documents exist, all six retained refs
resolve, relevant safe tree names exist, and protected-looking historical paths
were not read. It cannot prove executable replay from tree names alone, cannot
prove global source absence, and does not revalidate historical predictive
results. A retained ref may contain artifacts outside the inspected metadata
scope.

## Disposition

`ARCHAEOLOGY-037` closes the current family-level archaeology lane as
`SUPPORTED_EXHAUSTION` for safe metadata-only work. Exact replay should reopen
only when a genuinely new historical artifact is required to resolve a disputed
classification. The program should move to the next non-redundant outcome-blind
question; no C5 or protected comparison is authorized by this result.

Evidence:

- `research/alpha_historical_archaeology_audit_v1.py`
- `research_knowledge/historical_archaeology_audit_v1.json`
- external result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_historical_archaeology_audit_v1.json`
- code SHA-256:
  `bb6214e69b4553be52ed07b40344e5a57af6ed1af4d2798d408f819c6b51fff9`
- external result SHA-256:
  `dd1201a169e4f0f9b2194c637e3f91204f20cf5146ac22a58dd65abeb97e904c`
