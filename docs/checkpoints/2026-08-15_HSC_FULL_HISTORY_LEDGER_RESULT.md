# HSC Full-History Ledger V1 — bounded result

Date: 2026-08-15 (Asia/Jakarta)  
Branch: `data/idx-hsc-full-history-ledger-v1`  
Prepared HEAD: `52a62c4913402ad5d6908c6c06f2a0f738a7ba80`  
Parent source: `data/idx-ownership-hsc-source-remediation-v1@ba03d0d0ebe89f9219a2ac885af758b5e51c68ef`

## Verdict

`HSC_FULL_HISTORY_LEDGER_READY_FOR_OWNERSHIP_CONCENTRATION_CONTRACT`

This is a bounded official event-ledger result through the cutoff
2026-08-15. It does not authorize free-float/effective-supply inference, HHI,
daily forward filling, Foreign Flow integration, model work, or outcome access.

## Recovery and provenance

The accepted parent transport was reused: preserved official IDX
`GetAnnouncement` metadata locators plus canonical IDX `StaticData` paths,
retrieved through the working official `www.idx.id` host. No announcement
number or path was guessed.

External artifact root:

`D:\Documents\Project\idx-hsc-full-history-ledger-20260815-v1`

Final manifest SHA-256:

`230fec0544fb7464e63008ee080fda0c8082049626529f0a565376601416b55d`

The manifest contains 8 preserved official metadata JSON files, 118 official
PDFs (main publication plus attachment for 59 announcement records), and all
normalized/audit artifact hashes. Twenty-four PDFs were reused from the
accepted parent capture; 94 were newly fetched from official StaticData.
There were no failed official PDF fetches.

## Exact chronology

The authoritative row-level chronology is `normalized/hsc_events.csv` and its
JSON equivalent in the external root. It contains 59 events:

- 2026-04-02: AGII, BREN, DSSA, IFSH, LUCY, MGLV, RLCO, ROCK, SOTS.
- 2026-05-08: WBSA.
- 2026-05-30: TCPI.
- 2026-06-02: MGRO original, then MGRO `KOREKSI`.
- 2026-06-04: SATU.
- 2026-07-01: DGWG.
- 2026-07-02: HATM.
- 2026-07-03: LUCY `HSC_REMOVED`.
- 2026-07-15: 37 revised-methodology additions: POLU, BBHI, BNLI,
  BTPN, BYAN, BINA, BELI, YUPI, PGUN, KING, FITT, CMNT, DCII, BNII,
  ALII, CMNP, MEGA, PRAY, STTP, LIFE, RISE, FAPA, KONI, SMAR, MPRO,
  ELPI, SILO, MCOL, BBSI, MORA, SRAJ, MKPI, MLPT, SOHO, DNET, GEMS,
  FILM; plus the official MEGA correction.
- 2026-08-05: AGAR, ALKA, BKDP.
- 2026-08-11: BAJA.

Event counts are 56 `ORIGINAL`, 2 `CORRECTION`, and 1 `REMOVAL`.
Methodology counts are 17 `HSC_2026_INITIAL` and 42
`HSC_2026_PRICE_IMPACT_REVISION`. All active rows have explicit concentration
percentages and official attachment SHA-256 values.

Two source-format anomalies were retained in the audit rather than hidden:
CMNP's attachment prints `KSEI- 5024` and is normalized to the canonical
`KSEI-5024/DIR/0726`; BAJA contains a `KEI-5817` typo alongside the canonical
`KSEI-5817/DIR/0826`. Both are recorded in `audit/event_parse_audit.json`.

## Replay reconciliation

The strict loader `load_hsc_events_csv()` and `replay_hsc_events()` were used.
All nine checkpoints passed:

| Checkpoint | Active count |
|---|---:|
| Initial April cohort | 9 |
| After WBSA | 10 |
| After TCPI | 11 |
| After MGRO correction | 12 |
| After SATU | 13 |
| After DGWG + HATM | 15 |
| After LUCY removal | 14 |
| After July expansion | 51 |
| Final cutoff 2026-08-15 | 55 |

The July target file reconciles exactly to 51 tickers. The final bounded
current set is the July 51 plus AGAR, ALKA, BKDP, and BAJA; no later RSC or
correction was admitted from the preserved official metadata capture through
the cutoff. The complete final ticker set is stored and hash-pinned in
`official_current_target_20260815.csv`.

The cutoff search evidence covers the preserved official IDX metadata window
2026-08-01 through 2026-08-16, with HSC records observed through 2026-08-11.
Absence after BAJA is reported only within that bounded evidence window; no
unbounded absence claim is made.

## Validation

- Focused HSC tests: `16 passed, 0 failed`.
- Full repository pytest: `105 passed, 1 failed`.
- The only failure is the known unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  Current storage correctly surfaces independent `raw_close` and
  `vendor_adj_close` conflicts, while the old test still expects one. No
  storage change was made.
- `git diff --check`: pass.

No models, features, daily panels, Foreign Flow, Financial PIT, Corporate
Actions, O2, TradingView, labels, or protected outcomes were accessed.
