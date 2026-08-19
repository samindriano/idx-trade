# Price-Basis Remediation V1 — Open/HLC Recertification Gate

Status: `IMPLEMENTED_READY_FOR_LOCAL_EXECUTION`

Scope is intentionally narrow. This checkpoint closes only the stale proof created when Price-Basis Remediation V1 changed `high`/`low`/`close` while leaving Open unchanged.

## Scientific question

After applying the immutable H/L/C overlay to the 1,657 certified repaired rows / 12 tickers, does every available Open still satisfy:

```text
corrected_low <= Open <= corrected_high
```

The audit checks two Open lineages separately:

1. **Accepted V4-X Open** — reconstructed with the same derivative-Open + immutable recovery-overlay price-evidence builder used by the historical V4-X target-entry lineage. Non-admitted Open is treated as unavailable, not forced into the gate.
2. **Corrected-panel Open column** — the existing panel `open` value, which Price-Basis Remediation V1 intentionally did not change.

## Guardrails

- parent remediation manifest is SHA-pinned;
- corrected panel and HLC overlay hashes are verified against the remediation manifest;
- expected repair population remains exactly 1,657 rows / 12 tickers;
- no Open repair;
- no H/L/C repair in this runner;
- no Volume or Regular-Market-Value audit or repair;
- no model fit, scoring, tuning, or refit;
- no target-value access;
- no protected-forward access;
- no provider calls;
- no parent artifact overwrite.

The Volume/Regular-Market-Value lane remains independent and is not a dependency of this Open/HLC gate.

## Runner

```text
scripts/run_price_basis_open_hlc_recertification_v1.py
```

Default local inputs:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\price_basis_remediation_v1_20260820
```

Default output:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\price_basis_open_hlc_recertification_v1_20260820
```

## PASS contract

PASS status:

```text
POST_REMEDIATION_OPEN_HLC_RECERTIFIED
```

Required conditions:

- repaired corrected H/L is valid on all audited rows;
- accepted V4-X Open has zero corrected-H/L range violations wherever Open is admitted/available;
- corrected-panel Open has zero corrected-H/L range violations wherever finite/available;
- violation artifact contains zero rows.

A PASS closes only the Open-vs-corrected-HLC gate. It does **not** by itself authorize a clean V2/V4-X refit; other independently scoped post-remediation guards must still pass.

## Local validation

```powershell
cd "C:\Users\Sam\OneDrive\Documents\Project\idx-trade-v4-ca-targeted"

git fetch origin data/price-basis-remediation-v1
git switch data/price-basis-remediation-v1
git pull --ff-only

python -m pytest -q `
  tests/test_price_basis_open_hlc_recertification_v1_contract.py

$openHlcOut = "D:\Documents\Project\idx-trade-data-gate-20260808v\price_basis_open_hlc_recertification_v1_20260820"
Test-Path $openHlcOut

python scripts/run_price_basis_open_hlc_recertification_v1.py `
  --output-dir "$openHlcOut"
```

The output directory must be absent/empty before execution; the runner refuses overwrite.
