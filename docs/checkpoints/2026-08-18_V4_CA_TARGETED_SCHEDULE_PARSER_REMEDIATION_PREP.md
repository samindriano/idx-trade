# V4 CA Targeted Schedule Parser Remediation — Prepared

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Status: `OFFLINE_REMEDIATION_PREPARED_LOCAL_RUNTIME_REQUIRED`

## Trigger

The frozen seven-event targeted KSEI acquisition completed with one resolved static NISP event and six unresolved mechanical events. The subsequent document parse audit showed that four stock-split PDFs (ISAT, PTRO, CUAN, RAJA) visibly contained the exact semantic phrase for starting trading on the new nominal-value basis in the Regular/Negotiated Market, yet the parser emitted `NO_EXPLICIT_REGULAR_MARKET_TRANSITION`. The same rows also exposed a ticker extraction failure where `KODE` was parsed instead of the actual security code. PANI remained a likely table-layout extraction problem; ADRO remained potentially a genuine linkage/evidence issue.

Frozen parent targeted-evidence manifest SHA-256:

`df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b`

## Remediation boundary

This remediation is parser-only and offline.

- no provider/network call;
- no re-acquisition or source substitution;
- no price inference;
- no Record/Distribution date fallback to a transition;
- no target/rank materialization;
- no model fit, prediction, performance computation, or protected/fresh-forward outcome access;
- original raw KSEI document bytes are reused by exact SHA-256 identity.

## Implementation

Added:

- `src/idx_trade/v4_ca_targeted_schedule_parser_remediation.py`
- `scripts/run_v4_ca_targeted_schedule_parser_remediation.py`
- `tests/test_v4_ca_targeted_schedule_parser_remediation.py`

The remediation runner requires the exact parent manifest above, verifies the parent output hashes, locates each previously captured PDF by source SHA-256, and extracts text with pypdf `extraction_mode="layout"`.

Exact transition evidence is admitted only when one explicit regular-market semantic anchor and one date occur on the same layout-preserved PDF line. Supported remediation anchors include:

- stock split: `Mulai perdagangan saham dengan Nilai Nominal Baru ... Pasar Reguler`;
- explicit HMETD/dividend Ex rows in the Regular Market, including the KSEI-style `Tanggal Ex di Pasar Reguler ...` form.

Ticker remediation rejects header tokens such as `KODE` and requires an explicit four-character security code from the official document text.

The runner preserves the accepted NISP static evidence from the parent bundle and writes a new evidence root using the same continuity-compatible schema. The output records `provider_calls=true` for inherited acquisition lineage and separately records `provider_calls_in_remediation=false` for the actual remediation run.

## Fail-closed behavior

Flattened date lists are not reordered or inferred. If layout extraction does not preserve an exact semantic-row/date association, the event remains unresolved. Multiple exact transition semantics also remain unresolved.

## Required local validation

The repository-side implementation is complete, but the authoritative raw PDFs live only in the user's Windows artifact root. Local runtime must therefore:

1. run focused parser tests and `py_compile`;
2. run `run_v4_ca_targeted_schedule_parser_remediation.py` against the exact parent root;
3. inspect the remediated linkage and parse audits;
4. only after independent audit of recovered dates, run the existing continuity replay against the new evidence root.

Do not rerun the KSEI acquisition script.
