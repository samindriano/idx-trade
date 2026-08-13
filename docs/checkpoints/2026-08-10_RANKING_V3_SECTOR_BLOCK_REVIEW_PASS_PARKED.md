# Ranking V3-D Sector-Relative — PIT Data-Gate Block Review

Date: 2026-08-10 (Asia/Jakarta)

Status: **REVIEW PASS — V3-D PARKED BLOCKED / OUTCOMES UNCONSUMED**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

Reviewed blocked-run HEAD: `1f005e39eaa4403d268112d2113843b403c275c9`

## Review decision

The `BLOCKED_PIT_SECTOR_HISTORY` decision is methodologically correct under the frozen V3-D contract.

The local operator correctly refused to construct historical sector intervals from current-sector labels or to invent `effective_from`, `effective_to_exclusive`, or `available_at` values from monthly report labels. No V3-D outcome was viewed, so ordinals 008/009 remain unconsumed and the cumulative evaluated V3 denominator remains 7.

V3-D is therefore **parked**, not killed. It may be reopened only if a defensible PIT sector-history source chain is later obtained.

## Validation accepted

- final branch/remote reported clean and synchronized;
- full repository pytest: `290 passed, 0 failed, 3 warnings` in `26.2 s`;
- no V3-D cache or manifest was created;
- no F1-F4 V3-D performance metrics were computed;
- V2F5/V2F6 remained sealed;
- reserved post-2026-07-31 V2 fresh-forward outcomes remained untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written.

## Additional source lead found during independent review

A later independent public-source check found one useful lead that does **not** by itself clear the gate:

1. the official IDX index page explicitly points to the original `Pengumuman Klasifikasi dan Panduan IDX-IC` and `Pengumuman Indeks Sektoral IDX-IC`;
2. the official page states the IDX-IC sector indices launched on 2021-01-25 and gives evaluation/effective-day conventions for sector indices;
3. publicly indexed copies of BEI announcement `Peng-00012/BEI.POP/01-2021` dated 2021-01-21 contain the initial sector-index constituent list.

This is sufficient to justify keeping a future recovery lane open, but not sufficient for present V3-D authorization. A complete ticker-level change history through the development window, including new listings/reclassifications and defensible publication/availability semantics, has not been established from immutable first-party material.

Do not lower the PIT standard merely because the initial 2021 classification can be reconstructed.

## Controlling V3-D state

- primary candidate remains exact V2 25 features + frozen six PIT sector-relative features;
- post-V3-C NORMAL/STRESS robustness amendment remains frozen;
- V3-D outcome authorization remains absent;
- ordinals 008/009 remain `result_viewed=false`;
- cumulative evaluated V3 count remains `7`.

## Future V3-D unblock routes

Acceptable future routes include:

- official BEI/IDX historical classification or sector-index constituent announcements with explicit publication and effective dates;
- immutable IDX Statistics/Factbook/TICMI-delivered historical files if they establish the required ticker/date semantics and source bytes can be hashed;
- another first-party archival source that proves the full interval chain without current-label backfill.

Any future attempt must re-run the PIT validator and outcome-independent cache/coverage gate before scoring.

## Roadmap decision

Do not stall the V3 ladder on this data dependency. Proceed to **V3-E TRUE-RANKING** as the next active Tier-1 hypothesis.

V3-E must remain separately attributable: exact V2 control versus one tightly bounded nonlinear same-date ranking formulation. It must not inherit Structure-Lite merely to make the experiment stronger, and it must not use V3-D sector features while the PIT gate is blocked.

V2F5/V2F6 remain sealed until the hypothesis ladder and at most one preregistered integration experiment are complete.
