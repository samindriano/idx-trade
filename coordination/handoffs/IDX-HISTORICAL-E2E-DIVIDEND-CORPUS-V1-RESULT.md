# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-DIVIDEND-CORPUS-V1
model_used: GPT-5
reasoning_level: high
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `4cded37de834d017b9852765ddb2827166a009b3`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: `a698782846fbd13bc57367390ee7f3ca4b9acd92`
scope: outcome-blind official IDX issuer-announcement corpus discovery
files_changed:
  - `scripts/capture_forward_dividend_announcements_v1.py`
  - `src/idx_trade/forward_dividend_acquisition_v1.py`
  - `tests/test_forward_dividend_acquisition_v1.py`
  - `docs/checkpoints/2026-08-24_HISTORICAL_E2E_DIVIDEND_CORPUS_BOUNDARY_V1.md`
  - this handoff

findings:
  - The pinned direct IDX endpoint is `ListedCompany/GetAnnouncement`.
  - `pageSize=100,indexFrom=100` can return an empty page before `ResultCount`
    is exhausted; a bounded probe with `pageSize=9999` returned all 106 rows.
  - The launcher now requests the larger page while retaining strict count and
    pagination completeness gates.
  - Issuer histories may include security-class identifiers such as `BABY-R`.
    Those raw rows are preserved but excluded from the common-share dividend
    candidate contract; other issuer mismatches remain fail-closed.
  - Fresh market-wide acquisition did not complete because `ASSA` returned
    HTTP 403 after earlier partial progress.

decisions_made:
  - No retry after the HTTP 403.
  - No provider substitution.
  - No dividend event was promoted.
  - No strict replay scope was opened.
  - Partial raw stages remain external and are not treated as an atomic corpus.

decisions_needed:
  - Whether MAIN authorizes a separately bounded, rate-limited continuation or
    an official archive route to establish complete per-ticker coverage.
  - Whether the current strict dividend gate should remain blocked until that
    evidence exists. Current evidence supports keeping it blocked.

blocking_risks:
  - Market-wide no-event proof is absent for the 347-ticker exposure universe.
  - HTTP 403/rate-limit behavior prevents claiming complete coverage from the
    current one-shot acquisition.

validation_run:
  - `python -m pytest tests/test_forward_dividend_acquisition_v1.py -q` → 9 passed
  - `python -m py_compile scripts/capture_forward_dividend_announcements_v1.py src/idx_trade/forward_dividend_acquisition_v1.py tests/test_forward_dividend_acquisition_v1.py` → PASS
  - `git diff --check` → PASS

recommended_next_action: Keep `DIVIDEND_MARKET_WIDE_NO_EVENT_PROOF_MISSING`
  active; review the pinned endpoint/rate-limit boundary before any further
  acquisition. Do not run historical performance replay or Monte Carlo while
  the strict scope remains empty.
