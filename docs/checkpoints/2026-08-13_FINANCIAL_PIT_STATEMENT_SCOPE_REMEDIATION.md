# Financial PIT Statement-Scope Resolver Remediation

Date: 2026-08-13 (Asia/Jakarta)

Status: `REVIEW_REMEDIATION_COMPLETE`

Parent lane: `data/financial-pit-statement-scope-v1`

## Scope and boundaries

This is an engineering-only remediation of the bounded statement-scope
resolver. It does not reclassify the 6,108 exact joins, rerun the 7,370-row
network census, download attachments, derive financial facts/features, train
models, or access protected outcomes. The immutable attachment root remains:

`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`

The lane remains `REVIEW` pending ChatGPT review.

## Remediations

### XLSX visibility contract

All XLSX evidence paths now use one workbook relationship and sheet-visibility
map. The resolver decodes cells only from sheets whose state is `visible`;
`hidden` and `veryHidden` worksheets are excluded. The fallback statement-title
scan no longer scans raw `xl/worksheets/*.xml`, so hidden/template titles cannot
resolve or conflict with visible filing evidence.

### XBRL authority contract

XBRL scope is accepted only from an exact inline-XBRL element whose `name` is:

`idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities`

and whose `contextRef` is exactly `CurrentYearInstant`. This is the only
context proven in the bounded sample. Plain text labels, other concepts,
missing context, unproven context IDs, invalid values, and wrong-context
authoritative concepts remain `UNRESOLVED`.

If multiple authoritative current-context facts resolve to different scopes,
the resolver returns `UNRESOLVED`. An invalid/wrong-context occurrence also
forces `UNRESOLVED` rather than being ignored beside a valid fact.

## Adversarial validation

Added tests for:

- hidden XLSX title with no visible scope -> `UNRESOLVED`;
- visible XLSX selector with conflicting hidden title -> visible result remains
  authoritative;
- XBRL plain scope label without the exact IDX-DEI concept -> `UNRESOLVED`;
- exact IDX-DEI concept with wrong or missing context -> `UNRESOLVED`;
- conflicting authoritative current-context XBRL facts -> `UNRESOLVED`.

The 11 manually verified immutable samples remain `11/11` correctly resolved:
the same seven `CONSOLIDATED` and four `SEPARATE` results as the prior
checkpoint.

## Validation

- focused resolver + Financial PIT tests: `27 passed, 0 failed`;
- full pytest: `498 passed, 0 failed, 3 warnings`;
- `git diff --check`: clean;
- no provider/network calls and no external raw-file changes.

## Decision boundary

`CONDITIONAL_FILING_LEVEL_SCOPE_RESOLVER_READY_REMEDIATED`

The resolver is now fail-closed against the two reviewed semantic blockers.
The prior bounded conclusion is unchanged: no market-wide scope reclassification
or PIT-ready count is claimed. PDF empirical coverage remains limited by the
absence of captured PDF bytes.
