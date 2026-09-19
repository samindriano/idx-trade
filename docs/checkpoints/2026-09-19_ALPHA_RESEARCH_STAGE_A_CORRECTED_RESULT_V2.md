# Alpha Research Program — Corrected Stage A Result V2

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Protocol: `2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1`  
Stage: `A_OUTCOME_BLIND`  
Result: `PASS_STRUCTURAL_ONLY / NO-GO FOR HISTORICAL ALPHA CLAIM`

## Correction lineage

The first Stage A implementation was independently rejected as non-conformant:
its beta denominator was reversed, it did not join the authoritative decision
mask before aggregation/ranking, it did not explicitly validate Financial
knowledge time, and its temporal audit did not use the frozen six 100-session
window. Its output remains in the earlier staging directory but is invalid
engineering evidence and was never used for an alpha claim.

The intermediate masked implementation was also retained as a separate run,
but its review exposed that its rolling features still operated on surviving
rows rather than a full official-session grid and its Financial ranks were
formed before the eligibility join. It too is not evidence.

The corrected implementation keeps the same four hypotheses and candidate
budget. It makes the following conformance repairs before any target access:

- reindexes each ticker to all 1,260 official sessions for rolling windows;
- uses the active regular-trade and trailing-60-session liquidity mask before
  market aggregation and candidate ranking;
- estimates C1 beta through `t-1` and divides covariance by market variance;
- treats zero/invalid turnover as missing;
- checks Financial knowledge time <= decision timestamp, period date <= signal
  date, bundle flags, provenance, and the full five-field requirement before
  ranking;
- records source/code/schema/timestamp/commit hashes;
- writes only to the isolated staging root.

EOD `t` values are allowed because the decision is made after EOD `t` for the
`t+1` transition. Only future rows are forbidden; the C1 beta fit explicitly
excludes the current row.

## Reproducibility

- Corrected code path: `research/alpha_stage_a_v2.py`
- Corrected implementation identity: `alpha_stage_a_v3_corrected`
- Corrected code SHA-256:
  `62a16137d039c0304e00fbf91de65ed5c70d50952faccf2aff1b0a587f49e59a`
- Frozen-window robustness code:
  `research/alpha_stage_a_robustness_v2.py`
- Robustness code SHA-256:
  `8f60b26bb812bfc5f513a91c97797f14c7e18552b405b682c88d02243a67a80c`
- Independent verifier:
  `research/verify_alpha_stage_a_v3.py`
- Independent verifier SHA-256:
  `075cb462bbafa502c211f777e05fcdbcca842785c855d75b92305a60ade47d2e`
- Final guarded staging directory:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Feature parquet SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Audit JSON SHA-256:
  `f9bfaf368d7157b9b35ff282ffcf18ff06579b9978b5a029609dacc7ecdaa38b`
- Manifest JSON SHA-256:
  `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Frozen-window robustness JSON SHA-256:
  `93b1c5379da09dd82e3550c6552190a15a018ae5f87aa36d68259dc5d28cd011`
- Independent audit JSON SHA-256:
  `c6629caf46ff1945ddc5bd9e6a2fe4e174c179a18c854411e8b8ed656368cbc6`

The independent audit returned `PASS`: exact schema, zero duplicate keys,
all source rows present, no scores/ranks outside the eligible mask, ranks in
`[0,1]`, all source/code/artifact hashes match, exactly 600 frozen sessions
are audited, and both audit paths report `outcome_accessed=false`.
The final guard pass additionally proves canonical session/anchor hashes,
source-key closure, and absence of network/provider imports or HTTP calls in
the construction code.

## Corrected structural results

The decision universe contains 310,761 eligible panel rows across 711 tickers
under the frozen active/liquidity rule. Candidate coverage is measured only
against that eligible universe:

| Candidate | Finite eligible rows | Eligible coverage | Dates | Tickers |
|---|---:|---:|---:|---:|
| C1 residual reversal | 295,243 | 95.0065% | 1,141 | 704 |
| C2 participation confirmation | 310,761 | 100.0000% | 1,201 | 711 |
| C3 financial quality/growth | 30,994 | 9.9736% | 291 | 265 |
| C4 path efficiency reversal | 310,323 | 99.8591% | 1,201 | 711 |

Corrected full-row Spearman relationships were C1/C2 `-0.23035511`, C1/C3
`-0.02365537`, C1/C4 `0.41126169`, C2/C3 `-0.04554962`, C2/C4
`-0.11908659`, and C3/C4 `-0.03261201`. These are internal feature
diagnostics only; incumbent overlap remains `UNKNOWN` because incumbent score
artifacts are not opened under the admission gate. A focused read-only
inventory of the known `forward_monitoring/model_runs` area found incumbent
score artifacts only for post-cutoff forward dates; those artifacts were not
used as a historical same-window comparator.

The frozen robustness audit uses the last 600 official sessions split into six
100-session folds. C1 coverage ranges from 99.45% to 99.98%, C2 is 100% in all
folds, and C4 ranges from 99.77% to 100%. C3 is absent or effectively
single-name in early folds, reaches 24.60% in fold 4, and 38.69% in folds 5–6;
its top-10 ticker share is 15.63% in fold 4 versus roughly 3%–4.6% for the
market-only candidates. This is a structural coverage/concentration warning,
not predictive evidence.

## Status and blocker

- C1, C2, and C4: `FUTURE_RESEARCH` / structural capability only.
- C3: `BLOCKED` by partial Financial admission and low/late coverage.
- No candidate has target access, IC/ICIR, OOS, friction, or prospective
  evidence. No candidate is a `RESEARCH_SURVIVOR`.
- The exact remaining blocker is unchanged: authoritative Data QA has not
  certified a population-wide, historical-as-of, same-science source subset
  for new-alpha claims. Therefore the historical outcome stage remains closed.
