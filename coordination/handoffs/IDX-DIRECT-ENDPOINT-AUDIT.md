# Handoff

from: Codex/IDX-Direct-Endpoint-Audit
to: ChatGPT independent review
task_id: IDX-DIRECT-ENDPOINT-AUDIT-V1
model_used: Codex root; no worker delegated
reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
source_commit: `afa68e57e8aa770ca3e3ba26ed07edcbba7907c6`
branch: `data/idx-direct-endpoint-audit-v1`
head_commit: `67b922bcac18d4395505bbd645cfb0c2c30dd381` (follow-up PIT semantics checkpoint)

## Scope

Bounded read-only setup/discovery audit of `nichsedge/idx-bei` for direct
official IDX endpoints that could support PIT sector history, historical
listing universe, corporate actions/shares, and financial-report provenance.
No model integration, bulk backfill, dataset mutation, protected outcome
access, retraining, or rescore.

## Files changed

- `docs/checkpoints/2026-08-13_IDX_DIRECT_ENDPOINT_AUDIT_BLOCKED.md`
- `coordination/handoffs/IDX-DIRECT-ENDPOINT-AUDIT.md`
- `coordination/TEAM_STATUS.md` (lane claim/status row only)

The cloned `idx-bei` repository is external and remains outside Git:
`D:\Documents\Project\idx-bei-direct-audit-20260813`.

## Findings

- `idx-bei` cloned at `75d6c0f`; its existing tests pass `24/24` under Python
  3.13.5. `uv sync` was unavailable because `uv` is not installed.
- The client can issue a direct request only to the extent shown by the
  bounded smoke test: with `impersonate=None`, IDX returned HTTP `403` HTML
  from Cloudflare, not JSON.
- Request: `/primary/TradingSummary/GetStockSummary`,
  `date=20260811`, `start=0`, `length=5`.
- Total direct requests: `3` (two raw direct probes for evidence capture and
  one `IDXClient` wrapper check with `max_retries=0`); all returned 403.
- No endpoint expansion occurred after the challenge. The candidate routes in
  the checkpoint are static source inventory only, not runtime evidence.
- External manifest SHA:
  `9239312e103e636adc26074420a2abe1d096e89109efe8cb9c52bf256e369896`.
- Immutable IDX-Trade artifacts and model semantics were untouched.

## Decisions made

- `BLOCKED_DIRECT_IDX_SECURITY_CHALLENGE`.
- Do not use the cloned repository's default Chrome impersonation as a
  challenge bypass.
- Do not promote candidate endpoints, historical PIT coverage, or source
  parity from static documentation.

## Decisions needed

- ChatGPT review: whether a compliant, separately authorized access path exists
  before any future direct IDX endpoint retry.

## Blocking risks

- Direct official IDX endpoint access is denied by the observed security
  challenge in this runtime. No current evidence establishes that the
  historical PIT-sector, listing-history, issued-history, or financial-report
  routes are reachable without bypassing that challenge.

## Validation

- `python -m pytest tests/ -q` in external `idx-bei/python`: `24 passed`.
- Direct request smoke with `impersonate=None`: `403`.
- `IDXClient(max_retries=0, delay_seconds=0, impersonate=None)`: `403`.

## Follow-up result

The user authorized testing the repository's documented usage. With the
repository default `curl_cffi` `impersonate="chrome"`, the stock-summary smoke
request and 15 bounded `LINK_FINANCIAL_DATA_RATIO` queries returned HTTP 200.
The ratio rows include sector hierarchy fields and `fsDate`, but no publication
timestamp. `periodQuarter` is not self-describing: for BIPI/2022 the observed
mapping was 1→2021-09-30, 2→2022-03-31, 3→2022-06-30, 4→2022-09-30.

PIT cross-check is negative for ratio fields: PALM is already `Financials` on
`fsDate=2023-06-30`, while the existing official PIT evidence says its change
was effective 2023-10-02. `GetAllAnnouncement` was also tested with a bounded
PALM date filter and returned HTTP 503 Cloudflare HTML. The follow-up checkpoint
is `docs/checkpoints/2026-08-13_IDX_BEI_DOCUMENTED_CLIENT_PIT_PROBE.md` and its
external manifest SHA is
`0c213a8fe035526a914ce5b4119730d8a60de4215202a99319db6355a6ef9e17`.

Decision: transport is technically usable under the repository's documented
impersonation method, but `LINK_FINANCIAL_DATA_RATIO` is not PIT-safe and
`GetAllAnnouncement` remains unverified. Do not integrate the ratio sector
fields into PIT history.

## Recommended next action

Stop for independent ChatGPT review. Do not bulk acquire, modify the IDX-Trade
dataset/model, open protected outcomes, or retry with browser impersonation.
