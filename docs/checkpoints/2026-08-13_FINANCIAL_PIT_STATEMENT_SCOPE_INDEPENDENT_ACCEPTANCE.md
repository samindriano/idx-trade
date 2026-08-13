# Financial PIT Statement-Scope Resolver — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/financial-pit-statement-scope-v1`
Reviewed HEAD: `e4537c16c5011d8cafc55bc72e8f04017b874baf`
Reviewed remediation commit: `68fe984f5d45391fff084873aad2a194a48649e5`
Decision: `FINANCIAL_PIT_STATEMENT_SCOPE_RESOLVER_ACCEPTED_OFFLINE_RECLASSIFICATION_NEXT`

## Review conclusion

The bounded statement-scope feasibility result and engineering remediation are accepted.

The two prior semantic blockers are closed:

1. XLSX scope evidence now uses the workbook relationship and sheet-visibility map for every evidence path. Hidden and `veryHidden` worksheets cannot contribute scope evidence, including fallback statement-title evidence.
2. Inline XBRL scope now requires the exact IDX-DEI concept `idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities` with `contextRef=CurrentYearInstant`. Plain labels, wrong concepts, wrong or missing contexts, invalid values, and conflicting authoritative facts fail closed to `UNRESOLVED`.

The immutable manually verified sample remains 11/11: seven `CONSOLIDATED`, four `SEPARATE`, zero mixed. This supports the current filing-level resolver contract for the observed IDX representations, while preserving the rule that any future genuinely mixed authoritative scope requires statement/fact-level schema escalation.

PDF empirical coverage remains unproven because PDF bytes were not present in the existing immutable capture and no redownload was authorized. PDF cases therefore remain fail-closed unless separately validated later.

## Validation accepted

- focused Financial PIT tests: 27 passed;
- full pytest: 498 passed, 0 failed, 3 existing warnings;
- `git diff --check`: clean;
- no network calls, attachment redownloads, census reruns, financial fact/feature derivation, model work, or protected outcome access.

## Authorized next milestone

A separate **offline scope reclassification / PIT-ready coverage recomputation** is authorized.

Reuse only the already captured immutable Financial PIT attachments and existing 6,108 exact report-announcement byte joins. Do not rerun the 7,370 network census and do not redownload attachments.

The offline task should:

- apply the accepted scope resolver to each exact join using the preserved attachment bytes;
- emit `CONSOLIDATED`, `SEPARATE`, or `UNRESOLVED` plus auditable evidence and source hash;
- recompute PIT-ready counts by year/period under the existing publication-chain gates;
- preserve the existing 74 ambiguous attachment cases, 2 hash conflicts, 28 HTTP/provider failures, and publication-linkage gaps as excluded/fail-closed rather than repairing them;
- report format coverage (XLSX/XBRL/PDF/unsupported), resolved-vs-unresolved scope counts, and any mixed/conflicting authoritative content;
- stop before financial fact extraction, ratios/features, model work, or protected outcomes.

Only after independent review of that offline coverage result may a Financial PIT fact-table milestone be considered.
