# Alpha Future Evaluation Packet V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`

This packet is the one-shot protected-evaluation contract for the current fixed
portfolio. It is deliberately complete before target admission and contains no
outcome payload. It must not be executed unless a separately reviewed Data QA
admission artifact passes all gates below.

## 1. Candidate IDs

Exactly four fixed candidates:

1. C1 — `residual_reversal_5_v1`
2. C2 — `participation_confirmation_5_v1`
3. C3 — `financial_quality_growth_v1`
4. C4 — `path_efficiency_reversal_20_v1`

H-LIQ-01 is not in this packet. Its prototype remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` and cannot silently
expand the protected candidate budget.

## 2. Frozen implementations and hashes

Implementations are the corrected Stage A construction, not the invalid V1
implementation:

- `research/alpha_stage_a_v2.py`; source SHA-256 at the last guarded run:
  `62a16137d039c0304e00fbf91de65ed5c70d50952faccf2aff1b0a587f49e59a`.
- Corrected feature artifact:
  `alpha_stage_a_v3_features.parquet`; guarded artifact SHA-256 at the
  robustness run:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`.
- Formula definitions and implementation contract:
  `2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md`.

At execution time, recompute and record the code/artifact hashes and refuse to
run if they differ from the frozen manifest without a new admission decision.

## 3. Target contract

- Target identifier:
  `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`.
- H5: `Close_(t+5) / Open_(t+1) - 1`.
- H10: `Close_(t+10) / Open_(t+1) - 1`.
- Primary target: equal-weight consensus of ascending average-tie ranks,
  `0.5 * H5_rank + 0.5 * H10_rank`.
- Missing horizons are missing, never zero-filled.
- No substitute target, H5-only run, proxy label, target reconstruction, or
  target-derived feature is allowed.

## 4. Population and common support

- Universe: `V4_PRIMARY_LIQUID_CAUSAL_V1`.
- Security must be a PIT common share, `LISTED` and `ACTIVE` at EOD `t`.
- Apply the frozen trailing-60 official-session market-value rule: at least 20
  finite observations and median regular-market value at least IDR 1 billion.
- Candidate and incumbent must use exactly the same eligible ticker/date rows.
- No top-N substitute, future-derived universe, survivorship repair, or
  candidate-specific population is permitted.

## 5. Split and evaluation boundaries

- Last 600 eligible official sessions available to the frozen historical
  design, split into six chronological non-overlapping 100-session folds.
- Training/development/evaluation boundaries remain those in the frozen
  protocol; no refit or boundary shift is allowed after admission.
- Historical comparison ends at session 1249 / 2026-07-17 under the current
  protocol. It is not prospective validation.
- The current panel has only ten post-cutoff sessions and cannot mature a new
  H5/H10 prospective holdout. Do not reinterpret those sessions as a new test.

## 6. Purge and embargo

- Ten official-session purge before each validation start.
- Validation start `s` excludes training signal sessions `s-10` through
  `s-1`.
- Preserve the existing fold-level target observability rules for both H5 and
  H10.
- Any target/calendar ambiguity fails closed.

## 7. Metrics

Primary:

- daily cross-sectional Spearman IC on common eligible rows;
- six-fold consensus median and q25 IC;
- paired candidate-minus-incumbent IC delta.

Secondary, all predeclared:

- ICIR;
- positive-session and positive-fold fraction;
- Top-30 mean target percentile;
- Top-30 minus Bottom-30 target spread;
- fold-stratified moving-block bootstrap, 2,000 repetitions, block length 10,
  seed 42;
- H5 and H10 separately plus consensus.

No extra metric may be selected after outcomes are visible.

## 8. Acceptance gates

Historical `RESEARCH_SURVIVOR` requires all frozen gates:

- candidate median fold IC `>= 0.025`;
- candidate q25 fold IC `>= 0.010`;
- at least five positive folds;
- Top-30 percentile `>= 0.52`;
- Top-30 minus Bottom-30 spread `>= 0.04`;
- bootstrap lower bound `> 0`;
- paired consensus mean IC delta `>= 0.005`;
- paired spread delta `>= 0.010`;
- paired Top-30 delta `>= 0.005`;
- paired q25 delta `>= 0`;
- at least four positive fold deltas;
- both H5 and H10 present under their frozen observability rules.

Failure of any required gate is recorded once. No rescue, sign flip, weight
change, window change, model change, or retry is allowed.

## 9. Friction and economics

Use the frozen structural/economic assumptions only:

- buy fee 15 bps;
- sell fee 25 bps;
- slippage 10 bps per side;
- sensitivity 0/25 bps;
- existing stamp-duty rule;
- 15% EOD NAV entry cap;
- 1% causal regular-market-value capacity reference.

Report turnover, concentration, and friction sensitivity separately from alpha
metrics. Coarse capacity is not a broker-fill guarantee.

## 10. Orthogonality and incumbent comparison

Before interpreting any candidate gate, record:

- exact same-window incumbent artifact identity and hash;
- candidate/incumbent score correlation and Top-K overlap on common support;
- fold and period slices;
- conditional information only under a predeclared, non-tuned procedure.

If the incumbent artifact or common-support identity is missing, status is
`UNKNOWN/BLOCKED`; do not infer incremental information from internal C1–C4
correlation.

## 11. Robustness tests

Use only the frozen predeclared views:

- six chronological folds;
- first/last half of the 600-session window;
- calendar/regime slices already defined by the incumbent contract;
- ticker and date breadth;
- missingness/eligibility sensitivity;
- fixed Top-K turnover, concentration, and liquidity exposure;
- previously documented structural robustness results.

No alternative slice may create a second PASS route. No parameter sweep is
permitted after target access.

## 12. Admission preconditions

Before any protected read, require a fresh independent artifact proving:

- population completeness;
- historical-as-of/PIT authority;
- identity and calendar continuity;
- corporate-action transition basis;
- revision/vintage completeness;
- H5 and H10 target authority;
- immutable common-support incumbent identity;
- untouched protected-evaluation state and exact counter/lock semantics.

If any item is absent, do not open targets and leave the queue unchanged.

## 13. Stopping rule and audit trail

- Execute at most once per fixed candidate after all admission gates pass.
- Stop immediately on integrity, provenance, schema, target, or common-support
  failure.
- Preserve the exact input manifest, code hash, artifact hash, admission hash,
  execution timestamp, fold boundaries, metrics, and gate results.
- A historical survivor is not a production promotion. Prospective untouched
  evidence is still required.
- If no admission artifact passes, the packet remains
  `SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`.

## Current packet verdict

The packet is complete as a specification but not executable. The current
authoritative state has not granted target admission, so this lane must remain
outcome-blind.
