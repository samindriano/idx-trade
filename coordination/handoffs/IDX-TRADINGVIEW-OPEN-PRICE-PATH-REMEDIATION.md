# Handoff

from: Codex/TradingView-Open-Price-Path-Remediation
to: ChatGPT independent review
task_id: IDX-TRADINGVIEW-OPEN-PRICE-PATH-REMEDIATION
model_used: Luna xhigh root/workers
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: Stage-2 `1906f8a9e3c582384d3b414ee3b763120398df95`
branch: `data/tradingview-open-price-path-remediation-v1`
head_commit: `b9d035cff2d30df3d06e7c453c581dab06362456`

## Scope

One bounded remediation combining Stage 1 Open/session semantics and Stage 2
price-path contract. It corrects the classifier contradiction taxonomy,
reuses preserved offline evidence, executes exactly the frozen 30-request 60m
regular/extended probe, and updates the semantic contract readiness. It does
not authorize acquisition, admission V2, modelling, Path Risk, O2, outcomes,
panel writes, or Historical OPEN recovery.

## Lineage

- Stage 1: `data/tradingview-open-session-semantics-v1@80898c9098196db0275c1748cdfa28c859ff24b9`;
- Stage 2: `data/tradingview-intraday-price-path-contract-v1@1906f8a9e3c582384d3b414ee3b763120398df95`;
- independent activity: `data/tradingview-intraday-independent-activity-resolution-v1@c943a76fd56872d981a87519c2eb7072c413322c`;
- provider adapter: Mathieu `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`;
- canonical panel SHA before/after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Findings

- classifier no longer upgrades contradictory regular pre-open evidence to an
  auction-inclusive verdict; preserved Stage-1 verdict remains
  `TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`;
- independent official activity resolves 195/195 prior uncertain sessions as
  regular-market `Volume=0`, `Value=0`, `Frequency=0`, with 0 unresolved;
- offline 2026-07-01 extended 1m/5m evidence: 10/10 pre-open Opens equal
  official Open and 10/10 equal TV1D Open; no repair or selection performed;
- live 60m probe: 30/30 `AVAILABLE`, 0 retries, 0 fetch-more; extended first
  timestamp 08:45 WIB on 15/15 pairs, regular first timestamp 09:00 WIB;
- extended first Open equals official Open 14/15 and official Open lies inside
  extended first-bar H/L 15/15; regular first Open equals official Open 9/15;
- evidence supports semantic preregistration readiness, not auction identity
  or admission V2. Original admission rejection is unchanged.

## Runtime artifacts

External root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_open_price_path_remediation_v1_20260814`

Manifest SHA: `1c4ae4b69fbfb0a2e5912feafa251d805facb8c0e04ba8790fdec1e148c6ac02`.
Live summary SHA: `562550beaaa2d8b8a9a944a182182467be63c77f9eab49738bc648b297730931`.
Live pair CSV SHA: `60a86693fd1e80af38d13854716bb7053b2eb499b49e117abbccad954ee6fddf`.
Offline summary SHA: `34a14bf9b217e5fd927a6baf446068d412681ed1f4cbd9956c30a5dfc8ca8b89`.

The first live finalization attempt failed at a local output-directory write
after all 30 raw responses had been saved. Raw-only finalization completed
without another provider call.

## Validation

Focused and full pytest results are recorded in the final checkpoint and final
message. `git diff --check` is required before push. No provider call is
authorized after this handoff.

## Recommended next action

Stop for independent ChatGPT review. If approved, create a separate frozen
admission V2 specification; do not treat this remediation as authorization to
acquire history or fit a model.
