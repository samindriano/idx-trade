# Handoff

from: Codex/Clean-V2-Open-Alpha-Prereg
to: ChatGPT/Open-Alpha-Research
task_id: IDX-V2-OPEN-ALPHA-PREREG
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `504c51bad25517bf496ee14856be704935d0f5d4`
branch: `research/idx-v2-open-alpha-prereg-v1`
scope: One authorized atomic historical comparison of CONTROL, V2.1, and V2.2 on the frozen common-support population; stop after result artifacts for independent review.
head_commit: to be set after the result checkpoint commit and normal fast-forward push

## Files changed

- `src/idx_trade/open_alpha_prereg.py`
- `src/idx_trade/open_alpha_historical.py`
- `tests/test_open_alpha_prereg.py`
- `tests/test_open_alpha_historical.py`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_PREREGISTRATION.md`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_OUTCOME_BLIND_AUDIT_RUNTIME.md`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_PREREG_REMEDIATION.md`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_HISTORICAL_RUN.md`
- `coordination/handoffs/IDX-V2-OPEN-ALPHA-PREREG.md`

## Findings

- clean V2 source: 292,631 rows / 737 tickers;
- one exact common support for all three eventual models: **277,244 rows / 729 tickers**;
- common-support key SHA: `e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`;
- exclusions: 12,589 current Open unavailable, 1,876 current flat range, 922 previous ACTIVE flat range;
- zero duplicate keys, listing invalid rows, current non-ACTIVE rows, calendar unresolved rows, and regular suspension conflicts;
- previous ACTIVE gap min/median/max: 1 / 1 / 39 sessions;
- Open-related maximum absolute correlation: 0.582885;
- separate feature hashes: CONTROL 25 `1107bf6a`, V2.1 28 `9bf62fd9`, V2.2 28 `228c3afa`;
- 31-feature all-six-Open combination is explicitly prohibited;
- survivor gate and both-survive head-to-head winner rule are executable and frozen;
- previous ancestor checks: listing/session/ACTIVE/suspension violations all zero;
- joined `signal_session_index == panel_session_index` violations: zero;
- strict external boolean parsing rejects unknown values and treats `"False"` as false;
- future-row causal invariance: true;
- historical run used only the three separate 25/28/28 feature identities; the 31-feature combined model remained prohibited;
- exact H10 labels joined to all 277,244 common-support rows with no identity gaps;
- six frozen folds produced 18 fold-local model artifacts and same-fold prediction identities matched exactly;
- V2.1 vs CONTROL gate: median PR delta `+0.00007359`, q25 `-0.00250461`, 3 positive folds, FAIL;
- V2.2 vs CONTROL gate: median PR delta `+0.00029955`, q25 `-0.00240718`, 3 positive folds, FAIL;
- both challengers fail the frozen q25 rule; deterministic verdict `RETAIN_CLEAN_V2`;
- no provider call, fresh-forward outcome access, canonical model/counter change, final refit, tuning, or promotion.

## Decisions made

- V2 remains the clean parent.
- V3-B remains closed/failed; old O2 remains orphaned diagnostic only.
- Flat current/previous ranges fail closed; no synthetic fill or feature rescue.
- The candidate population is measured from corrected lineage and is not copied from the prior 278,168-row artifact.
- The remediation rerun preserved the exact 277,244-row population and key SHA.
- The one authorized historical comparison is complete and remains historical-development evidence only.
- Clean V2 is retained; V2.1 and V2.2 are not promoted and no downstream run is authorized by this handoff.

## Validation

- focused tests: 12 passed;
- full pytest: 51 passed, 1 pre-existing `test_storage.py` failure unrelated to this lane.
- Remediation runtime artifacts and hashes are in:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_remediation1_retry1`.
- remediation audit summary SHA: `82a7814d1ef52776eef0766005468e9297230e89ba13338776cd6324737cc0fb`;
- remediation artifact manifest SHA: `a9ecc02744e815a6581e053422bfc219affd036205e780ad82e9caf36083c247`.
- historical runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_historical_v1_20260813_001`;
- historical summary SHA: `23d37a6c95cc7ae11f0eca6a745d9077622e809e012dc77b232d0d1adb0e3186`;
- historical predictions SHA: `21bf24d4c9bb8d10775edaaf10175013482fadb1bdd8a09df793b8fec7c68040`;
- historical artifact manifest SHA: `f0b8a0a0f15655a3663084a4ecc988320b320f1ec63b5589262ac40e9893f97e`;
- historical artifact count: 28, including 18 fold-local models.

## Blocking risks / review requests

- ChatGPT should independently review the historical metrics, predictions,
  paired gate calculations, and artifact manifest.
- Do not refit, tune, promote, or start any downstream/forward run until review
  is complete. The existing storage-test baseline failure remains separately
  owned and was not changed here.

recommended_next_action: independent ChatGPT review of the one completed historical run; no automatic next experiment.
