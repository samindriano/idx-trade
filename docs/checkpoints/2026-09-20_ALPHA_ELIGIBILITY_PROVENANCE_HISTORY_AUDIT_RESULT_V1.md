# Eligibility Provenance History Audit V1

Date: 2026-09-20 (Asia/Jakarta)  
Experiment: `ELIGIBILITY-PROVENANCE-039`  
Status: `SUPPORTED_PROVENANCE_NARROWED`

## Question and boundary

What is the historical origin and meaning of the competing minimum-20 and
min-periods-60 rules? This audit reads only Git history, docs, and source code.
It does not regenerate a panel, select a population, access providers/cloud,
or read protected outcomes.

## Evidence

The minimum-20 rule predates the 2026-09-19 protocol. Commit `26aac816`
(2026-08-09) contains the legacy primary liquidity implementation in
`src/idx_trade/research_features.py`:

- `PRIMARY_LIQUIDITY_LOOKBACK = 60`;
- `PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20`;
- a manual official-session window;
- finite ACTIVE-value filtering;
- qualification when finite count is at least 20;
- median calculated over the finite observations.

The same commit's `docs/RESEARCH_SPECIFICATION_V1.md` describes at least 20
valid ACTIVE observations in the trailing 60 official sessions. The later
19-Sep protocol (`a02a1547`) repeats that 20-in-60 wording; it is not the first
local appearance of the rule.

The new Stage-A implementations differ:

- Stage-A V1 (`2b056802`) uses complete-window rolling helpers with
  `min_periods=window`, but has no explicit later `>=20` eligibility mask.
- Stage-A V2 (`1ebced27`) inherits complete-window rolling behavior and adds
  the explicit `>=20` check. Because the rolling values are unavailable until
  60 finite rows, that check is redundant for the implementation's count and
  median fields.
- The generic security-master `minimum_warmup_sessions=60` / `IPO_WARMUP`
  behavior is a separate listing-age/security eligibility concept, not the
  legacy liquidity finite-observation threshold.

## Narrowed interpretation

The evidence supports the following distinction:

| Number | Proven meaning | Not proven |
|---|---|---|
| 60 | trailing official-session lookback; also appears as separate generic IPO warm-up and current rolling completeness behavior | that 60 finite observations is the authoritative liquidity population rule |
| 20 | minimum finite ACTIVE observations inside that 60-session window in the legacy primary liquidity contract | that the legacy contract automatically governs the new candidate protocol without a current authority binding |

This changes the blocker from unknown numerical provenance to an authority
binding question. It does **not** authorize replacing the current mask, choosing
the larger sample, or regenerating candidate artifacts.

## Red-team and limitations

- The legacy manual-count logic and pre-protocol specification were both
  verified from retained Git refs.
- Both new Stage-A versions use complete-window rolling behavior; V2's later
  `>=20` check is redundant under that behavior.
- Historical provenance is not the same as current incumbent-specific Data-QA
  authority.
- No predictive outcome, protected payload, panel regeneration, or provider
  access occurred.

## Disposition

`POLICY_AUTHORITY_MISSING` remains the safe admission status, now annotated as
`PROVENANCE_NARROWED`. The only legitimate next step is a hash-bound project
authority decision that explicitly states whether the historical 20-in-60
liquidity contract governs this new candidate protocol, followed by isolated
regeneration and replay. Until then, do not mix masks or open outcomes.

Evidence:

- `research/alpha_eligibility_provenance_history_v1.py`
- `research_knowledge/eligibility_provenance_history_v1.json`
- external result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_eligibility_provenance_history_v1.json`
- code SHA-256:
  `82af867fd58cff6e3999b42fa0063c7f8da8c0436063329607b7cc8d42853166`
- external result SHA-256:
  `c6e4ba13928e36718394bba90d4566686c64cc2d2ecdd2c39c84eb44a5c33a9a`
