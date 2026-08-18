# V4 CA Schedule Event Impact Attribution V1 — Preregistration

Status: `ACTIVE_PREEXECUTION_FROZEN`

## Parent

- scientific/result parent: `data/idx-v4-ca-blocker-attribution-v2@1ae3d8f36010a717491ad47396f73dd63bb5e864`
- exact post-KSEI continuity ledger SHA-256:
  `9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`
- exact schedule-needs SHA-256:
  `1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a`
- frozen population: `344,790` rows / `610` tickers / `600` signal dates / H5+H10.

## Motivation

Blocker Attribution V2 established two optimistic clearing dimensions:

- all 39 current schedule uncertainties resolved: 600/600 H5/H10/consensus,
  minimum consensus `0.9585987261`;
- all current coverage blockers resolved: also 600/600, but with much thinner
  minimum consensus `0.9035087719`.

The next question is therefore not whether the schedule dimension can clear the
gate. It is which schedule events actually matter to the frozen failing dates,
and how small a defensible acquisition priority set can be identified before
any new official-document retrieval.

## Frozen diagnostic semantics

1. This is an offline, outcome-blind attribution only.
2. The current `39` `SCHEDULE_REQUIRED` event identities are immutable inputs.
3. A schedule-blocked ledger row may carry one or more `blocking_event_ids`.
4. A counterfactual row becomes resolved only if **all** event IDs blocking that
   row are included in the selected subset. Partial resolution of a multi-event
   row does nothing.
5. The counterfactual is deliberately optimistic: selected schedule events are
   assumed to resolve benignly for affected rows. It does not reconstruct
   whether the eventual exact transition is inside or outside the target
   interval.
6. Therefore every selected subset is an acquisition-priority diagnostic, not
   continuity certification.
7. The following current blockers remain completely untouched:
   - `6,844` KSEI-history coverage rows;
   - `1,200` cross-source rows;
   - `240` known mechanical-crossing rows.
8. Frozen gate remains `>= 0.90` independently for H5, H10, and H5/H10
   consensus on each of the 600 signal dates.
9. Baseline must reproduce exactly `462 / 461 / 461` passing dates.
10. All-39 schedule ceiling must reproduce exactly `600 / 600 / 600`.
11. Exact reason counts must remain:
    - no crossing: `312,294`;
    - exact schedule required: `24,212`;
    - KSEI coverage unresolved: `6,844`;
    - known crossing: `240`;
    - cross-source unresolved: `1,200`.

## Event impact

For every one of the 39 events, report at least:

- ticker / source type / family / source dates;
- blocking row count;
- sole-blocking row count;
- affected signal-date count;
- affected baseline-failing-date count;
- single-event deficit reduction;
- single-event newly passing H5/H10/consensus date metrics;
- schedule rows actually released by that event alone.

Events with zero ledger blocking rows remain explicitly visible and are not
silently removed from the source evidence table.

## Critical event universe

The critical universe is the union of event IDs appearing on schedule-blocked
rows whose signal date fails at least one baseline H5/H10/consensus gate.
Events occurring only on dates that already pass at baseline cannot be needed
to repair a failing date because hypothetical event resolution is monotone.

## Gate-clearing subset search

The runner performs three levels:

1. deterministic greedy selection over the full critical universe, maximizing
   current deficit reduction, then newly passing date metrics, newly resolved
   schedule rows, blocking-row potential, with lexical ID as deterministic
   tie-break;
2. reverse deletion from that order until the subset is **inclusion-minimal**:
   removing any one remaining event makes the frozen 600-date gate fail;
3. exact exhaustive minimum-cardinality search **only** when the complete
   critical universe has at most 12 events.

If the critical universe exceeds 12, no global-minimum claim is permitted. The
reported subset must be labeled
`DETERMINISTIC_INCLUSION_MINIMAL_NOT_GLOBAL_CARDINALITY_PROVEN`.

If exact search is run over the entire critical universe and succeeds, the
runner may label the result `GLOBAL_MINIMUM_CARDINALITY_PROVEN`.

## Hard boundaries

No provider/network call, KSEI retry, official schedule acquisition,
cross-source remediation, parser or semantic change, threshold/universe
change, R5/R10, target/rank materialization, model fit, prediction,
IC/performance/bootstrap, or protected/fresh-forward outcome access is allowed.

A passing counterfactual subset does not authorize acquisition automatically;
ChatGPT review of the exact event list is required first.
