# V4 CA Targeted Schedule Parser Remediation V2 Result

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Status: `V2_PARTIAL_PARSER_RECOVERY_V3_GEOMETRY_HARDENING_PREPARED`

## Local V2 validation

User-local validation on the authoritative Windows worktree passed:

- branch fast-forwarded to `035cf1d`;
- focused parser suites: `9 passed`;
- `py_compile`: PASS;
- output root did not exist before run;
- remediation run completed outcome-blind with `provider_calls_in_remediation=false`.

V2 remediation manifest SHA-256:

`72bbd533a24c3b81906f3194ab9f3737116ac77f76fe16520340474e736b0af3`

The inherited request-record hash remained unchanged from the original targeted acquisition, confirming no new provider activity.

## V2 findings

Ticker extraction was repaired for all seven parsed documents. The prior erroneous `KODE` identities became the correct tickers CUAN, ISAT, PANI, PTRO and RAJA.

PANI was materially recovered at the parser layer:

- family: `RIGHTS_HMETD`;
- exact transition: `2025-12-09`;
- semantic: `REGULAR_MARKET_EX_DATE`;
- parse status: `PARSED_EXACT_TRANSITION`.

However PANI still failed event linkage because the V2 layout reparse dropped the parent Record/Distribution dates that had previously linked the document to the frozen event source dates.

The four stock-split documents remained unresolved despite correct ticker/family identity. V2 layout extraction did not preserve an exact same-line association between `Mulai perdagangan saham dengan Nilai Nominal Baru ... Pasar Reguler` and its date.

ADRO remained unresolved and continued to look qualitatively different from the parser failures.

## Important correction

The V2 reparsed `record_date` values for CUAN/ISAT/PTRO/RAJA are not trusted for event linkage. They align suspiciously with likely transition dates and can be artifacts of PDF table flattening. V3 must not allow those reparsed Record/Distribution fields to make an event pass.

## V3 hardening prepared

The repository implementation was hardened again after the V2 result:

1. pypdf text-matrix geometry is collected with `visitor_text`;
2. visual rows are reconstructed only from near-identical y baselines and left-to-right x ordering;
3. exact transition remains same-visual-row semantic + one date only;
4. flattened date lists remain non-inferable;
5. event linkage may use only:
   - unchanged Record/Distribution identity from the frozen parent parse, or
   - a newly recovered exact transition date that itself exactly equals one of the frozen event `source_dates`;
6. V2 reparsed Record/Distribution fields are never used for linkage;
7. parse audit now records layout and geometry transition context for forensic review.

No provider calls, source substitution, price inference, target/rank materialization, model fit, prediction, performance, or protected/fresh-forward outcome access are authorized or performed.

The next local run must use the original V1 targeted-evidence root as parent, not the V2 remediation root, and must write a fresh V3 output directory.
