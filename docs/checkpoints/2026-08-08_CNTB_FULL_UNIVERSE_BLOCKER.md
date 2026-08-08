# CNTB full-universe blocker — 2026-08-08

## Checkpoint

Window: `2026-06-02 -> 2026-07-31`

Full common-stock gate before this fix:

- discovered before scope: 964 securities;
- CNTX excluded as `NON_COMMON_SHARE`;
- required common-stock universe: 963;
- passed: 962;
- failed: CNTB only;
- UNKNOWN sessions: CNTB on 2026-07-30 and 2026-07-31;
- missing ACTIVE prices: 0.

## Symptom

Targeted official Stock Summary fetches for 2026-07-30 and 2026-07-31 did not contain CNTB. The existing contract correctly refused to convert Stock Summary row absence into `NO_TRADE`, leaving both sessions `UNKNOWN`.

## Diagnosis

This is not a reason to weaken Stock Summary semantics. A separate official legal-state source exists.

IDX announcement `Peng-SPT-00006/BEI.PP1/08-2024`, dated 2024-08-07, explicitly suspended PT Century Textile Industry Tbk securities `CNTX` and `CNTB` in **all markets**, effective from Session I on 2024-08-07, in connection with the company's voluntary-delisting/go-private process.

Official document reference:

`https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202408/1c38a14af6_65c8eafbaf.pdf`

A later IDX announcement `Peng-UPT-00004/BEI.PP1/03-2025` opened the security **only in the Negotiated Market** for a crossing transaction on 2025-03-26 and stated that the security would be suspended again in all markets after the transaction. That event does not reopen the Regular Market.

Therefore the daily/EOD research venue (`REGULAR`) remains explicitly suspended across the 2026 certification window.

## Fix

Do not infer state from Stock Summary row absence.

Instead:

1. add a narrowly curated official-legal-state registry;
2. require each curated row to retain `IDX_EXCHANGE_ANNOUNCEMENT` source identity and explicit source reference;
3. canonicalize and conflict-check curated intervals through the same interval contract as reconstructed events;
4. record CNTB `REGULAR/SUSPENDED` from 2024-08-07 onward;
5. lock 2026-07-30 and 2026-07-31 with regression tests.

Relevant files:

- `src/idx_trade/curated_tradability.py`
- `config/curated_tradability_intervals.csv`
- `tests/test_curated_tradability.py`

## Permanent lesson

Source layers answer different questions:

- Stock Summary row presence/metrics: direct session execution evidence;
- legal suspension announcement: explicit exchange legal state.

When direct execution evidence is absent but authoritative legal state exists, use the legal-state evidence. Never turn provider/source row absence into a guessed state merely to close a gate.

## Next action

Merge the curated official interval into the existing reconstructed tradability intervals and rerun only the existing 43-session full-universe gate. No broad data refetch is required.

If this removes the final CNTB UNKNOWN sessions and no new blocker appears, materialize/freeze the 43-session certified snapshot and proceed to the 126-session history-expansion checkpoint.
