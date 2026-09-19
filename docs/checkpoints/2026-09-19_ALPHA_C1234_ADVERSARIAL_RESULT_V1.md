# C1/C2/C4 Adversarial Structural Audit V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `Q_J_OUTCOME_BLIND_C1234_ADVERSARIAL_AUDIT`
Result: `PASS_STRUCTURAL_ONLY`

## Purpose and boundary

This audit attempts to falsify the corrected C1/C2/C4 construction without
opening targets, forward returns, protected labels, providers, network data, or
incumbent score artifacts. It is a main-run adversarial audit with an
independent verifier; it is not the missing independent worker red-team for
Phase Q. Accordingly, Phase Q remains `PARTIAL` and no candidate is marked
`READY_FOR_REENTRY`.

## Inputs

| Input | SHA-256 |
|---|---|
| `research/alpha_stage_a_v2.py` | `62a16137d039c0304e00fbf91de65ed5c70d50952faccf2aff1b0a587f49e59a` |
| `alpha_stage_a_v3_features.parquet` | `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4` |
| `model_safe_signal_research_panel_1260_final_clean.parquet` | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` |
| `official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| `security_master_1260_final_reconciled.csv` | `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e` |

## Checks and results

All checks passed:

| Attack surface | Result |
|---|---|
| AST parse / implementation integrity | `PASS` |
| Negative shifts | `PASS — none found` |
| Backward/forward fill | `PASS — none found` |
| Network imports and HTTP calls | `PASS — none found` |
| Causal feature tokens and date-wise cross-sectional ranks | `PASS` |
| Exact C1/C2/C4 score and rank schema | `PASS` |
| Target-like feature column scan | `PASS — none found` |
| Feature/panel row and key equality | `PASS` |
| Duplicate `(ticker,date)` keys | `PASS — none` |
| Official-session date closure | `PASS` |
| Per-ticker chronological ordering | `PASS` |
| Security-master ticker uniqueness | `PASS` |
| Active identity interval coverage | `PASS — 310,761 / 310,761 eligible rows` |
| Score/rank mask closure outside eligibility | `PASS` for C1/C2/C4 |
| Rank bounds and finite values | `PASS` for C1/C2/C4 |

Candidate support:

| Candidate | Finite eligible rows | Finite dates | Finite tickers | Top-30 dates |
|---|---:|---:|---:|---:|
| C1 | 295,243 | 1,141 | 704 | 1,141 |
| C2 | 310,761 | 1,201 | 711 | 1,201 |
| C4 | 310,323 | 1,201 | 711 | 1,201 |

Listing-age exposure was also measured without using outcomes. The selected
Top-30 share with listing age at most 60 days was 0% for all three candidates.
The selected share with age at most 365 days was 9.664% for C1, 11.599% for
C2, and 10.977% for C4, versus 7.498% in the eligible universe. This is a
concentration warning, not a predictive or survivorship conclusion.

## Interpretation

The audit supports the following limited statement:

> The corrected C1/C2/C4 feature construction is internally coherent under
> these target-free static, key, mask, calendar, identity-interval, and
> numerical checks.

It does **not** establish:

- corporate-action-adjusted price-basis consistency;
- issuer/ISIN continuity beyond the supplied security-master interval map;
- historical-as-of or revision/vintage authority;
- absence of survivorship in the underlying frozen panel;
- liquidity/ADV or executable capacity;
- predictive value, OOS performance, incremental information, or superiority.

## Artifacts and verification

- Builder: `research/alpha_c1234_adversarial_audit_v1.py`
- Builder SHA-256: `c2ddfa9fd13d331a9a514ebba28e763c1aebf42287152cd572f1afea26d2fa44`
- Independent verifier:
  `research/verify_alpha_c1234_adversarial_audit_v1.py`
- Verifier SHA-256: `0950872b2271cb99ca1b99967bab0174eb13c8a0b264f266560f15aa8ac409c7`
- Output: `alpha_c1234_adversarial_audit_v1.json` in
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Output SHA-256: `6bfcba7070be218d288a0cf894f8d7e54b170bf624966e38a758061ed7d6dae8`
- Legacy verifier result: `PASS` for artifact-envelope checks only; it is not
  an independent structural replay.
- Source-recomputing replay: `PASS_INDEPENDENT_STRUCTURAL_REPLAY`; see
  `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`.
- Outcome/provider/target/incumbent access flags: all `false`
- Candidate ID created: `false`

## Decision

Retain C1/C2/C4 as `FUTURE_RESEARCH`. Do not promote them to
`READY_FOR_REENTRY` on this audit alone. Resolve price-basis/PIT admission and
the remaining identity/survivorship/capacity uncertainties before any
protected evaluation.
