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
  `4e7fdf28ecf3080f19ed647b7a604cd14c6045a65c39fbdecb3bd39f25413bd3`
- Frozen-window robustness code:
  `research/alpha_stage_a_robustness_v2.py`
- Robustness code SHA-256:
  `8f60b26bb812bfc5f513a91c97797f14c7e18552b405b682c88d02243a67a80c`
- Independent verifier:
  `research/verify_alpha_stage_a_v3.py`
- Independent verifier SHA-256:
  `075cb462bbafa502c211f777e05fcdbcca842785c855d75b92305a60ade47d2e`
- Staging directory:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-v3\20260919T-corrected-v3\`
- Feature parquet SHA-256:
  `1fe49a16588f48d3baf8b26dd72281e4b3d19632168d32b8f6c383b93cdabc63`
- Audit JSON SHA-256:
  `84e1f07206667c9570283c471768c4fa63289a9356ef341da881049873ee0cf0`
- Manifest JSON SHA-256:
  `f374d6e6e0cfa401f9f8fd669b0c93a7b852d9c82ae558e23bd17ee3e8a97edc`
- Frozen-window robustness JSON SHA-256:
  `9e0d43a66c682c600e215b1075c5e159794a24441d0c9f3198221a83013a3b31`
- Independent audit JSON SHA-256:
  `14f4adec409a15c68158c7b5d79738ca4b452d2e8b11221861ce3afb07d64c18`

The independent audit returned `PASS`: exact schema, zero duplicate keys,
all source rows present, no scores/ranks outside the eligible mask, ranks in
`[0,1]`, all source/code/artifact hashes match, exactly 600 frozen sessions
are audited, and both audit paths report `outcome_accessed=false`.

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
artifacts are not opened under the admission gate.

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
