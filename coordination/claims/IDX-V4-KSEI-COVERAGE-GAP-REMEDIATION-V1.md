# Claim — IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1

owner: `ChatGPT/V4-KSEI-Coverage-Gap`
branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
parent: `data/idx-v4-ca-blocker-attribution-v1@052351372215a5752199513a23cf3f7373ac1f59`
status: `PREPARED_LOCAL_PROVIDER_EXECUTION_PENDING`

## Scope

Target only the exact 43 KSEI history coverage gaps frozen by the accepted 610-ticker census. Diagnose the immutable parent request failures, then perform one bounded official-KSEI-only recovery attempt for those 43 tickers using the unchanged strict history parser. Materialize an append-only coverage/history overlay and, if the acquisition completes, one outcome-blind continuity replay under the latest accepted V4 CA semantics.

## Exact 43-ticker identity

SHA-256 of newline-delimited sorted tickers plus trailing newline:

`1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`

The exact tickers are frozen in `config/v4_ksei_coverage_gap_remediation_v1.json`.

## Hard boundaries

- no recrawl of the 567 already coverage-certified tickers;
- no alternate provider or mirror;
- no alternate KSEI security identity / alias substitution;
- no parser or CA semantic relaxation;
- no target, rank, model, prediction, performance, protected/fresh-forward outcome access;
- raw provider bytes and merged full history/continuity ledgers remain external;
- Git promotion is limited to small provenance, delta, summary, and per-date artifacts.

Before the local provider run, the canonical `origin/main:coordination/TEAM_STATUS.md` row must be set to `ACTIVE` under the repository safe shared-file rule. If another ACTIVE lane owns the same 43-ticker KSEI coverage scope, STOP.
