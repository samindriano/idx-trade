# IDX-Trade Alpha Research — ChatGPT Handoff V3

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`  
Branch: `codex/alpha-available-data-20260919`  
Latest evidence content: continuation audit on this branch; prior baseline `96a3f12b`
Latest H-LIQ source decomposition: `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
Latest H-LIQ independent verifier: `research/verify_alpha_hliq01_source_decomposition_v1.py`
Current future-evaluation packet: `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md`
Latest re-entry contract closure: `2026-09-19_ALPHA_REENTRY_PACKET_CONTRACT_CLOSURE_RESULT_V1.md`
Latest H-FRAG-01 source audit: `2026-09-19_ALPHA_HFRAG01_SOURCE_AUDIT_RESULT_V1.md`
Latest H-FRAG-01 independent verifier: `research/verify_alpha_hfrag01_source_audit_v1.py`
Latest FILINGAGE-01 source audit: `2026-09-19_ALPHA_FILINGAGE01_SOURCE_AUDIT_RESULT_V1.md`
Latest EXECSTATE-01 source audit: `2026-09-19_ALPHA_EXECSTATE01_SOURCE_AUDIT_RESULT_V1.md`
Latest SUSPSTATE-01 reconciliation: `2026-09-19_ALPHA_SUSPSTATE01_RECONCILIATION_RESULT_V1.md`
Latest CA residual coverage: `2026-09-19_ALPHA_CA_RESIDUAL_COVERAGE_RESULT_V1.md`
Latest SECTOR-01 source audit: `2026-09-19_ALPHA_SECTOR01_SOURCE_AUDIT_RESULT_V1.md`
Latest literature mechanism card: `2026-09-19_ALPHA_LITERATURE_MECHANISM_CARD_REVERSAL_LIQUIDITY_V1.md`
Latest C1/C2/C4 verifier-scope adjudication: `2026-09-19_ALPHA_C1234_REDTEAM_SCOPE_ADJUDICATION_RESULT_V1.md`
Latest H-LIQ temporal persistence red-team: `2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`
Latest re-entry packet freshness audit: `2026-09-19_ALPHA_REENTRY_PACKET_FRESHNESS_AUDIT_RESULT_V1.md`
Latest H-EXC-02 CA sensitivity: `2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`
Latest H-EXC-02 horizon stability: `2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`
Latest Open capability audit: `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`
Latest Phase-Q correction replay: `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`
External staging root: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Jawaban singkat

Tidak, riset tidak berhenti total. Yang masih diblokir adalah historical
predictive evaluation karena Data QA belum mengadmit population completeness,
PIT/as-of, issuer identity, corporate-action/price basis, revision/vintage,
dan H5/H10. Pre-admission, outcome-blind structural research masih berjalan di
lane terpisah ini.

Tidak ada perubahan pada `origin/main`, canonical/incumbent model, production
data, capture/cloud/R2, scheduler, telemetry, provider/network, atau protected
target/outcome.

## Status kandidat sekarang

| Candidate | Support | Top-30 turnover | Status |
|---|---:|---:|---|
| C1 residual reversal 5 | `295,243 / 310,761` (`95.0065%`) | `42.15%` | `FUTURE_RESEARCH`; CA/PIT fragility highest |
| C2 participation confirmation 5 | `310,761 / 310,761` (`100%`) | `32.91%` | `FUTURE_RESEARCH` |
| C3 financial quality/growth | `30,994` rows; `278` usable dates | `10.93%` | `BLOCKED`; financial/PIT support sparse |
| C4 path-efficiency reversal 20 | `310,323 / 310,761` (`99.8591%`) | `23.70%` | `FUTURE_RESEARCH / ECONOMIC_CAUTION` |
| H-LIQ-01 | `155,679` finite rows; diagnostic only | `10.306%` baseline | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 |
| H-VOL-01 | `308,514` finite rows; diagnostic only | `29.2778%` mean | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 |
| H-EXC-02 | `308,067` finite rows; diagnostic only | `40.7750%` mean | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 |

Base friction figures are frozen structural proxies, not realized P&L. No
candidate has a predictive, OOS, IC/ICIR, or incumbent-superiority claim.

## Apa yang sudah didapatkan

1. Corrected decision universe: `310,761` eligible rows across `711` tickers.
   C1/C2/C4 have broad structural support; C3 is blocked by sparse financial
   and PIT capability.
2. Causal/structural checks: prior-only shifts, future-row mutation isolation,
   key uniqueness, official-session masks, rank bounds, and source-hash checks
   passed. These are not proof of full historical PIT or CA authority.
   The C1/C2/C4 v2 verifier is independently structural/artifact-level, not a
   full independent feature-constructor or eligibility rebuild; its scope is
   now recorded explicitly.
3. Independent structural-lab replay recomputed the full candidate and pairwise
   maps and passed `PASS_INDEPENDENT_SOURCE_REPLAY`, `mismatch_count=0`.
4. Phase-Q red-team reviews covered causal/PIT/identity/CA, economics/
   concentration/liquidity, and combinations/H-LIQ. No new candidate was
   admitted.
5. H-LIQ-01 is structurally distinct from C2 on average, but conditional
   dependence rises in the top-value bucket. A fixed size-neutral diagnostic
   reduced selected bottom-value Q25 exposure from `39.672%` to `14.983%`, but
   raised mean Top-30 turnover from `10.306%` to `20.785%`; hence no C5.
6. C1+C4 has the lowest tested combination turnover at `34.85%`, but daily
   Spearman is about `0.8499`; this is not evidence of incremental alpha.
7. Capacity stress used only `regular_market_value` as a proxy. It sharpens
   implementation caution but does not establish ADV, spreads, fills, or
   executable capacity.
8. Corporate-action forensic work verified the retained `1,657/1,657` HLC
   overlay and replay stability. `188` unresolved non-stable scale rows and
   open-price residuals keep CA/PIT admission blocked.

9. Independent capacity-tail review found C1 median/q95/max Top-30 turnover
   `40.00%/56.67%/66.67%`, C2 `33.33%/50.00%/63.33%`, and C4
   `23.33%/36.67%/46.67%`; sessions above 50 bps were `220/599`, `60/599`,
   and `1/599`. C4's low mean turnover is offset by bottom-value Q1 exposure
   `34.46%`; this is implementation caution, not capacity proof.
10. H-LIQ-01 remains distinct from C1/C4 but shares a persistent participation
    component with C2. Its bottom-value Q1 share is `39.67%`, and its early-to-
    late Q1 share moves `51.3%` to `29.5%`; retain no-C5 status.
11. The fixed C2 turnover-level source decomposition was independently
    recomputed: mean daily Spearman against the removed level component falls
    from `0.1647556` to `0.0157646`, but residual dependence with full C2 is
    `0.0843185` and bottom-value Q1 share worsens to `50.3889%`. This supports
    only `STRUCTURAL_NONREDUNDANCY_VS_C2_LEVEL_ONLY`; H-LIQ remains
    `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`, with no C5 ID.
12. Re-entry packet V2 now has direct source/manifest/code hashes, key-digest
    binding, explicit missingness/tie rules, a fail-closed C3 gate, and frozen
    robustness/friction references. Independent contract verification and the
    outcome-blind firewall pass, but the verdict remains `NO-GO_FOR_REENTRY /
    BLOCKED_BY_DATA_ADMISSION`.
13. H-FRAG-01 audited the official stock-summary cache in the isolated lane.
    The cache is internally coherent: `1,104,064` rows, `1,260` parquet/
    sidecar pairs, duplicate key count `0`, official source identity exact,
    and `981,940/981,940` volume/value overlap with the frozen panel exact.
    However, the preregistered ratio validity gate fails: non-regular volume
    ratio boundedness violations `8,750` rows and frequency ratio violations
    `7` rows. Independent source verification and outcome-blind firewalls
    passed, but the result is `SOURCE_BLOCKED / PARTIAL`; no C5, target,
    outcome, or packet expansion was created. See
    `2026-09-19_ALPHA_HFRAG01_SOURCE_AUDIT_RESULT_V1.md`.
14. A bounded local-data inventory found `Dataset-Saham-IDX` (external commit
    `bc0ac771`, `1,014` CSVs, `1,146,324` rows, 2019-07-29–2025-02-21). It is
    `BLOCKED`: no row-level knowledge-time/vintage field, 56 duplicate ticker
    groups including 11 non-identical copies, and unclear CA/identity/source
    selection. Its static sector/listing files are `METADATA_ONLY`. A dedicated
    admission audit confirmed 923/1,260 official-session dates intersect and
    left PIT, identity, CA basis, and foreign-flow timing unresolved.
15. H-VOL-01 compression was tested as one fixed structural representation:
    `-log(median_5((high-low)/close) / median_60((high-low)/close))`. It has
    `308,514` finite eligible rows, low mean Top-30 overlap with C1/C2/C4/
    H-LIQ-01 of `9.5209% / 8.0155% / 15.5676% / 13.5803%`, but `29.2778%`
    mean turnover and `42.7200%` selected bottom-value Q1 concentration.
    Prior range-family adjacency and unresolved PIT/CA/capacity prevent C5
    admission; this is structural evidence only. Full result is in
    `2026-09-19_ALPHA_HVOL01_COMPRESSION_RESULT_V1.md`.
16. H-VOL-01 CA sensitivity was separately audited against the retained 188
    unresolved rows. The substitution changed `547` scores and `8,876` ranks;
    mean/minimum Top-30 overlap was `99.8307% / 86.6667%`. This narrows but
    does not clear price-basis risk, and H-VOL remains outside the protected
    packet with no C5 ID. See
    `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`.
17. A fixed horizon-stability audit compared H-VOL `5/20`, `5/60`, and
    `20/120`. The baseline reproduced exactly; `5/20` mean turnover was
    `36.2583%`, `5/60` was `29.2778%`, and `20/120` support fell to
    `271,045` rows. Pairwise Top-30 overlap was `58.9675% / 9.9182% /
    29.3193%`; no horizon was selected and no C5 was created. See
    `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md`.
18. H-EXC-01 tested previous-close high/low excursion asymmetry without Open
    or volume. It had `305,814` finite rows, but unbounded score tails
    (`-16.2 / 5.0`) and `40.9694%` mean Top-30 turnover. The exact raw form is
    `STRUCTURALLY_REJECTED_AS_WRITTEN`; no post-result clipping or denominator
    rescue was performed, and the broader mechanism remains an untested future
    question. See `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`.
19. H-EXC-02 tested a new preregistered bounded absolute-distance excursion
    balance. It has exact score domain `[-1,1]`, `308,067` finite eligible rows,
    `40.7750%` mean Top-30 turnover, and `86.6667%` maximum turnover. It is
    structurally distinct but high-churn; no C5 or protected-packet change.
    See `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`.
20. The H-EXC-02 188-row CA sensitivity kept support identical and produced
    `99.9722% / 93.3333%` mean/minimum Top-30 overlap, but changed `3,977`
    ranks. This narrows a specific basis risk only; no C5 or status upgrade.
    See `2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`.
21. The fixed H-EXC-02 horizon audit evaluated `5/20/60`: mean turnover fell
    to `40.7750% / 20.4944% / 11.7570%`, but pairwise Top-30 overlap was only
    `34.7905% / 24.3750% / 42.3333%`. No horizon was selected; the longer
    forms remain future representations, not a repair or predictive result.
    See `2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`.
22. Historical Open capability is partial: `201,415/310,761` eligible rows
    are positive finite and all `1,201` eligible dates have at least 30 rows.
    Mixed IDX/Yahoo provenance, `20,995` source transitions, and missing
    available-at/PIT/execution authority keep H-MICRO-02 blocked. See
    `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`.

23. Independent Phase-Q red-team found two historical implementation defects:
    robustness lookback variants were positionally misaligned after a merge,
    and combination liquidity percentiles used the full-panel denominator.
    Corrected V2 mean overlaps are C1 h3/h10 `57.2333%/52.0389%`, C2
    `65.3167%/60.1389%`, and C4 h10/h40 `44.7611%/45.4111%`; corrected
    combination bottom-value Q25 exposure is `30.7722%–40.6722%`. V1 is
    preserved for lineage but superseded for these claims. No status or packet
    membership changed. See
    `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`.

## Latest CA exposure attribution

The latest read-only counterfactual replay exactly reproduced stored baseline
scores for C1/C2/C4. It classified changed `(ticker,date)` rows against the
188-row unresolved artifact:

| Candidate | Direct score/rank changes | Spillover score/rank changes | Direct / spillover changed Top-30 slots | Mean Top-30 overlap | Minimum |
|---|---:|---:|---:|---:|---:|
| C1 | `66 / 65` | `82,291 / 31,281` | `18 / 1,172` | `98.2618%` | `36.6667%` |
| C2 | `66 / 65` | `457 / 8,929` | `38 / 96` | `99.8140%` | `83.3333%` |
| C4 | `66 / 62` | `319 / 9,877` | `12 / 52` | `99.9112%` | `86.6667%` |
| H-LIQ-01 diagnostic | `66 / 63` | `317 / 10,247` | `16 / 174` | `99.7363%` | `90.0000%` |

Meaning: C1's score sensitivity is mostly cross-sectional spillover, while
C2/C4 have smaller but visible direct-row sensitivity. “Direct” and
“spillover” are preregistered row classifications, not causal proof and not
an admitted correction. Full evidence is in
`2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md`.

## What remains blocked

- Historical PIT/as-of and population completeness admission.
- Issuer/ISIN continuity and complete corporate-action price-basis authority.
- Revision/vintage authority and real capacity fields.
- Protected H5/H10/forward outcomes, target ranking, IC/ICIR/OOS, incumbent
  comparison, refit, promotion, or model deployment.

## Safe next steps

Continue only with bounded, outcome-blind audits of local evidence: source
admission, issuer/CA/PIT provenance, capacity clarification, and documentation
integrity. The highest-value unblock is an independent Data QA admission
artifact. If no new admissible evidence appears, stopping is reasonable; there
is no justification to open target data merely to force a winner.

## Primary documents

- `2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md`
- `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `2026-09-19_ALPHA_STRUCTURAL_LAB_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_SIZE_NEUTRAL_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
- `2026-09-19_ALPHA_HFRAG01_SOURCE_PREREGISTRATION_V1.md`
- `2026-09-19_ALPHA_HFRAG01_SOURCE_AUDIT_RESULT_V1.md`
- `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
- `2026-09-19_ALPHA_CAPACITY_STRESS_RESULT_V1.md`
- `2026-09-19_ALPHA_PHASE_FRONTIER_AUDIT_RESULT_V1.md`
- `2026-09-19_ALPHA_REENTRY_PACKET_AUDIT_RESULT_V2.md` (historical/stale; use contract closure)
- `2026-09-19_ALPHA_RESEARCH_RISK_REGISTER_V1.md`
- `2026-09-19_ALPHA_DATASET_SAHAM_IDX_ADMISSION_AUDIT_V1.md`
- `2026-09-19_ALPHA_HVOL01_COMPRESSION_PREREGISTRATION_V1.md`
- `2026-09-19_ALPHA_HVOL01_COMPRESSION_RESULT_V1.md`
- `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_PREREGISTRATION_V1.md`
- `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`
- `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_PREREGISTRATION_V1.md`
- `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md`
- `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_PREREGISTRATION_V1.md`
- `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`

## Hard boundary

### Latest continuation evidence

- FILINGAGE-01: `70,931` reporting-age rows are internally coherent, but
  coverage starts in 2024 and public availability, revision/vintage, and
  identity authority are unresolved. `NOT_ADMITTED`.
- EXECSTATE-01: `1,104,064` official execution-state rows over `1,260`
  sessions reconcile exactly to the raw cache and session report. The
  `NO_TRADE` label is not admitted as suspension, illiquidity, or executable
  capacity; semantics, completeness, PIT timing, vintage, and identity remain
  unknown.
- SUSPSTATE-01: only `1,168` regular interval rows overlap no-trade, while
  `120,498/121,666` unique no-trade keys are outside the sparse interval
  source; `471` overlapping interval-key groups prohibit silent deduplication.
  `SOURCE_BLOCKED`.
- CA residual coverage: unresolved non-stable-scale rows overlap the retained
  HLC overlay `0/188`; listing-interval matches are narrow only and do not
  establish issuer/ISIN or event semantics.

These are source-quality/structural findings only. No target, outcome,
provider, cloud, incumbent, canonical, capture, scheduler, telemetry, or
production state was accessed or changed. The official IDX-IC sector archive
capability audit is complete; it remains
metadata/structural only because publication timing, daily membership
intervals, and identity continuity were not demonstrated.

SECTOR-01 is now complete: `22` structured 2022/2023 sheets contain `1,607`
rows and `837` unique ticker codes, but the archive has PDF-only year gaps,
cross-sheet `GWSA`/`KOTA` duplicates, and no daily/PIT/identity/vintage
authority. It remains `SOURCE_PARTIAL_STRUCTURAL_SIGNAL / NOT_ADMITTED`; no
feature or candidate was created. See
`2026-09-19_ALPHA_SECTOR01_SOURCE_AUDIT_RESULT_V1.md`.

Literature mapping found no justified new raw reversal/liquidity candidate;
those mechanisms overlap C1/C2/H-LIQ-01. Industry-adjusted reversal is kept as
a future specification only, because current sector history lacks daily PIT
membership, publication timing, identity, and revision authority. See
`2026-09-19_ALPHA_LITERATURE_MECHANISM_CARD_REVERSAL_LIQUIDITY_V1.md`.

H-LIQ temporal red-team coverage/mask checks pass, but six fixed 100-session
blocks show Q4 H-LIQ/C2 dependence `0.0762–0.3053` and bottom-value Q1 share
`29.47%–51.30%`. This fails an unqualified persistence claim; H-LIQ remains
no-C5 and novelty/economic meaning remain unknown. See
`2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`.

Re-entry packet indexing is logically consistent for C1-C4 with C3
fail-closed, but packet freshness is `UNKNOWN`: the frozen contract manifest
head differs from the current lane head. The packet remains
specification-only and must not execute; stale V1 references are now repaired
or labeled historical. See
`2026-09-19_ALPHA_REENTRY_PACKET_FRESHNESS_AUDIT_RESULT_V1.md`.

No protected outcome was opened, no provider/network scrape was performed, no
canonical or active dataset was changed, and no telemetry/capture/cloud state
was touched. The lane remains structurally productive but predictive proof is
not yet authorized.

## Latest continuation — CA basis, capacity tails, and no-new-mechanism decision

- CA/issuer red-team: HLC overlay coverage is narrow (`1,657/981,940` rows),
  residual keys are disjoint, and issuer/ISIN transition authority is absent;
  no repair or admission is justified.
- Capacity/friction-tail artifact: six surfaces, `600` sessions, `18,000`
  slots each; q95/q99/max turnover, fixed friction burdens, HHI/effective
  names, and separate value/raw-volume/dollar-turnover quartiles are now
  durable and independently verified. Real executable capacity remains
  blocked.
- Mechanism-surface adjudication: no new PIT-defensible OHLCV/value candidate
  was found. Effort-vs-result, breakout/rejection, and dispersion directions
  are covered, redundant, or source-blocked; protected budget remains C1-C4.

See `2026-09-19_ALPHA_CA_ISSUER_BASIS_REDTEAM_RESULT_V1.md`,
`2026-09-19_ALPHA_CAPACITY_FRICTION_TAIL_RESULT_V1.md`, and
`2026-09-19_ALPHA_NEW_MECHANISM_SURFACE_ADJUDICATION_V1.md`.

Additional red-team results:

- C3 denominator erratum: matched-source coverage is `25.8313%` for
  quality-core and `12.4308%` for all-five; both remain structural-only and
  C3 remains blocked.
- Packet provenance: producer binding is verified, packet attestation is
  stale, and full freshness remains unknown. Future packet updates must bind
  producer commit `P` and attest packet commit `Q` separately.
- Dataset-Saham-IDX remains blocked; no row-level vintage/PIT evidence changed
  its admission status.

See `2026-09-19_C3_CAPABILITY_DENOMINATOR_REDTEAM_ERRATUM_V1.md` and
`2026-09-19_ALPHA_REENTRY_PACKET_PRODUCER_BINDING_RECONCILIATION_RESULT_V1.md`.

The persisted local Zapi artifacts were also reviewed without network access:
one BBCA company-profile snapshot and empty March/August dividend probes.
They fail the parity/semantic admission checks and provide no historical
available-at, revision, issuer/ISIN, or CA authority. Zapi remains
`BLOCKED / NOT_ADMITTED`; no feature or candidate was created. See
`2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md`.

The existing KSEI ownership/free-float archive was also audited without
network access. Eight aggregate equity snapshots pass schema/arithmetic
checks and overlap the panel completely on their exact dates, but provide only
`8/1,260` dates, no row-level publication/revision contract, and no explicit
free-float field. H-FLOW-01 remains a future source specification and no C5
was created. See
`2026-09-19_ALPHA_OWNERSHIP_KSEI_SOURCE_AUDIT_RESULT_V1.md`.

The local market-index/breadth archive was then audited in the isolated lane.
Direct and Zapi copies match exactly across registered fields on three sampled
rich dates; market-total reconciliation is exact for the 2024/2026 samples and
has a recorded localized exception for 2021. The digital archive has only
three sampled monthly blocks, so it does not establish a continuous PIT-safe
daily feature source. Status is
`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`; no candidate or model
evaluation was run. See
`2026-09-20_ALPHA_MARKET_CONTEXT_SOURCE_AUDIT_RESULT_V1.md`.

An independent H-LIQ-01 red-team adjudication found the same-surface
C2-level residualization insufficient as mechanism evidence. Full-C2
dependence remains `0.0843185`, low-value exposure worsens to `50.3889%`, and
six-block dependence is unstable. Same-surface retry is `NO-GO`; H-LIQ remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` and no C5 was created.
See `2026-09-20_ALPHA_HLIQ01_NOVELTY_NO_RETRY_ADJUDICATION_V1.md`.

The next local source surface, `panel-depth`, was audited read-only. It has 12
symbols and 18,835 rows, exact raw/hash and arithmetic checks, and exact
official IDX parity on 23/23 available comparisons. BBCA is an exact duplicate
of an existing historical-depth surface. The rows do not provide PIT/available
time, revision/vintage, row-level identity/ISIN, issuer-transition, or
corporate-action authority, so admission remains
`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`. No feature or model
evaluation was run; incumbent/canonical/capture/cloud state is unchanged. See
`2026-09-20_ALPHA_PANEL_DEPTH_SOURCE_AUDIT_RESULT_V1.md`.

An independent Phase-Q red-team keeps C1/C2/C4 and combinations at `NO-GO` for
readiness: C1 is basis-sensitive, all three lack executable-capacity evidence,
full constructor/PIT/population proof is unknown, and C1/C4 are not additive-
independent. No outcome or incumbent evidence was opened. See
`2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`.

The local census found no admissible new surface. TradingView BBCA max and
Investing BBCA max are partial, basis-divergent deep histories; other newly
checked surfaces are duplicates, snapshots, current/intraday, or metadata-only.
See `2026-09-20_ALPHA_DATA_SURFACE_CENSUS_V1.md`.

The BBCA reconciliation found TradingView price basis `IDX/TV=5` through
2021-10-12 and `=1` from 2021-10-13, while Investing has no exact OHLCV match
on 1,568 IDX-overlap dates and no constant scale. Neither source was admitted
or rescaled. See
`2026-09-20_ALPHA_BBCA_PRICE_BASIS_RECONCILIATION_RESULT_V1.md`.

The follow-up CA linkage audit found 61 exact BBCA panel/IDX HLC trace rows,
but zero BBCA rows in both retained CA ledgers. This is forensic alignment,
not event-level authority; no source was rescaled or admitted. See
`2026-09-20_ALPHA_BBCA_CA_EVENT_LINKAGE_RESULT_V1.md`.

The panel-depth field-contract audit covers all 19 fields across 18,835 rows.
Structural arithmetic and bid/offer ordering pass, but field-level PIT,
revision/vintage, identity/ISIN, CA/share basis, price/value units, quote
timing/depth, and executable semantics are missing. Bid/offer is a future raw
surface only; foreign-flow remains in the existing H-FLOW family. The bounded
specification is `FUTURE_QUOTE_FLOW_INTERACTION_V1`, not a candidate, and no
C5 or predictive evaluation was run. See
`2026-09-20_ALPHA_PANEL_DEPTH_FIELD_CONTRACT_RESULT_V1.md`.

Independent review adds two constraints: CA/issuer exposure is only bounded
forensic sensitivity, not population-complete safety, and the current re-entry
packet is byte-fresh across `P=10939862`, `Q=e44f43ca`, attestation-run `R0=37390dae` but not
fully source-fresh. C1 remains most sensitive under the 188-row stress; no
candidate is upgraded and protected evaluation remains NO-GO. See
`2026-09-20_ALPHA_CA_CANDIDATE_EXPOSURE_COMPLETENESS_RESULT_V1.md`.

The local inventory was extended by six raw surfaces: historical foreign flow,
listing/delisting lifecycle, monthly/statutory free-float, HSC ownership
events, and broker/margin category state. They are all capability-only and
remain partial or blocked; no feature or candidate was admitted. See
`2026-09-20_ALPHA_LOCAL_DATA_SURFACE_CENSUS_CONTINUATION_V1.md`.

The official foreign-flow archive now has an independent structural audit:
1,129,024 rows and 1,288 sessions are hash/calendar/schema consistent, with
exact net arithmetic. It remains source-blocked because publication time is
unknown and T+1 is not a public-availability certificate; no feature or
candidate was admitted. See
`2026-09-20_ALPHA_FOREIGN_FLOW_HISTORICAL_SOURCE_AUDIT_RESULT_V1.md`.

The listing/delisting archive was audited next. Its 440 monthly raw files,
962 current rows, and 163 delisting rows pass independent hash, schema,
row-count, source-reference, and raw-payload parity checks. It remains
`PARTIAL / IDENTITY_BLOCKED`: six ticker conflicts remain, the source is not
daily PIT membership, and issuer/ISIN, publication-time, revision/vintage,
and corporate-action linkage are absent. No universe repair, feature,
candidate, packet, target, or incumbent state changed. See
`2026-09-20_ALPHA_LISTING_DELISTING_LIFECYCLE_SOURCE_AUDIT_RESULT_V1.md`.

The LBRE free-float corpus was independently audited afterward. All 58,671
manifest artifacts match bytes and hashes, but 868 lineage rows remain
unresolved: 532 multiple-original ambiguities, 332 missing-original cases,
and 4 invalid correction chronologies. It is monthly issuer-report data, not
a daily PIT population panel, so it remains
`PARTIAL / SOURCE_REMEDIATION_REQUIRED`; no feature, candidate, universe mask,
target, or incumbent state changed. See
`2026-09-20_ALPHA_LBRE_FREE_FLOAT_SOURCE_AUDIT_RESULT_V1.md`.

The statutory free-float snapshot was independently checked afterward. The
2,145 new files and seven reused parent bindings hash-match; 2025-12-31 has
923 exact-share rows out of 956, while 2026-03-31 is percentage-only with no
exact-share rows. Its embedded LBRE lineage has 93 excluded and 18
parse-unresolved rows. It remains
`PARTIAL / SOURCE_REMEDIATION_REQUIRED`, with no feature, candidate, universe
mask, target, or incumbent state changed. See
`2026-09-20_ALPHA_STATUTORY_FREE_FLOAT_SOURCE_AUDIT_RESULT_V1.md`.

The HSC ownership event ledger was independently audited afterward. All 137
manifest artifacts match bytes and hashes; the normalized ledger has 59 unique
events (56 originals, two corrections, one removal), replay passes, and the
effective cutoff target is 55 tickers. It remains `PARTIAL / EVENT_ONLY`, not
a daily PIT/population panel: completeness, issuer/ISIN continuity, CA
linkage, revision/vintage coverage, and public availability are unresolved.
No feature, candidate, universe mask, target, or incumbent state changed. See
`2026-09-20_ALPHA_HSC_OWNERSHIP_EVENT_SOURCE_AUDIT_RESULT_V1.md`.

The broker/margin snapshot was audited afterward. All 73 manifest files and
official/Zapi raw parity gates pass for 326 eligible, 220 margin, and 965
stock rows. Semantics remain blocked: 106 eligible rows are absent from
Margin Summary, all-six metric equality is 0/220, the source is not proven to
be financing flow or an exact All Stock filter, and publication/knowledge time
is absent. No feature, candidate, universe mask, target, or incumbent state
changed. See
`2026-09-20_ALPHA_BROKER_MARGIN_SNAPSHOT_SOURCE_AUDIT_RESULT_V1.md`.
