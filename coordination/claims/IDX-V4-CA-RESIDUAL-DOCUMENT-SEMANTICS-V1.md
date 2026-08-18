# Claim — IDX-V4-CA-RESIDUAL-DOCUMENT-SEMANTICS-V1

Status: `ACTIVE_PREP`
Owner: `ChatGPT/V4-CA-Residual-Document-Semantics`
Branch: `data/idx-v4-ca-residual-document-semantics-v1`
Scientific parent: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1@c2246e5e82dc642950017e38e57cd97700e15199`

## Scope

Outcome-blind, offline-only reuse of the already acquired official KSEI Stage-2 raw schedule corpus to resolve the residual corporate-action continuity blocker.

Authorized work:

- exact document semantics for the 61 residual schedule-required events;
- exact Voluntary Conversion cash/tender/buyback classification only when official document semantics and deterministic event linkage both pass;
- exact mechanical transition extraction only from explicit regular-market Ex Date or first-new-basis trading date;
- offline continuity replay under the already frozen V4 600-date / >=90% contract if document evidence is admitted.

Not authorized:

- provider/network calls or redownloads;
- alternate data sources;
- Record/Distribution Date as a mechanical transition fallback;
- price-jump inference or adjusted-price shortcuts;
- R5/R10, target ranks, model fitting, predictions, IC/performance, protected/fresh-forward outcomes;
- modification of V4-0/V4-1/V4-2/V4-3 target/evaluation/model contracts.

## Coordination note

The latest canonical `origin/main:coordination/TEAM_STATUS.md` was read before starting and no overlapping active residual-document semantics lane was present. This connector cannot safely perform a small-line edit to the very large shared TEAM_STATUS without replacing the full file; therefore local execution remains prohibited until the local operator refetches latest `main` and adds/updates this exact lane to `ACTIVE`. Branch-local implementation preparation may proceed; no external local run/provider access is authorized before that canonical update.
