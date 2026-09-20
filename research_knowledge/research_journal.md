# Durable Research Journal

This journal is a compact batch log. Detailed evidence remains in the linked
checkpoint files; this file records why the next question changed.

## 2026-09-19 — structural and mechanism batch

- Reconstructed prior alpha/failure history and froze the outcome-blind C1–C4
  budget.
- Rejected the first Stage-A implementation as an engineering defect, then
  built the corrected causal/session/key implementation.
- Measured C1–C4 structural support, turnover, concentration, robustness,
  internal dependence, and proxy economics.
- Explored H-LIQ-01, H-VOL-01, H-EXC-01, and H-EXC-02 without adding C5.
- Closed monotone transforms and unsafe/raw representations as no-retry or
  future-only directions.

## 2026-09-19 late — red-team and source-capability batch

- Red-teamed CA/price basis, capacity tails, H-LIQ decomposition/persistence,
  source semantics, and packet freshness.
- Audited Dataset-Saham-IDX, Open capability, foreign-flow, lifecycle,
  ownership/free-float, market context, and panel-depth surfaces.
- Conclusion: source availability is not the same as PIT or admission authority.

## 2026-09-20 — forensic closure and tooling batch

- Audited BBCA basis/event linkage, HSC, broker/margin, LBRE, statutory
  free-float, and local-surface closure.
- Formalized the CA/issuer/basis admission contract.
- Independently replayed C1/C2/C4 constructor: 981940 keys with zero
  eligibility/score/rank mismatches.
- Formalized the eligibility contradiction and fail-closed guard.
- Hardened packet/firewall/lane controls and produced the ChatGPT audit handoff.

## 2026-09-20 — durable knowledge batch

- Added this compact machine-readable and human-readable memory layer.
- No experiment was rerun and no protected data was accessed.
- The next high-information question is eligibility provenance; if authority
  remains missing, classify `POLICY_AUTHORITY_MISSING` and move to tooling,
  common-support, and historical reinterpretation surfaces.

## Eligibility provenance addendum

- The protocol gives 60 the meaning of trailing official-session lookback and
  20 the meaning of minimum finite observations; the median threshold is part of
  the liquidity rule.
- Both Stage-A versions inherit generic `min_periods=window` behavior, so the
  current implementation requires a complete 60-value rolling window and makes
  the later `>=20` test redundant for those rows.
- Candidate feature windows also use 60/20, while `security_master` exposes a
  separate generic warm-up path. No evidence supports an incumbent-specific
  origin, and Data-QA is a separate blocked gate.
- Classification remains `POLICY_AUTHORITY_MISSING`; no population was chosen.

## 2026-09-20 — eligibility counterfactual clarification

- Replayed the two unresolved policy interpretations outcome-blind on the
  hash-bound panel, financial bundle, official sessions, and tradability
  anchors.
- Minimum-20 produces 348,765 eligible rows versus 310,761 under minimum-60;
  the mask difference is 38,004 rows across 619 tickers.
- Common-finite rank changes are material for C1/C3/C4 (73.1086%/96.6122%/
  99.5192%) but zero for C2 because C2's feature rolling warm-up remains 60.
- This strengthens the conclusion that security eligibility and feature
  availability have been conflated in the current implementation. It does not
  establish policy authority or authorize regeneration.
- The first turnover comparison used all official dates and was superseded by
  an explicit previous-official-session calculation over the frozen 600-session
  scope; the corrected minimum-60 values align with the official structural
  scope to rounding.

## 2026-09-20 — tooling mutation and authority-packet audit

- A synthetic audit exercised corrupt hashes, missing bindings, changed code,
  network imports, obvious protected markers, C5 injection, policy selection,
  and re-entry opening. All expected failures failed closed; safe baselines
  passed.
- The audit found that the hybrid firewall is not a semantic allowlist:
  disguised field names and unexpected non-matching schema columns can pass.
- A newly surfaced data-authority packet initially passed despite five missing
  evidence refs. The verifier was corrected to require relative refs and
  counterfactual refs to exist; a dedicated missing-reference test now fails
  closed.
- The authority packet remains `BLOCKED_PRE_ADMISSION`; it is a reusable
  bounded map, not permission to open outcomes or re-enter predictive work.
- The lane verifier then exposed a separate process-scope false negative:
  legitimate `tests/` files were outside its allowlist. Adding only `tests/`
  keeps the lane narrow and removes that false failure; it does not strengthen
  runtime-access claims.

## 2026-09-20 — bounded historical archaeology closure

- Ran `ARCHAEOLOGY-037` over the current archaeology/failure/tombstone/lineage
  documents and six retained Git refs using metadata/tree names only.
- Confirmed the family-level map is supported, while exact source-level replay
  remains partial for V4-E/F/G and protected/auxiliary families.
- Counted protected-looking historical paths without reading them; no historical
  target/outcome payload was opened.
- Latest PIT/integrity adjudication remains authoritative over earlier promotion
  headlines, especially V3-B Structure-Lite.
- Classified the safe metadata-only archaeology lane as bounded exhausted and
  moved the frontier to the next non-redundant question.

## 2026-09-20 — semantic tooling challenger

- Ran `TOOLING-038` using temporary outcome-blind text, Parquet, and packet
  mutations.
- Confirmed false greens for disguised semantic text/schema fields and unknown
  nested packet fields; unknown top-level packet fields still fail closed.
- Confirmed that canonical JSON is deterministic only when explicit sorted
  serialization is applied, and that the packet audit lacks an expected
  verifier-version hash pin.
- Kept the protected boundary closed and classified current PASS states as
  scoped hash/path/denylist evidence only; no firewall production behavior was
  changed.

## 2026-09-20 — eligibility provenance history audit

- Audited retained pre-protocol Git refs for the origin of the minimum-20 and
  min-periods-60 rules without regenerating the panel or opening outcomes.
- Confirmed a legacy primary-liquidity contract with a 60 official-session
  lookback and at least 20 finite ACTIVE observations; this predates the
  2026-09-19 protocol and is not merely new protocol wording.
- Confirmed Stage-A V1/V2 complete-window rolling behavior and that V2's later
  `>=20` check is redundant under `min_periods=window`; generic security-master
  60-session IPO warm-up is a separate concept.
- Narrowed the blocker from unknown provenance to missing current authority
  binding. No population was selected, no candidate was regenerated, and the
  safe status remains `POLICY_AUTHORITY_MISSING`.

## 2026-09-20 — independent formula mutation challenger

- Built a temporary 3-ticker, 150-session fixture and an independently written
  reference for C1/C2/C4 plus average-tie ranks.
- Baseline replay passed on all 450 keys. Five declared mutations were then
  detected: C1 denominator, C1 market timing, C2 log transform, C4 sign, and
  eligibility mask.
- A first 72-session fixture was rejected because C1 had no finite support;
  the accepted run uses 150 sessions. This is harness-quality evidence only.
- Classified `TOOLING-040` as `SUPPORTED_SCOPED`; no formula, verifier, or
  production behavior was changed.

## 2026-09-20 — nested packet schema challenger

- Built a research-only draft exact nested-key allowlist for the current
  authority packet and compared it with the existing verifier.
- Baseline passed both layers. The strict draft rejected five declared nested
  or missing-field mutations; the current verifier accepted four of those and
  rejected the unknown top-level field.
- Corrected an initial over-strict draft that confused candidate-specific
  required fields and H-EXC scalar subforms before accepting the result.
- Classified `TOOLING-041` as `SUPPORTED_SCOPED`; no production verifier or
  packet behavior was changed.

## 2026-09-20 — verifier freshness challenger

- Tested a draft versioned-result contract requiring schema, current verifier
  SHA-256, and current packet SHA-256.
- Baseline passed; missing/stale verifier hash, stale packet hash, and stale
  result schema all failed the draft contract while the unchanged packet still
  validated PASS.
- This separates packet validity from freshness of a historical verifier
  result. Classified `TOOLING-042` as `SUPPORTED_SCOPED`; no production
  verifier behavior changed.

## 2026-09-20 — program completion audit

- Audited the objective requirement-by-requirement against current registries,
  verifiers, tests, lane state, and frontier.
- Classified the available local outcome-blind surface as substantially
  exhausted: remaining material decisions require unavailable authority/data or
  independent review; repeated local work would mostly duplicate evidence.
- Kept predictive evidence unopened, candidate statuses unchanged, and all
  incumbent/canonical/cloud/capture/telemetry/production boundaries untouched.

## 2026-09-20 — candidate-specific era authority map

- Mapped C1-C4 formula inputs to candidate-specific authority gates and
  stratified the frozen structural artifact by natural calendar year.
- C1/C2/C4 have broad finite support from 2022 onward; C3 has no finite rows
  through 2024 and begins on 2025-04-25, with partial support through
  2026-07-17.
- Every observed panel key is an ACTIVE anchor and none is NO_TRADE, but 458
  ACTIVE anchor rows are absent from the panel in 2021-2024. This narrows the
  structural boundary without proving population completeness.
- No era, candidate, or policy was selected. The map is SUPPORTED_SCOPED;
  remaining authority requires owner policy plus population/identity/CA and,
  for C3, publication/revision/provenance contracts.

## 2026-09-20 — eligibility delta by era

- Decomposed the minimum-20 versus minimum-60 mask difference by natural
  calendar year using the frozen panel, official sessions, and ACTIVE anchors.
- The difference occurs in every year: 11,623 new rows in 2021; 4,257 in
  2022; 4,577 in 2023; 4,669 in 2024; 7,741 in 2025; and 5,137 in 2026.
- This disproves the narrower hypothesis that the ambiguity is only an early
  warm-up artifact. It remains a policy-sensitive upstream population choice
  in the latest observed years, without establishing which rule is authoritative.
- No policy, era, or candidate subset was selected; the protected boundary
  remains closed.

## 2026-09-20 — calendar-year Top-30 mechanics

- Added fixed Top-30 turnover, selection persistence, slot concentration,
  one-session rank displacement, and between-year selected-ticker overlap by
  natural calendar year.
- C1/C2/C4 show mild 2026 partial-year turnover increases versus 2022; C3
  has no usable Top-30 date before 2025 and its long persistence/high HHI are
  support-sensitive; current evidence does not establish sparse support as the
  cause of its turnover/persistence pattern.
- Corrected the initial output contract so between-year Jaccard is `null` and
  marked non-comparable when either year has no selection support.
- No era, policy, candidate status, or outcome was selected or accessed.

## 2026-09-20 — score-separation mechanics

- Added a fixed Top-30 rank-30/rank-31 score-boundary diagnostic to separate
  score geometry from turnover. It records same-day-IQR-normalized boundary
  gaps, top-1-to-cutoff gaps, exact ties, unique-score fraction, and same-year
  next-session turnover associations.
- C2 has the widest normalized boundary gap (median 0.05912) and lower mean
  next turnover (32.62%) than C1 (0.01089; 41.74%) and C4 (0.00936; 23.26%).
  C3 has 10.18% exact boundary ties and only 275 usable dates, so its lower
  turnover remains support-sensitive.
- Corrected the first execution to exclude December-to-January pairs from
  year-stratified next-session comparisons; only the corrected rerun was
  retained. No candidate, policy, era, or outcome was selected.

## 2026-09-20 — formula-component anatomy

- Reconstructed the official-session market-side components for C1/C2/C4 and
  checked them against the stored guarded scores. All finite values matched
  exactly: C1 295243, C2 310761, C4 310323, maximum absolute difference 0.0.
- C1 and C4 rank geometry is dominated by their reversal numerators, with
  median daily score/component Spearman -0.9599 and -0.9519. C2 is an
  interaction: ret_5 median association 0.2681 and abnormal-turnover log
  -0.0045, while its Top-30 names are elevated on both components.
- This strengthens the shared-reversal caution without proving predictive
  redundancy. No C5, policy, era, candidate promotion, or protected outcome
  was introduced.

## 2026-09-20 — C2 interaction quadrants

- Decomposed fixed C2 Top-30 slots into the four sign quadrants of `ret_5` and
  log abnormal turnover. Pooled selection is 68.68% positive-return/high-
  activity and 31.32% negative-return/low-activity; cross-sign quadrants get
  zero slots because their product is negative.
- The mixture shifts from 78.80%/21.20% in 2025 to 59.90%/40.10% in 2026
  partial year. This is a descriptive composition shift, not a regime-return
  claim and not a reason to create a new candidate.

## 2026-09-20 — C1/C4 numerator-overlap decomposition

- Compared stored C1/C4 Top-30 selections with numerator-only reversal proxies,
  then compared stored-score cross-candidate overlap with numerator-only
  cross-candidate overlap.
- Within-candidate mean overlap is 63.75% for C1 and 62.22% for C4. Across
  candidates it is 35.80% for stored scores versus 36.82% for numerator-only
  proxies. Normalizers therefore matter, but they do not materially explain
  the shared C1/C4 overlap.
- This strengthens the structural shared-reversal caution without proving
  predictive redundancy, orthogonality failure, capacity, or candidate
  promotion. Protected outcomes remain closed.

## 2026-09-20 — universe breadth versus turnover

- Tested whether adjacent-session finite-support breadth explains fixed Top-30
  turnover, using same-calendar-year official-session pairs only.
- C1/C2/C4 finite support averages 99.54%/100.00%/99.85% of eligible rows;
  count-versus-turnover Spearman is only 0.133/0.061/0.175. Absolute count
  change is similarly weak, so there is no strong common breadth explanation
  for their churn.
- C3 finite support averages 35.96% of eligible rows; count-versus-turnover
  rho is -0.372 overall and -0.711 in 2026 partial year, while absolute
  count-change rho is 0.439 in 2026. This strengthens the existing conclusion
  that C3's low turnover and persistence are support-sensitive.
- The result is structural/correlational only. No candidate, policy, era, or
  protected outcome was selected or accessed.

## 2026-09-20 — eligibility versus feature warm-up

- Decomposed finite candidate support by the current
  `eligible_decision_universe` mask. Every finite C1/C2/C3/C4 score is inside
  the mask; there are no finite scores outside eligibility.
- Eligible-row missingness is C1 `15518`, C2 `0`, C3 `279767`, and C4 `438`.
  This separates security eligibility from candidate feature warm-up/source
  availability and shows that C3 sparsity is within eligible rows on the
  observed artifact.
- This is an implementation/data-surface distinction only. It does not bind
  the eligibility policy, historical population completeness, PIT/report
  availability, identity, CA basis, or predictive validity.

## 2026-09-20 — independent red-team adjudication

- Confirmed the CNTX population boundary: 458 ACTIVE anchor rows from
  2021-04-29 through 2024-08-01 are absent from the 981,940-row panel, and
  the replay seeds its ticker universe from panel tickers. Zero key mismatch
  therefore proves observed-panel replay reproducibility only, not historical
  population completeness or survivorship safety.
- Reproduced five stale current-tree registry-reference occurrences and
  repaired them to existing canonical artifacts; the strengthened verifier
  surfaced one additional stale occurrence and repaired it too. Six unique
  unavailable historical commit-qualified refs are now explicitly
  ledger-classified as unavailable; the knowledge verifier fails closed on
  unclassified reference rot.
- Independent C3 support/turnover association is approximately Spearman
  `-0.3545581106` over 271 usable same-year pairs. C3 is support-sensitive,
  but sparse support is not established as the cause of turnover/persistence.
- Reclassified C2 quadrant shares as formula component/anatomy evidence rather
  than independent mechanism confirmation because the sign behavior is largely
  implied by `ret_5 * log(abnormal turnover)` ordering.
- Added and passed a full eligible-mask stored/recomputed finiteness assertion:
  C1/C2/C4 mismatch counts are `0/0/0`. These remain implementation checks,
  not PIT, population, or predictive admission.

## 2026-09-20 — panel versus anchor state census

- Compared the panel with every regular ACTIVE/NO_TRADE anchor key. The anchor
  has `982398` ACTIVE and `121666` NO_TRADE rows; the panel overlaps all
  `981940` ACTIVE keys and zero NO_TRADE keys.
- `CNTX` is the only ACTIVE ticker absent from the panel, while `34` anchor
  tickers are NO_TRADE-only. This clarifies that the panel is an active-trade
  subset of the observed anchor surface, not proof of a complete historical
  universe or survivorship safety.

## 2026-09-20 — public EOD/IPO source coverage

- Acquired three public GitHub source families into the isolated staging root:
  two pinned EOD ticker-file snapshots and one IPO-only JSON snapshot. Also
  inspected a pinned IDX-API wrapper for official issuer, delisting,
  new-listing, and relisting route names.
- Both EOD snapshots contain CNTX. The newer snapshot has 983 files and
  1,289,820 rows through 2026-05-29; the older explicit all-ticker folder has
  958 files and 1,078,040 rows through 2025-02-21.
- The newer snapshot covers 1,060,071/1,062,767 anchor keys and
  943,283/945,693 panel keys through its own date cutoff. Its six missing
  ticker files exactly match the IPO dataset's declared new-stock list
  (BACH, EMMI, JECX, JELI, PRDL, RANS), giving bounded evidence for a
  snapshot-timing/new-issue explanation.
- This changes the CNTX conclusion from “panel-absent” to
  “panel-absent but discoverable in independent public EOD snapshots.” It does
  not change the population/PIT/survivorship blocker: neither snapshot has
  row-level public-availability/revision semantics, issuer/ISIN continuity,
  complete historical membership, or CA-effective-basis authority.
- Ordinary curl access to the official IDX host received a Cloudflare 403
  challenge. No authenticated/provider call, bypass, canonical write, or
  protected-outcome access occurred. Do not retry the same snapshot family;
  reopen only for a new official event archive or authoritative PIT/lifecycle
  contract.

## 2026-09-20 — anchor state-transition semantics

- Ordered `ACTIVE`/`NO_TRADE` states by ticker across the 1,260-session anchor
  surface. `583/980` tickers switch state; the median changed-ticker count is
  `10`, the 95th percentile is `212.9`, and the maximum is `374` transitions.
- The sequence is state geometry, not lifecycle proof. No transition was mapped
  to suspension, delisting, relisting, ticker reuse, issuer change, or a clean
  interval without state and identity authority.

## 2026-09-20 — eligibility policy versus Top-30 membership

- Added a direct cross-policy selection-set comparison for the minimum-20 and
  min-periods-60 counterfactual branches. Both branches were reconstructed from
  the frozen panel, financial capability bundle, official sessions, and regular
  ACTIVE anchors; no policy was selected.
- Mean cross-policy Top-30 overlap is C1 `96.52%`, C2 `100.00%`, C3 `94.05%`
  over 278 common selection dates, and C4 `91.71%` over 1201 dates. Exact
  daily matches are C1 `32.52%`, C2 `100%`, C3 `22.30%`, and C4 `12.74%`.
- The policy fork therefore changes actual decision sets for C1/C3/C4, not only
  row counts or rank denominators. C2's exact invariance is consistent with its
  independent 60-session feature warm-up. This strengthens the policy blocker;
  it does not establish policy correctness, predictive robustness, capacity, or
  candidate admission.

## 2026-09-20 — C1/C4 horizon bridge

- Reconstructed raw `-ret_5`, C1 residual numerator, stored C1, raw `-ret_20`,
  and stored C4 representations on the frozen structural surface.
- Raw 5-session versus raw 20-session Top-30 overlap is `37.96%`, close to
  residual-numerator versus raw C4 `36.82%` and stored C1 versus stored C4
  `35.80%`. This does not support a single horizon-only explanation for shared
  C1/C4 membership.
- C1 raw versus residual-numerator overlap is `84.55%`; stored C1 versus
  residual numerator is `63.75%`; stored C4 versus raw 20-session reversal is
  `62.22%`. Beta residualization changes the short-horizon representation, but
  the C1/C4 normalizers materially shape final Top-30 membership.
- The result is structural formula anatomy only. No predictive redundancy,
  orthogonality, capacity, candidate, policy, or outcome claim follows.

## 2026-09-20 — official IDX current-directory cross-check

- Retained an ordinary public GET to IDX `GetCompanyProfiles` in isolated
  staging. The response is HTTP 200 with 962 rows and 962 unique current
  codes; all status values are zero and listing dates range from 1977-08-10 to
  2026-07-10.
- The dedicated verifier passed 9/9 checks. The new response exactly matches
  the prior official current snapshot by code and listing date, and official
  current codes are a strict subset of the 980-code anchor surface. The 18
  anchor-only codes include CNTX.
- The six official current codes absent from the newer Pholenk EOD snapshot
  have official listing dates 2026-07-07 through 2026-07-10. This strengthens
  the bounded snapshot-timing/new-issue explanation already supported by the
  IPO snapshot, but does not establish row-level availability time.
- The existing 440-month official lifecycle archive remains event-level and
  identity/PIT blocked. The current directory was not used to reinterpret its
  conflicts or to repair any historical state.
