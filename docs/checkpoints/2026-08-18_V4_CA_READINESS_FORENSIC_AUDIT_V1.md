# V4 Corporate-Action Continuity + Post-CA Readiness Forensic Audit V1

Date: 2026-08-18 (Asia/Jakarta)
Status: `AUDIT_IN_PROGRESS_NO_TARGET_OR_PROVIDER_ACCESS`
Owner: `ChatGPT/V4-CA-Readiness-Forensics`

## Scope

Independent read-only/adversarial review requested by the user over the V4 corporate-action continuity lineage and the boundary from a future CA certification into the already frozen V4 target/model execution contract.

No provider execution, historical R5/R10, target rank, model fit, prediction, performance metric, bootstrap, protected-forward, or fresh-forward outcome is accessed by this audit.

## Current conclusions

### A. No decision-changing CA scientific error found so far

The latest CA semantics are aligned to the frozen target interval:

- V4 entry is official `Open_(t+1)` and terminal is `Close_(t+h)`;
- the CA base ledger independently constructs entry index `signal_index+1` and terminal index `signal_index+h`;
- an exact mechanical transition blocks iff `entry_date < transition_date <= terminal_date`;
- entry on the transition date is therefore already post-event basis and is not treated as a cross-basis interval;
- Record/Distribution dates are linkage fields only, never generic market-effective transition dates;
- no price-jump inference, adjusted-price rescue, or outcome-dependent schedule selection is admitted;
- unresolved coverage, cross-source disagreement, and unresolved schedule/effective-date state remain fail-closed.

The event-window preregistration explicitly froze the conservative rule that a relevant schedule-required event with unknown exact transition remains unresolved rather than using the ±60-day evidence-selection halo as a synthetic transition bound. This is conservative by design, not a runtime bug.

### B. Earlier Voluntary Conversion reporting defect was not a semantic defect

The forensic replay established that the parent contained 63 relevant Voluntary Conversion rows; 34 strict source-native security-to-currency rows were actually removed/reclassified non-blocking, while 29 remained schedule-required. The earlier `0 reclassified` report was an audit-count underreporting caused by the narrower remediation audit. Removed IDs exactly equal the 34 strict predicate IDs. Current lineage therefore should retain the forensic replay as the authoritative explanation.

### C. KSEI coverage remediation behaved scientifically as intended

The 43-ticker targeted remediation recovered 31 strict histories and exposed 24 additional active mechanical rows rather than blindly waiving missing coverage. This materially changed the blocker mix and is evidence that the fail-closed recovery design worked. Current accepted state remains 598/610 certified tickers, 12 unresolved tickers, MEGA/SCMA cross-source conflicts, and 240 known crossing rows before the seven-event targeted evidence run.

### D. Attribution results are diagnostics, not certification

The seven-event set `NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN` is deterministic inclusion-minimal under the frozen optimistic counterfactual attribution, not a proven global minimum. Its 600/600/600 counterfactual must not be interpreted as the expected provider result: newly exact mechanical transitions may become known crossing rows in the real continuity replay.

## Current targeted seven-event lane audit

### Pre-provider pytest import defect — fixed

The user's first local validation correctly failed before provider access because pytest imported `scripts.run_v4_ca_targeted_schedule_evidence` as a package module while that direct runner imports an existing sibling script by direct-script name. Direct `python scripts/...py` execution would expose `scripts/` on `sys.path`; pytest collection did not.

Only the focused test harness was changed to put the repository `scripts/` directory on `sys.path` before importing the direct runner. Provider/scientific code, selected identities, parser, semantics, thresholds, and pins are unchanged. Remediation commit: `4f3ecf8f5d433c8835d0581dfb0f6664c4281074`.

The user's primary checkout also contains unrelated untracked `apps/`, so it is not an admissibly clean execution worktree. Use a fresh dedicated worktree; do not delete/stash unrelated bytes as part of CA.

### Targeted acquisition semantics — current audit

NISP is narrowly bound to the exact selected event ID and source-date set `{2024-09-06}`. A static non-blocking classification requires exactly one strict KSEI registered-security row with Voluntary Conversion, Active status, parsed source ratio, left security NISP, right security in the frozen currency-token set, exact source-date overlap, and official source URL/SHA. Multiple candidates fail closed.

The six selected mechanical events use only the existing KSEI schedule semantics: exact ticker, compatible family, exact Record/Distribution overlap for event identity, explicit regular-market Ex or first-new-basis trading date, official session, KSEI reference and source SHA. Record/Distribution never becomes the transition itself.

The replay layers targeted evidence on top of accepted residual-document semantics and the accepted 598/610 KSEI remediation history, then rebuilds the entire frozen continuity state from the original base ledger. It does not mutate the latest ledger in place. Newly exact transitions can therefore become `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` rather than being automatically waived.

A specific red-team check found no prior mechanical candidate row for NISP in the accepted prior event-evidence file, so reclassifying the selected NISP static cash event non-blocking does not by itself create a new NISP cross-source conflict under the frozen represented-vs-prior rule.

## Post-CA readiness finding — real gap, not CA science failure

The frozen V4 target executor requires a continuity evidence table keyed by:

`ticker, signal_date, horizon`

with non-empty:

`continuity_status, policy_id, evidence_id, evidence_sha256`.

The CA event-window ledger currently emits:

`ticker, signal_date, horizon, entry_date, terminal_date, continuity_status, continuity_reason, blocking_event_ids, blocking_transition_dates, policy_id`

but does **not** emit the target-executor-required per-row `evidence_id` and `evidence_sha256`. There is also no authorized historical target execution runner yet; the target-execution freeze intentionally stopped at synthetic/local prefit validation while CA was pending.

Therefore a future CA verdict `CERTIFIED` is necessary but not by itself sufficient to immediately run R5/R10. Before first target access, freeze a deterministic, outcome-blind CA→target continuity-evidence adapter/orchestrator that:

1. consumes only the final accepted, hash-pinned CA continuity bundle;
2. preserves exact `(ticker, signal_date, horizon)` identities;
3. maps continuity status without semantic reinterpretation;
4. creates deterministic evidence IDs and SHA-256 provenance from the accepted CA ledger/manifest/policy bytes;
5. verifies every required row has non-empty provenance;
6. verifies H5/H10 per-date scoring population identity before consensus;
7. refuses target materialization unless the final CA summary certifies all frozen H5/H10/consensus date gates;
8. then passes the adapter output into the already frozen target executor without changing target/model/evaluation contracts.

This bridge should be frozen while still outcome-blind. It is an engineering/provenance readiness step, not a new scientific hypothesis and must not access R5/R10 while being validated.

## Additional hardening candidates before provider execution

These are currently classified as hardening, not known decision-validity defects:

1. `verify_targeted_root` cryptographically verifies the summary and the scientifically consumed `targeted_evidence.csv`, but does not currently re-hash every auxiliary declared acquisition output (linkage audit, parse audit, request records). Full-output verification would strengthen provenance even though those auxiliary files are not fed into classification.
2. The event-window per-date consensus computation correctly uses the H5/H10 resolved-ticker intersection, but should explicitly assert identical H5/H10 base decision populations per signal date before using the H5 denominator. The immutable base ledger is hash-pinned and prior runs are consistent; an explicit invariant would make this fail-closed rather than implicit.
3. A stray four-byte `docs/checkpoints/__tmp_should_not_create.md` exists in older lineage. It is repository hygiene noise only and should not be interpreted as scientific evidence.

No hardening item above authorizes post-result rescue. Any code hardening must be completed and frozen before the targeted provider result is exposed.

## Interim verdict

`CA_SCIENCE_LINEAGE_NO_DECISION_CHANGING_ERROR_FOUND_SO_FAR_TARGETED_PREPROVIDER_TEST_DEFECT_FIXED_POST_CA_PROVENANCE_BRIDGE_REQUIRED`

The current CA gate remains blocked until the exact seven-event provider acquisition and one frozen continuity replay are completed and independently reviewed. Even if that replay certifies continuity, historical V4 target/model execution remains blocked until the deterministic continuity-provenance bridge is frozen and validated outcome-blind.
