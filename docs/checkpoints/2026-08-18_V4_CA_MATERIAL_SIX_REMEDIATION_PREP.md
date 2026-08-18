# V4 CA material-six remediation — preparation

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-material-six-remediation-v1`
Status: `PREPARED_FOR_SINGLE_LOCAL_RUNTIME`

## Exact scope

This lane is restricted to the six material names selected after the outcome-blind 740→610 universe audit:

- `FREN`
- `ADRO`
- `MEGA`
- `SCMA`
- `AVIA`
- `SMAR`

No model, target, realized return, prediction, rank, performance metric, or protected/fresh-forward outcome is accessed.

## Failure-class-specific remediation

### FREN

The universe audit proved that FREN is the only `POTENTIAL_CA_SUPPORT_DATA_GAP`: it has 302 primary-liquid signal rows on the exact frozen 600 validation dates but was absent from the 610-ticker CA support.

The new runner therefore adds FREN back to support as ticker 611 and materializes exactly `302 × 2 = 604` H5/H10 continuity rows from the already frozen primary-liquid rules and official calendar.

The runner also downloads and hashes the issuer-official XLSMART material disclosure for 16 April 2025. The document states that Smartfren Telecom (SF) and Smart Telecom merged into XL as the surviving company, SF/ST ceased to exist by operation of law, and the merger became effective on 16 April 2025. This exact legal/security-cessation boundary is admitted as a FREN transition. **No FREN→EXCL price stitching is permitted.**

FREN complete KSEI history is separately retried with the unchanged strict KSEI URL/parser. If that complete-history capture remains unavailable, FREN coverage is explicitly `false`; all FREN windows remain fail-closed and the final 611-ticker replay decides whether the aggregate 90% gate still holds.

### MEGA

The runner refreshes the official KSEI registered-security page with the unchanged strict parser and downloads/hashes Bank Mega's issuer-official 2026 bonus-share disclosure.

The issuer document identifies:

- bonus ratio: `1 old MEGA : 1 bonus MEGA`;
- Regular/Negotiated cum bonus: 9 April 2026;
- Regular/Negotiated ex bonus: **10 April 2026**;
- record date: 13 April 2026;
- distribution: 30 April 2026.

The exact regular-market ex-bonus date `2026-04-10` is admitted as an issuer-official price-basis transition. This also adjudicates the source taxonomy mismatch where KSEI can expose the stock component under `Right Distribution`/mixed-dividend semantics while the issuer calls it bonus shares.

### SCMA

The frozen prior evidence contains exact source action `82840`, candidate date `2026-08-10`. The new runner proves at runtime that SCMA has no other in-period prior candidate and that 2026-08-10 is after the maximum frozen H5/H10 terminal date.

Only under those exact assertions is SCMA removed from the ticker-wide cross-source conflict set. The ±60-calendar-day selection halo remains an evidence-acquisition scope; it is not allowed to poison all historical SCMA target windows when the candidate itself is after every target terminal.

### AVIA / SMAR

Both remain members of the accepted 599/610 KSEI census but were unresolved transport/coverage gaps. They are retried through the same frozen official KSEI transport and parser used for ICBP:

- exact official registered-security URL;
- fresh session;
- official-home warmup;
- maximum two security attempts;
- no parser relaxation;
- no alternate provider;
- no alias/substitution.

Success certifies only coverage and parsed source-native history. Any newly exposed mechanical event remains subject to the existing CA event-window semantics.

### ADRO

ADRO is re-probed diagnostically through the same strict KSEI page, but its frozen history/event identity is not replaced automatically.

The official KSEI page exposes the 2024 AAI/AADI-linked right distribution as `4389 ADRO : 1000 ADRO-H`, record 29 November 2024, distribution 2 December 2024, with no source-native Cum Date. No primary official document found in this lane states the exact Regular Market ex-entitlement/first-new-basis date.

Therefore:

- Record Date is **not** accepted as transition;
- Distribution Date is **not** accepted as transition;
- inferred `2024-11-28` is explicitly forbidden;
- ADRO remains `UNRESOLVED_PRIMARY_REGULAR_MARKET_EX_DATE_NOT_PROVEN` unless future primary evidence supplies the exact market transition.

This is intentional fail-closed behavior, not exclusion of ADRO from the universe.

## Final replay

The one-shot runtime expands the CA support to 611 tickers, merges strict KSEI results, applies only the exact FREN/MEGA/SCMA adjudications above, preserves the accepted targeted/residual evidence stack, and reruns the unchanged per-date 90% continuity gate.

The output records a per-ticker verdict for all six plus the final aggregate certification. A provider failure is not a workflow crash and is not converted into a pass; the ticker remains explicitly unresolved.

## Implementation

- `src/idx_trade/v4_ca_material_six_remediation.py`
- `scripts/run_v4_ca_material_six_remediation.py`
- `scripts/run_v4_ca_material_six_remediation_v2.py` — corrected orchestration entrypoint
- `tests/test_v4_ca_material_six_remediation.py`

The V2 entrypoint contains orchestration-only corrections: canonical frozen output filename handling and fail-closed continuation when AVIA/SMAR retries fail. Scientific semantics are unchanged.

## Stop condition

Do not authorize V4 target/model execution from this preparation checkpoint. First run the exact local workflow, inspect the six per-ticker verdicts and the 611-ticker per-date continuity result, then record an acceptance/result checkpoint.
