# BBCA CA-event linkage audit — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`

## Result

`PASS_STRUCTURAL_ONLY / EVENT_AUTHORITY_NOT_ESTABLISHED`

The retained BBCA trace is useful forensic context but does not certify a
corporate-action event, effective date, ratio, issuer, or ISIN transition.

- `bbca_2021_trace.csv` contains 61 BBCA rows from 2021-10-13 through
  2022-01-07, with `sessions_since_recorded_split` 0 through 60.
- Panel-versus-IDX HLC equality is exact on 61/61 trace rows.
- The trace's only zero-session row is 2021-10-13; five/14/20/60 rows retain
  pre-event values in the 5-session/ATR14/20-session/60-session lookback flags.
- Neither the retained CA event census (26 rows) nor the strict transition
  semantics ledger (162 rows) contains any BBCA row.
- The event census contains 26 rows across eight tickers and six event families;
  absence of BBCA is not evidence that no BBCA event occurred.

The trace date aligns with the 5x-to-1x TradingView/IDX basis break and the IDX
listed-share change recorded in the separate price audit. That alignment is a
forensic clue only. It cannot be promoted into event truth because the local
event ledgers do not carry a BBCA authority row or a certified effective-date /
ratio / issuer-ISIN contract.

## Boundary and disposition

No price was repaired or rescaled. No feature, candidate, target, outcome,
model score, or protected packet was changed. Keep TradingView, Investing, and
the BBCA trace outside admitted feature inputs. The existing global CA/issuer
and price-basis block remains in force.

## Inputs and hashes

| Input | SHA-256 |
|---|---|
| `bbca_2021_trace.csv` | `17c79b31d63d1a0c4f7da277b233ed78f0330076efc0bce80e292131fba48a5a` |
| `ca_event_census.csv` | `10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3` |
| `ca_transition_semantics_reconciliation.csv` | `fd3baafe16e94aaf7e57ba1b715c2995e2ae9c6169002ecb39f13f8648b0137c` |

Staged output artifacts:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/`

| Artifact | SHA-256 |
|---|---|
| `alpha_bbca_ca_event_linkage_v1.json` | `fcc267956bb4c77069cd125bbac540b5c303a4231f54fea4c3710f8bda8a4278` |
| `alpha_bbca_ca_event_linkage_v1_verification.json` | `4add68c559f9924d2d405152bac0e9244e8b15dae67855e114e80a9ebd25c650` |
| `alpha_bbca_ca_event_linkage_v1_hash_contract.json` | `d6658bbe2067c1c0e6c2a2de828c6259149887156c00c8966c7eb0efe2f165a5` |
| `alpha_bbca_ca_event_linkage_v1_firewall.json` | `c7d607e2de1ddf59d9e32b7730925a74b7d4bbb6da1b686b941e1de76991c08b` |
| `alpha_bbca_ca_event_linkage_v1.py` | `6ffe87d8d8b26add35817ba90b3222961979bf5802819494a45c6960bc766cc3` |
| `verify_alpha_bbca_ca_event_linkage_v1.py` | `f9973954b50517a0cad6126f5b880efba571f919f87113dd543cad8f227bf538` |

Structural verifier, artifact hash contract, and outcome-blind target/privacy
firewall all report `PASS`. No network/provider access was used.
