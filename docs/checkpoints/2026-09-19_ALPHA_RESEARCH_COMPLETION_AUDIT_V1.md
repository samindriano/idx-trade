# IDX-Trade Alpha Research — Pre-Admission Completion Audit V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
HEAD at audit: `e44f43ca4beb1cad7a9be9331567498a8beb16fd`  
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`

## Purpose and boundary

This is a completion audit of the long-horizon, pre-admission research
objective. It is not a predictive evaluation and does not certify any alpha.
The audit uses only the isolated lane, existing outcome-blind artifacts, and
read-only verifier runs.

The following remained out of scope and were not opened or modified:

- protected H5/H10, forward returns, labels, and target-derived incumbent data;
- incumbent/canonical/model data, capture runtime, cloud/R2, scheduler,
  production jobs, counters, and telemetry;
- provider fallback, live scraping, and any external data mutation;
- model fitting, IC/ICIR/OOS scoring, superiority claims, and promotion.

## Executive disposition

`PRE_ADMISSION_PROGRAM_SUBSTANTIALLY_COMPLETE / TARGET_AND_SOURCE_ADMISSION_BLOCKED`

The bounded pre-admission program has durable coverage for archaeology,
available-data inventory, C1-C4 structural work, C3 capability analysis,
orthogonality, mechanism review, robustness, economics, adversarial review,
future-data mapping, packet specification, and knowledge preservation.

This does not mean the research objective is scientifically closed. The
remaining decision-changing work depends on new authority or new evidence:

1. independent Data QA admission with population-complete historical
   available-at target semantics;
2. global corporate-action/issuer/ISIN and price-basis authority;
3. historical executable-capacity inputs such as ADV/spread/queue/fill;
4. daily PIT sector/industry history and identity/revision authority;
5. a separately frozen candidate contract if C3 or a future H-LIQ/H-VOL/
   H-EXC-02 hypothesis is ever considered for evaluation.

No current candidate is a research survivor, and no protected evaluation is
authorized by this audit.

## Objective coverage matrix

Status meanings: `COMPLETE` means the bounded outcome-blind deliverable is
durable; `PARTIAL` means useful work exists but a named gate remains;
`BLOCKED` means an external or protected prerequisite is missing.

| Objective area | Status | Evidence / remaining gate |
|---|---|---|
| Prior alpha archaeology and failure taxonomy | `COMPLETE` | `2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md`; `2026-09-19_ALPHA_FAILURE_TAXONOMY_V1.md`. Mechanisms are kept separate from representation/model/data failures. |
| Data, PIT, provenance, and unused-source inventory | `COMPLETE / ADMISSION BLOCKED` | `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md`; `2026-09-19_DATA_CAPABILITY_MATRIX_V1.md`; source audits. No local source establishes global PIT, identity, CA, or revision authority. |
| C1/C2/C3/C4 structural deepening | `COMPLETE STRUCTURAL` | Stage A, structural, robustness, economics, and independent replay artifacts. No target-free result is predictive evidence. |
| C3 financial capability | `COMPLETE CAPABILITY / BLOCKED SCIENCE` | `2026-09-19_C3_FINANCIAL_CONTRACT_MAP_RESULT_V1.md`; `2026-09-19_C3_CAPABILITY_DENOMINATOR_REDTEAM_ERRATUM_V1.md`. Quality-core is a capability island, not a frozen candidate contract. |
| Orthogonality and redundancy | `COMPLETE STRUCTURAL` | Structural orthogonality map and daily/rolling diagnostics. Predictive incremental information versus incumbent remains blocked. |
| New mechanism discovery | `COMPLETE BOUNDED / FUTURE ONLY` | `2026-09-19_ALPHA_NEW_MECHANISM_SURFACE_ADJUDICATION_V1.md`. No defensible new candidate from the admitted OHLCV/value surface; H-LIQ/H-VOL/H-EXC-02 remain non-candidates. |
| Robustness and parameter representation checks | `COMPLETE STRUCTURAL` | Corrected key-aligned robustness artifacts; rank/z/robust-z duplicate finding; horizon and missingness diagnostics. No outcome tuning. |
| Economic and capacity review | `PARTIAL / PROXY COMPLETE` | Capacity/friction-tail artifact covers six surfaces and structural tails. Real ADV/spread/queue/fill capacity remains unknown. |
| Combinations | `COMPLETE STRUCTURAL / CAUTION` | Equal-weight C1/C2/C4 combinations recorded; no weight optimization and no packet addition. |
| Source-capability expansion | `COMPLETE INVENTORY / ACCESS BLOCKED` | FILINGAGE-01, EXECSTATE-01, SUSPSTATE-01, CA residual, SECTOR-01, and Dataset-Saham-IDX audits. None changes admission. |
| Independent adversarial review | `PARTIAL / CORRECTIONS COMPLETE` | CA/issuer-basis, C3-denominator, packet-provenance, capacity-tail, and prior correction replays are durable. Global PIT/identity/price-basis/capacity authority remains unresolved. |
| Candidate novelty gate | `COMPLETE MILESTONE` | Candidate budget remains C1-C4; no C5 created. H-LIQ remains `NOVELTY_PENDING`. |
| Future evaluation packet | `COMPLETE SPECIFICATION / BLOCKED` | V2 packet and contract are statically verified; execution requires independent admission and fresh producer/packet attestation. |
| Knowledge and negative-result preservation | `COMPLETE MILESTONE` | Ledger, phase matrix, risk register, re-entry queue, handoffs, taxonomy, and do-not-retry boundaries are linked. |
| Autonomous continuation | `ACTIVE BUT GATED` | Continue only for genuinely new source/authority or bounded non-redundant red-team evidence. Do not repeat closed analyses. |

## Candidate disposition at audit

| ID / family | Disposition | Why it is not promoted |
|---|---|---|
| C1 residual reversal | `FUTURE_RESEARCH` | Structurally measured; price-basis/CA, PIT admission, target evidence, and executable capacity remain absent. |
| C2 participation confirmation | `FUTURE_RESEARCH` | Structurally measured; PIT/identity/price-basis and target admission remain absent. |
| C3 financial quality/growth | `BLOCKED` | All-five contract remains sparse and provenance/PIT governance is incomplete; quality-core has no separate frozen candidate contract. |
| C4 path-efficiency reversal | `FUTURE_RESEARCH` | Structurally measured; price-basis/CA, PIT admission, target evidence, and executable capacity remain absent. |
| H-LIQ-01, H-VOL-01, H-EXC-02 | `FUTURE RESEARCH / NO C5` | Bounded structural evidence exists, but novelty, economic caution, horizon dependence, CA/PIT, and capacity gates are unresolved. |

## Latest independent verifier evidence

All four reruns used explicit isolated/staged paths and completed with exit code
0 on the current lane:

- C3 contract verifier: `PASS` — no outcome/target/provider access, exact
  contract set, no-fill/no-fallback interpretation.
- Capacity-tail verifier: `PASS` — exact six-surface candidate set, 600
  sessions, 18,000 Top-30 slots per surface, bounded quartile/concentration
  arithmetic, and `executable_capacity_admitted=false`.
- Future-packet verifier: `PASS` — exact C1-C4 budget, source/implementation
  hashes, key digests, six robustness evidence bindings, clean worktree, and
  `specification_only=true`.
- Outcome-blind target/privacy firewall: `PASS` — no forbidden path literal,
  network/provider import, target/outcome access, or forbidden output column in
  the audited code/JSON/Parquet set.

Rerun artifacts were written only to the isolated staging root:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

- `alpha_future_evaluation_packet_v2_verification_rerun_e44f43ca.json`  
  SHA-256: `a4343d8ff5af65b9e1c578af889dafa255420547682f51b7e9f3fd2dea56233f`
- `alpha_research_target_firewall_audit_rerun_e44f43ca.json`  
  SHA-256: `9ba29cb0eaf0a0b33a7261a1329247813677eb06d7983e888415edcdc4c3b099`

The original guarded capacity and C3 inputs were read-only inputs to the
reruns; no existing staged artifact was overwritten.

## Re-entry decision

`NO-GO FOR PROTECTED EVALUATION`.

The future packet is ready as a specification, not as an executable job. A
future re-entry run must first receive independent Data QA admission, refresh
producer/packet attestation without a circular self-hash, re-run the target
firewall, and preserve the one-shot/no-rescue/no-refit contract. C3 must fail
closed if its admitted support remains below the frozen contract.

## Durable read-in pointers

- `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
- `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_REENTRY_QUEUE_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PROGRAM_FINAL_HANDOFF_V1.md`
- `2026-09-19_ALPHA_RESEARCH_CHATGPT_HANDOFF_V3.md`
- `2026-09-19_ALPHA_REENTRY_PACKET_PRODUCER_BINDING_RECONCILIATION_RESULT_V1.md`

## Final scope statement

This audit records substantial completion of the pre-admission research
program, not completion of the scientific question. The next meaningful state
change requires new admissible authority or a future protected evaluation
performed under the already frozen gates. Until then, the correct disposition
is to preserve the current negative/blocked results and avoid redundant
experiments, provider fallback, target access, or production mutation.

## Continuation amendment — 2026-09-20

The historical audit above remains bound to its recorded HEAD. The lane has
since advanced through additional non-target work:

- HSC ownership ledger: 137/137 artifact hashes, normalized parity, replay,
  and 55-ticker cutoff parity pass; admission remains event-only/PIT-blocked.
- Broker/margin snapshot: 73/73 artifact hashes and official/Zapi raw parity
  pass for 220 margin and 965 stock rows; admission remains single-date and
  snapshot-only blocked, with 106/326 eligible names absent and 0/220 all-six
  metric equality.
- CA/issuer-basis review: an independent replay found no new contradiction;
  PIT remains UNKNOWN, CA basis and executable capacity remain readiness
  failures, and C1/C4 remain non-additive. A reusable
  `CA_ISSUER_PRICE_BASIS_ADMISSION_V1` future specification was added without
  changing candidate or packet status.

Current continuation HEAD: `f4132c20`. The lane remains isolated, the
worktree is clean after the continuation commit, and the protected-target
boundary is unchanged.

## Continuation amendment — independent metadata/surface review — 2026-09-20

At snapshot HEAD `d318de60d9588e31bab5a0c47be5bdaab6b0d999`, two independent
read-only reviews found documentation issues and no scientific admission
change. The handoff's current-head and attestation pointers were stale; they
now identify the latest recorded clean rerun `R2=fbaa824c` while retaining the
historical `R0`/`R1` chain. The phase-matrix next-frontier text was corrected
to remove completed Phase-Q/CA work. The reviews also found that
`Dataset-Saham-IDX` was not an explicit row in the capability maps; it is now
listed as `BLOCKED / NOT_ADMITTED` with its 1,014-file/1,146,324-row evidence
and unresolved PIT, identity, duplicate-source, and CA gates.

No code, source data, candidate formula, packet bytes, target, outcome,
canonical, capture, cloud, telemetry, or production state was modified. The
complete independent-review evidence is recorded in
`2026-09-20_ALPHA_CONTROL_AND_SURFACE_REDTEAM_RESULT_V1.md`.
