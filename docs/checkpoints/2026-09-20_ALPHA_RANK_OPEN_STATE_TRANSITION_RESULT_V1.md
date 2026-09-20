# C1-C4 Rank-to-Open State Transition Audit — Result V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_ONLY / ADMISSION BLOCKED`

## Conclusion

The audit passed its structural contract and found materially different
historical Open readiness across the frozen Top-30 rank selections. C1, C2,
and C4 have roughly 29–33% of selected slots marked `PENDING_OPEN`; C3 has
0.42% pending among its selected rows but has a sparse complete Top-30 window
(`278/600` sessions). This is a capability/state-transition finding only. It
does not establish PIT timing, source authority, corporate-action correctness,
survivorship safety, executable fills, or predictive value.

## Fixed scope and privacy gates

- Frozen tail window: `600` official sessions, `2024-01-12` through
  `2026-07-31`.
- Selection: stored C1-C4 rank, descending, ascending ticker tie-break, `K=30`.
- `READY_OPEN`: positive finite same-row Open with `Low <= Open <= High`.
- `PENDING_OPEN`: every selected row failing that condition; no imputation.
- Turnover denominators remain fixed at `K=30`; pending slots are not silently
  renormalized.
- Outcome/target/provider/canonical/protected access: `FALSE`.
- Open imputation: `FALSE`.
- Structural invariant check: `PASS` (`READY + PENDING = selected`; band counts
  reconcile; entry count equals ranked-out plus rank-missing exits).

## Aggregate result

| Candidate | Complete Top-30 dates | Selected slots | Ready slots | Pending slots | Pending rate | Mean requested turnover | Mean Open-ready turnover | Rank-missing exits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 residual reversal | 600 | 18,000 | 12,696 | 5,304 | 29.4667% | 0.421536 | 0.601948 | 87 |
| C2 participation confirmation | 600 | 18,000 | 11,991 | 6,009 | 33.3833% | 0.329104 | 0.561770 | 172 |
| C3 financial quality/growth | 278 | 8,340 | 8,305 | 35 | 0.4197% | 0.109333 | 0.115030 | 615 |
| C4 path-efficiency reversal | 600 | 18,000 | 12,443 | 5,557 | 30.8722% | 0.236950 | 0.486366 | 118 |

The Open-ready turnover is higher than requested turnover for C1/C2/C4 because
the fixed-K metric exposes ready-slot loss and re-entry around missing Open;
it is not an executable turnover estimate.

## Pending distribution and transition detail

| Candidate | Median pending slots/day | Maximum pending slots/day | Median pending rate/day | Max pending streak | Entry / ranked-out / rank-missing / hold |
|---|---:|---:|---:|---:|---:|
| C1 | 1 | 30 | 3.3333% | 19 | 7,575 / 7,488 / 87 / 10,395 |
| C2 | 1 | 30 | 3.3333% | 30 | 5,914 / 5,742 / 172 / 12,056 |
| C3 | 0 | 4 | 0% | 6 | 902 / 287 / 615 / 7,348 |
| C4 | 1 | 29 | 3.3333% | 57 | 4,258 / 4,140 / 118 / 13,712 |

Pending counts by rank band were:

| Candidate | Rank 1–10 | Rank 11–20 | Rank 21–30 |
|---|---:|---:|---:|
| C1 | 1,813 / 6,000 | 1,753 / 6,000 | 1,738 / 6,000 |
| C2 | 2,113 / 6,000 | 1,986 / 6,000 | 1,910 / 6,000 |
| C3 | 2 / 2,780 | 7 / 2,780 | 26 / 2,780 |
| C4 | 1,943 / 6,000 | 1,829 / 6,000 | 1,785 / 6,000 |

The C3 rank-missing exit count is high because its stored rank support is
sparse; that is a support/identity observation, not evidence that C3 is
better or worse.

## Interpretation and remaining unknowns

This audit establishes that aggregate Open coverage is not equivalent to
rank-conditioned readiness. It gives a reusable structural state vocabulary
for future operational review, but it cannot answer whether a pending Open
would later become available, whether the recorded value was known at the
decision time, or whether a fill could occur. No alpha candidate, eligibility
policy, Decision V2 rule, sizing, execution, canonical dataset, capture, cloud,
telemetry, or protected outcome was changed.

## Provenance

- Preregistration:
  `docs/checkpoints/2026-09-20_ALPHA_RANK_OPEN_STATE_TRANSITION_PREREGISTRATION_V1.md`
- Code: `research/alpha_rank_open_state_transition_v1.py`
- Code SHA-256:
  `d8dafd9eb4485f77b222ceae423791e86a3016e3c65c52d5345d84ac29180f76`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-rank-open-state-transition\alpha_rank_open_state_transition_v1.json`
- Result SHA-256:
  `e71d5ae00f010d779c2b202dda0215e32c8c0b64ee93c7ce6faaab8e5b3e49cd`
- Feature SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability-anchor SHA-256:
  `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- Runtime/repository reference used by the script:
  `5b59864d+rank-open-working-tree`
