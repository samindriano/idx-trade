# E2E Final Pre-Weekday Reconciliation — 2026-08-23

Date: 2026-08-23 (Asia/Jakarta)  
Branch: `integration/idx-e2e-baseline-paper-v1`  
Validated source commit before this checkpoint: `c943960af93785a2eba3989d6fd34e5392f4cd26`  
Remote hardening baseline adopted: `af7c65f787b231a25dfff3126dabeb59c93a33f8`

## Scope and boundary

This is a Sunday deployment reconciliation only. It does not change V4-X1,
Decision V2, Sizing V1, Execution V1, labels, protected outcomes, or the live
PAPER state. No retroactive paper execution was attempted.

The four-commit remote hardening was reviewed. The only concrete defect was a
stale regression assertion in
`tests/test_v4_x1_execution_v1_official_open_verify.py`: the hardened Zapi
envelope now rejects a direct-payload relabel with the specific
`OFFICIAL_OPEN_ZAPI_RAW_PROJECT_MISMATCH` error. The assertion was updated in
the local commit recorded above; production code was not changed by this
remediation.

## Validation

- Official Open / execution focused suite: **47 passed**.
- Operational, CA, orchestration, phase-attestation, Official Open, and
  execution verification suite: **97 passed**.
- Full repository pytest: **702 passed**, 3 pre-existing pandas
  `FutureWarning`s, 0 failures.
- `py_compile`: PASS for changed/affected modules and scripts.
- `git diff --check`: PASS.

The hardened envelope contract is covered: expected `project=finance:idx`,
non-empty envelope timestamp, nested `provider=idx`, nested
`path=TradingSummary/GetStockSummary`, coherent full-session counts, wrong
markers rejected, transport relabels rejected, zero OpenPrice remains
unavailable, and malformed direct HTTP 200 does not silently fall back.

## Real dynamic-CA smoke

One bounded smoke used the production capture implementation, not a hand-built
attestation:

- phase: `POST_EOD`
- from/through: `2026-08-21` / `2026-08-21`
- required tickers: `BBCA`
- provider checkout: `D:\Documents\Project\idx-bei-forward-ca-provider`
- provider commit: `75d6c0f74fa360d225794c70c383348977de6798`
- isolated output root:
  `C:\Users\Sam\AppData\Local\Temp\idx-e2e-dynamic-ca-smoke-20260823-b457faaa6a53413198bd968d5048d123`

The first official IDX `ListingActivity/GetIssuedHistory` request returned
HTTP **403** after the provider transport's bounded retry policy. The run
therefore stopped fail-closed. It left only a `.partial.*` staging directory
with raw evidence for the attempted legs; the final phase directory,
`MANIFEST.json`, and V1.2 attestation were not published. Consequently the
real provider-level attestation verifier was **not reached**. No Zapi fallback
was substituted for this CA source, and no protected outcome was accessed.

Verdict: `DYNAMIC_CA_REAL_PROVIDER_SMOKE_BLOCKED_IDX_HTTP_403`.

## Deployment reconciliation

Before reconciliation, the installed E2E task pointed to external config SHA
`6a64e8ef3f0659ed7eb46de816fcacb191e9c4808c91f154c6e1909bbcb7f0d1`, which
still pinned commit `759e1c0e...` and the stale CA capture-script SHA
`a391b776...`. The current branch's actual CA script SHA is
`76a5af4c5a636a4f89a922d6e05cda892296a1b72ff3c148a7ee31d2905e12db`.

The final deployment state is recorded in the handoff: external config is
repinned to the final clean branch HEAD and actual script bytes; the existing
`IDXTrade-E2E-Paper` action is updated only with the new config SHA. The task
is not reinstalled and its trigger/settings contract is preserved.

`IDXTrade-E2E-OfficialOpen` remains the existing task, with direct IDX primary
and Zapi raw IDX passthrough only on direct transport failure. No duplicate
task was created.

## Sunday conclusion

The code and deployment pins are reconciled, but the real dynamic-CA source
smoke is blocked by official IDX HTTP 403 and no legitimate weekday cycle has
occurred. The system remains armed for the first prospective weekday evidence;
no first-live-weekday pass is claimed.

Decision: `CONTROLLED_LIVE_E2E_ARMED_FIRST_WEEKDAY_PROOF_PENDING`.
