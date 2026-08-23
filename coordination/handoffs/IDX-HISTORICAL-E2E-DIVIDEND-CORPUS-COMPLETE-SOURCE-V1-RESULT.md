# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-DIVIDEND-CORPUS-COMPLETE-SOURCE-V1
model_used: GPT-5
reasoning_level: high
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `369907b6b9a9aec740624d2ffd5b210e54cf9d84`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: `0d341bb9ca2aa12acab7d464d7f27190c30860f3`
scope: offline normalization and coverage audit of immutable official IDX
  issuer-announcement raw bytes
files_changed:
  - `src/idx_trade/forward_dividend_acquisition_v1.py`
  - `scripts/capture_historical_dividend_corpus_batch_v1.py`
  - `scripts/normalize_historical_dividend_corpus_batch_v1.py`
  - corresponding tests
  - this checkpoint and handoff

findings:
  - All 347 required tickers have complete raw `GetAnnouncement` responses.
  - 53,637 source rows passed exact response-count checks.
  - 921 dividend-related candidates were extracted: 844 cash, 60 ambiguous,
    and 17 unsupported non-cash.
  - Cash candidates span 201 tickers and reference 2,023 official attachments.
  - 146 tickers have no dividend-keyword candidate in the complete source
    pages, but this is not yet a certified no-event result.

decisions_made:
  - Source raw bytes remain immutable and external.
  - Parser alias handling was tightened to exclude only explicit non-common
    security/metadata forms; other issuer mismatches remain fail-closed.
  - Normalization was offline; no provider call was made for the normalized
    artifact.
  - The frozen dividend gate and historical replay scope remain blocked.

decisions_needed:
  - Whether to authorize attachment-level semantic acquisition/review for the
    844 cash candidates, or accept the source-complete-but-semantics-pending
    boundary.

blocking_risks:
  - Title-level candidates do not prove exact dividend economic terms,
    ex/entitlement/payment chronology, or correction lineage.

validation_run:
  - focused dividend/source tests: 11 passed with external `--basetemp`
  - py_compile: PASS
  - git diff --check: PASS

recommended_next_action: Use the complete source manifest to group exact
  announcement identities and perform only the smallest attachment-level
  semantic review needed for actual exposure windows. Do not run performance
  replay or Monte Carlo before the strict scope is frozen.
