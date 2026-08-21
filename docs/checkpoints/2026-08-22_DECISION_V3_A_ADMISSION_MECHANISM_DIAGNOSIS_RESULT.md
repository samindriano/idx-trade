# Decision V3 A Admission Mechanism Diagnosis Result

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_A_ADMISSION_MECHANISM_DIAGNOSIS`

Consumed manifest SHA-256: `15bf4ddabd35944d12024d5da592f8eff1f278a37ff8327a9b414d19fdf7d816`

Parent same-session manifest SHA-256: `bb2b38696d83629ace4a50609eb042e42951086fda27c7d9f39ad50f25f87902`

## Primary result

The magnitude of `soft_rank_gap` inside the already-selected A_SOFT population has essentially no monotonic association with durability:

- next-session severe: Spearman `-0.00654`; nonsevere mean gap `9.278`, severe mean gap `9.087`;
- eventual severe among completed spells: Spearman `0.02377`; nonsevere mean gap `9.260`, severe mean gap `9.250`;
- completed holding duration: Spearman gap vs duration `0.04768`.

Within-session discordant-pair evidence is also non-supportive of a larger-gap-is-better mechanism: 7 discordant outcome pairs across 6 eligible sessions; larger gap belonged to the nonsevere entry in 3 pairs and to the severe entry in 4; protective share excluding ties `0.4286`, equal-session-weighted protective share `0.50`.

Therefore the data do **not** support interpreting larger soft rank gap magnitude as the durability mechanism, and no new gap cutoff is authorized.

## Candidate-history clue

Within A_SOFT, entries that become severe on the next session show materially weaker pre-entry history despite similar current/previous ranks and similar rank-gap magnitude:

- `rank_t_minus_2`: severe mean `65.43` vs nonsevere `31.47`; median `33` vs `18`;
- `rank_t_minus_3`: severe mean `69.09` vs nonsevere `34.01`; median `38` vs `19`;
- `top20_run_including_entry`: severe mean `2.26` vs nonsevere `5.37`; median `2` vs `3`;
- `last3_top20_count`: severe mean `2.13` vs nonsevere `2.58`; median `2` vs `3`;
- current rank differs only modestly (`7.78` severe vs `7.06` nonsevere), and previous rank is actually slightly better for severe (`11.65` vs `13.17`).

The strongest descriptive clue is thus **trajectory stability / sustained Top20 presence**, not larger rank-gap magnitude.

## Interpretation boundary

This diagnosis cannot estimate the causal effect of the existing `gap >= 5` A_SOFT admission hurdle because all observed A_SOFT entries already passed that hurdle. It only rejects the stronger claim that larger gap magnitude inside the admitted population predicts better durability.

No Decision V4 rule, replay, threshold sweep, PnL, return, protected/fresh-forward outcome, model refit, or provider call occurred.

## Stop rule

`CONSUME_AND_STOP_MECHANISM_DIAGNOSIS_RETURN_TO_DECISION_V4_DESIGN`

No further mechanism diagnosis should be launched automatically from this result. The next work is Decision V4 design/brainstorming, with candidate-history stability treated as a design clue and capacity/underfill risk retained as a hard constraint from V2.
