# Decision V3 — Adversarial Kill Diagnosis Result

Date: 2026-08-21 Asia/Jakarta

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_KILL_DIAGNOSIS`

This checkpoint freezes the single authorized local diagnosis run performed from audited implementation HEAD `5f6b75d615f4e1326889c3868d79e20e8eca8923`.

## Frozen lineage

- V2 structural manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`
- V2 structural plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`
- historical source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- historical score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- sessions: `600`
- score rows: `172,697`
- local artifact root: `D:\Documents\Project\idx-v4-x1-decision-v3-kill-diagnosis-20260821-v1`
- diagnosis manifest SHA-256: `9ab7f282de86556b3c158f7e1c31c8883b38f9108e94ecd8e43a92b9344c8444`

All guards remained false for Decision simulation, alternative rules/thresholds, sweeps, realized returns/PnL, H5/H10 Decision internals, protected/fresh-forward access, providers/network, and model refit/retune.

## 1. Global fresh-current-Top10 persistence

Across `3,347` fresh current-Top10 observations (`3,342` next-session evaluable), previous-rank proximity is informative globally, not only on V2-underfilled sessions:

| Previous rank | n | Next Top-10 | Next Top-20 |
|---|---:|---:|---:|
| <=20 | 1,555 | 43.23% | 66.26% |
| 21–30 | 423 | 33.81% | 54.85% |
| 31–50 | 406 | 30.05% | 50.00% |
| 51–100 | 446 | 26.46% | 36.10% |
| 101–200 | 375 | 27.20% | 38.93% |
| >200 | 123 | 20.33% | 27.64% |
| previous absent | 19 | 26.32% | 36.84% |

Interpretation:

- `previous <=20` is the strongest challenger evidence state.
- `previous 21..50` is materially weaker than core but materially stronger than distant history as a broad class.
- evidence beyond rank 50 is weak and not monotonic enough to justify finer sub-threshold tuning.
- previous absence has only `n=19`; it does not support granting the same temporal-evidence status as a previously observed distant rank.

The reporting bins remain descriptive. No alternative Decision threshold was simulated.

## 2. Severe-collapse replacement context

There were `583` V2 `EXIT_PENDING_1` observations with current rank `>50`.

- next-session recovery to rank <=20: `18.35%`
- therefore non-recovery to <=20: approximately `81.65%`
- share occurring on V2 high-churn (>=3 replacement) transitions: `45.11%`
- at least one same-session unheld core challenger (`previous <=20`, current Top10): `87.99%`
- at least one core or near challenger (`previous <=50`, current Top10): `95.71%`
- mean core supply: `2.424`; median `2`
- mean near `21..50` supply: `1.787`; median `2`

Interpretation:

- severe first-day collapses usually do not recover immediately.
- replacement evidence is usually present on the same session.
- however, severe collapses are also concentrated on already-busy sessions, so immediate severe exit remains a genuine churn-risk hypothesis rather than a free improvement.

This diagnosis does not estimate the exact V3 trajectory.

## 3. Underfill supply after removing already-consumed V2 Core candidates

The exact V2 underfilled set remains:

- sessions: `135`
- vacancy-days: `307`
- mean vacancies/session: `2.274`
- median vacancies/session: `2`

After correctly excluding core candidates already consumed by V2, residual `Core + previous 21..50` supply is sufficient to cover every remaining vacancy on only:

- `77 / 135` sessions = `57.04%`

Residual supply summary:

- mean `Core + 21..50` supply: `1.926`
- median: `2`
- p75: `3`

Weak blocks remain the same mechanism at higher intensity:

- Block 3: adequacy `50.88%`, `57` underfilled sessions, `144` vacancy-days
- Block 6: adequacy `52.94%`, `34` underfilled sessions, `74` vacancy-days

Interpretation:

The first V3 preregistration's Tier-B-only capacity rescue is insufficiently supported. `previous 21..50` should not be assumed to eliminate underfill.

## 4. What the kill diagnosis supports

The evidence supports retaining these generic concepts:

1. **severity-aware incumbent handling**: rank `>50` is meaningfully different from mild `21..50` deterioration;
2. **graded challenger evidence**: `previous <=20`, `21..50`, and distant previous rank contain different levels of persistence evidence;
3. **permission should be graded rather than binary**: weak evidence may justify lower-priority vacancy use without granting turnover-creating authority;
4. block-specific/regime-specific Decision logic remains unsupported.

## 5. What the kill diagnosis rejects or weakens

The following exact design claim from prereg V1 is not accepted:

> only Tier A (`previous <=20`) and Tier B (`previous 21..50`) may ever fill vacancies, while every previous rank >50 is completely unqualified.

That pairing leaves too much policy-created capacity shortage in the observed V2 stress set.

Previous-absent candidates remain a separate weak-evidence case because the global sample is only 19.

## 6. Scientific boundary

This result does not authorize:

- Decision V3 implementation from prereg V1;
- V3 structural replay;
- threshold sweep around 50;
- current-rank sub-thresholds inside Top10;
- H5/H10 rescue rules;
- returns/PnL inspection;
- alpha V4-X2 work.

## 7. Next step

Revise the Decision V3 preregistration once, using the smallest generic graded-permission architecture consistent with this result, then perform another adversarial pre-implementation audit before writing Decision code.