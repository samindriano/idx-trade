# V4 Corporate-Action Continuity + Post-CA Readiness Forensic Audit V1

Date: 2026-08-18 (Asia/Jakarta)
Status: `FORENSIC_AUDIT_SUBSTANTIALLY_COMPLETE_PREPROVIDER_VALIDATION_PENDING`
Owner: `ChatGPT/V4-CA-Readiness-Forensics`

## Scope

Independent read-only/adversarial review requested by the user over the V4 corporate-action continuity lineage and the boundary from a future CA certification into the already frozen V4 target/model execution contract.

No provider execution, historical R5/R10, target rank, model fit, prediction, performance metric, bootstrap, protected-forward, or fresh-forward outcome was accessed by this audit.

## Final scientific findings

### A. No decision-changing CA scientific error found

The latest CA semantics are aligned to the frozen target interval:

- V4 entry is official `Open_(t+1)` and terminal is `Close_(t+h)`;
- the CA base ledger independently constructs entry index `signal_index+1` and terminal index `signal_index+h`;
- an exact mechanical transition blocks iff `entry_date < transition_date <= terminal_date`;
- entry on the transition date is therefore already post-event basis and is not treated as a cross-basis interval;
- Record/Distribution dates are linkage fields only, never generic market-effective transition dates;
- no price-jump inference, adjusted-price rescue, or outcome-dependent schedule selection is admitted;
- unresolved coverage, cross-source disagreement, and unresolved schedule/effective-date state remain fail-closed.

The event-window preregistration explicitly froze the conservative rule that a relevant schedule-required event with unknown exact transition remains unresolved rather than using the ±60-day evidence-selection halo as a synthetic transition bound. This is conservative by design, not a runtime bug.

The original base ledger also independently used `entry_index=signal_index+1` and `terminal_index=signal_index+h`, so the later event-window test is applied to exactly the same economic interval as the frozen V4 raw return target.

### B. Earlier Voluntary Conversion reporting defect was not a semantic defect

The forensic replay established that the parent contained 63 relevant Voluntary Conversion rows; 34 strict source-native security-to-currency rows were actually removed/reclassified non-blocking, while 29 remained schedule-required. The earlier `0 reclassified` report was an audit-count underreporting caused by the narrower remediation audit. Removed IDs exactly equal the 34 strict predicate IDs. Current lineage therefore should retain the forensic replay as the authoritative explanation.

### C. KSEI coverage remediation behaved scientifically as intended

The 43-ticker targeted remediation recovered 31 strict histories and exposed 24 additional active mechanical rows rather than blindly waiving missing coverage. This materially changed the blocker mix and is evidence that the fail-closed recovery design worked. Current accepted state remains 598/610 certified tickers, 12 unresolved tickers, MEGA/SCMA cross-source conflicts, and 240 known crossing rows before the seven-event targeted evidence run.

### D. Attribution results are diagnostics, not certification

The seven-event set `NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN` is deterministic inclusion-minimal under the frozen optimistic counterfactual attribution, not a proven global minimum. Its 600/600/600 counterfactual must not be interpreted as the expected provider result: newly exact mechanical transitions may become known crossing rows in the real continuity replay.

### E. Current per-date consensus logic is scientifically correct

The current event-window evaluator computes H5 and H10 resolved ticker sets separately and uses their exact intersection for consensus observability. This corrects the weaker early gate implementation that used only the minimum of H5/H10 resolved counts. The frozen base ledger is hash-pinned and current runs show the same decision population for both horizons. An explicit H5/H10 population-equality assertion remains useful hardening but is not evidence that prior current-lineage counts were wrong.

## Current targeted seven-event lane audit

### Pre-provider pytest import defect — fixed

The user's first local validation correctly failed before provider access because pytest imported `scripts.run_v4_ca_targeted_schedule_evidence` as a package module while that direct runner imports an existing sibling script by direct-script name. Direct `python scripts/...py` execution would expose `scripts/` on `sys.path`; pytest collection did not.

Only the focused test harness was changed to put the repository `scripts/` directory on `sys.path` before importing the direct runner. Provider/scientific code, selected identities, parser, semantics, thresholds, and pins are unchanged. Remediation commit: `4f3ecf8f5d433c8835d0581dfb0f6664c4281074`.

The user's primary checkout also contains unrelated untracked `apps/`, so it is not an admissibly clean execution worktree. Use a fresh dedicated worktree; do not delete/stash unrelated bytes as part of CA.

### Targeted acquisition semantics — accepted pre-provider design

NISP is narrowly bound to the exact selected event ID and source-date set `{2024-09-06}`. A static non-blocking classification requires exactly one strict KSEI registered-security row with Voluntary Conversion, Active status, parsed source ratio, left security NISP, right security in the frozen currency-token set, exact source-date overlap, and official source URL/SHA. Multiple candidates fail closed.

The six selected mechanical events use only the existing KSEI schedule semantics: exact ticker, compatible family, exact Record/Distribution overlap for event identity, explicit regular-market Ex or first-new-basis trading date, official session, KSEI reference and source SHA. Record/Distribution never becomes the transition itself.

The replay layers targeted evidence on top of accepted residual-document semantics and the accepted 598/610 KSEI remediation history, then rebuilds the entire frozen continuity state from the original base ledger. It does not mutate the latest ledger in place. Newly exact transitions can therefore become `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` rather than being automatically waived.

A specific red-team check found no prior mechanical candidate row for NISP in the accepted prior event-evidence file, so reclassifying the selected NISP static cash event non-blocking does not by itself create a new NISP cross-source conflict under the frozen represented-vs-prior rule.

No provider/scientific defect was found in the current seven-event acquisition/replay logic after the pytest harness remediation. Local focused validation must still pass in a clean worktree before the one authorized provider run.

## Post-CA readiness findings — real engineering gaps, not CA science failures

### 1. CA continuity provenance adapter was missing

The frozen V4 target executor requires a continuity evidence table keyed by:

`ticker, signal_date, horizon`

with non-empty:

`continuity_status, policy_id, evidence_id, evidence_sha256`.

The CA event-window ledger emits the scientific/audit state and `policy_id`, but not the target-executor-required per-row `evidence_id` and `evidence_sha256`.

A separate outcome-blind bridge has therefore been prepared on:

`integration/idx-v4-ca-target-continuity-bridge-v1`

It requires an externally supplied exact accepted final CA manifest SHA, refuses a non-certified bundle, verifies the final ledger identity and all 600 H5/H10/consensus date gates, requires identical H5/H10 per-date base populations, and deterministically derives row-level provenance hashes before delegating to the already frozen target-side continuity validator. It has not been run on historical CA output and does not access targets/outcomes.

### 2. Row-level target price evidence was missing

The frozen target executor also requires:

`ticker, date, market_state, accepted_open, open_admitted, close, close_admitted`.

The accepted target-support census already computes the same source/state ingredients and proves technical support feasibility, but only emits aggregate/session support artifacts; it does not emit a row-level table directly consumable by the target executor.

A synthetic-only row-level price evidence builder has therefore also been prepared on the same bridge branch. It preserves the target-support census market-state precedence, requires exact derivative-panel identity, uses positive accepted derivative Open first, admits the accepted CA-scale overlay only on still-missing derivative rows, re-attests overlay canonical H/L/C identity and recovered-Open bounds, keeps canonical raw Close, and delegates its final schema validation to the frozen target-side `prepare_price_evidence` function.

This builder is code-preparation only. Historical price-evidence materialization remains forbidden until CA continuity is independently certified and accepted.

### 3. Historical orchestration remains intentionally unauthorized

The target-execution protocol explicitly remains `SYNTHETIC_ONLY_CA_CONTINUITY_LEDGER_PENDING` and sets historical target/model/performance authorization false. No historical runner should be activated merely because bridge code exists. After CA certification, the final CA manifest SHA and bridge code/tests must be independently reviewed/frozen first; only then may a separate execution authorization materialize R5/R10.

## Additional hardening notes

These are hardening opportunities, not known decision-validity defects:

1. `verify_targeted_root` verifies the summary and scientifically consumed `targeted_evidence.csv`; re-hashing every auxiliary declared acquisition output would strengthen full forensic provenance but does not alter the classification input.
2. The event-window per-date consensus computation already uses exact resolved-set intersection. Adding an explicit H5/H10 base-population equality assertion would make a currently implicit invariant fail-closed.
3. The old target-support census marks the accepted CA-scale overlay by membership because that overlay was independently hash-pinned and verified as exactly 2,184 valid rows. The new prepared price-evidence bridge re-attests the actual `recovered_open` and canonical H/L/C before any eventual target-side use.
4. A stray four-byte `docs/checkpoints/__tmp_should_not_create.md` exists in older lineage. It is repository hygiene noise only and is not scientific evidence.

No hardening item authorizes post-result rescue. Any code that changes the provider/replay classification path must be frozen before targeted evidence result exposure.

## Forensic verdict

`V4_CA_SCIENCE_LINEAGE_NO_DECISION_CHANGING_ERROR_FOUND_TARGETED_PREPROVIDER_TEST_DEFECT_FIXED_POST_CA_EXECUTION_BRIDGES_PREPARED_SYNTHETIC_ONLY`

Current CA status remains blocked until the exact seven-event provider acquisition and one frozen continuity replay complete and are independently reviewed. The audit does not claim that the seven events will certify the gate.

If the targeted replay later certifies continuity, the next sequence is:

1. independently review and pin the exact final CA manifest/ledger hashes;
2. validate the prepared continuity-provenance and row-level price-evidence bridges with synthetic/frozen-input tests only;
3. issue a separate historical target-execution authorization;
4. materialize the locked R5/R10 and rank ledger once;
5. execute the frozen Control vs Geometry3 six-by-100 historical-development evaluation without rescue/tuning.
