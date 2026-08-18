"""Outcome-blind bridge from certified V4 CA continuity to target provenance.

The frozen V4 target executor already requires row-level continuity provenance
(`policy_id`, `evidence_id`, `evidence_sha256`).  Corporate-action continuity
replays intentionally emit richer scientific/audit columns instead.  This
module performs only a deterministic provenance adaptation after an
independently reviewed CA bundle is certified and its exact manifest SHA is
supplied by the caller.

It never reads prices, returns, targets, predictions, or performance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .ranking_v4_3_target_execution import prepare_continuity_evidence


CA_SUMMARY_SCHEMA = "v4_ca_event_window_support_v1"
CA_MANIFEST_SCHEMA = "v4_ca_event_window_support_manifest_v1"
CA_CERTIFIED_VERDICT = "V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED"
EXPECTED_ROWS = 344_790
EXPECTED_DATES = 600
EXPECTED_HORIZONS = {5, 10}
GATE_RATE = 0.90


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(values: pd.Series, *, label: str) -> pd.Series:
    out = pd.to_datetime(values, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{label}")
    return out


def validate_certified_summary(
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    if summary.get("schema_version") != CA_SUMMARY_SCHEMA:
        raise RuntimeError("CA_SUMMARY_SCHEMA_INVALID")
    if manifest.get("schema_version") != CA_MANIFEST_SCHEMA:
        raise RuntimeError("CA_MANIFEST_SCHEMA_INVALID")
    if summary.get("verdict") != CA_CERTIFIED_VERDICT:
        raise RuntimeError("CA_CONTINUITY_NOT_CERTIFIED")
    if summary.get("corporate_action_continuity_certified") is not True:
        raise RuntimeError("CA_CONTINUITY_CERTIFIED_FLAG_INVALID")
    if manifest.get("status") != CA_CERTIFIED_VERDICT:
        raise RuntimeError("CA_MANIFEST_STATUS_INVALID")
    if summary.get("outcome_blind") is not True or manifest.get("outcome_blind") is not True:
        raise RuntimeError("CA_BUNDLE_NOT_OUTCOME_BLIND")
    for key in (
        "target_or_rank_materialized",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"CA_BUNDLE_FORBIDDEN_FLAG:{key}")
    if int(summary.get("frozen_rows", -1)) != EXPECTED_ROWS:
        raise RuntimeError("CA_FROZEN_ROW_COUNT_CHANGED")
    if int(summary.get("frozen_dates", -1)) != EXPECTED_DATES:
        raise RuntimeError("CA_FROZEN_DATE_COUNT_CHANGED")
    per_date = summary.get("per_date") or {}
    for key in ("h5_gate_dates", "h10_gate_dates", "consensus_gate_dates"):
        if int(per_date.get(key, -1)) != EXPECTED_DATES:
            raise RuntimeError(f"CA_DATE_GATE_NOT_ALL_PASS:{key}")
    for key in ("h5_min_rate", "h10_min_rate", "consensus_min_rate"):
        if float(per_date.get(key, -1.0)) < GATE_RATE:
            raise RuntimeError(f"CA_MIN_RATE_BELOW_GATE:{key}")


def validate_continuity_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "horizon",
        "continuity_status",
        "continuity_reason",
        "blocking_event_ids",
        "blocking_transition_dates",
        "policy_id",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"CA_LEDGER_COLUMNS_MISSING:{','.join(sorted(missing))}")
    out = frame.copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["signal_date"] = _normalize_date(out["signal_date"], label="signal_date")
    out["horizon"] = pd.to_numeric(out["horizon"], errors="raise").astype(int)
    if len(out) != EXPECTED_ROWS:
        raise RuntimeError(f"CA_LEDGER_ROW_COUNT_CHANGED:{len(out)}")
    if out["signal_date"].nunique() != EXPECTED_DATES:
        raise RuntimeError("CA_LEDGER_DATE_COUNT_CHANGED")
    if set(out["horizon"].unique()) != EXPECTED_HORIZONS:
        raise RuntimeError("CA_LEDGER_HORIZON_SET_CHANGED")
    if out.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("CA_LEDGER_DUPLICATE_IDENTITY")
    if out["policy_id"].fillna("").astype(str).str.strip().eq("").any():
        raise RuntimeError("CA_LEDGER_POLICY_ID_MISSING")

    for date, block in out.groupby("signal_date", sort=False):
        h5 = set(block.loc[block["horizon"].eq(5), "ticker"])
        h10 = set(block.loc[block["horizon"].eq(10), "ticker"])
        if h5 != h10:
            raise RuntimeError(
                f"CA_LEDGER_H5_H10_POPULATION_MISMATCH:{pd.Timestamp(date).date()}"
            )
    return out.sort_values(
        ["signal_date", "ticker", "horizon"], kind="mergesort"
    ).reset_index(drop=True)


def build_target_continuity_evidence(
    ledger: pd.DataFrame,
    *,
    accepted_ca_manifest_sha256: str,
    continuity_ledger_sha256: str,
) -> pd.DataFrame:
    manifest_sha = str(accepted_ca_manifest_sha256).lower().strip()
    ledger_sha = str(continuity_ledger_sha256).lower().strip()
    for label, digest in (("manifest", manifest_sha), ("ledger", ledger_sha)):
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise RuntimeError(f"INVALID_SHA256:{label}")

    source = validate_continuity_ledger(ledger)
    rows: list[dict[str, Any]] = []
    for row in source.itertuples(index=False):
        payload = {
            "accepted_ca_manifest_sha256": manifest_sha,
            "continuity_ledger_sha256": ledger_sha,
            "ticker": str(row.ticker),
            "signal_date": pd.Timestamp(row.signal_date).date().isoformat(),
            "horizon": int(row.horizon),
            "continuity_status": _text(row.continuity_status),
            "continuity_reason": _text(row.continuity_reason),
            "blocking_event_ids": _text(row.blocking_event_ids),
            "blocking_transition_dates": _text(row.blocking_transition_dates),
            "policy_id": _text(row.policy_id),
        }
        row_sha = _canonical_sha(payload)
        rows.append(
            {
                "ticker": payload["ticker"],
                "signal_date": payload["signal_date"],
                "horizon": payload["horizon"],
                "continuity_status": payload["continuity_status"],
                "policy_id": payload["policy_id"],
                "evidence_id": f"V4_CA_CONTINUITY_ROW:{row_sha}",
                "evidence_sha256": row_sha,
            }
        )
    evidence = pd.DataFrame(rows)
    # Reuse the already frozen target-side validator as the final schema gate.
    return prepare_continuity_evidence(evidence)


def load_and_verify_certified_bundle(
    root: Path,
    *,
    expected_manifest_sha256: str,
) -> tuple[pd.DataFrame, str, str]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    ledger_path = root / "v4_frozen_continuity_ledger_event_window.csv"
    for path in (manifest_path, summary_path, ledger_path):
        if not path.is_file():
            raise RuntimeError(f"CA_BUNDLE_REQUIRED_FILE_MISSING:{path}")

    actual_manifest_sha = sha256_file(manifest_path)
    expected = str(expected_manifest_sha256).lower().strip()
    if actual_manifest_sha != expected:
        raise RuntimeError(
            f"CA_ACCEPTED_MANIFEST_SHA_MISMATCH:{actual_manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if sha256_file(summary_path) != manifest.get("summary_sha256"):
        raise RuntimeError("CA_SUMMARY_HASH_MISMATCH")
    validate_certified_summary(summary, manifest)

    outputs = summary.get("output_hashes") or {}
    manifest_outputs = manifest.get("output_hashes") or {}
    actual_ledger_sha = sha256_file(ledger_path)
    if outputs.get("continuity_ledger") != actual_ledger_sha:
        raise RuntimeError("CA_LEDGER_SUMMARY_HASH_MISMATCH")
    if manifest_outputs.get("continuity_ledger") != actual_ledger_sha:
        raise RuntimeError("CA_LEDGER_MANIFEST_HASH_MISMATCH")

    ledger = validate_continuity_ledger(pd.read_csv(ledger_path, dtype=str, keep_default_na=False))
    return ledger, actual_manifest_sha, actual_ledger_sha
