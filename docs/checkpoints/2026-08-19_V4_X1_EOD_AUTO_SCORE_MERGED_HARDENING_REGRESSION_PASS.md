# V4-X1 EOD Auto-Score — Merged Hardening Regression PASS

Date: 2026-08-19 Asia/Jakarta

## Status

`MERGED_HARDENING_REGRESSION_PASS_READY_FOR_FINAL_RUNTIME_SMOKE`

The V4-X1 auto-score branch now contains the accepted canonical EOD adversarial hardening lineage (`7b21c50d278b13c8e94cdebddd4ca35765d7274e`) as an explicit merge ancestor. The user reran the expanded EOD + provider + monitoring + V4-X1 focused regression suite on merged HEAD `198356ae144dee9b5c95df66f9b4838dc72b3dd8`; all collected tests passed, `git diff --check` produced no error, and the checkout remained clean.

## Preserved boundaries

- Scheduled Task has not yet been repointed to this branch.
- Existing canonical EOD task remains the operational owner until final runtime smoke passes.
- No protected outcome access is authorized.
- No model refit or retuning is authorized.
- V4-X1 model fingerprint remains `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`.
- Existing first prospective score for 2026-08-19 remains immutable; expected artifact SHA is `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`.

## Next gate

Run one final local runtime smoke from the merged-hardening branch. It must return `PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED`, exit code 0, preserve the existing artifact SHA, and leave the V4-X1 counter at `1/100`. Only then may the Windows Scheduled Task be repointed to the V4-X1 EOD pipeline.
