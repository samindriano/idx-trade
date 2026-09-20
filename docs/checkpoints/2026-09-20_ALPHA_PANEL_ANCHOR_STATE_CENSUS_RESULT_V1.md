# Panel versus Tradability-Anchor State Census V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_COVERAGE / NO ADMISSION`

## Result

The tradability-anchor file contains 1,104,064 unique ticker/date rows across
980 tickers:

| Anchor state | Rows | Tickers | Panel-key overlap |
|---|---:|---:|---:|
| `ACTIVE` | 982,398 | 946 | 981,940 |
| `NO_TRADE` | 121,666 | 617 | 0 |

The panel contains 981,940 rows across 945 tickers. Its keys are a subset of
the ACTIVE anchor keys, and the only ACTIVE ticker absent from the panel is
`CNTX`. The anchor has 583 tickers with both states, 363 ACTIVE-only tickers,
and 34 NO_TRADE-only tickers.

## Interpretation

This confirms that the observed panel is an active-trade panel: it excludes all
known `NO_TRADE` keys and includes every ACTIVE key except CNTX. That is useful
structural coverage evidence, but it is not historical universe completeness.
The anchor itself could be incomplete, and NO_TRADE-only securities may still
matter to survivorship-safe population construction even though they are not
eligible active-trade rows. The census therefore strengthens the distinction
between observed-panel replay completeness and historical population safety; it
does not resolve the missing population/PIT/identity authority.

No policy, candidate, era, population, provider, cloud/R2, canonical, capture,
telemetry, scheduler, production, or protected outcome state was changed.

## Reproducibility

- Script: `research/alpha_panel_anchor_state_census_v1.py`
- Test: `tests/test_alpha_panel_anchor_state_census_v1.py`
- Durable result: `research_knowledge/panel_anchor_state_census_v1.json`
- Anchor input SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- Panel input SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Code SHA-256: `85e21304bed8398873f7d04a3c4d7c5bd9e0a969e5cee6028c5ec1d8b98c0eaa`
- Isolated external result SHA-256: `182c5344f084b86473cbe6b6399bab48623c437dce95518042464b8189d2bf5b`
