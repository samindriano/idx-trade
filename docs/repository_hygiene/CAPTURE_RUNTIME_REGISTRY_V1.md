# IDX-Trade Capture Runtime Registry V1

Date: 2026-08-26 Asia/Jakarta
Status: `CAPTURE_SURFACE_CANONICALIZED_DELETE_PLAN_PENDING_APPLY`

Purpose: define the small set of data-acquisition systems that are allowed to remain conceptually active. A branch named `capture`, `forward`, `archive`, or `monitoring` is not automatically a canonical collector.

## Canonical capture surface

Exactly five capture families are recognized:

1. **Official Open Capture**
   - execution-grade authority: IDX `TradingSummary/GetStockSummary` -> `OpenPrice`
   - transport: `DIRECT_IDX_THEN_ZAPI_RAW_V1`
   - cloud archive prefix: `official-open-v1`
   - scheduled default-branch GitHub Actions producer; downstream E2E admission is separate and fail-closed.

2. **EOD Market Capture**
   - one canonical post-close transaction, not competing collectors.
   - **Stock EOD**: per-security OHLCV / Stock Summary inputs needed by clean scoring and paper runtime.
   - **Market + Index EOD context**: benchmark/index context belonging to the same EOD market transaction.
   - cloud-first POST_EOD orchestration is the intended replacement for the Windows-hosted operational path after first genuine cloud proof.

3. **Corporate Action Capture**
   - official prospective CA evidence and attestation needed for execution/accounting continuity.
   - integrated into the accepted E2E/CA-aware runtime; do not create a second independent CA collector merely for migration convenience.

4. **Stockbit Stream Capture**
   - scheduled GitHub Actions -> private R2.
   - current production workflow is on `main`; old bootstrap/remediation/smoke branches are not production authorities.

5. **Stockbit Intraday Capture**
   - current post-close intraday reconstruction/capture remains operationally distinct from Stockbit Stream.
   - functionality is retained; runtime migration from Windows to cloud is a future bounded migration lane.

## Not separate capture systems

The following are downstream/derived/research surfaces and must not be documented as independent canonical collectors unless a future explicit contract changes that decision:

- foreign-flow representation/forward sidecar: derived from canonical Stock Summary raw; historical forward implementation reports `provider_calls=0` for the sidecar path.
- price/trend state.
- reliability/uncertainty shadow evidence.
- model scoring, Decision, Sizing, Execution and PaperState.
- historical source-recovery experiments.

## Failed / closed source families

Do not revive these merely because cloud migration is underway:

- historical executable-Open recovery via approximate/provider-mismatched Yahoo/Zapi/TradingView/Investing paths;
- historical TradingView/Investing intraday admission attempts that failed frozen coverage/fidelity gates;
- early CA historical-continuity/scaffold attempts superseded by the clean/continuity/forward-CA lineage.

`docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md` remains binding historical evidence.

## Branch disposition audit

### A. `SAFE_TO_DELETE_BRANCH`

These heads are already merged/contained in a live canonical lineage. Removing the branch ref does not remove the production code or accepted history.

| Branch | Evidence / reason |
|---|---|
| `ops/idx-official-open-r2-cloud-capture-v1` | PR #90 merged; implementation retained in accepted E2E integration lineage. |
| `ops/idx-official-open-cloud-scheduler-v1` | PR #91 merged to `main`; scheduler workflow is retained on default branch. |
| `integration/e2e-cloud-first-orchestration-v1` | PR #92 merged; accepted integration merge SHA `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`. |
| `integration/forward-eod-automation-monitoring` | fully contained by current E2E integration ancestry; no active PR. |
| `integration/v4-x1-eod-auto-score-v1` | fully contained by current E2E integration ancestry; no active PR. |
| `fix/stockbit-stream-zapi-envelope-v1` | PR #35 merged. |
| `fix/stockbit-stream-daily-capture-v1` | PR #72 merged. |
| `fix/stockbit-stream-transient-reliability-main-v1` | PR #79 merged. |
| `fix/stockbit-stream-schema-diagnostics-v1` | PR #81 merged. |
| `fix/stockbit-r2-retention-v1` | retention remediation/closure merged; remote long-term policy recorded applied and verified. |

### B. `ARCHIVE_EXACT_HEAD_THEN_DELETE`

These contain unique unmerged commits, but their runtime purpose is superseded. Preserve an exact forensic ref before deleting the original branch.

| Branch | Exact audited head | Disposition |
|---|---|---|
| `ops/idx-forward-open-archive-v1` | `dc5e84b589eebe040119f48f9f69538d398a9d36` | PR #12 closed unmerged; source remained `BLOCKED_SOURCE_NOT_FROZEN`; never execution-grade; superseded by Official IDX `OpenPrice`. |
| `data/stockbit-stream-prospective-archive-v1` | `009be16e5db8a7a9899cff73f10f53dfc8a3fe6c` | four unique early-generation archive/workflow commits; production functionality is superseded by the evolved `main` Stockbit V2 path. |
| `ops/stockbit-stream-observable-smoke-v1` | `17803978c1e145dbe084c828e45bed5247c13aa6` | PR #34 intentionally closed unmerged after validation-only five-ticker smoke; relevant envelope/runtime change subsequently promoted through PR #35. |

Because the current GitHub connector exposes branch-ref creation but not tag-ref creation/deletion, temporary exact-head forensic refs were created under:

- `archive/capture-hygiene-v3/forward-open-scaffold-dc5e84b5`
- `archive/capture-hygiene-v3/stockbit-v1-base-009be16e`
- `archive/capture-hygiene-v3/stockbit-observable-smoke-17803978`

A local/API-capable hygiene apply should preferably convert these to lightweight/annotated `archive/capture-hygiene-v3/*` tags and then remove both the original branches and temporary archive branches atomically.

### C. `DO_NOT_DELETE_YET`

| Branch | Reason |
|---|---|
| `audit/stockbit-stream-v2-red-team-v1` | PR #36 remains open/draft and contains unique adversarial work. |
| `data/market-index-forward-eod-v1-monitoring` | still has unique commits relative to current E2E integration; must audit/absorb EOD index-context behavior first. |
| `fix/stockbit-intraday-postclose-fix-v1` | current Stockbit intraday operational implementation; future cloud migration target. |
| `ops/e2e-paper-cloud-launcher-v1` | active cloud launcher PR #93 lane. |
| `integration/idx-e2e-baseline-paper-v1` | current accepted E2E implementation anchor. |

Historical/research branches outside the capture surface are intentionally out of scope for this pass.

## Runtime deletion safety

Branch cleanup is not scheduler retirement.

- Stockbit Stream production workflow checks out the default branch, not old remediation branches.
- Official Open workflow checks out a commit SHA, not its old implementation branch.
- E2E cloud launcher checks out accepted integration SHA `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`.
- Windows E2E/EOD/intraday tasks remain untouched until their specific cloud replacement proves one genuine prospective cycle and retirement is separately authorized.

## Next hygiene gate

1. merge this registry/documentation cleanup;
2. audit the two unique `data/market-index-forward-eod-v1-monitoring` commits against the accepted EOD market transaction;
3. close/integrate PR #36 before deciding its branch disposition;
4. using a local/API-capable atomic ref operation, create permanent archive tags for the three exact unique heads and delete only branches certified above;
5. verify default-branch workflows and pinned-SHA workflows remain unchanged after branch deletion.
