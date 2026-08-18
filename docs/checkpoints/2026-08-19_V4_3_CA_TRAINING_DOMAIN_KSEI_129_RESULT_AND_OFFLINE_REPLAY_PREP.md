# V4-3 CA training-domain — KSEI 129 result and offline replay prep

Date: 2026-08-19 Asia/Jakarta
Branch: `data/v4-3-ca-training-domain-ksei-129-v1`
Status: `KSEI_129_RESULT_PINNED_OFFLINE_REPLAY_READY`

## Accepted bounded acquisition result

The exact frozen 129 historical decision-domain tickers absent from the final
611-ticker CA census were acquired once from the unchanged public KSEI
registered-security endpoint under the frozen strict parser/transport policy.

Observed result:

- ticker count: **129**;
- coverage certified: **93**;
- coverage unresolved: **36**;
- normalized history rows: **2,065**;
- all 36 unresolved failures: `HTTP_NON_200_OR_EMPTY`;
- target/rank materialized: **false**;
- model fit: **false**;
- performance computed: **false**;
- protected-forward accessed: **false**.

Acquisition manifest SHA-256:

`bb1043f36f20cd418be1b602ce9204cfcf8ca7ec546c57d913590b3898ea4976`

The observed manifest is now pinned in
`config/v4_3_ca_training_domain_ksei_129_v1.json` and must not be replaced by a
retry result merely to improve the gate.

## Why the next step is offline replay, not provider retry

The blocked pre-acquisition training-domain run had 129 decision tickers wholly
outside the CA census and minimum combined support around 79-80%. Recovering 93
of those identities materially changes coverage, but the frozen scientific
question is whether the exact combined Open/Close + CA gate is now >=90% across
the frozen validation and eligible training history.

Therefore the next step consumes the observed 93/36 result exactly as-is:

- all **129** delta coverage rows are appended in memory;
- the **93** certified rows may contribute normalized KSEI history;
- the **36** unresolved rows remain explicit `coverage_certified=false`;
- no unresolved ticker is dropped or waived;
- the accepted parent 611 census is not rewritten;
- no provider/network call occurs in replay;
- no target return/rank, model fit, prediction, performance, or protected
  outcome is accessed.

## Offline runner

`scripts/run_v4_3_ca_training_domain_ksei_129_offline_replay.py`

The runner verifies:

1. the exact acquisition manifest SHA above;
2. every child artifact SHA recorded by that manifest;
3. observed counts 129 / 93 / 36 / 2,065;
4. the original final CA, PIT-support, admission, validation-fold and support
   pins;
5. all existing final CA event semantics including exact FREN/ADRO/MEGA
   overlays;
6. the frozen >=90% combined H5/H10/consensus support gate;
7. exact frozen tail-600 validation identity and fold training-date sets.

Only a replay PASS may authorize the next engineering step of pinning the
historical execution runner. A replay BLOCKED result triggers residual
outcome-blind CA attribution; it does not authorize KSEI retries, exclusions,
threshold changes, target access, or model fitting.
