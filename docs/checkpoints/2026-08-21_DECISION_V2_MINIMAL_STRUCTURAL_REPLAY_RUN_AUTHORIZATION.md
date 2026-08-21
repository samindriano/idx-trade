# Decision V2 Minimal — Single Structural Replay Run Authorization

Date: 2026-08-21 Asia/Jakarta

Status: `SINGLE_LOCAL_REPLAY_AUTHORIZED_NOT_YET_EXECUTED`

Controlling runner audit: `RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_REPLAY_AUTHORIZED`

Audited implementation head: `044e8e9a3190935848938ca19d5ea3c9f7c98c01`

## Exactly one authorized local run

Run from the repository checkout on Windows using the audited runner head.

Pinned source root:

`D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2`

Pinned source identities enforced by the runner:

- `MANIFEST.json` SHA-256 `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- score Parquet SHA-256 `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- 600 sessions
- 172,697 rows

Suggested fresh output root:

`D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1`

The output directory must not already exist.

## PowerShell sequence

```powershell
git fetch origin
git switch research/idx-decision-v2-minimal-structural-replay-runner-v1
git pull --ff-only origin research/idx-decision-v2-minimal-structural-replay-runner-v1

$expected = "044e8e9a3190935848938ca19d5ea3c9f7c98c01"
$actual = (git rev-parse HEAD).Trim()
if ($actual -ne $expected) {
    throw "STOP: audited runner HEAD mismatch: $actual != $expected"
}

$root = "D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
$out = "D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"

if (Test-Path -LiteralPath $out) {
    throw "STOP: output dir already exists; do not overwrite: $out"
}
if (Test-Path -LiteralPath ($out + ".staging")) {
    throw "STOP: staging dir already exists; inspect before proceeding: $out.staging"
}

python scripts/run_v4_x1_decision_v2_minimal_structural_replay.py `
    --historical-root $root `
    --output-dir $out `
    --authorization "DECISION_V2_MINIMAL_STRUCTURAL_REPLAY_REVIEW_ACCEPTED_V1"
```

## Expected completion evidence

A successful invocation must print:

- a structural summary with status exactly one of:
  - `DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT`
  - `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`
- final `manifest=<path>`
- final `manifest_sha256=<sha256>`

The output root must contain the structural summary and SHA-manifested ledgers produced by the runner.

## Stop rule after this invocation

After the single run completes, do not rerun and do not alter any Decision threshold.

Return only the generated structural result / manifest evidence for independent result review.

If the result is `REJECT`, freeze the rejection first. No threshold rescue, H5/H10 rule, smoothing, parameter sweep, model refit, or historical PnL inspection is authorized.

If the result is `ACCEPT`, freeze the accepted Decision V2 Minimal implementation/profile and proceed to prospective outcome-blind Decision shadow preparation. Historical PnL inspection is not a prerequisite.
