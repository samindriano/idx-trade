# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V3-FINAL-STRUCTURE-LITE-LATE-DEV-CONFIRM
model_used: Codex Luna xhigh orchestra profile
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `bf9f7d311aacd08884d59abd0e3a16942add26cf`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: final branch HEAD reported by Codex after documentation push

## Scope

Executed exactly the authorized one-shot final V3 late-development confirmation
from `coordination/handoffs/IDX-RANKING-V3-FINAL-STRUCTURE-LITE-LATE-DEV-RUN.md`.
The existing V3-B Structure-Lite definition, model semantics, gates and
ordinal accounting were unchanged. The atomic run consumed V2F5 and V2F6 only.

## Validation

- full pytest: `319 passed, 0 failed, 3 warnings, 14.42s`;
- late cache: `286,453` rows, `737` tickers, sessions `20..1224`;
- cache SHA: `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA: `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- cache status: `RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN`;
- control equivalence: PASS on `59,491` rows, max score/metric diffs `0.0`;
- absolute gate: PASS;
- paired gate: PASS;
- final verdict: `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`;
- final architecture: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- cumulative architecture-candidate count remains `9`; no new ordinal.

Metrics:

- V2F5 control / Structure-Lite PR delta: `0.0260816692 / 0.0277478118`;
- V2F6 control / Structure-Lite PR delta: `0.0186432663 / 0.0321593843`;
- paired PR improvement: V2F5 `+0.0016661426`, V2F6 `+0.0135161180`;
- median/worst paired PR: `+0.0075911303 / +0.0016661426`;
- median ROC change: `+0.0072411913`;
- paired Q5-Q1 change: V2F5 `+0.0215800814`, V2F6 `+0.0038483525`;
- median/worst Q5-Q1 change: `+0.0127142169 / +0.0038483525`;
- top-decile lift changes: V2F5 `+0.0164814105`, V2F6 `-0.0043770061`;
- top-decile Jaccard: V2F5 `0.3335037056`, V2F6 `0.3631662689`.

## Runtime artifacts

Prepare directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_prepare_20260810_001`

Run directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_run_20260810_001`

Main run hashes:

- summary `79f01660a2ef98b6de3ef38905adab7109a04afa78cb4969d323f92b618ff52e`;
- control equivalence `d48fd50b7eeddd0cfcb1d6f107023a635fb709b03fe18a290da44e2cdf28d483`;
- metrics `5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25`;
- predictions `64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b`;
- paired `51fa9d893b32597ab30c67961811b42f107350587a30e726ec5bf8ec2e188c04`;
- overlap `c6f77e3e19761aba43d1325d639c6eea62d9b7450ded5044a1b0c00d8773e530`;
- runtime `b7f1f9725da55e25a4779bb1f95c3b9724e0ff6484011c703cde51c98ab18723`;
- total runtime `26.6248833s`.

## Decisions and boundaries

V3-B is now late-development confirmed as the final historical-development
architecture. This does not authorize fresh-forward validation or downstream
production/trading stages.

- V2F5/V2F6 consumed exactly once;
- sessions `1225+` not materialized/scored;
- V3-D remains blocked/unviewed;
- fresh-forward outcomes untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` not written;
- no forward validation, calibration, Stage 6, `IDX-VAL-002`, execution/PnL,
  paper/live, integration, or main merge.

## Recommended next action

ChatGPT should review the checkpoint and accept/reject the historical result.
Do not automatically start forward validation or calibration.
