# IDX-Trade Alpha Research — Latest Read-In V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`  
HEAD at this checkpoint: `0a9bbbb9efab2ee7178e7e59ae92bdc04d16d137`

## Jawaban singkat

Riset **belum berhenti total**. Yang masih diblokir adalah tahap historical
predictive: membuka H5/H10, menghitung IC/ICIR/OOS, membandingkan dengan
incumbent, dan menetapkan model survivor. Data QA canonical masih `BLOCKED`
karena population completeness dan historical-as-of authority belum diakui.

Sebaliknya, pekerjaan outcome-blind yang aman sudah menghasilkan cukup banyak
bukti struktural. Tiga red-team read-only terbaru selesai dan semuanya
berujung `NO-GO` untuk menaikkan status kandidat menjadi `READY` atau membuat
klaim model baru lebih baik.

Follow-up Phase Q kemudian memperbaiki verifier, deterministic selection, dan
missing-value handling; detail dengan hash ada di
`2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`.

## Batas lane dan isolasi

- Semua pekerjaan berada di branch/worktree riset terpisah.
- `origin/main` tidak diubah; canonical/incumbent, capture/cloud/R2,
  scheduler, counter, production artifact, dan protected outcome vault tidak
  disentuh atau dibuka.
- Tidak ada target, forward label, provider/network, atau model score incumbent
  yang diakses.
- Derived artifacts tetap berada di external staging root:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Hasil utama sampai sekarang

Universe keputusan terkoreksi: **310.761 eligible rows / 711 ticker**.

| ID | Mekanisme tetap | Support struktural | Top-30 turnover | Base burden | Status |
|---|---|---:|---:|---:|---|
| C1 | residual reversal 5 sesi | 295.243 / 95,0065% | 42,15% | 25,29 bps/NAV | `FUTURE_RESEARCH` |
| C2 | participation confirmation 5 sesi | 310.761 / 100% | 32,91% | 19,75 bps/NAV | `FUTURE_RESEARCH` |
| C3 | financial quality/growth | 30.994 / 9,9736%; 278 tanggal usable | 10,93% | 6,56 bps/NAV | `BLOCKED` |
| C4 | path-efficiency reversal 20 sesi | 310.323 / 99,8591% | 23,70% | 14,22 bps/NAV | `FUTURE_RESEARCH` |

Base burden hanyalah asumsi struktural biaya, bukan realized P&L.

Pekerjaan yang sudah selesai secara bounded/outcome-blind:

1. Rekonstruksi prior alpha, failure taxonomy, dan sumber data.
2. Corrected causal feature construction, eligibility, official-session mask,
   ranking, schema, hash, dan firewall C1/C2/C4.
3. Coverage, missingness, turnover, persistence, concentration, liquidity/value
   proxy, horizon sensitivity, normalization, universe stress, dan friction.
4. C3 capability diagnosis: quality-only lebih luas, tetapi kontrak YoY tetap
   terlalu sparse untuk scientific evaluation.
5. H-LIQ-01 structural/novelty study; **tidak** dibuat sebagai C5.
6. Empat kombinasi equal-weight C1/C2/C4; tidak ada weight optimization dan
   tidak ada kombinasi yang masuk protected four-ID packet.
7. Corporate-action/price-basis follow-up dan tiga red-team read-only.

## Tiga red-team terbaru

### 1. Kausal, PIT, kalender, identity, corporate action

**Yang lolos:** causal code memakai prior-only shifts; mutation pada future row
tidak mengubah score sebelumnya; 981.940/981.940 key cocok; duplicate key nol;
official dates, eligibility mask, rank bounds, dan source hashes konsisten.

**Yang belum terbukti:** historical PIT/as-of/revision, issuer/ISIN continuity,
population completeness/survivorship, dan global corporate-action/price-basis
authority. Security-master interval mapping bukan bukti continuity issuer.

Known HLC overlay **1.657/1.657** cocok dan replay tidak mengubah Top-30.
Namun forensic substitution pada **188 unresolved scale rows** memberi
sensitivity berikut:

| Kandidat | Rank berubah | Minimum Top-30 overlap |
|---|---:|---:|
| C1 | 10,617% | 36,667% |
| C2 | 2,894% | 83,333% |
| C4 | 3,203% | 86,667% |

Ini bukan koreksi data dan bukan hasil predictive; ini peringatan bahwa C1
belum basis-safe. Selain itu, verifier adversarial saat ini masih terlalu
bergantung pada boolean di JSON dan belum sepenuhnya menghitung ulang semua
assertion dari sumber.

### 2. Ekonomi, konsentrasi, likuiditas, fragility

Turnover struktural baseline tetap benar, tetapi **C4 tidak boleh disebut
lebih unggul secara ekonomi hanya karena turnover-nya lebih rendah**. C4
memiliki tilt ke nama/value proxy yang lebih rendah likuiditasnya:

- value Spearman terhadap C2 sekitar `-0,194`;
- low-liquidity Q25 slots C4 `34,46%`, C1 `26,63%`, C2 `21,26%`;
- q10 value proxy C4 sekitar IDR `5.022.700`, lebih rendah dari C1/C2;
- tail concentration C4 top-10 sekitar `11,83%` dan low-liquidity share
  sekitar `39,38%`.

Real ADV, spread, queue, dan capacity historis tetap `UNKNOWN`. Selected
recent-listing exposure juga lebih tinggi daripada eligible baseline dan
otoritas listed-to belum cukup untuk menyimpulkan survivorship.

Red-team juga menemukan risiko tooling: market-state diagnostic memakai
`pct_change()` default, sementara candidate builder memakai
`fill_method=None`; dampak missing-close perlu diaudit sebelum diagnostic itu
dipakai lagi.

### 3. Kombinasi dan H-LIQ novelty

- Equal-weight/boundary policy kombinasi tetap terjaga; tidak ada ID baru.
- C1+C4 turnover struktural terendah di kombinasi yang diuji: `34,85%`.
- Tetapi C1/C4 memiliki hubungan tinggi (daily Spearman sekitar `0,8499`),
  sehingga low turnover belum membuktikan incremental information.
- H-LIQ-01 tetap `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.
  Dependence terhadap komponen turnover C2 meningkat dari sekitar `-0,046`
  di Q1 menjadi `0,468` di Q4; ini structural dependence, bukan bukti
  economic meaning.
- Combination builder dan structural robustness helper kini memakai tie-break
  ticker eksplisit. Replay canonical tidak mengubah set, tetapi row-permutation
  test menunjukkan tie risk nyata pada 52 tanggal C3.
- Metadata hash pada dokumen kombinasi sudah disinkronkan dengan artifact aktual;
  provenance tetap struktural dan tidak menjadi bukti predictive.

### Phase-Q tooling replay

- Verifier lama hanya envelope-level; JSON check maps tidak direcompute.
- Verifier v2 melakukan independent source replay dan lulus
  `PASS_INDEPENDENT_STRUCTURAL_REPLAY`.
- Structural robustness dan structural lab diregenerate setelah deterministic
  tie-break dan `pct_change(fill_method=None)` patch; kedua verifier lulus.
- Default-fill counterfactual sebelumnya mengubah C1 pada 52/600 Top-30 dates,
  sehingga patch dipertahankan walaupun dampak C2/C4 kecil.

## Keputusan status

Tidak ada kandidat yang saat ini boleh diberi label `READY`, `RESEARCH_SURVIVOR`,
atau “lebih baik dari model alpha lama”. Status yang aman:

- **C1:** `FUTURE_RESEARCH`, dengan unresolved price-basis fragility tertinggi.
- **C2:** `FUTURE_RESEARCH`, coverage dan bounded liquidity profile paling baik,
  tetapi belum PIT/predictive admitted.
- **C3:** `BLOCKED` karena support financial/PIT sparse.
- **C4:** `FUTURE_RESEARCH / ECONOMIC_CAUTION`; turnover rendah tidak cukup.
- **H-LIQ-01:** novelty belum selesai dan belum menjadi C5.
- **Combinations:** structural future hypotheses saja; bukan model baru yang
  sudah terbukti incremental.

## Apa yang masih boleh dilanjutkan

Masih boleh dilakukan di lane ini, tetap read-only atau staged-derived:

1. Menambah lineage eksplisit untuk generasi Stage-A yang duplicate/superseded.
2. Melanjutkan bounded corporate-action/issuer-basis, capacity, dan PIT source
   admission audit dari data yang memang sudah ada.
3. Menjaga ledger, phase matrix, dan re-entry queue tetap sinkron.

Yang **belum boleh** dilakukan: membuka target/outcome/incumbent, menjalankan
OOS/IC/ICIR, scraping/provider probe baru untuk mengejar hasil, mengubah
canonical/protected dataset, reset/archive telemetry, atau mempromosikan model.

## Re-entry gate

Jika dan hanya jika Data QA memberikan admission artifact yang terpisah dan
terverifikasi untuk population completeness, PIT/as-of, identity/calendar,
corporate-action basis, revision/vintage, serta H5 dan H10, barulah frozen
C1-C4 packet boleh dievaluasi sekali pada common support. Sampai saat itu,
status di atas tetap berlaku.

## Dokumen detail

- `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
- `2026-09-19_ALPHA_C1234_ADVERSARIAL_RESULT_V1.md`
- `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_NOVELTY_RESULT_V1.md`
- `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_REENTRY_QUEUE_V1.md`

No predictive superiority claim is made.
