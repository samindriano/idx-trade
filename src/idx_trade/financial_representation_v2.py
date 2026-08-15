"""Outcome-blind Financial PIT Representation V2 structural audit.

This module audits a compact, same-reporting-period Financial representation.
It deliberately stops before label loading, score computation, model fitting,
or performance interpretation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from idx_trade.financial_pit_alpha import (
    FINANCIAL_FEATURE_PANEL_SHA256,
    FROZEN_V2_FOLDS,
    V2_COMMON_SUPPORT_SHA256,
    load_v2_common_support,
    sha256_file,
)


CORE_FEATURES = (
    "leverage_liabilities_to_assets",
    "liquidity_cash_to_assets",
    "margin_net_income_to_revenue",
)
YOY_FEATURES = ("yoy_revenue", "yoy_total_assets")
CANDIDATE_FEATURES = (*CORE_FEATURES, *YOY_FEATURES)
PERIOD_RANK = {"Q1": 1, "H1": 2, "9M": 3, "FY": 4}
EXPECTED_PANEL_SHA256 = FINANCIAL_FEATURE_PANEL_SHA256
EXPECTED_SUPPORT_SHA256 = V2_COMMON_SUPPORT_SHA256
EXPECTED_CONTRACT_VERSION = "FINANCIAL_PIT_ALPHA_V1_ASOF_JOIN_V2"
EXPECTED_PANEL_CENSUS_SHA256 = "e33ded6fcd6b12c6083c8e877ae78ce4a82d05279a4f3b62aee04f7f25d28343"


class FinancialRepresentationError(ValueError):
    """Raised when an immutable input violates the representation contract."""


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return str(value)


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default)


def _key_hash(frame: pd.DataFrame, columns: Iterable[str]) -> str:
    selected = frame.loc[:, list(columns)].copy()
    for column in selected.columns:
        selected[column] = selected[column].map(lambda value: "" if pd.isna(value) else str(value))
    selected = selected.sort_values(list(selected.columns), kind="mergesort")
    payload = "\n".join(
        "\x1f".join(row) for row in selected.astype(str).itertuples(index=False, name=None)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_columns(frame: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise FinancialRepresentationError(f"{label} missing columns: {missing}")


def _period_date(frame: pd.DataFrame) -> pd.Series:
    end = pd.to_datetime(frame["reporting_period_end"], errors="coerce")
    instant = pd.to_datetime(frame["reporting_instant_date"], errors="coerce")
    result = end.fillna(instant)
    return result.dt.normalize()


def _load_pinned_states(
    *,
    v2_support_path: Path,
    financial_panel_path: Path,
    census_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    manifest_path = census_dir / "support_census_manifest.json"
    states_path = census_dir / "selected_feature_states.parquet"
    summary_path = census_dir / "support_census_summary.json"
    for path in (manifest_path, states_path, summary_path):
        if not path.exists():
            raise FinancialRepresentationError(f"missing pinned input: {path}")

    if sha256_file(v2_support_path) != EXPECTED_SUPPORT_SHA256:
        raise FinancialRepresentationError("V2 support SHA-256 mismatch")
    if sha256_file(financial_panel_path) != EXPECTED_PANEL_SHA256:
        raise FinancialRepresentationError("Financial panel SHA-256 mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        raise FinancialRepresentationError("Financial census contract changed")
    if manifest.get("outcomes_accessed") or manifest.get("performance_metrics_computed"):
        raise FinancialRepresentationError("Financial census is not outcome-blind")
    inputs = manifest.get("inputs", {})
    if inputs.get("financial_feature_panel", {}).get("sha256") != EXPECTED_PANEL_SHA256:
        raise FinancialRepresentationError("census panel provenance mismatch")
    if inputs.get("v2_common_support", {}).get("sha256") != EXPECTED_SUPPORT_SHA256:
        raise FinancialRepresentationError("census V2 provenance mismatch")
    if sha256_file(states_path) != manifest.get("files", {}).get("selected_feature_states.parquet"):
        raise FinancialRepresentationError("selected Financial states SHA-256 mismatch")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        raise FinancialRepresentationError("Financial census summary contract changed")
    if summary.get("metrics_computed") or summary.get("outcomes_accessed"):
        raise FinancialRepresentationError("Financial census summary is not outcome-blind")

    support = load_v2_common_support(v2_support_path, EXPECTED_SUPPORT_SHA256)
    states = pd.read_parquet(states_path)
    _require_columns(
        states,
        (
            "row_id",
            "ticker",
            "fiscal_year",
            "feature_id",
            "period_stratum",
            "feature_value",
            "availability_status",
            "reporting_version_id",
            "reporting_attachment_sha256",
            "reporting_knowledge_at_utc",
            "reporting_period_start",
            "reporting_period_end",
            "reporting_instant_date",
            "reporting_period_evidence_kind",
            "reporting_period_evidence_location",
            "representation_format",
            "input_source_refs_json",
            "input_source_locations_json",
            "input_fact_identities_json",
        ),
        "selected Financial states",
    )
    if set(states["feature_id"].dropna().unique()) - set(
        (
            "size_log_total_assets",
            "size_log_revenue",
            "leverage_liabilities_to_assets",
            "capital_equity_to_assets",
            "liquidity_cash_to_assets",
            "profitability_net_income_to_assets",
            "profitability_attributable_income_to_equity",
            "cash_flow_ocf_to_net_income",
            "cash_flow_ocf_to_revenue",
            "margin_net_income_to_revenue",
            "yoy_revenue",
            "yoy_net_income",
            "yoy_total_assets",
        )
    ):
        raise FinancialRepresentationError("selected states contain an unknown Financial feature")
    if states["row_id"].min() < 0 or states["row_id"].max() >= len(support):
        raise FinancialRepresentationError("selected states contain an out-of-range row_id")
    identity = support[["row_id", "ticker"]].merge(
        states[["row_id", "ticker"]].drop_duplicates(), on="row_id", how="inner", suffixes=("_support", "_state")
    )
    if (identity["ticker_support"] != identity["ticker_state"]).any():
        raise FinancialRepresentationError("selected state ticker does not match V2 support")
    return support, states, {
        "financial_panel_sha256": EXPECTED_PANEL_SHA256,
        "v2_support_sha256": EXPECTED_SUPPORT_SHA256,
        "selected_feature_states_sha256": sha256_file(states_path),
        "support_census_manifest_sha256": sha256_file(manifest_path),
        "support_census_summary_sha256": sha256_file(summary_path),
        "source_census_contract_version": EXPECTED_CONTRACT_VERSION,
    }


def _prepare_candidate_states(states: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    frame = states[states["feature_id"].isin(CANDIDATE_FEATURES)].copy()
    frame["fiscal_year_num"] = pd.to_numeric(frame["fiscal_year"], errors="coerce")
    frame["period_rank"] = frame["period_stratum"].map(PERIOD_RANK)
    frame["reporting_knowledge_at_utc"] = pd.to_datetime(
        frame["reporting_knowledge_at_utc"], utc=True, errors="coerce"
    )
    if frame[["fiscal_year_num", "period_rank", "reporting_knowledge_at_utc"]].isna().any().any():
        raise FinancialRepresentationError("candidate state has malformed chronology or knowledge time")
    frame["period_date"] = _period_date(frame)
    frame["period_chronology_valid"] = frame["period_date"].notna()
    value = pd.to_numeric(frame["feature_value"], errors="coerce")
    frame["available_flag"] = frame["availability_status"].eq("AVAILABLE") & value.notna() & np.isfinite(value)
    malformed = frame["availability_status"].eq("AVAILABLE") & ~frame["available_flag"]
    frame.loc[malformed, "availability_status"] = "MALFORMED_AVAILABLE"

    duplicate_key = [
        "row_id",
        "feature_id",
        "period_stratum",
        "fiscal_year_num",
        "reporting_version_id",
        "reporting_attachment_sha256",
        "reporting_knowledge_at_utc",
    ]
    compare = ["feature_value", "availability_status", "period_date", "reporting_period_start", "reporting_period_end"]
    conflicts = 0
    for _, group in frame.groupby(duplicate_key, sort=False, dropna=False):
        if group[compare].astype(str).drop_duplicates().shape[0] > 1:
            conflicts += 1
    if conflicts:
        raise FinancialRepresentationError(f"candidate state duplicate conflicts: {conflicts}")
    frame = frame.drop_duplicates(duplicate_key, keep="first").reset_index(drop=True)
    return frame, {
        "candidate_state_duplicate_conflicts": conflicts,
        "candidate_state_unresolved_period_date_rows": int((~frame["period_chronology_valid"]).sum()),
    }


def _select_latest_bundle(states: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    bundle_columns = [
        "row_id",
        "fiscal_year_num",
        "period_stratum",
        "period_rank",
        "period_date",
        "reporting_version_id",
        "reporting_attachment_sha256",
        "reporting_knowledge_at_utc",
    ]
    bundles = states[states["period_chronology_valid"]][bundle_columns].drop_duplicates().copy()
    metadata_conflicts = (
        bundles.groupby(["row_id", "reporting_version_id", "reporting_attachment_sha256"])
        .agg(
            fiscal_periods=("period_stratum", "nunique"),
            fiscal_years=("fiscal_year_num", "nunique"),
            period_dates=("period_date", "nunique"),
        )
    )
    metadata_conflict_rows = int(
        metadata_conflicts[
            (metadata_conflicts["fiscal_periods"] > 1)
            | (metadata_conflicts["fiscal_years"] > 1)
            | (metadata_conflicts["period_dates"] > 1)
        ].shape[0]
    )
    bundles = bundles.sort_values(
        ["row_id", "fiscal_year_num", "period_rank", "period_date", "reporting_knowledge_at_utc", "reporting_version_id"],
        kind="mergesort",
    )
    max_chrono = bundles.groupby("row_id", as_index=False).tail(1)[
        ["row_id", "fiscal_year_num", "period_rank", "period_date"]
    ]
    top = bundles.merge(
        max_chrono,
        on=["row_id", "fiscal_year_num", "period_rank", "period_date"],
        how="inner",
    )
    max_knowledge = top.groupby("row_id")["reporting_knowledge_at_utc"].transform("max")
    top = top[top["reporting_knowledge_at_utc"].eq(max_knowledge)].copy()
    top["bundle_identity"] = (
        top["reporting_version_id"].astype(str)
        + "|"
        + top["reporting_attachment_sha256"].astype(str)
    )
    ambiguous = top.groupby("row_id")["bundle_identity"].nunique().gt(1)
    chosen = (
        top.sort_values(["row_id", "bundle_identity"], kind="mergesort")
        .drop_duplicates("row_id", keep="last")
        .reset_index(drop=True)
    )
    chosen["bundle_status"] = "SELECTED"
    chosen.loc[chosen["row_id"].isin(ambiguous[ambiguous].index), "bundle_status"] = "AMBIGUOUS_SAME_BUNDLE"
    return chosen, {
        "bundle_metadata_conflict_rows": metadata_conflict_rows,
        "ambiguous_same_bundle_rows": int(ambiguous.sum()),
    }


def _status_class(status: Any, *, no_state: bool = False) -> str:
    if no_state:
        return "NO_FINANCIAL_STATE"
    if status == "AVAILABLE":
        return "AVAILABLE"
    if status == "MISSING_INPUT":
        return "DECLARED_MISSING_INPUT"
    if status == "DENOMINATOR_NONPOSITIVE":
        return "ECONOMIC_NONPOSITIVE_DENOMINATOR"
    if status in {"UNRESOLVED_INPUT", "UNIT_MISMATCH", "AMBIGUOUS_SAME_TIME", "BUNDLE_FEATURE_MISSING"}:
        return "TECHNICAL_OR_SEMANTIC_UNRESOLVED"
    return "TECHNICAL_INVALID"


def _build_bundle_rows(
    support: pd.DataFrame,
    states: pd.DataFrame,
    chosen: pd.DataFrame,
    selection_diagnostics: dict[str, int],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    rows = support[["row_id", "ticker", "date", "signal_session_index", "decision_timestamp_utc"]].copy()
    chosen_columns = [
        "row_id",
        "bundle_status",
        "fiscal_year_num",
        "period_stratum",
        "period_rank",
        "period_date",
        "reporting_version_id",
        "reporting_attachment_sha256",
        "reporting_knowledge_at_utc",
    ]
    rows = rows.merge(chosen[chosen_columns], on="row_id", how="left")
    rows = rows.rename(
        columns={
            "fiscal_year_num": "bundle_fiscal_year",
            "period_stratum": "bundle_period_stratum",
            "period_rank": "bundle_period_rank",
            "period_date": "bundle_period_date",
            "reporting_version_id": "bundle_reporting_version_id",
            "reporting_attachment_sha256": "bundle_reporting_attachment_sha256",
            "reporting_knowledge_at_utc": "bundle_reporting_knowledge_at_utc",
        }
    )
    rows["bundle_status"] = rows["bundle_status"].fillna("NO_FINANCIAL_STATE")
    unresolved_period_rows = set(
        states.loc[~states["period_chronology_valid"], "row_id"].astype(int).unique()
    )
    rows.loc[
        rows["row_id"].isin(unresolved_period_rows) & rows["bundle_status"].eq("NO_FINANCIAL_STATE"),
        "bundle_status",
    ] = "UNRESOLVED_PERIOD_BOUNDARY"
    cutoff = pd.to_datetime(rows["decision_timestamp_utc"], utc=True)
    knowledge = pd.to_datetime(rows["bundle_reporting_knowledge_at_utc"], utc=True, errors="coerce")
    rows["bundle_filing_age_days"] = (cutoff - knowledge).dt.total_seconds() / 86400.0
    rows["bundle_filing_age_days"] = rows["bundle_filing_age_days"].round(9)

    merge_keys = ["row_id", "reporting_version_id", "reporting_attachment_sha256", "reporting_knowledge_at_utc"]
    selected = states.merge(
        chosen[merge_keys + ["bundle_status"]],
        on=merge_keys,
        how="inner",
    )
    selected_counts = selected.groupby("row_id").size()
    version_counts = selected.groupby("row_id")["reporting_version_id"].nunique()
    rows["bundle_candidate_state_count"] = rows["row_id"].map(selected_counts).fillna(0).astype(int)
    rows["bundle_candidate_source_versions"] = rows["row_id"].map(version_counts).fillna(0).astype(int)

    provenance_columns = [
        "row_id",
        "feature_id",
        "fiscal_year",
        "period_stratum",
        "feature_value",
        "availability_status",
        "available_flag",
        "reporting_version_id",
        "reporting_attachment_sha256",
        "reporting_publication_at_utc",
        "reporting_knowledge_at_utc",
        "reporting_period_start",
        "reporting_period_end",
        "reporting_instant_date",
        "reporting_period_evidence_kind",
        "reporting_period_evidence_location",
        "representation_format",
        "input_source_refs_json",
        "input_source_locations_json",
        "input_fact_identities_json",
    ]
    provenance = selected[provenance_columns].copy()

    for feature_id in CANDIDATE_FEATURES:
        subset = selected[selected["feature_id"].eq(feature_id)].copy()
        value = pd.to_numeric(subset["feature_value"], errors="coerce")
        subset["safe_available"] = subset["availability_status"].eq("AVAILABLE") & value.notna() & np.isfinite(value)
        subset = subset.sort_values(["row_id", "feature_id"], kind="mergesort").drop_duplicates("row_id", keep="first")
        rows = rows.merge(
            subset[["row_id", "feature_value", "availability_status", "safe_available"]].rename(
                columns={
                    "feature_value": f"{feature_id}__value",
                    "availability_status": f"{feature_id}__status",
                    "safe_available": f"{feature_id}__available",
                }
            ),
            on="row_id",
            how="left",
        )
        rows[f"{feature_id}__status"] = rows[f"{feature_id}__status"].fillna("BUNDLE_FEATURE_MISSING")
        rows[f"{feature_id}__missing_class"] = [
            _status_class(status, no_state=(bundle == "NO_FINANCIAL_STATE"))
            for status, bundle in zip(rows[f"{feature_id}__status"], rows["bundle_status"])
        ]
        rows[f"{feature_id}__available"] = rows[f"{feature_id}__available"].fillna(False).astype(bool)

    ambiguous_mask = rows["bundle_status"].eq("AMBIGUOUS_SAME_BUNDLE")
    for feature_id in CANDIDATE_FEATURES:
        rows.loc[ambiguous_mask, f"{feature_id}__status"] = "AMBIGUOUS_SAME_BUNDLE"
        rows.loc[ambiguous_mask, f"{feature_id}__available"] = False
        rows.loc[ambiguous_mask, f"{feature_id}__missing_class"] = "TECHNICAL_OR_SEMANTIC_UNRESOLVED"

    rows["core3_available"] = rows[[f"{feature}__available" for feature in CORE_FEATURES]].all(axis=1)
    rows["core3_plus_yoy_revenue_available"] = rows["core3_available"] & rows["yoy_revenue__available"]
    rows["core3_plus_yoy_assets_available"] = rows["core3_available"] & rows["yoy_total_assets__available"]
    rows["all_five_available"] = rows["core3_plus_yoy_revenue_available"] & rows["yoy_total_assets__available"]
    rows["same_bundle_violation"] = (
        rows["bundle_status"].eq("AMBIGUOUS_SAME_BUNDLE")
        | rows["bundle_candidate_source_versions"].gt(1)
        | (rows["bundle_status"].eq("SELECTED") & rows["bundle_candidate_state_count"].ne(len(CANDIDATE_FEATURES)))
    )
    rows["selected_knowledge_time_violation"] = knowledge > cutoff
    rows["selected_bundle_provenance_complete"] = rows["bundle_status"].eq("SELECTED") & rows[
        "bundle_reporting_version_id"
    ].notna() & rows["bundle_reporting_attachment_sha256"].notna() & knowledge.notna()
    summary = {
        **selection_diagnostics,
        "support_rows": int(len(rows)),
        "support_tickers": int(rows["ticker"].nunique()),
        "financial_bundle_rows": int(rows["bundle_status"].eq("SELECTED").sum()),
        "no_financial_state_rows": int(rows["bundle_status"].eq("NO_FINANCIAL_STATE").sum()),
        "unresolved_period_boundary_rows": int(rows["bundle_status"].eq("UNRESOLVED_PERIOD_BOUNDARY").sum()),
        "same_bundle_violation_rows": int(rows["same_bundle_violation"].sum()),
        "knowledge_time_violation_rows": int(rows["selected_knowledge_time_violation"].sum()),
        "provenance_incomplete_rows": int((~rows["selected_bundle_provenance_complete"] & rows["bundle_status"].eq("SELECTED")).sum()),
    }
    return rows, provenance, summary


def _fold_coverage(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for fold in FROZEN_V2_FOLDS:
        for block, start, end in (
            ("train", fold.train_start, fold.train_end),
            ("purge", fold.purge_start, fold.purge_end),
            ("validation", fold.validation_start, fold.validation_end),
        ):
            block_rows = rows[rows["signal_session_index"].between(start, end)]
            record: dict[str, Any] = {
                "fold": fold.name,
                "block": block,
                "session_index_start": start,
                "session_index_end": end,
                "rows": int(len(block_rows)),
                "tickers": int(block_rows["ticker"].nunique()),
                "financial_bundle_rows": int(block_rows["bundle_status"].eq("SELECTED").sum()),
                "financial_bundle_tickers": int(block_rows.loc[block_rows["bundle_status"].eq("SELECTED"), "ticker"].nunique()),
            }
            for feature_id in CANDIDATE_FEATURES:
                available = int(block_rows[f"{feature_id}__available"].sum())
                record[f"{feature_id}_available"] = available
                record[f"{feature_id}_rate_on_financial_rows"] = (
                    available / record["financial_bundle_rows"] if record["financial_bundle_rows"] else None
                )
                record[f"{feature_id}_completely_absent"] = available == 0
            for name, column in (
                ("core3", "core3_available"),
                ("core3_plus_yoy_revenue", "core3_plus_yoy_revenue_available"),
                ("core3_plus_yoy_assets", "core3_plus_yoy_assets_available"),
                ("all_five", "all_five_available"),
            ):
                count = int(block_rows[column].sum())
                record[f"{name}_available"] = count
                record[f"{name}_rate_on_financial_rows"] = (
                    count / record["financial_bundle_rows"] if record["financial_bundle_rows"] else None
                )
            records.append(record)
    return pd.DataFrame(records)


def _period_coverage(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    work = rows[rows["bundle_status"].eq("SELECTED")].copy()
    work["decision_year"] = pd.to_datetime(work["date"]).dt.year
    for (decision_year, period), group in work.groupby(["decision_year", "bundle_period_stratum"], dropna=False, sort=True):
        record = {
            "decision_year": int(decision_year),
            "period_stratum": period,
            "financial_bundle_rows": int(len(group)),
            "tickers": int(group["ticker"].nunique()),
        }
        for feature_id in CANDIDATE_FEATURES:
            record[f"{feature_id}_available"] = int(group[f"{feature_id}__available"].sum())
        record["core3_available"] = int(group["core3_available"].sum())
        record["core3_plus_yoy_revenue_available"] = int(group["core3_plus_yoy_revenue_available"].sum())
        record["core3_plus_yoy_assets_available"] = int(group["core3_plus_yoy_assets_available"].sum())
        record["all_five_available"] = int(group["all_five_available"].sum())
        records.append(record)
    return pd.DataFrame(records)


def _ticker_overlap(rows: pd.DataFrame) -> pd.DataFrame:
    work = rows[rows["bundle_status"].eq("SELECTED")].copy()
    records: list[dict[str, Any]] = []
    for ticker, group in work.groupby("ticker", sort=True):
        records.append(
            {
                "ticker": ticker,
                "financial_bundle_rows": int(len(group)),
                "core3_rows": int(group["core3_available"].sum()),
                "core3_plus_yoy_revenue_rows": int(group["core3_plus_yoy_revenue_available"].sum()),
                "core3_plus_yoy_assets_rows": int(group["core3_plus_yoy_assets_available"].sum()),
                "all_five_rows": int(group["all_five_available"].sum()),
                "bundle_periods": ",".join(sorted(group["bundle_period_stratum"].dropna().astype(str).unique())),
                "bundle_years": ",".join(sorted(group["bundle_fiscal_year"].dropna().astype(int).astype(str).unique())),
            }
        )
    return pd.DataFrame(records)


def _candidate_decision(rows: pd.DataFrame, fold: pd.DataFrame) -> dict[str, Any]:
    eligible = rows[rows["bundle_status"].eq("SELECTED")]
    semantic_integrity = {
        "same_bundle_violation_rows": int(rows["same_bundle_violation"].sum()),
        "knowledge_time_violation_rows": int(rows["selected_knowledge_time_violation"].sum()),
        "provenance_incomplete_rows": int(
            ((~rows["selected_bundle_provenance_complete"]) & rows["bundle_status"].eq("SELECTED")).sum()
        ),
    }
    # The Financial era is the inherited V2F4-V2F6 block in which the accepted
    # Financial support is non-empty. This is structural, not performance-led.
    financial_era = fold[fold["fold"].isin({"V2F4", "V2F5", "V2F6"})]
    train_rows = financial_era[financial_era["block"].eq("train")]
    candidate_rows: dict[str, Any] = {}
    for name, features, columns in (
        ("CORE3", CORE_FEATURES, [f"{feature}__available" for feature in CORE_FEATURES]),
        ("CORE3_PLUS_YOY_REVENUE", (*CORE_FEATURES, "yoy_revenue"), ["core3_plus_yoy_revenue_available"]),
        ("CORE3_PLUS_YOY_ASSETS", (*CORE_FEATURES, "yoy_total_assets"), ["core3_plus_yoy_assets_available"]),
        ("CORE3_PLUS_BOTH_YOY", CANDIDATE_FEATURES, ["all_five_available"]),
    ):
        absent_training_blocks = [
            row.fold
            for row in train_rows.itertuples()
            if any(bool(getattr(row, f"{feature}_completely_absent")) for feature in features)
        ] if name == "CORE3" else [
            row.fold for row in train_rows.itertuples() if bool(getattr(row, f"{columns[0]}")) is False
        ]
        candidate_rows[name] = {
            "features": list(features),
            "training_blocks_completely_absent": absent_training_blocks,
            "financial_era_training_blocks": int(len(train_rows)),
            "financial_era_validation_blocks": int(len(financial_era[financial_era["block"].eq("validation")])),
            "structural_integrity_pass": all(value == 0 for value in semantic_integrity.values()),
        }
        candidate_rows[name]["structurally_admissible"] = (
            candidate_rows[name]["structural_integrity_pass"]
            and not absent_training_blocks
        )
    if candidate_rows["CORE3_PLUS_YOY_REVENUE"]["structurally_admissible"] and candidate_rows["CORE3_PLUS_YOY_ASSETS"]["structurally_admissible"]:
        block = "CORE3+2_YOY"
    elif candidate_rows["CORE3_PLUS_YOY_REVENUE"]["structurally_admissible"]:
        block = "CORE3+1_YOY_REVENUE"
    elif candidate_rows["CORE3_PLUS_YOY_ASSETS"]["structurally_admissible"]:
        block = "CORE3+1_YOY_TOTAL_ASSETS"
    elif candidate_rows["CORE3"]["structurally_admissible"]:
        block = "CORE3"
    else:
        block = "NO_STRUCTURALLY_ADMISSIBLE_BLOCK"
    return {
        "semantic_integrity": semantic_integrity,
        "candidate_admission": candidate_rows,
        "recommended_structural_block": block,
        "eligible_financial_rows": int(len(eligible)),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def run_structural_audit(
    *,
    v2_support_path: str | Path,
    financial_panel_path: str | Path,
    census_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FinancialRepresentationError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    support, states, input_hashes = _load_pinned_states(
        v2_support_path=Path(v2_support_path),
        financial_panel_path=Path(financial_panel_path),
        census_dir=Path(census_dir),
    )
    candidate_states, prep_diagnostics = _prepare_candidate_states(states)
    chosen, selection_diagnostics = _select_latest_bundle(candidate_states)
    rows, provenance, row_summary = _build_bundle_rows(support, candidate_states, chosen, selection_diagnostics)
    fold = _fold_coverage(rows)
    period = _period_coverage(rows)
    ticker = _ticker_overlap(rows)

    # A source state is already selected by the accepted 18:00 census. Verify
    # that no selected state violates its exact decision cutoff.
    support_cutoffs = support[["row_id", "decision_timestamp_utc"]].copy()
    support_cutoffs["decision_timestamp_utc"] = pd.to_datetime(support_cutoffs["decision_timestamp_utc"], utc=True)
    future_check = candidate_states.merge(support_cutoffs, on="row_id", how="left")
    future_count = int(
        (pd.to_datetime(future_check["reporting_knowledge_at_utc"], utc=True) > future_check["decision_timestamp_utc"]).sum()
    )
    row_summary["post_18_selected_state_rows"] = future_count
    row_summary["candidate_state_rows"] = int(len(candidate_states))
    row_summary["candidate_state_tickers"] = int(candidate_states["ticker"].nunique())
    row_summary["candidate_features"] = list(CANDIDATE_FEATURES)
    row_summary["core_features"] = list(CORE_FEATURES)
    row_summary["yoy_features"] = list(YOY_FEATURES)
    row_summary["selected_bundle_hash"] = _key_hash(
        rows,
        [
            "row_id",
            "bundle_fiscal_year",
            "bundle_period_stratum",
            "bundle_reporting_version_id",
            "bundle_reporting_attachment_sha256",
            "bundle_reporting_knowledge_at_utc",
        ],
    )
    row_summary["support_identity_hash"] = _key_hash(support, ["ticker", "date", "signal_session_index"])
    row_summary["decision_year_rows"] = {
        str(int(year)): int(count) for year, count in rows.assign(decision_year=pd.to_datetime(rows["date"]).dt.year).groupby("decision_year").size().items()
    }
    decision = _candidate_decision(rows, fold)
    summary = {
        "status": "FINANCIAL_REPRESENTATION_V2_STRUCTURAL_AUDIT_COMPLETE",
        "outcome_blind": True,
        "labels_loaded": False,
        "predictions_loaded": False,
        "performance_metrics_computed": False,
        "model_fit": False,
        "o2_accessed": False,
        "fresh_forward_accessed": False,
        "protected_outcomes_accessed": False,
        "network_calls": 0,
        "contract": {
            "one_latest_reporting_period_bundle": True,
            "bundle_chronology": "max fiscal_year, period rank Q1<H1<9M<FY, and exact source period date; latest knowledge revision only within the selected chronology",
            "cutoff": "18:00:00 Asia/Jakarta converted to UTC",
            "same_bundle_required": True,
            "feature_fallback_across_periods": False,
            "period_strata": list(PERIOD_RANK),
        },
        "inputs": input_hashes,
        "preparation": prep_diagnostics,
        "rows": row_summary,
        "candidate_decision": decision,
    }
    rows.to_parquet(output / "bundle_rows.parquet", index=False)
    provenance.to_parquet(output / "selected_candidate_provenance.parquet", index=False)
    fold.to_csv(output / "fold_coverage.csv", index=False)
    period.to_csv(output / "coverage_by_period.csv", index=False)
    ticker.to_csv(output / "ticker_overlap.csv", index=False)
    _write_json(output / "summary.json", summary)

    artifact_hashes = {
        path.relative_to(output).as_posix(): sha256_file(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name not in {"manifest.json", "manifest.sha256"}
    }
    manifest = {
        "schema": "idx-trade/financial-representation-v2-structural-audit-v1",
        "artifact_hashes": artifact_hashes,
        "summary_sha256": artifact_hashes["summary.json"],
        "input_hashes": input_hashes,
        "outcome_blind": True,
        "labels_loaded": False,
        "performance_metrics_computed": False,
        "model_fit": False,
        "protected_outcomes_accessed": False,
    }
    _write_json(output / "manifest.json", manifest)
    manifest_sha = sha256_file(output / "manifest.json")
    (output / "manifest.sha256").write_text(f"{manifest_sha}  manifest.json\n", encoding="utf-8")
    _write_json(output / "manifest.json", manifest)
    manifest_sha = sha256_file(output / "manifest.json")
    (output / "manifest.sha256").write_text(f"{manifest_sha}  manifest.json\n", encoding="utf-8")
    return {"summary": summary, "manifest_sha256": manifest_sha, "output_dir": str(output)}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2-support", type=Path, required=True)
    parser.add_argument("--financial-panel", type=Path, required=True)
    parser.add_argument("--census-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_structural_audit(
        v2_support_path=args.v2_support,
        financial_panel_path=args.financial_panel,
        census_dir=args.census_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": result["summary"]["status"], "recommended_structural_block": result["summary"]["candidate_decision"]["recommended_structural_block"], "manifest_sha256": result["manifest_sha256"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
