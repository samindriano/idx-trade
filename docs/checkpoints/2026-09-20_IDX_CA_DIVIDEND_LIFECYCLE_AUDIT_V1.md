# IDX-Trade Corporate Action / Dividend Lifecycle Audit V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `BOUNDED_PASS_WITH_POLICY_AND_SOURCE_BLOCKERS`  
Scope: isolated, outcome-blind system deep-dive; no provider call, cloud/capture
mutation, canonical-data write, production change, or protected-outcome access.

This checkpoint extends the system-wide marathon. It is deliberately separate
from the historical alpha archive and from the incumbent/model-alpha lane.
It records both the earlier corporate-action work and the current continuation
audit. Historical/prior evidence is labelled explicitly; it is not silently
re-presented as a fresh live result.

## 1. Historical user-provided corporate-action thread

The attached text file
`C:\Users\Sam\.codex\attachments\fd198658-3b8d-43ff-987b-6a577a58d990\pasted-text.txt`
contains a prior Zapi feature request and follow-up:

- 2026-09-01: request for deterministic corporate-action coverage metadata on
  `GET /v1/finance:idx/corporate-actions?code=BBCA`, including coverage start/end,
  total, pagination, `complete_for_query`, and source.
- 2026-09-02: follow-up asking for the same contract on stock splits, an
  optional combined endpoint type, explicit semantics for `completeForQuery`,
  distinction between valid-empty and invalid/unverified tickers, source/report
  provenance, family-specific date semantics, and revision/correction metadata
  only where upstream actually provides it.
- 2026-09-07: Zapi documentation links were supplied for stock splits,
  corporate actions, dividends, rights offerings, additional listings,
  delistings, and new listings.
- The thread contains conversational “done”/follow-up messages, but no
  hash-pinned response contract, immutable response artifact, pagination proof,
  row-level available-at timestamp, revision identity, or admission record.

Disposition: this is `HISTORICAL_USER_PROVIDED_FEATURE_REQUEST`, useful for
lineage and future source review, but not evidence that Zapi corporate-action
coverage is complete, PIT-safe, canonical, or admitted into the model/system.

## 2. Earlier repository work — HISTORICAL / PRIOR

The earlier repository work did not stop at the Zapi thread. The following
artifacts are present in the pinned runtime/documentation history:

| Earlier artifact | Result | Boundary |
|---|---|---|
| `2026-08-22_E2E_REAL_BBCA_DIVIDEND_DURABLE_RESTART_ACCEPTANCE.md` | Real admitted official IDX BBCA cash-dividend evidence; process-style reload through ex-date receivable and 2026-09-16 settlement; one settlement and zero receivable after payment; `45 passed` focused slice | Offline acceptance using already captured official evidence; explicitly no Zapi request |
| `2026-08-23_E2E_DIVIDEND_ACQUISITION_V1_2_ACCEPTANCE.md` | Fresh real direct IDX D2B batch; `69 passed` focused dividend/CA suite and `608 passed` full repository suite at that historical head | Zapi dividend data was not used; gross-versus-tax/net treatment intentionally unresolved |
| `2026-08-23_CASH_DIVIDEND_E2E_REMEDIATION_RESULT.md` | `DETERMINISTIC_CORE_REPLAY_PASS`, `PRODUCTION_PATH_REPLAY_PASS`, `RESUME_PROBE_PASS`; `83 passed` focused remediation and `656 passed` full repository suite at that historical head | Tax/net policy remained unresolved; no live scheduler/protected-forward mutation |
| `2026-08-23_CASH_DIVIDEND_E2E_ADVERSARIAL_RESULT.md` | Economic-oracle and cold-restart adversarial coverage; one settlement, no double credit, pending Open recovery, and production replay | Synthetic files plus real verifiers; not broker-fill or provider-completeness proof |

These are genuine historical acceptance records, not claims about the current
live deployment. The current alpha lane also has a separate CA/issuer price
basis audit: `2026-09-20_ALPHA_CA_CANDIDATE_EXPOSURE_COMPLETENESS_RESULT_V1.md`.
That audit remains `PASS_BOUNDED_FORENSIC / GLOBAL_BASIS_BLOCKED`: 55 official
stock-split inventory rows are discovery inventory, 39 have numeric ratios, and
there is no population-wide transition ledger joining every candidate to
effective time, issuer/ISIN, knowledge time, and price basis.

## 3. Current source/admission position — CURRENT

The local Zapi admission audit
`2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md` remains the governing
read-only source-capability result:

- four persisted Zapi probe directories were inspected without network access;
- one BBCA profile snapshot contained one 2026 dividend row;
- March and August monthly dividend probes contained zero usable rows;
- the response surface exposed request pagination fields but no row-level
  publication/knowledge time, revision/vintage identifier, source-selection
  contract, or historical available-at field;
- official parity failed for the sampled event;
- result: `BLOCKED / NOT_ADMITTED / NO_NEW_ALPHA_SURFACE`.

Therefore the user-provided Zapi thread is retained as a historical source lead,
not used to repair the clean panel, construct a dividend feature, or certify
corporate-action completeness. The exact requirement that would be needed for
future admission is: bounded pagination/completeness semantics, row-level PIT
timing, security identity continuity, event-family date semantics, immutable
source/revision identity, and independent authority/parity.

## 4. Current pinned runtime contract audit

The component audit used the isolated scratch extraction pinned to runtime
commit `045e25a19d9f71170d2c863e768102937e59ad73` at:

`C:\Users\Sam\AppData\Local\Temp\idx-system-045e25a1-dd0f02dcb71f48cf82d2b81e0eead8cf`

No source in that extraction or in the active checkout was edited. Relevant
implementation surfaces:

- `src/idx_trade/forward_dividend_v1.py`: certified event, entitlement,
  receivable, settlement, ledger normalization, total-return NAV, execution
  state/ledger hashes, and Decision/Sizing/Execution bridge.
- `src/idx_trade/forward_dividend_runtime_v1_1.py`: append-only certified
  registry, state/ledger/registry hashes, atomic snapshot writes, recursive
  parent chain, tamper checks, and fork detection.
- `src/idx_trade/forward_dividend_orchestration_v1.py`: coverage/journal
  progression, blocker-to-certification resolution, evidence references, and
  same-day phase ordering.
- `src/idx_trade/forward_dividend_execution_v1_1.py`: execution-time authority,
  date-window, status, and attachment/review verification.

### 4.1 Certified-event gates — bounded PASS

The event validator requires a non-empty event id, normalized ticker, positive
per-share amount, ordered `cum < ex <= record <= payment` dates, and a 64-hex
source-evidence hash. Direct certification additionally requires admitted
semantic fields, announcement/document hashes, and byte-level attachment
verification. A post-cum announcement is allowed only with explicit matching
knowledge-time metadata; late entitlement recovery then requires an immutable
cum-date state.

This protects against using a later announcement as if it had been known before
the cum date. It does not by itself prove that the source population is
complete; that is the separate source/admission problem above.

### 4.2 Entitlement and receivable lifecycle — bounded PASS

The lifecycle is explicit:

`certified event -> cum-date entitlement -> ex-date receivable -> payment-date settlement -> cash`

The cum-date snapshot uses the position at cum date. Selling on ex-date does
not erase an already recorded entitlement. A first buy on ex-date cannot receive
the prior dividend. Late certification cannot infer entitlement from the
current mutated position and fails closed without the historical cum-date state.

Receivable amount is recomputed as entitled shares times gross dividend/share.
Ledger normalization rejects duplicate rows, receivables without entitlements,
settlements without entitlements, conflicting event identity, and mismatched
source/date/amount fields.

### 4.3 NAV versus spendable cash — bounded PASS

Before payment, a receivable contributes to total-return NAV but remains outside
base cash and therefore outside spendable cash. At payment, the receivable is
removed and the exact gross amount is credited to cash. Repeated processing at
the same payment session is state-idempotent and does not double-credit.

The design intentionally records gross paper credit with
`UNRESOLVED_GROSS_PAPER_CREDIT`. It does not infer tax, net proceeds, withholding,
or investor-specific treatment. This is a policy blocker for economic
certification, not a hidden tax calculation.

### 4.4 Execution and restart binding — bounded PASS

Dividend-aware execution plans bind both the dividend-aware state hash and
ledger hash. A changed state or ledger fails before open execution. When a
receivable changes total-return NAV, the bridge resizes from corrected NAV while
keeping projected available cash unchanged. This preserves the intended
distinction between NAV and spendable cash.

Runtime snapshots bind base paper state, dividend ledger, certified registry,
internal hashes, snapshot payload hash, and a recursively verified prior
snapshot. Identical same-session snapshots are idempotent; divergent same-session
content fails; modified parents/reviews fail; dropped registry events and
forked snapshot histories fail.

The durable snapshot contract is stronger than an in-memory replay, but it does
not prove that an external cash/broker statement agrees with the paper gross
settlement. It also does not resolve tax policy or provider population
completeness.

## 5. Current synthetic observation — CURRENT MARATHON

A new isolated synthetic probe used one certified BBCA-like event with 200
shares, Rp25 gross dividend/share, cum `2026-08-28`, ex `2026-08-31`, payment
`2026-09-16`, and a synthetic 64-hex evidence hash. It touched only Python
objects in the scratch extraction; no repository, provider, cloud, capture, or
canonical artifact was changed.

Observed values:

| Check | Observation | Result |
|---|---:|---|
| Cum-date entitlement | 200 shares | PASS |
| Ex-date receivable | Rp5,000 | PASS |
| Ex-date base cash | Rp1,000,000 unchanged | PASS: receivable not spendable cash |
| Ex-date total-return NAV in probe | Rp1,005,000 for cash-only state plus receivable | PASS |
| Payment cash | Rp1,005,000 | PASS |
| Receivables after payment | 0 | PASS |
| Settlements after payment | 1 | PASS |
| Same-session payment replay | state equal to first payment | PASS |
| Tax treatment | `UNRESOLVED_GROSS_PAPER_CREDIT` | EXPLICIT POLICY BLOCKER |
| Late certification without historical cum state | `DIVIDEND_V1_HISTORICAL_CUM_STATE_REQUIRED` | PASS_FAIL-CLOSED |
| Late certification with immutable cum state | 200 shares recovered | PASS |

The probe is a contract/invariant observation, not a market-performance result
and not a new real corporate-action event.

## 6. Validation evidence run in this continuation

Selected tests were run from the pinned scratch extraction with `PYTHONPATH=src`:

| Test group | Count | Result |
|---|---:|---|
| `test_forward_dividend_v1.py` | 13 | PASS |
| `test_forward_dividend_runtime_v1_1.py` | 15 | PASS |
| `test_forward_dividend_execution_v1_1.py` | 10 | PASS |
| `test_forward_dividend_orchestration_v1.py` | 40 | PASS |
| `test_forward_dividend_disposition_v1_2.py` | 8 | PASS |
| `test_forward_dividend_provenance_v1_2.py` | 10 | PASS |
| `test_forward_dividend_semantic_review_v1_2.py` | 20 | PASS |
| **combined continuation slice** | **116** | **PASS** |

The runtime/orchestration subset was also rerun with pass listing: 15 runtime
tests and 40 orchestration tests passed. Coverage includes same-session
idempotency, payload/parent/review tamper, registry append-only behavior,
receivable-to-settlement progression, fork detection, coverage monotonicity,
journal hash chains, blocker resolution, and same-day phase ordering.

## 7. Findings and remaining blockers

### PASS / bounded

1. Certified cash-dividend mechanics are explicit and hash-bound.
2. Cum-date entitlement, ex-date receivable, payment settlement, and NAV/cash
   separation are locally deterministic.
3. Duplicate/conflicting event identity and ledger inconsistencies fail closed.
4. Late knowledge requires historical cum-date state instead of current-position
   inference.
5. Runtime snapshot and journal ancestry are recursively verified and fork-aware.
6. The Decision/Sizing/Execution bridge preserves dividend-aware identity and
   spendable-cash semantics.

### FAIL / UNKNOWN / policy-bound

1. Zapi corporate-action coverage is not admitted as complete or PIT-safe. The
   historical feature request and documentation links do not provide a pinned
   response contract or source artifact.
2. Non-cash structural corporate actions remain fail-closed; the current cash
   dividend lifecycle cannot certify splits, rights, bonus shares, conversions,
   mergers, listing, relisting, or delisting mechanics.
3. Gross-versus-net/tax policy is intentionally unresolved. A production
   economic claim must choose and freeze the accounting treatment before it can
   be called tax-correct.
4. Settlement is modeled from the certified payment date. There is no separate
   broker/custodian cash-statement authority in this lane, so external settlement
   reconciliation is UNKNOWN.
5. The current CA/issuer price-basis audit still lacks population-wide event,
   issuer/ISIN, knowledge-time, and common-price-basis linkage for every alpha
   candidate/window.
6. This validation does not remove the broader system blockers already recorded:
   durable T0/continuity crash gaps, missing full runtime-config/projected-CA
   identity, absent portfolio risk overlay, uncalibrated slippage, and missing
   aggregate liquidity guard.
7. A current synthetic positive-buy underfill composed with the CA lifecycle
   produced entitlement/receivable/payment for actual 1,200 shares rather than
   the 5,000 planned shares. The resulting IDR 95,000 difference is an upstream
   execution-underexposure consequence, not a CA over-entitlement defect; the
   residual buy was absent before CA processing.

## 8. Decision and next frontier

Decision for this lane:

`CASH_DIVIDEND_LIFECYCLE = BOUNDED_PASS`

`CORPORATE_ACTION_SOURCE_COMPLETENESS = BLOCKED / NOT_ADMITTED`

`NON_CASH_CA_EXECUTION = FAIL_CLOSED`

`TAX_NET_POLICY = UNRESOLVED`

This does not justify reopening Zapi/provider acquisition, changing the clean
panel, or promoting a new alpha. The next high-value local system frontier is a
single synthetic end-to-end invariant matrix that composes Decision state,
sizing, partial fills, projected CA cash, cost accounting, nominal risk,
restart, and artifact identity. Any future CA-source work must remain a new
explicit source-admission lane with its own completeness/PIT/identity contract.

## 9. Provenance and non-mutation statement

- Active lane: `codex/alpha-available-data-20260919`.
- Pinned runtime extraction: `045e25a19d9f71170d2c863e768102937e59ad73`.
- New work in this continuation: this documentation checkpoint only; no
  implementation or configuration change.
- The current checkout had unrelated concurrent modifications/untracked files;
  they were not staged, edited, removed, or reset.
- No provider/network/Zapi call, cloud/R2 access, production scheduler/capture
  action, canonical data mutation, telemetry action, archive/reset, merge, or
  push was performed.
