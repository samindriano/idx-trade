# IDX-Trade Alpha Research — ChatGPT Handoff V2

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Branch: `codex/alpha-available-data-20260919`
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
Evidence baseline commit: `126614b6e8d075d9df463ffa741c9170fb5f87e3`
External staging root: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Ringkasan satu kalimat

Riset **belum berhenti total**: pre-admission, outcome-blind research masih
boleh dilanjutkan di lane ini, tetapi historical predictive evaluation belum
boleh dibuka karena Data QA belum mengadmit population completeness, PIT/as-of,
identity, corporate-action basis, revision/vintage, serta H5/H10.

## Isolasi dan batas yang sudah dijaga

- Semua pekerjaan dilakukan di branch/worktree terpisah; `origin/main` tidak
  diubah.
- Canonical/incumbent model, production artifact, capture/cloud/R2, scheduler,
  telemetry, counter, provider/network, protected target/label, dan forward
  outcome tidak disentuh atau dibuka.
- Tidak ada IC, ICIR, OOS, target-ranked spread, incumbent comparison,
  superiority claim, refit, weight optimization, atau model promotion.
- Derived artifacts disimpan di external staging root di atas; tidak ada
  overwrite terhadap dataset aktif.

## Status keputusan saat ini

| Item | Status aman | Makna |
|---|---|---|
| C1 residual reversal 5 sesi | `FUTURE_RESEARCH` | Struktur tersedia, tetapi price-basis/PIT/predictive belum admitted. |
| C2 participation confirmation 5 sesi | `FUTURE_RESEARCH` | Coverage struktural paling lengkap; bukan bukti predictive. |
| C3 financial quality/growth | `BLOCKED` | YoY/financial/PIT support terlalu sparse untuk evaluasi ilmiah. |
| C4 path-efficiency reversal 20 sesi | `FUTURE_RESEARCH / ECONOMIC_CAUTION` | Turnover rendah tidak cukup; liquidity/value proxy lebih lemah. |
| H-LIQ-01 | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` | Hipotesis mekanistik; belum dibuat sebagai C5. |
| C1/C2/C4 combinations | `STRUCTURAL FUTURE HYPOTHESES` | Tidak ada ID baru dan belum ada bukti incremental information. |
| `READY`, `RESEARCH_SURVIVOR`, “lebih baik dari incumbent” | `NOT ALLOWED` | Belum ada target admission dan predictive evidence. |

## Bukti struktural utama

Corrected decision universe: **310,761 eligible rows / 711 ticker**.

| ID | Finite eligible support | Top-30 turnover | Base friction burden |
|---|---:|---:|---:|
| C1 | 295,243 / 95.0065% | 42.15% | 25.29 bps/NAV |
| C2 | 310,761 / 100.0000% | 32.91% | 19.75 bps/NAV |
| C3 | 30,994 / 9.9736%; 278 usable dates | 10.93% | 6.56 bps/NAV |
| C4 | 310,323 / 99.8591% | 23.70% | 14.22 bps/NAV |

Base friction is a frozen structural assumption, not realized P&L.

Completed bounded work includes prior-alpha archaeology, corrected causal
feature construction, eligibility/session/ranking/firewall checks, coverage and
missingness, turnover/persistence, concentration, proxy economics, horizon and
normalization stress, C3 capability diagnosis, H-LIQ novelty work, four fixed
combinations, corporate-action/price-basis forensic work, and three Phase-Q
read-only red-team reviews.

## Important findings and limitations

1. Causal/PIT/identity/CA review passed the bounded structural checks: prior-only
   shifts, future-row mutation isolation, 981,940/981,940 key match, zero
   duplicate keys, date/mask/rank bounds, and source-hash consistency.
2. That does **not** prove historical PIT/as-of correctness, issuer continuity,
   survivorship/population completeness, revision/vintage correctness, or global
   corporate-action authority.
3. The known HLC overlay has 1,657/1,657 matches and replay stability. There
   remain 188 unresolved scale rows. A non-admitted counterfactual substitution
   changes C1 ranks on 10.617% of compared rows with minimum Top-30 overlap
   36.667%; C2 is 2.894% / 83.333%; C4 is 3.203% / 86.667%.
4. H-LIQ-01 is structurally distinct from C2 on average but dependence rises in
   the top-value bucket; it remains novelty/economic caution, not C5.
5. C1+C4 has the lowest tested combination turnover at 34.85%, but the pair is
   highly correlated structurally (daily Spearman about 0.8499). Low turnover is
   not incremental alpha.

## Capacity stress result

The latest read-only capacity audit used the guarded feature set and frozen
`regular_market_value` as a proxy over 600 sessions and 18,000 Top-30 slots per
candidate. It did **not** use ADV, traded value, spread, queue depth, fill
probability, or executable capacity.

- C1: 546 unique names; top-10 aggregate-value share 50.1230%; effective names
  25.403; aggregate entry/exit value ratio 1.06802.
- C2: 556 unique names; top-10 aggregate-value share 36.6950%; effective names
  47.699; aggregate entry/exit value ratio 1.41567.
- C4: 517 unique names; top-10 aggregate-value share 48.5595%; effective names
  23.157; aggregate entry/exit value ratio 1.03554.

This sharpens implementation caution but does not change C1/C2/C4 disposition.
Real historical capacity remains `UNKNOWN/BLOCKED`.

## Audit/tooling status

- Stage-A lineage is pinned. The guarded feature hash is
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`.
- Current staged consumers were audited: the guarded hash is used by the
  current C1/C2/C4, CA, capacity, combination, H-LIQ, identity, firewall,
  economics, structural-lab, and robustness artifacts. Old hashes are confined
  to historical staging artifacts and are not silently treated as current.
- The new C1/C2/C4 adversarial verifier independently replays source data and
  passes `PASS_INDEPENDENT_STRUCTURAL_REPLAY`.
- The old structural-lab verifier was envelope-only. It has now been
  superseded for current evidence by `research/verify_alpha_structural_lab_v2.py`,
  which independently recomputes the full candidate and pairwise metric maps
  and passes `PASS_INDEPENDENT_SOURCE_REPLAY` with zero mismatches.
- Access flags in JSON artifacts are self-attested metadata, not process-level
  proof of protected-data non-access.

## What can continue safely

1. Add/enforce feature, manifest, code, source, and repository-head hash binding
   on every future research-only output.
2. Continue bounded CA/issuer-basis, PIT source-admission, and capacity audits
   only from data already in scope.
3. Resolve the remaining H-LIQ novelty/capacity and 188-row CA exposure
   questions without protected outcomes.
4. Keep the ledger, phase matrix, re-entry queue, and evidence pointers in sync.

## What remains prohibited

Do not open H5/H10 or any protected forward outcome; do not run OOS/IC/ICIR;
do not compare candidates to the incumbent; do not scrape/probe new providers
to chase a result; do not modify canonical/protected data; do not reset/archive
telemetry; and do not promote a model.

## Re-entry condition

Only after an independent Data QA admission artifact covers population
completeness, PIT/as-of, identity/calendar, corporate-action basis,
revision/vintage, and H5/H10 may the frozen C1-C4 packet be evaluated once on
common support. Until then, the safe conclusion is: **substantial structural
progress, no predictive winner yet**.

## Primary evidence

- `2026-09-19_ALPHA_RESEARCH_LATEST_READIN_V1.md`
- `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_STRUCTURAL_LAB_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_STAGE_A_LINEAGE_RESULT_V1.md`
- `2026-09-19_ALPHA_STAGE_A_CONSUMER_AUDIT_V1.md`
- `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
- `2026-09-19_ALPHA_CAPACITY_STRESS_RESULT_V1.md`
- `2026-09-19_ALPHA_C1234_ADVERSARIAL_RESULT_V1.md`
