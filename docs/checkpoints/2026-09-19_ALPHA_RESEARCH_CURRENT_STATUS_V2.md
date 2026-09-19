# IDX-Trade Alpha Research — Current Status V2

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
Status: `PRE-ADMISSION RESEARCH ACTIVE / HISTORICAL TARGET STAGE BLOCKED`

This is the concise durable read-in for a future ChatGPT session. It
supersedes the conversational summary, but detailed evidence remains in the
linked checkpoint documents and staged JSON artifacts.

The newest consolidated read-in, including the three completed Phase-Q
read-only red-team reports, is
`2026-09-19_ALPHA_RESEARCH_LATEST_READIN_V1.md`. Read it together with this
status file before continuing.

The compact cross-session handoff is
`2026-09-19_ALPHA_RESEARCH_CHATGPT_HANDOFF_V3.md`.

The follow-up tooling/selection replay is recorded in
`2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`.
The latest independent red-team correction replay is recorded in
`2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`.

## Latest continuation update — local Zapi probe admission audit

The already persisted local Zapi artifacts were inspected read-only. They
contain one BBCA company-profile snapshot and empty March/August dividend
payloads; the profile fails its official parity review, and the dividend
reviews fail row-selection/identity/semantic gates. No historical
available-at, revision/vintage, issuer/ISIN, or corporate-action authority is
established. Zapi remains `BLOCKED / NOT_ADMITTED` and does not create a new
alpha surface or alter the C1-C4 packet. See
`2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md`.

## Latest continuation update — ownership/KSEI source quality audit

The persisted KSEI archive was audited read-only and independently verified.
Eight annual/monthly snapshots contain 803–1,007 equity rows each, have no
duplicate equity codes or arithmetic failures, and overlap 100% of panel
tickers on their exact dates. They cover only `8/1,260` panel dates, however;
retrieval time is not row-level publication time, and no revision, issuer/ISIN,
or effective-free-float contract is established. The five company-profile
probes add no explicit free-float field. H-FLOW-01 remains
`FUTURE_SPECIFICATION / SOURCE_PARTIAL / NOT_ADMITTED`; no feature or C5 was
created. See `2026-09-19_ALPHA_OWNERSHIP_KSEI_SOURCE_AUDIT_RESULT_V1.md`.

## Latest continuation update — CA basis, capacity tails, and mechanism closure

An independent CA/issuer-basis red-team confirms that the HLC overlay is
bounded forensic evidence, not a global price-basis certificate: it covers
`1,657/981,940` panel rows, the `188` residual keys are disjoint, and the
security master lacks issuer/ISIN transition authority. C1 is materially
sensitive under the registered basis stress; C2/C4/H-LIQ/H-VOL/H-EXC-02 remain
unresolved. See `2026-09-19_ALPHA_CA_ISSUER_BASIS_REDTEAM_RESULT_V1.md`.

A new outcome-blind capacity/friction-tail artifact over the fixed 600-session
window and six surfaces adds q95/q99/max turnover burden, HHI/effective names,
and separate market-value/raw-volume/dollar-turnover quartile exposure. It
passes independent verification and strengthens economic caution, but real
capacity remains blocked. See
`2026-09-19_ALPHA_CAPACITY_FRICTION_TAIL_RESULT_V1.md`.

The bounded new-mechanism review found no defensible new candidate from the
currently admitted OHLCV/value surface. Effort-vs-result, breakout/rejection,
and cross-sectional-disagreement directions are covered, redundant, or
source-blocked. H-LIQ/H-VOL/H-EXC-02 remain future research only. See
`2026-09-19_ALPHA_NEW_MECHANISM_SURFACE_ADJUDICATION_V1.md`.

## Latest continuation update — C3 and packet provenance red-team

The C3 red-team found that the existing capability map should distinguish two
denominators: full eligible panel (`310,761`) versus matched eligible
financial-source rows (`249,333`). Correct matched-source rates are `25.8313%`
for quality-core (`64,406` rows) and `12.4308%` for all-five (`30,994` rows).
Quality-core remains a structural capability island without a frozen candidate
contract, and C3 remains blocked. See
`2026-09-19_C3_CAPABILITY_DENOMINATOR_REDTEAM_ERRATUM_V1.md`.

Packet provenance is now more precise: producer binding `10939862...` is
verified and byte-consistent for Stage-A code/protocol, but packet/contract
were introduced later. Packet attestation is stale and full freshness remains
unknown; future updates must bind producer commit `P` and attest packet commit
`Q` separately. See
`2026-09-19_ALPHA_REENTRY_PACKET_PRODUCER_BINDING_RECONCILIATION_RESULT_V1.md`.

Dataset-Saham-IDX remains `BLOCKED / NOT_ADMITTED`; the independent provenance
red-team found no row-level timing/vintage evidence that changes this.

## Latest continuation update — available-data frontier audits

The isolated lane completed four additional source-capability audits without
opening targets or touching incumbent/canonical/capture/cloud state:

- FILINGAGE-01: `70,931` reporting-age rows are arithmetically coherent, but
  coverage begins in 2024 and public-availability, revision/vintage, and
  identity authority are unresolved. `SOURCE_PARTIAL_STRUCTURAL_SIGNAL /
  NOT_ADMITTED`.
- EXECSTATE-01: `1,104,064` official execution-state rows over `1,260`
  sessions reconcile exactly to cache/session reports. `NO_TRADE` is not
  admitted as suspension, illiquidity, or executable capacity.
- SUSPSTATE-01: only `1,168` regular interval rows overlap no-trade;
  `120,498/121,666` unique no-trade keys are outside the sparse intervals and
  `471` duplicate interval-key groups prohibit silent deduplication.
- CA residual: unresolved scale rows overlap the retained HLC overlay `0/188`;
  issuer/ISIN and event semantics remain unknown.
- SECTOR-01: `22` structured 2022/2023 sheets contain `1,607` current rows
  plus `14` exit rows and `837` current ticker codes. PDF-only gaps,
  `GWSA/KOTA` cross-sheet duplicates, and absent daily/PIT/identity/vintage
  authority keep the surface `NOT_ADMITTED`.

These results improve the capability map and negative-evidence record but do
not create a candidate or change the protected C1-C4 packet. The next useful
work requires a genuinely new independent source-contract surface; provider
fallback, target access, and imputation remain disallowed.

A bounded literature-to-mechanism review likewise found no justified new raw
reversal/liquidity candidate: those mechanisms overlap the existing C1/C2/
H-LIQ-01 work. Industry-adjusted reversal is retained as a future
specification only, pending daily PIT sector membership and identity/revision
authority. See `2026-09-19_ALPHA_LITERATURE_MECHANISM_CARD_REVERSAL_LIQUIDITY_V1.md`.

The H-LIQ temporal persistence red-team passes coverage/mask integrity across
six 100-session blocks, but Q4 H-LIQ/C2 dependence ranges `0.0762–0.3053` and
selected bottom-value Q1 share ranges `29.47%–51.30%`. This fails an
unqualified persistence claim and leaves H-LIQ `FUTURE_RESEARCH /
NOVELTY_PENDING / ECONOMIC_CAUTION`, with no C5 or packet change. See
`2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`.

The re-entry packet freshness audit confirms C1-C4 indexing and C3 fail-closed
behavior, but the frozen contract manifest head differs from the current lane
head. Freshness is `UNKNOWN`; the V2 packet remains specification-only and
must not execute. Stale V1 references were repaired or labeled historical. See
`2026-09-19_ALPHA_REENTRY_PACKET_FRESHNESS_AUDIT_RESULT_V1.md`.
Stage-A generation lineage is recorded in
`2026-09-19_ALPHA_STAGE_A_LINEAGE_RESULT_V1.md`.
Downstream hash binding is recorded in
`2026-09-19_ALPHA_STAGE_A_CONSUMER_AUDIT_V1.md`.

## Executive answer

The program is **not blocked everywhere**. A large amount of legal,
outcome-blind research is complete, and the latest adversarial audit added
evidence for C1/C2/C4. The only hard stop is the protected historical
predictive stage: authoritative Data QA has not admitted a population-complete,
historical-as-of target contract.

Therefore:

- C1, C2, and C4 are structurally credible enough for future evaluation, but
  none has predictive evidence.
- C3 is blocked by sparse financial/PIT capability, not proven to be a bad
  economic mechanism.
- H-LIQ-01 remains a future hypothesis, not a new candidate ID.
- No current alpha survivor or superiority claim is valid.
- The lane remains isolated; incumbent, canonical data, capture/cloud,
  scheduler, counters, production artifacts, and protected outcomes were not
  modified or opened.

Important verifier nuance: the C1/C2/C4 adversarial v2 replay passes its
independent artifact/structural checks, but it does not independently rebuild
the feature constructor or eligibility masks; its full-construction scope is
`UNKNOWN`. Structural-lab has a separate independent source-recomputing v2
replay with `mismatch_count=0`; the old envelope-only verifier remains
historical tooling and is not the authoritative replay result. See
`2026-09-19_ALPHA_C1234_REDTEAM_SCOPE_ADJUDICATION_RESULT_V1.md`.

## Absolute scientific boundary

Until an independently reviewed Data QA admission artifact exists, do not:

- open H5/H10, forward returns, protected labels, or target-derived incumbent
  predictions;
- calculate IC, ICIR, OOS performance, target-ranked spreads, or candidate vs
  incumbent predictive comparisons;
- tune, rescue, refit, sign-flip, optimize weights, claim superiority, claim
  `RESEARCH_SURVIVOR`, or promote a model;
- reconstruct protected labels through a proxy.

This is a target-admission block, not a total research block.

## Current candidate snapshot

The corrected decision universe is 310,761 eligible rows across 711 tickers.
All figures below are structural/capability observations only.

| ID | Mechanism | Finite eligible support | Top-30 turnover | Base burden | Status |
|---|---|---:|---:|---:|---|
| C1 | 5-session residual reversal | 295,243 / 95.0065% | 42.15% | 25.29 bps/NAV | `FUTURE_RESEARCH` |
| C2 | 5-session participation confirmation | 310,761 / 100.0000% | 32.91% | 19.75 bps/NAV | `FUTURE_RESEARCH` |
| C3 | financial quality/growth | 30,994 / 9.9736%; 278 usable Top-30 dates | 10.93% | 6.56 bps/NAV | `BLOCKED` |
| C4 | 20-session path-efficiency reversal | 310,323 / 99.8591% | 23.70% | 14.22 bps/NAV | `FUTURE_RESEARCH` |

The base burden uses the frozen structural assumption of 15 bps buy fee,
25 bps sell fee, and 10 bps slippage per side. It is not realized P&L.

## What has been completed

1. **Prior-work archaeology and failure taxonomy**: V2/V3/V4 families,
   financial, participation, price-path, foreign-flow, ownership/free-float,
   suspension/resumption, and auxiliary work were reconstructed. Failed
   representations were kept separate from mechanisms that remain untested.
2. **Data/PIT inventory**: the clean OHLCV panel, official sessions,
   tradability anchors, financial bundle, metadata-only activity snapshot, and
   blocked/partial source surfaces were classified. No new source was admitted
   merely because it exists locally.
3. **Corrected C1-C4 construction**: causal feature code, eligibility mask,
   official-session closure, ranks, schema, hashes, and independent firewall
   checks were completed.
4. **Structural deepening**: coverage, temporal support, turnover, persistence,
   rank churn, liquidity/value exposure, concentration, horizon sensitivity,
   normalization equivalence, missingness stress, and universe stress were
   measured.
5. **Orthogonality**: structural Spearman diagnostics show the main duplicate
   caution is C1/C4 (`+0.4113` daily pooled diagnostic); low correlation is not
   predictive orthogonality.
6. **C3 capability decomposition**: quality-core capability is broader
   (64,406 rows / 505 dates with at least 30 names), but any YoY/all-five
   contract remains sparse (30,994 rows / 278 usable Top-30 dates). No
   arbitrary C3 subset was promoted.
7. **H-LIQ-01**: one fixed temporal-liquidity hypothesis was structurally
   studied and red-teamed. It remains
   `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`, with no C5 ID.
8. **Combination/economics**: C1+C2, C1+C4, C2+C4, and C1+C2+C4 were measured
   at equal weights only. C1+C4 had the lowest tested combination turnover
   (34.85%); no combination entered the protected four-ID packet.
9. **Capacity stress**: value-traded capacity proxies were quantified, but
   historical ADV/spread/queue/capacity authority is absent. These are
   implementation cautions, not executable-capacity claims.
10. **Latest adversarial audit**: C1/C2/C4 implementation and frozen outputs
    passed outcome-blind structural checks (details below).
11. **Phase-Q red-team synthesis**: three read-only reviews are now complete.
    Causal/calendar/mask checks pass, but PIT/as-of, identity, survivorship,
    price basis, real capacity, and full independent recomputation remain
    unresolved. The reviews are documented in the latest read-in; no candidate
    became `READY`.
11. **H-LIQ-01 novelty diagnostic**: the temporal-variability score is not a
    monotone duplicate of C2, but dependence with the turnover-level component
    rises from -0.046 in Q1 to 0.468 in Q4. It remains a future hypothesis,
    not C5.

## Latest adversarial result

Artifact: `alpha_c1234_adversarial_audit_v1.json` in the external staging
root. Result: `PASS_STRUCTURAL_ONLY`.

Checks passed:

- no negative shifts, backward/forward fill, network imports, or HTTP calls;
- required causal feature tokens and cross-sectional date ranking present;
- exact C1/C2/C4 score/rank schema;
- no target-like feature column;
- feature/panel row and key equality; no duplicate `(ticker,date)` keys;
- all feature dates are official sessions and per-ticker dates are ordered;
- security-master tickers are unique;
- all 310,761 eligible keys map to exactly one active security-master interval;
- every candidate score/rank mask is closed outside eligibility;
- rank bounds are valid and no score/rank infinities occur.

Support from this audit:

| ID | finite eligible rows | finite dates | finite tickers | Top-30 dates |
|---|---:|---:|---:|---:|
| C1 | 295,243 | 1,141 | 704 | 1,141 |
| C2 | 310,761 | 1,201 | 711 | 1,201 |
| C4 | 310,323 | 1,201 | 711 | 1,201 |

The audit explicitly does **not** certify corporate-action price basis,
issuer/ISIN continuity beyond the frozen interval mapping, or historical PIT
authority. It accessed no targets, outcomes, providers, or incumbent score
artifacts and created no candidate ID.

The legacy verifier passed only an envelope check and is not sufficient as an
independent replay. The new source-recomputing verifier passed:
`status=PASS_INDEPENDENT_STRUCTURAL_REPLAY`; all recomputed structural maps,
source hashes, identity summary, and listing-age metrics matched the artifact.
Its access-absence flags remain explicitly self-attested, not process-level
proof.

The follow-up CA/price-basis audit found that the known 1,657-row HLC overlay
is already embedded in the current panel and replay leaves all C1/C2/C4
Top-30 sets unchanged. A separate forensic substitution of 188 unresolved
`idx_close` comparison rows changed C1 ranks on 10.617% of compared rows with
a 36.667% minimum Top-30 overlap, versus 2.894% / 83.333% for C2 and 3.203%
/ 86.667% for C4. These are sensitivity warnings, not corrections or
predictive evidence; C1 now has the highest unresolved price-basis fragility.

## Data admissibility and unresolved risks

| Surface | Disposition | Consequence |
|---|---|---|
| Clean OHLCV panel | `PARTIAL / FROZEN_ONLY` | structural diagnostics only |
| Official sessions / tradability anchors | `PARTIAL / FROZEN_ONLY` | calendar and same-session masking only |
| Financial PIT bundle | `PARTIAL / PARKED` | C3 capability diagnosis only |
| Activity metadata snapshot | `METADATA_ONLY / NON-ADMISSIBLE` | cannot become historical liquidity evidence |
| Sector/industry history | unavailable/partial | sector robustness remains incomplete |
| Historical spread/ADV/order-book | unavailable/partial | real capacity remains unknown |
| Corporate-action and issuer basis | unresolved | no same-basis certification |
| H5/H10 and prospective outcome vault | `BLOCKED` | no predictive evaluation |

Highest-value unresolved questions are corporate-action/price-basis authority,
population-wide PIT financial vintages, historical liquidity/capacity, sector
history, and the remaining independent red-team coverage for C1/C2/C4.

H-LIQ-01's novelty question is partially answered: retain the mechanism card,
but do not admit a candidate ID because shared participation information and
economic/PIT risks remain material. Deterministic selection and explicit
no-fill handling were fixed and replayed in the Phase-Q follow-up.

The preregistered size-neutral diagnostic shows that bottom-value exposure is
partly scale-related (39.672% to 14.983%), but mean Top-30 turnover rises from
10.306% to 20.785%. This is a useful representation result, not a candidate
upgrade or C5 admission.

## Queue and exact next action

No candidate is currently `READY_FOR_REENTRY`. C1/C2/C4 are conditionally
engineering-ready; C3 remains blocked; H-LIQ-01 and H-VOL-01 remain pending
future hypotheses, not candidate IDs.

For future gate ordering only (not an alpha ranking), C2/C4 have lower
bounded unresolved-basis sensitivity than C1. C1 should not be treated as
price-basis-ready until the 188 rows and open residuals are resolved.

When Data QA admission arrives, the next action is:

1. Read the fresh canonical `TEAM_STATUS.md` and admission artifact.
2. Verify population completeness, PIT/as-of, identity/calendar,
   corporate-action basis, revision/vintage, and both H5/H10 horizons.
3. If any gate is absent or unknown, do not open outcomes and leave statuses
   unchanged.
4. If every gate passes, run the already-frozen C1-C4 packet once on common
   support, with no rescue, refit, or variant sweep.

Until then, continue only with non-redundant outcome-blind work such as
bounded CA/issuer-basis auditing, capacity clarification, and dedicated
read-only red-team review. Do not repeat completed C1-C4 structural metrics.

## Repository, artifacts, tests, and provenance

- Branch: `codex/alpha-available-data-20260919`
- Latest status update commit before this checkpoint: `0a9bbbb9`
- External staging root:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Adversarial builder: `research/alpha_c1234_adversarial_audit_v1.py`
- Adversarial verifier: `research/verify_alpha_c1234_adversarial_audit_v1.py`
- Builder SHA-256: `c2ddfa9fd13d331a9a514ebba28e763c1aebf42287152cd572f1afea26d2fa44`
- Verifier SHA-256: `0950872b2271cb99ca1b99967bab0174eb13c8a0b264f266560f15aa8ac409c7`
- Audit JSON SHA-256: `6bfcba7070be218d288a0cf894f8d7e54b170bf624966e38a758061ed7d6dae8`
- Audit status: `PASS_STRUCTURAL_ONLY`
- Verifier status: `PASS`
- Protected-target firewall: previously `PASS`; no protected access in this
  continuation.
- Canonical `origin/main`: not modified.

Detailed durable documents:

- `2026-09-19_ALPHA_RESEARCH_PROGRAM_FINAL_HANDOFF_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PROGRAM_CHECKPOINT_V2.md`
- `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_REENTRY_QUEUE_V1.md`
- `2026-09-19_ALPHA_C1234_ADVERSARIAL_RESULT_V1.md`
- `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_NOVELTY_RESULT_V1.md`
- `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_STAGE_A_LINEAGE_RESULT_V1.md`
- `2026-09-19_ALPHA_STAGE_A_CONSUMER_AUDIT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_LATEST_READIN_V1.md`

No predictive superiority claim is made.

## Latest continuation update — CA exposure attribution

The research lane remains active for bounded, outcome-blind work. A new
read-only counterfactual replay exactly reproduced the stored C1/C2/C4
baseline scores and attributed changed rows against the 188-row unresolved
price-basis artifact. C1 had `66` direct score changes and `82,291` spillover
score changes; C2 had `66` and `457`; C4 had `66` and `319`. “Direct” means
the changed `(ticker,date)` key is present in the unresolved artifact, not that
causality has been proven. No candidate disposition changed and no correction
was promoted. See `2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md` and
the compact handoff `2026-09-19_ALPHA_RESEARCH_CHATGPT_HANDOFF_V3.md`.

## Latest frontier audit

Independent read-only audits added three decision-relevant findings. Capacity
tails strengthen C1 friction caution and C4 bottom-value/capacity caution;
H-LIQ-01 remains no-C5 because it is distinct but composition-sensitive; and
`Dataset-Saham-IDX` is a newly surfaced but blocked data source with no
row-level PIT/vintage contract and 11 non-identical duplicate ticker copies.
No candidate status changed. See
`2026-09-19_ALPHA_PHASE_FRONTIER_AUDIT_RESULT_V1.md`.
The newly surfaced source's detailed admission result is
`2026-09-19_ALPHA_DATASET_SAHAM_IDX_ADMISSION_AUDIT_V1.md` and remains
`BLOCKED / NOT_ADMITTED`.

## Latest H-VOL-01 continuation

One fixed daily volatility-compression representation was evaluated in the
same outcome-blind lane: `-log(median_5((high-low)/close) /
median_60((high-low)/close))`. It produced `308,514` finite eligible rows,
`29.2778%` mean Top-30 turnover, and `42.7200%` selected bottom-value Q1
share. Its low bounded overlap with existing candidates is not predictive
orthogonality; adjacent historical range families and unresolved PIT/price
basis/capacity keep it at `FUTURE_RESEARCH / NOVELTY_PENDING /
ECONOMIC_CAUTION`. No C5 was created. See
`2026-09-19_ALPHA_HVOL01_COMPRESSION_RESULT_V1.md`.

The H-VOL-specific CA sensitivity audit then substituted the same retained
`idx_close` values used in the existing 188-row forensic lane. It changed 547
scores and 8,876 ranks, while preserving `99.8307%` mean Top-30 overlap and
`86.6667%` minimum overlap. This is bounded forensic evidence only: price-basis
authority remains unresolved and H-VOL stays no-C5.

The protected re-entry packet was revalidated after these additions: it still
contains exactly C1-C4, with H-LIQ-01 and H-VOL-01 explicitly excluded. Hashes
for the packet, protocol, implementation, guarded features, and manifest match
the recorded specification. The packet remains
`SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`.

The fixed H-VOL horizon audit also evaluated `5/20`, `5/60`, and `20/120`.
The baseline `5/60` reproduced exactly; `5/20` raised mean Top-30 turnover to
`36.2583%`, while `20/120` reduced mean turnover to `12.5789%` but left only
`271,045` finite eligible rows. Pairwise Top-30 overlap was only
`58.9675% / 9.9182% / 29.3193%` across the three pairs. No horizon was
selected and H-VOL remains `FUTURE_RESEARCH / NOVELTY_PENDING /
ECONOMIC_CAUTION`, outside the protected packet. See
`2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md`.

H-EXC-01 then tested previous-close high/low excursion asymmetry without
current Open or volume. It had `305,814` finite rows but unbounded score tails
(`-16.2 / 5.0`) and `40.9694%` mean Top-30 turnover, so the exact raw form is
`STRUCTURALLY_REJECTED_AS_WRITTEN`. The broader excursion/rejection mechanism
is not closed, but no clipping or denominator rescue was authorized. See
`2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`.

H-EXC-02 then tested a new preregistered bounded absolute-distance balance:
`median_5((abs(high-prev_close)-abs(low-prev_close)) /
(abs(high-prev_close)+abs(low-prev_close)))`. It produced `308,067` finite
eligible rows over `1,201` dates and `711` tickers, with exact score domain
`[-1,1]`, but mean/q95/max Top-30 turnover of
`40.7750% / 56.6667% / 86.6667%`. Mean Top-30 overlap with C1/C2/C4/H-LIQ/
H-VOL was `1.3380% / 25.8562% / 4.9431% / 14.7849% / 11.4543%`. This fixes
the numerical-bound failure as a new contract, but not the high-churn,
capacity, PIT, or CA risks. Disposition remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 was created.
See `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`.

The dedicated H-EXC-02 CA sensitivity audit replaced `close` in memory only
for the retained 188 unresolved rows. Baseline and counterfactual support were
both `308,067`; `155` score rows and `3,977` ranks changed, but Top-30 overlap
was `99.9722%` mean and `93.3333%` minimum across 8 changed dates, with only
`1 / 19` direct/spillover changed slots. This narrows the specific basis risk
without clearing global PIT/CA authority or changing the disposition. See
`2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`.

The preregistered H-EXC-02 horizon audit then evaluated fixed median windows
`5/20/60`. Mean Top-30 turnover fell from `40.7750%` to `20.4944%` to
`11.7570%`, but pairwise Top-30 overlap was only `34.7905% / 24.3750% /
42.3333%`; no horizon was selected. The lower-turnover forms are distinct
future representations, not an economic repair or predictive result. See
`2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`.

An Open capability audit refined the H-MICRO-02 data boundary: positive finite
Open is present on `201,415/310,761` eligible rows (`64.8135%`) and all
`1,201` eligible dates have at least 30 Open rows. However, provenance is split
between IDX/Yahoo with `20,995` source transitions, and available-at, PIT,
corporate-action, identity, and execution semantics remain unadmitted.
H-MICRO-02 is `PARTIAL_CAPABILITY / BLOCKED_SOURCE_ADMISSION`, not a candidate.
See `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`.

## Latest continuation update — corrected Phase-Q red-team replay

An independent read-only red-team found two implementation defects in prior
target-free reports. The old robustness lookback replay aligned variant scores
positionally after a reset-index merge; the corrected key-aligned V2 replay
changes mean Top-30 overlap from invalid V1 values near 11–12% to C1 h3/h10
`57.2333%/52.0389%`, C2 `65.3167%/60.1389%`, and C4 h10/h40
`44.7611%/45.4111%`. The old combination report ranked liquidity percentiles
over the full panel instead of eligible rows; the corrected V2 bottom-value Q25
exposure is `30.7722%–40.6722%` across combinations, not `0.4333%–0.7056%`.

The V1 outputs remain preserved for lineage but are superseded for these two
interpretations. Candidate formulas, turnover, equal weights, and friction
scenarios were unchanged. No candidate status changed, no C5 was created, and
the protected packet remains exactly C1–C4. Both V2 verifiers and the
outcome-blind static firewall pass. See
`2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`.

## Latest continuation update — market-context / breadth source audit

The local market-index/breadth archive was audited read-only in the isolated
lane. Direct and Zapi copies match exactly on three sampled rich dates. Market
totals reconcile exactly on 2024-06-21 and 2026-07-31; 2021-01-04 has an
explicit localized composite-versus-component discrepancy. The digital archive
contains only three sampled monthly blocks, so no continuous PIT-admissible
feature or candidate was created. Status remains
`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`; C1–C4, the protected
packet, and all main/canonical/capture/cloud/telemetry state are unchanged.
See `2026-09-20_ALPHA_MARKET_CONTEXT_SOURCE_AUDIT_RESULT_V1.md`.

## Latest continuation update — H-LIQ-01 novelty no-retry adjudication

An independent worker red-team reviewed the unresolved H-LIQ question. The
same-date OLS residualization of H-LIQ rank on C2 turnover-level rank is not
independent evidence of a new mechanism; the residual retains `0.0843185`
dependence with full C2 and worsens bottom-value exposure from `39.6722%` to
`50.3889%`. Six-block dependence also varies materially. The result is
`UNKNOWN` for mechanism-level novelty, `FAIL/UNKNOWN` for unqualified
persistence/economic worth, and `NO-GO` for another same-surface retry. H-LIQ
remains `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 or packet
change. See `2026-09-20_ALPHA_HLIQ01_NOVELTY_NO_RETRY_ADJUDICATION_V1.md`.

## Latest continuation update — panel-depth source capability audit

The highest-information local non-redundant panel-depth surface was audited
read-only. The manifest contains 12 symbols and 18,835 rows, with exact raw
hash/byte matches, exact arithmetic invariants, and exact official parity for
23/23 available symbol/date pairs. The normalized BBCA rowset is an exact
duplicate of the historical-depth BBCA surface. No row-level PIT, revision,
identity/ISIN, issuer-transition, or corporate-action fields are present, so
the result is `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`; no feature,
candidate, or model evaluation was run. See
`2026-09-20_ALPHA_PANEL_DEPTH_SOURCE_AUDIT_RESULT_V1.md`.

## Latest continuation update — Phase-Q C1/C2/C4 red-team and local data census

An independent Phase-Q red-team keeps C1/C2/C4 and all combinations at `NO-GO`
for readiness: CA price basis fails readiness for C1, executable capacity fails
readiness for all three, and full constructor/PIT/population proofs remain
unknown. C1/C4 are not additive-independent. See
`2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`.

The local-data census found no admissible new surface. It classified TradingView
BBCA max and Investing BBCA max as partial, non-redundant, basis-divergent
histories and all remaining newly inspected probes as snapshot/current or
metadata-only. See `2026-09-20_ALPHA_DATA_SURFACE_CENSUS_V1.md`.

The BBCA basis reconciliation found TradingView at an exact 5x price basis
against IDX through 2021-10-12 and 1x from 2021-10-13, while Investing has
0/1,568 exact OHLCV field matches and no constant scale. This strengthens the
global CA/price-basis block; neither source was rescaled or admitted. See
`2026-09-20_ALPHA_BBCA_PRICE_BASIS_RECONCILIATION_RESULT_V1.md`.

The BBCA CA-event linkage audit then found 61 exact panel/IDX HLC trace rows,
but zero BBCA rows in both retained CA ledgers. The 2021-10-13 alignment is
therefore forensic context, not event-level authority; the global CA/issuer
block remains unchanged. See
`2026-09-20_ALPHA_BBCA_CA_EVENT_LINKAGE_RESULT_V1.md`.
