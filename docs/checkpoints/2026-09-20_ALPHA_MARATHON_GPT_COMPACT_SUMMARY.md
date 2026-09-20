# IDX-Trade Alpha Available-Data Marathon — Compact GPT Handoff

For the complete current-plus-historical archive, including the later public
EOD/IPO source-coverage result, read
`2026-09-20_ALPHA_MARATHON_ALL_FINDINGS_ARCHIVE_V1.md`. This file is only the
short snapshot.

**Snapshot:** 2026-09-20  
**Status:** `NO-GO / PRE-ADMISSION / OUTCOME-BLIND / PREDICTIVE STAGE BLOCKED`  
**Goal:** mempelajari alpha/model dan seluruh bukti data yang tersedia, secara PIT-safe dan fail-closed, tanpa memaksakan kandidat/model baru.

## Kesimpulan satu paragraf

Marathon ini berhasil memetakan dan menguji ulang sebagian besar permukaan riset alpha yang tersedia secara lokal, tetapi **tidak membuktikan model yang lebih baik**, tidak menghasilkan kandidat siap-admission, dan tidak membuka hasil prediktif. C1, C2, dan C4 cukup reproducible secara mekanis untuk riset lanjutan; C3 tersumbat oleh dukungan financial/PIT yang jarang dan terlambat. Validasi yang tersisa bernilai tinggi hampir semuanya membutuhkan authority/data yang tidak tersedia secara lokal: universe historis lengkap, corporate-action basis dan knowledge-time, vintage/revision publication data, serta execution/capacity data. Goal dihentikan secara natural karena mengulang analisis lokal tidak lagi memberi bukti baru yang dapat dipercaya.

## Batasan yang dijaga

- Semua pekerjaan berada di lane terpisah: worktree `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`, branch `codex/alpha-available-data-20260919`.
- Baseline `58f094b8`; snapshot terakhir `f9a7f9c7`.
- Tidak menyentuh incumbent/model-alpha, production/canonical data, cloud/provider/Zapi, capture, telemetry, scheduler, forward-monitoring, counters, atau protected target/outcome.
- Tidak membaca atau menggunakan H5/H10, forward returns, IC/Rank-IC/ICIR, OOS/PnL, maupun predictive result incumbent.
- Tidak membuat C5, tidak melakukan fit/optimization/selection untuk klaim model baru, dan tidak melakukan retry terhadap eksperimen yang sudah ditutup.

## Apa yang berhasil direproduksi

Konstruksi Stage-A awal sempat ditemukan salah pada arah beta denominator, urutan mask/rank, semantik rolling official-session, dan guard knowledge-time financial. Setelah dikoreksi, independent constructor replay cocok dengan frozen panel pada:

- 981.940 panel keys;
- eligibility masks;
- component scores;
- average-tie ranks;
- zero mismatch pada replay yang diuji.

Ini hanya membuktikan **reproducibility implementasi**, bukan kelengkapan PIT population, kebenaran corporate-action basis, capacity, atau predictive validity.

Frozen inputs:

- features: 981.940 rows, SHA-256 `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`;
- panel: SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- official sessions: 1.260, SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

## Candidate surface yang dipetakan

| Kandidat | Dukungan finite | Top-30 turnover kira-kira | Status |
|---|---:|---:|---|
| C1 residual reversal | 295.243 rows; 95,0065% | 42,15% | struktural; price-basis-sensitive; future research only |
| C2 participation confirmation | 310.761 rows; 100% current support | 32,91% | struktural; interaksi/tail cautions; future only |
| C3 financial quality/growth | 30.994 rows; 9,9736% | tidak layak dibandingkan | blocked oleh financial PIT/support |
| C4 path-efficiency reversal | 310.323 rows; 99,8591% | 23,70% | struktural; normalizer/overlap cautions; future only |

Empat-way finite intersection hanya 30.861 rows (9,9308% current eligible rows), didominasi C3. Ini bukan common-support evidence untuk admission.

## Eligibility dan authority

Protokol tertulis menyebut trailing 60 official sessions dengan minimum 20 finite observations, sementara implementasi memakai `min_periods=60`. Tidak ada authority yang mengikat salah satunya.

- Perbedaan policy: 38.004 rows dan 619 ticker, muncul di setiap tahun.
- Top-30 overlap lintas policy:
  - C1: 96,52% universe overlap; 32,52% exact daily;
  - C2: 100%; exact daily 100% (fitur sendiri sudah 60-session warmup);
  - C3: 94,05%; exact daily 22,30%;
  - C4: 91,71%; exact daily 12,74%; average symmetric difference 4,98 names.
- Tidak ada policy yang dipilih/diotorisasi: `POLICY_AUTHORITY_MISSING`.

## Population, identity, tradability

Tradability anchor berisi 1.104.064 rows / 980 tickers: `ACTIVE` 982.398 rows / 946 ticker dan `NO_TRADE` 121.666 rows / 617 ticker. Panel 981.940 rows / 945 ticker overlap seluruh ACTIVE keys dan tidak memuat NO_TRADE. CNTX adalah satu-satunya ticker ACTIVE yang tidak ada di panel (458 rows, 2021-04-29 sampai 2024-08-01).

Ini hanya membuktikan overlap dengan anchor yang ada; tidak membuktikan historical population completeness, survivorship-free universe, delisting/relisting, ticker reuse, atau issuer continuity. Status ACTIVE/NO_TRADE berosilasi: 583/980 ticker berubah status, median 10 transitions, q95 212,9, maksimum 374. Tanpa identity/publication authority, tidak boleh dipetakan menjadi event lifecycle.

## Temuan C1/C4 dan C2

- Transform rank/z/robust-z yang monotonic redundant secara urutan.
- C1/C4 numerator-only within-candidate overlap: 63,75% / 62,22%; stored cross-candidate overlap 35,80%, numerator-only 36,82%.
- Horizon bridge:
  - raw `-ret_5` vs raw `-ret_20`: Top-30 overlap 37,96%, mean daily Spearman 0,4327;
  - C1 raw vs residual: overlap 84,55%, Spearman 0,9338;
  - stored C1 vs residual numerator: overlap 63,75%, Spearman 0,9548;
  - stored C4 vs raw `-ret_20`: overlap 62,22%, Spearman 0,9370.
- Shared membership bukan bukti bahwa C1/C4 sekadar satu horizon. Beta residualization dan normalizer materially mengubah membership; ini tetap struktural.
- C2 = `ret_5 * log(abnormal turnover)`. Top-30 pooled slots: 68,68% positive-return/high-activity dan 31,32% negative-return/low-activity. 2025 = 78,80/21,20; 2026 partial = 59,90/40,10. Ini anatomi komposisi, bukan bukti regime-return.

## Turnover, breadth, economics

- Finite support rata-rata C1/C2/C4: 99,54% / 100,00% / 99,85%.
- Korelasi count-vs-turnover: 0,133 / 0,061 / 0,175.
- C3 finite support rata-rata 35,96%; rho -0,372 overall dan -0,711 pada 2026 partial, tetapi causation belum terbukti.
- Fixed combinations, persistence, concentration/HHI, quartiles, friction proxies, dan C1+C4 equal-weight (turnover terendah sekitar 34,85%) hanya diagnosis struktural. Tidak ada weight optimization.
- Historical executable ADV, spread, queue, fill, market impact, dan capacity tidak tersedia.

## Red-team / hypothesis results

- H-LIQ-01: aktivitas variability adalah surface berbeda secara struktural, tetapi nilai/partisipasi dan temporal economics tidak stabil; retry pada surface yang sama ditutup.
- H-VOL-01: volatility compression dapat diukur secara struktural, tetapi horizon- dan corporate-action-sensitive; future only.
- H-EXC-01: raw excursion punya tails kira-kira -16,2/5,0 dan churn tinggi; representation gagal sesuai definisinya, tanpa post-hoc rescue.
- H-EXC-02: bounded excursion numerically stable, tetapi tetap high-churn dan horizon-sensitive; future only.
- Temuan historis V2/V3/V4/V4-X1 diklasifikasikan ke implementation, source/PIT, sparse, redundancy, economics, semantic, atau replay-gap; replay lama yang tidak lengkap tidak dipromosikan menjadi bukti.

## Corporate action, basis, dan source blockers

Local census mencakup official sessions, panel/anchors, financial, foreign flow, Dataset-Saham-IDX, listing/delisting, free-float/ownership, broker/margin, historical Open, TradingView, dan Investing snapshots. Tidak ada sumber lokal yang sekaligus memiliki PIT completeness, publication/revision time, identity continuity, corporate-action mechanics, dan execution semantics.

Registered basis stress:

- HLC overlay: 1.657 rows;
- unresolved non-stable-scale residual: 188 disjoint rows;
- stressed basis mengubah 547 scores dan 8.876 ranks;
- minimum Top-30 overlap under stress: 86,6667%;
- tidak ada price yang diam-diam di-rescale atau di-repair.

Prioritas authority/data yang hilang:

1. PIT-complete historical universe dengan delisted/relisted/ticker reuse dan issuer/ISIN continuity;
2. event-complete corporate-action basis dengan effective time dan knowledge time;
3. publication/revision/vintage metadata untuk financial/flow;
4. historical executable ADV/spread/queue/fill/capacity;
5. baru kemudian common-support H5/H10 adjudication.

## Artefact, audit, dan verification terakhir

Durable evidence utama:

- `research_knowledge/manifest.json`
- `research_knowledge/experiment_registry.jsonl`
- `research_knowledge/findings_index.jsonl`
- `research_knowledge/no_retry_registry.jsonl`
- `research_knowledge/knowledge_synthesis.md`
- `research_knowledge/research_frontier.md`
- `research_knowledge/open_questions.md`
- `research_knowledge/research_journal.md`
- `docs/checkpoints/2026-09-20_ALPHA_MARATHON_AUDIT_HANDOFF_V6.md`

Latest verification:

- knowledge-base verifier: `PASS`; 53 experiments, 46 findings, 16 no-retry, 17 source-capability records;
- data-authority packet verifier: `PASS`; status tetap blocked, no provider/cloud/canonical access, no ready candidate, policy missing;
- protected-field scan: `PASS`; protected payloads persisted: `false`;
- focused tests: 22 passed;
- `git diff --check`: passed;
- worktree clean after commit `f9a7f9c7`.

Audit caveat: verifier PASS hanya membuktikan hash/path/schema/denylist/process assertions yang diperiksa; bukan semantic proof, PIT proof, atau predictive proof. Enam stale evidence references telah diperbaiki dan delapan unavailable historical references telah diklasifikasikan.

## Open questions dan stopping point

Open questions utama: `Q-001` policy authority, `Q-003` PIT population, `Q-004` corporate-action basis, `Q-005` revisions/publication, `Q-006` capacity, `Q-007` common support setelah policy/data tersedia, `Q-009` freshness contract, `Q-014` nested schema/version adoption, dan `Q-023` horizon bridge.

`research_knowledge/research_frontier.md` menyatakan local outcome-blind surface sudah substantially exhausted. Sisa pertanyaan bernilai tinggi memerlukan authority/data eksternal atau independent review; mengulang eksperimen lokal akan redundant dan tidak mengubah verdict.

## Handoff decision

Jangan menyebut hasil ini sebagai alpha baru, model menang, OOS improvement, atau admission. Jika GPT melanjutkan, langkah aman berikutnya adalah **review evidence dan merancang gate/ingestion contract untuk authority yang hilang**, tetap di lane terpisah. Tidak ada live model smoke yang justified sebelum policy, PIT universe, CA basis, publication vintage, dan execution data tersedia.

**Goal status:** complete by natural stopping point; predictive stage remains blocked.
