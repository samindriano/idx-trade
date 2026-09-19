# BBCA historical price-basis reconciliation — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`
Scope: read-only comparison of three locally staged BBCA payloads. No price
repair, feature construction, candidate creation, target/outcome access,
network/provider call, or canonical-data mutation.

## Result

`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

The audit establishes source/basis divergence and adjustment ambiguity. It does
not establish which source is authoritative, PIT-safe, corporate-action
correct, or suitable for feature admission.

### TradingView versus IDX

- TradingView: 6,356 rows, 2000-05-31–2026-09-18; metadata says
  `hasAdjustment=true`, `allowedAdjustment=any`, `barSource=trade`, and static
  ISIN `ID1000109507`.
- IDX history: 1,616 rows, 2020-01-02–2026-09-18.
- Date-normalized overlap: 1,615 rows.
- OHLC price fields are exact on 1,182 rows; all five OHLCV fields are exact on
  1,164 rows.
- `IDX close / TradingView close` is exactly 5.0 from 2020-01-02 through
  2021-10-12, then exactly 1.0 from 2021-10-13 through 2026-09-18.
- IDX `listedShares` changes from 24,408,459,900 to 122,042,299,500 on
  2021-10-13, a 5.0 ratio. This is a coincident structural marker only, not
  independent corporate-action certification.

### Investing versus IDX

- Investing: 2,065 rows, 2018-08-08–2026-09-18; `period=max`, `interval=1d`.
- Date-normalized overlap: 1,568 rows.
- Exact OHLCV matches: 0/1,568 for every field and 0/1,568 for all-field rows.
- The close ratio does not reduce to one constant scale: `IDX close /
  Investing close` median is approximately 635.5 in 2020, 108.6–160.0 in
  2022, 148.0 in 2024, and 60.7 on 2026-09-18. The basis/adjustment/time
  semantics remain unexplained locally.

TradingView and Investing overlap on 1,901 dates, with zero exact OHLCV
all-field rows. These are incompatible source representations for admission
until an authoritative basis and historical adjustment contract exists.

A follow-up linkage audit found 61 BBCA trace rows from 2021-10-13 through
2022-01-07 with exact panel-versus-IDX HLC equality, but zero BBCA rows in both
the retained CA event census and strict transition semantics ledger. The trace
therefore adds forensic alignment only; it does not certify the event or its
effective date. See `2026-09-20_ALPHA_BBCA_CA_EVENT_LINKAGE_RESULT_V1.md`.

## Decision

Keep both external surfaces `PARTIAL / SOURCE_ADMISSION_BLOCKED`; keep IDX as a
structural cross-check only. Do not back-adjust, rescale, merge, forward-fill,
or use either source in C1/C2/C4. The result strengthens the existing global
CA/price-basis readiness block, especially for C1, but creates no candidate and
no predictive claim.

## Reproducibility artifacts

Staged under:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/`

| Artifact | SHA-256 |
|---|---|
| `alpha_bbca_price_basis_reconciliation_v1.json` | `8899cd6e8ab021b671168b7817c76a4dfbc1633d62b3e8920c74c52fd3ac6612` |
| `alpha_bbca_price_basis_reconciliation_v1_verification.json` | `0be937fb95adf7a3d71c43f9e23c42dc9bea455c1d049e3a90eeade6fc5fcf70` |
| `alpha_bbca_price_basis_reconciliation_v1_hash_contract.json` | `6c53798c709b479ae9c4afc4fe59fd3cb2ff4436ec743915c601c5fddff895cb` |
| `alpha_bbca_price_basis_reconciliation_v1_firewall.json` | `df9396aba69e7b2de034fff98364473c4c812bbec52e15fbb631c89bc2ab1637` |
| `alpha_bbca_price_basis_reconciliation_v1.py` | `eb9dc71689e5fd25dc6acd9b41b01e80c909400a4d886dfb98227cb79d548d31` |
| `verify_alpha_bbca_price_basis_reconciliation_v1.py` | `5d4089e57da4e52bdd91f857ae0b24db0365a70adeeebb6fbea442327ff6e8e5` |

Structural verifier, artifact hash contract, and outcome-blind target/privacy
firewall all report `PASS`. The source manifest has `retry_policy=NONE` and all
safe mutation/outcome/model flags false.
