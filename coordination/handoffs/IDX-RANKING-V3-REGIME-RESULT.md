# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V3-REGIME-F1-F4-RUN
model_used: Codex
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 619b511f14d8e929f8f23ed7c001f72fe730566f
branch: research/idx-ranking-v2-spec-v1
head_commit: final documentation commit is reported after push
scope: frozen V3-C Regime-Specialization prepare and one F1-F4 discovery run

## Files changed

- `tests/test_ranking_v3_regime.py` — compatibility-only numeric assertion fix;
- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_F1_F4_RESULT.md`;
- `coordination/handoffs/IDX-RANKING-V3-REGIME-RESULT.md`.

Runtime caches, predictions, and model artifacts remain outside Git under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_regime_prepare_20260810_run1`

and

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_regime_run_20260810_run1`.

## Findings

- full IDX Trade pytest: `264 passed, 0 failed, 3 warnings`;
- all seven frozen input artifacts matched their required SHA-256 values;
- V3-C cache status: `RANKING_V3_C_REGIME_DISCOVERY_CACHE_FROZEN`;
- cache: `216,472` rows / `674` tickers / sessions `20..984`;
- cache SHA-256: `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- cache manifest SHA-256: `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- context-equivalence max absolute difference: `0.0` for all three fields;
- fragmentation gate: PASS for every F1-F4 fold;
- control equivalence: `V3_C_CONTROL_EQUIVALENCE_PASS`, `84,732` rows, max
  score/metric difference `0.0` at `1e-12`;
- two-expert absolute sanity: PASS;
- overall paired promotion: FAIL;
- regime-specific robustness: FAIL;
- final decision: `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- candidate verdict: `KEEP_DIAGNOSTIC`;
- cumulative evaluated count: `7`.

Key paired diagnostics:

- overall median PR-delta improvement `-0.0123171892`, q25
  `-0.0156725256`, worst `-0.0221428730`, nonnegative/not-below `1/4`;
- overall median ROC change `-0.0087919123`;
- overall median Q5-Q1 change `-0.0207539272`, nonnegative/not-below `0/4`;
- NORMAL median PR improvement `-0.0014712226`, nonnegative `2/4`;
- STRESS median PR improvement `-0.0289646749`, nonnegative `1/4`;
- worst fold-state PR improvement `-0.0372442541`.

## Decisions made

- The exact frozen V3-C contract was executed without redesign.
- The two-expert candidate is closed as `KEEP_DIAGNOSTIC`; V2 remains the
  control.
- No Structure-Lite inheritance, recency reopening, threshold/vote change,
  score normalization, blending, rescue candidate, or alternate regime was
  attempted.
- The two test assertion changes are engineering-only compatibility hardening;
  regime semantics and gates are unchanged.

## Prohibited-scope confirmation

- V2F5/V2F6: not accessed;
- reserved post-2026-07-31 V2 fresh-forward outcomes: not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- V3-D/V3-E, integration, calibration, Stage 6, `IDX-VAL-002`,
  execution-PnL, Kelly, paper/live, and main merge: not started.

## Validation and artifact identity

- result checkpoint: `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_F1_F4_RESULT.md`;
- result summary SHA-256:
  `ea6d67f09da7560f18696e2475565971ac8cae979ab9d0d1f42328814e7984f7`;
- control-equivalence artifact SHA-256:
  `2264cfa0d898451f8a09e9a01360ec73ae6022f9e55b2e70c0a4f39e08e26930`;
- metrics CSV SHA-256:
  `b869c1fe28be941be9c82745571569352f3db8c5c4118d620d97f90e4f31be9a`;
- state metrics SHA-256:
  `cf42986d62c02f28d3d55e9091d497476024e8b7e48a3c1669e8f59bcab3ffd9`;
- paired overall SHA-256:
  `88b0707a0e2e693b5a2c5b35ddf0911140a1431cf9215ca1ec89221b271c547e`;
- paired-by-state SHA-256:
  `2fd8c402e41e5a13428df56f42c012ae0baae4146d20c7ee7290132aef50b68d`;
- aggregate SHA-256:
  `1566cd62bc04aa0745c66b210dac227f4422c0e4ab6d272181b813643d68bc90`;
- verdict SHA-256:
  `4550b7cbb7cc9d009fb291218a4871b1aa544250063f07aed8093e0354527e5e`;
- runtime SHA-256:
  `fc1d967401623bbe770a65d0011407105d0c6730d2e70198b9e771f394f8e5a4`.

## Blocking risks / recommended next action

V3-C regime specialization did not survive its frozen discovery gates. Do not
rescue this hypothesis or infer independent validation from these historical
folds. Stop for ChatGPT review before any new V3 specification or sealed-fold
access.

validation_run: `264 passed, 0 failed, 3 warnings`; prepare coverage PASS;
control-equivalence PASS; absolute sanity PASS; overall paired FAIL; regime
robustness FAIL
recommended_next_action: independent ChatGPT review of the checkpoint and
artifact hashes; no automatic next-stage run
