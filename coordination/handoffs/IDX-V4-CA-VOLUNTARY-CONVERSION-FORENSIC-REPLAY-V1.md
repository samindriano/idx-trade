# Handoff — V4 CA Voluntary-Conversion Forensic Replay V1

Branch: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1`
Scientific code/config anchor: `0727d13597315b5c00d7829ff12beac55701b224`
Status: `READY_FOR_ONE_OFFLINE_LOCAL_REPLAY`

## Mandatory coordination before execution

Fetch latest `origin/main:coordination/TEAM_STATUS.md`. Confirm no newer ACTIVE lane owns this exact forensic scope, then add/update only:

`V4 CA voluntary-conversion forensic replay V1 | ACTIVE | Codex/V4-CA-VC-Forensic-Replay | data/idx-v4-ca-voluntary-conversion-forensic-replay-v1 / 0727d135... | Offline immutable-byte replay only; no provider/model/target/outcome work.`

Do not change any unrelated TEAM_STATUS row.

## Pull and validate

Checkout/pull the branch. Set `PYTHONPATH=src`.

Run:

```text
python -m pytest tests/test_v4_ca_voluntary_conversion_semantics.py tests/test_v4_ca_voluntary_conversion_forensic.py
```

Then:

```text
python -m py_compile src/idx_trade/v4_ca_voluntary_conversion_forensic.py scripts/run_v4_ca_voluntary_conversion_forensic_replay.py
```

Then `git diff --check`.

Any validation failure => STOP and report it. Do not execute the forensic replay and do not patch source/config in that same attempt.

## One exact offline replay

Use fresh output root:

`D:\Documents\Project\idx-v4-ca-voluntary-conversion-forensic-replay-20260818-v1`

It must not already exist.

Run exactly:

```text
python scripts/run_v4_ca_voluntary_conversion_forensic_replay.py --ksei-history "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1\ksei_ca_history.jsonl" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --parent-event-audit "docs\artifacts\v4_ca_event_window_static_20260818_v2\event_semantics_audit.csv" --remediation-event-audit "docs\artifacts\v4_ca_voluntary_conversion_remediation_20260818_v1\event_semantics_audit.csv" --parent-per-date "docs\artifacts\v4_ca_event_window_static_20260818_v2\v4_frozen_continuity_per_date_event_window.csv" --remediation-per-date "docs\artifacts\v4_ca_voluntary_conversion_remediation_20260818_v1\v4_frozen_continuity_per_date_event_window.csv" --output-dir "D:\Documents\Project\idx-v4-ca-voluntary-conversion-forensic-replay-20260818-v1"
```

This command is offline only. Provider/network calls are forbidden.

## Required interpretation

The runner has only three allowed verdicts:

- `FORENSIC_REPLAY_CONFIRMS_VOLUNTARY_CASH_RECLASSIFICATION_REPORTING_UNDERCOUNT`
- `FORENSIC_REPLAY_ZERO_RECLASS_IDENTITY_PASS`
- `FORENSIC_REPLAY_INCONSISTENT_BLOCKED`

Do not reinterpret or rescue a blocked verdict.

Specifically report:

- parent relevant event count;
- remediation relevant event count;
- removed and added event counts;
- parent-relevant Voluntary Conversion count;
- strict security-to-currency predicate count;
- actual reclassified-to-nonblocking count;
- remaining Voluntary Conversion schedule-required count;
- whether removed IDs exactly equal reclassified nonblocking IDs;
- whether every removed ID is strict Voluntary Conversion security-to-currency;
- exact ratio dump examples and counts by `ratio_parse_status`, `ratio_left_security == ticker`, and right-security token;
- parent vs remediation changed 600-date row count;
- final verdict;
- all output SHA-256 values and manifest SHA.

## Promotion

Keep the immutable full KSEI history external. The forensic outputs are small and may be promoted under:

`docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/`

Promote `summary.json`, `MANIFEST.json`, `event_set_diff.csv`, `voluntary_conversion_ratio_dump.csv`, `classifier_side_by_side.csv`, and `continuity_per_date_diff.csv`.

Add a result checkpoint and result handoff. No source/config edits after the replay output is exposed.

Update only this TEAM_STATUS lane to `REVIEW` with the exact verdict and final branch HEAD, push, ensure clean/synced, then STOP.

## Forbidden

No KSEI/provider calls, no schedule Stage 2/3, no new CA semantics, no R5/R10/target/rank materialization, no model fit/prediction/performance, no protected/fresh-forward outcome access.