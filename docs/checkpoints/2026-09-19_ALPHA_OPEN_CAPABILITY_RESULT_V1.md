# Historical Open Capability Audit — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / PARTIAL CAPABILITY`  
Hypothesis: `H-MICRO-02`

## Question and boundary

This read-only audit measured historical `open` availability and provenance in
the frozen clean panel. It did not construct a candidate, fill any missing
value, access targets/outcomes/providers, or modify panel, canonical data,
capture, cloud, telemetry, or protected artifacts.

## Coverage

| Scope | Result |
|---|---:|
| Frozen panel rows / tickers / dates | `981,940 / 945 / 1,260` |
| Positive finite Open rows in full panel | `535,095` (`54.4928%`) |
| Corrected eligible rows | `310,761` |
| Positive finite Open rows among eligible | `201,415` (`64.8135%`) |
| Eligible `open_available=True` rows | `201,415` (`64.8135%`) |
| Eligible flag-missing-Open rows | `0` |
| All-panel flag-missing-Open rows | `2` |
| Eligible dates with at least 30 Open rows | `1,201 / 1,201` |
| Eligible Open count per date, min / median / max | `42 / 206 / 364` |
| Eligible Open count per ticker, Q10 / median / Q90 | `9 / 181 / 705` |

All positive finite Open rows were within the recorded same-row high/low range
(`0` outside-range rows). This is a structural sanity check, not proof that
the Open is executable or PIT-authoritative.

## Provenance and continuity

Among eligible positive finite Open rows:

| Provenance | Rows |
|---|---:|
| `IDX_PUBLIC_STOCK_SUMMARY` | `119,536` |
| `YAHOO_RAW` | `81,879` |

The corresponding evidence statuses are `IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL`
(`60,251` rows) and `YAHOO_RAW_OPTIONAL` (`141,164` rows). The panel contains
`20,995` observed price-provenance transitions across ordered ticker histories.
The metadata fields report `corporate_action_integrity_verified=True` for all
`981,940` rows and `signal_contract=SIGNAL_RESEARCH_HLCV` for all rows, but
these are stored metadata assertions, not independent source authority.

## Capability decision

The Open field is now classified as:

`PARTIAL / SOURCE_SENSITIVE / BLOCKED_FOR_PIT_EXECUTABLE_ADMISSION`

This materially improves the data-capability map: the field is broad enough
for target-free structural inspection, including all eligible dates with at
least 30 available Open rows. It does not establish:

- historical available-at or knowledge-time semantics;
- authoritative source selection between IDX and Yahoo;
- corporate-action basis consistency across source transitions;
- survivorship/issuer continuity;
- executable fill, auction, or overnight timing semantics;
- predictive value.

H-MICRO-02 remains `BLOCKED_SOURCE_ADMISSION`, and no C5 ID is created.

## Provenance and hashes

- Preregistration: `2026-09-19_ALPHA_OPEN_CAPABILITY_PREREGISTRATION_V1.md`
- Code: `research/alpha_open_capability_audit_v1.py`
- Code SHA-256: `6b3fce1cb754129b64a8db78501e700eb4c9db131d899dff4466efb25477d683`
- Output: external staged `alpha_open_capability_audit_v1.json`
- Output SHA-256: `6964e7cca1b92753afbd1a268557ee2836dc5f2a25ac7a22c2794e4f96e8d658`
- Repository head used: `9de5417e`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

The JSON is staged at
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_open_capability_audit_v1.json`.
