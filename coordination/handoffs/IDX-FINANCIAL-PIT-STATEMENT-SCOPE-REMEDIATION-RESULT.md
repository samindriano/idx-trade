# Handoff

from: Codex/Financial-PIT-Statement-Scope
to: ChatGPT independent review
task_id: IDX-FINANCIAL-PIT-STATEMENT-SCOPE-REMEDIATION
model_used: gpt-5.6-luna xhigh with one read-only Orchestra audit worker
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 2fbfef0836106d819c892c6f820f5606896b4575
branch: data/financial-pit-statement-scope-v1
head_commit: pending push
scope: Engineering-only fail-closed remediation of XLSX visibility and XBRL authority/context semantics.
files_changed:
  - src/idx_trade/financial_scope_resolver.py
  - tests/test_financial_scope_resolver.py
  - docs/checkpoints/2026-08-13_FINANCIAL_PIT_STATEMENT_SCOPE_REMEDIATION.md
  - coordination/handoffs/IDX-FINANCIAL-PIT-STATEMENT-SCOPE-REMEDIATION-RESULT.md
findings:
  - XLSX title fallback now reuses workbook relationship and visible-sheet map; hidden and veryHidden sheets cannot contribute evidence.
  - XBRL requires exact idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities and contextRef=CurrentYearInstant.
  - wrong/missing context, plain labels, invalid context facts, and conflicting authoritative facts fail closed.
  - existing 11 manually verified samples remain 11/11.
decisions_made:
  - Keep the lane in REVIEW; do not reclassify census rows or claim PIT readiness.
  - Preserve no-network/no-redownload/no-facts/no-model/no-outcome boundaries.
decisions_needed:
  - ChatGPT review before any market-wide scope reclassification.
blocking_risks:
  - PDF bytes are absent from the immutable capture root; no PDF classification was promoted.
  - A future filing with genuine statement/fact-level mixed scope still requires schema escalation.
validation_run:
  - python -m pytest tests/test_financial_scope_resolver.py tests/test_financial_pit_adapter.py tests/test_financial_pit.py -q: 27 passed
  - python -m pytest -q: 498 passed, 0 failed, 3 warnings
  - git diff --check: clean
recommended_next_action: ChatGPT review of remediation; only then consider a separately authorized market-wide resolver census.
