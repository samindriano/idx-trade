# Handoff — V4 CA Voluntary-Conversion Semantics Remediation V1

Branch: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
Scientific parent/result: `data/idx-v4-ca-event-window-semantics-v1@96a652b311f868babab94ca24b32bf1df382627c`
Scientific code/config anchor: `fc6ede265abeae97f6871f7b852e84aa669c159b`
Status: `READY_FOR_ONE_OFFLINE_LOCAL_REMEDIATION_RUN`

## Mandatory first step

Fetch latest canonical `origin/main:coordination/TEAM_STATUS.md` and add/update only the lane `V4 CA Voluntary-Conversion Semantics Remediation V1` to `ACTIVE` before running anything locally. Preserve all other rows.

Then checkout/pull this branch and verify the scientific files are unchanged from anchor `fc6ede265abeae97f6871f7b852e84aa669c159b`:

- `src/idx_trade/v4_ca_voluntary_conversion_semantics.py`
- `scripts/run_v4_ca_voluntary_conversion_semantics_remediation.py`
- `tests/test_v4_ca_voluntary_conversion_semantics.py`
- `config/v4_ca_voluntary_conversion_semantics_remediation_v1.json`

Documentation-only commits after the anchor are allowed; source/config changes are not.

## Validation

Set `PYTHONPATH=src`.

```text
python -m pytest tests/test_v4_ca_voluntary_conversion_semantics.py tests/test_v4_ca_event_windows.py tests/test_v4_ca_input_pin_remediation.py
```

```text
python -m py_compile src/idx_trade/v4_ca_voluntary_conversion_semantics.py src/idx_trade/v4_ca_event_windows.py scripts/run_v4_ca_voluntary_conversion_semantics_remediation.py scripts/run_v4_ca_event_window_support.py
```

Then:

```text
git diff --check
```

Any validation failure => STOP. Do not patch and rerun in the same execution attempt.

## One authorized run — offline only

Fresh output root:

`D:\Documents\Project\idx-v4-ca-voluntary-conversion-remediation-20260818-v1`

Run exactly:

```text
python scripts/run_v4_ca_voluntary_conversion_semantics_remediation.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-voluntary-conversion-remediation-20260818-v1"
```

Provider calls must remain exactly zero. Do not use the prior schedule-evidence root in this first run.

## After run

STOP regardless of verdict. No Stage 2/3, no provider acquisition, no manual event fixing, and no target/model execution.

Promote only small result artifacts needed for review: summary, manifest, event semantic audit, per-date coverage, schedule-needs audit if reasonably small, and a result checkpoint. Full continuity ledger stays external.

Update only this lane in canonical TEAM_STATUS to `REVIEW` with the exact result and push.

## Return exactly

- validation counts / compile / diff-check;
- number of relevant events;
- number reclassified as `VOLUNTARY_CASH_SETTLEMENT`;
- remaining exact-transition events;
- remaining schedule-required events and unique tickers;
- H5/H10/consensus passing dates out of 600;
- minimum H5/H10/consensus continuity rates;
- final continuity verdict and `corporate_action_continuity_certified`;
- output hashes + external output root;
- branch final HEAD and clean/synced status;
- explicit confirmation: provider calls 0; R5/R10/model/prediction/performance/outcomes untouched.
