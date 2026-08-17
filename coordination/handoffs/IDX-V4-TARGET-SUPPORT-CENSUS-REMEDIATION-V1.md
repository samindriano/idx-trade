# IDX V4 Target-Support Census Remediation V1

Status: `PREPARED_FOR_EXACT_OFFLINE_RERUN`
Branch: `research/idx-v4-target-support-census-remediation-v1`
Parent: `research/idx-v4-target-support-census-v1@5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d`

## Finding

The prior 264/1,260-date / six-by-100 BLOCKED verdict is not decision-valid because the census omitted the accepted Yahoo+TradingView historical Open derivative and read Open primarily from the old immutable signal panel. Calendar-adjacent 600-session contiguity was also treated as a blocker even though V4-2 specifies consecutive **eligible** signal sessions.

## Prepared remediation

- consume pinned derivative panel SHA `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`;
- pin derivative artifact manifest SHA `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14`;
- exact one-to-one signal-panel identity check;
- derivative Open first, verified CA-scale overlay only as incremental missing-Open support;
- H5/H10/consensus eligible lists emitted separately;
- six-by-100 verdict derived from >=600 ordered eligible sessions for each required leg;
- no labels, returns, IC, model fit, provider/CA acquisition, or contract tuning.

Exact external rerun is still required because authoritative parquet bytes are local Windows artifacts unavailable to this ChatGPT runtime.
