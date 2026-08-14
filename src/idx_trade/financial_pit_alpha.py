"""Outcome-blind Financial PIT Alpha V1 support census.

This module freezes the join boundary for a future Financial PIT challenger.
It deliberately stops before fitting, scoring, label loading, or any provider
access.  The accepted Financial PIT panel is long by issuer, knowledge-time,
reporting-period stratum, and feature.  The resolver therefore selects a
latest eligible row independently for each ``feature_id`` and period stratum;
it never pools Q1/H1/9M/FY values.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from idx_trade.open_alpha_prereg import (
    CONTROL_FEATURE_COLUMNS,
    CONTROL_HGB_PARAMETERS,
    CONTROL_MODEL,
    CONTROL_PREPROCESSING,
    FROZEN_V2_FOLDS,
    SURVIVOR_GATE_RULE,
    WINNER_SELECTION_RULE,
    feature_order_sha256,
)


FINANCIAL_FEATURE_PANEL_SHA256 = (
    "1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023"
)
V2_COMMON_SUPPORT_SHA256 = (
    "6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6"
)
CONTRACT_VERSION = "FINANCIAL_PIT_ALPHA_V1_ASOF_JOIN_V2"
DECISION_CUTOFF_CONTRACT = "SESSION_DATE_18_00_ASIA_JAKARTA_UTC_EXACT"
ALLOWED_SCOPE = "CONSOLIDATED"
ALLOWED_INDUSTRY = "GENERAL"
PERIOD_KEYS = ("Q1", "H1", "9M", "FY")

FINANCIAL_FEATURE_IDS = (
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

FINANCIAL_SLOT_COLUMNS = tuple(
    f"financial__{feature_id}__{period_key}"
    for feature_id in FINANCIAL_FEATURE_IDS
    for period_key in PERIOD_KEYS
)
CANDIDATE_FEATURE_COLUMNS = {
    "CONTROL": tuple(CONTROL_FEATURE_COLUMNS),
    "FINANCIAL_ONLY": FINANCIAL_SLOT_COLUMNS,
    "V2_PLUS_FINANCIAL": tuple(CONTROL_FEATURE_COLUMNS) + FINANCIAL_SLOT_COLUMNS,
}
MISSING_HANDLING_CONTRACT = (
    "fold-local median SimpleImputer with missing indicators and "
    "keep_empty_features=True; no global/full-sample statistics"
)

V2_IDENTITY_COLUMNS = ("ticker", "date", "signal_session_index")
FORBIDDEN_OUTCOME_COLUMNS = {
    "binary_target",
    "target",
    "label",
    "label_status",
    "h10_target",
    "tp_first",
    "sl_first",
    "outcome",
    "forward_outcome",
}

FINANCIAL_REQUIRED_COLUMNS = (
    "ticker",
    "as_of_timestamp_utc",
    "fiscal_year",
    "fiscal_period",
    "period_stratification_key",
    "statement_scope",
    "industry_class",
    "feature_id",
    "feature_value",
    "availability_status",
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
    "input_attachment_sha256s_json",
    "feature_contract_version",
)


class FinancialAlphaContractError(ValueError):
    """Raised when a pinned input violates the frozen support contract."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sha256(path: str | Path, expected: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise FinancialAlphaContractError(
            f"SHA-256 mismatch for {path}: expected {expected}, got {actual}"
        )
    return actual


def _require_columns(columns: Iterable[str], required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(columns))
    if missing:
        raise FinancialAlphaContractError(f"{label} missing required columns: {missing}")


def _key_hash(frame: pd.DataFrame, columns: Iterable[str]) -> str:
    selected = frame.loc[:, list(columns)].copy()
    for column in selected.columns:
        selected[column] = selected[column].map(lambda value: "" if pd.isna(value) else str(value))
    selected = selected.sort_values(list(selected.columns), kind="mergesort")
    payload = "\n".join(
        "\x1f".join(row)
        for row in selected.astype(str).itertuples(index=False, name=None)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def session_decision_cutoff_utc(session_dates: pd.Series) -> pd.Series:
    """Return the frozen after-close cutoff for each local IDX session date.

    The clean V2 artifact exposes a normalized session date, while the frozen
    V2 contract says the signal is produced after that session's close.  The
    contract therefore uses exactly 18:00:00 Asia/Jakarta on that civil date,
    converted to UTC. This is an explicit timestamp rule, not a calendar-date
    join, and is intentionally persisted in every diagnostic row. A future
    experiment requiring a different operational cutoff must use a separately
    frozen contract.
    """

    values = pd.to_datetime(session_dates, errors="raise")
    if not isinstance(values, pd.Series):
        values = pd.Series(values)
    if values.dt.tz is None:
        local = values.dt.tz_localize("Asia/Jakarta")
    else:
        local = values.dt.tz_convert("Asia/Jakarta")
    normalized = local.dt.normalize()
    if not (local == normalized).all():
        raise FinancialAlphaContractError("V2 session dates must be normalized session dates")
    cutoff = normalized + pd.Timedelta(hours=18)
    return cutoff.dt.tz_convert("UTC")


def load_v2_common_support(path: str | Path, expected_sha256: str = V2_COMMON_SUPPORT_SHA256) -> pd.DataFrame:
    """Load only outcome-blind V2 identity columns and construct cutoffs."""

    path = Path(path)
    verify_sha256(path, expected_sha256)
    import pyarrow.parquet as pq

    columns = list(pq.ParquetFile(path).schema_arrow.names)
    forbidden = sorted(set(columns) & FORBIDDEN_OUTCOME_COLUMNS)
    if forbidden:
        raise FinancialAlphaContractError(f"V2 support exposes protected outcome columns: {forbidden}")
    _require_columns(columns, V2_IDENTITY_COLUMNS, "V2 support")
    frame = pd.read_parquet(path, columns=list(V2_IDENTITY_COLUMNS))
    if frame[list(V2_IDENTITY_COLUMNS)].isna().any().any():
        raise FinancialAlphaContractError("V2 identity contains missing values")
    duplicate_mask = frame.duplicated(list(V2_IDENTITY_COLUMNS), keep=False)
    if duplicate_mask.any():
        raise FinancialAlphaContractError(
            f"V2 support contains duplicate identity rows: {int(duplicate_mask.sum())}"
        )
    frame = frame.reset_index(drop=True)
    frame.insert(0, "row_id", np.arange(len(frame), dtype=np.int64))
    frame["decision_timestamp_utc"] = session_decision_cutoff_utc(frame["date"])
    frame["decision_timestamp_utc"] = frame["decision_timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return frame


def _normalize_period_key(value: Any) -> str:
    mapping = {
        "tw1": "Q1",
        "q1": "Q1",
        "h1": "H1",
        "tw2": "H1",
        "9m": "9M",
        "tw3": "9M",
        "fy": "FY",
        "audit": "FY",
    }
    key = mapping.get(str(value).strip().lower())
    if key is None:
        raise FinancialAlphaContractError(f"unsupported Financial PIT period stratum: {value!r}")
    return key


def load_financial_panel(path: str | Path, expected_sha256: str = FINANCIAL_FEATURE_PANEL_SHA256) -> pd.DataFrame:
    """Load and validate the accepted GENERAL+CONSOLIDATED panel."""

    path = Path(path)
    verify_sha256(path, expected_sha256)
    import pyarrow.parquet as pq

    columns = list(pq.ParquetFile(path).schema_arrow.names)
    _require_columns(columns, FINANCIAL_REQUIRED_COLUMNS, "Financial PIT panel")
    frame = pd.read_parquet(path)
    if set(frame["statement_scope"].dropna().unique()) != {ALLOWED_SCOPE}:
        raise FinancialAlphaContractError("Financial panel contains non-CONSOLIDATED scope")
    if set(frame["industry_class"].dropna().unique()) != {ALLOWED_INDUSTRY}:
        raise FinancialAlphaContractError("Financial panel contains non-GENERAL applicability")
    if set(frame["feature_id"].dropna().unique()) != set(FINANCIAL_FEATURE_IDS):
        raise FinancialAlphaContractError("Financial panel feature set is not the frozen 13-feature family")
    frame["period_key"] = frame["period_stratification_key"].map(_normalize_period_key)
    if set(frame["period_key"].unique()) != set(PERIOD_KEYS):
        raise FinancialAlphaContractError("Financial panel does not contain the four frozen period strata")
    frame["as_of_timestamp_utc"] = pd.to_datetime(frame["as_of_timestamp_utc"], utc=True, errors="coerce")
    if frame["as_of_timestamp_utc"].isna().any():
        raise FinancialAlphaContractError("Financial panel contains malformed as-of timestamps")
    frame["reporting_knowledge_at_utc"] = pd.to_datetime(
        frame["reporting_knowledge_at_utc"], utc=True, errors="coerce"
    )
    if frame["reporting_knowledge_at_utc"].isna().any():
        raise FinancialAlphaContractError("Financial panel contains malformed knowledge timestamps")
    duplicate_key = ["ticker", "fiscal_year", "feature_id", "period_key", "as_of_timestamp_utc"]
    duplicate_mask = frame.duplicated(duplicate_key, keep=False)
    if duplicate_mask.any():
        # Exact duplicate rows are harmless capture duplication; conflicting
        # rows are retained so the join can fail closed at the selected time.
        frame = frame.drop_duplicates(keep="first").reset_index(drop=True)
    return frame


def _conflicting_timestamp_keys(frame: pd.DataFrame) -> set[tuple[str, str, str, str, str]]:
    key_columns = [
        "ticker",
        "fiscal_year",
        "feature_id",
        "period_key",
        "reporting_knowledge_at_utc",
    ]
    compare_columns = [
        "feature_value",
        "availability_status",
        "reporting_version_id",
        "reporting_attachment_sha256",
        "reporting_knowledge_at_utc",
    ]
    conflicts: set[tuple[str, str, str, str, str]] = set()
    for key, group in frame.groupby(key_columns, sort=False, dropna=False):
        if group[compare_columns].astype(str).drop_duplicates().shape[0] > 1:
            conflicts.add(tuple(str(item) for item in key))
    return conflicts


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return str(value)


def _provenance_payload(row: pd.Series, feature_id: str, period_key: str) -> dict[str, Any]:
    def clean(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return _json_default(value)

    return {
        "feature_id": feature_id,
        "period_stratum": period_key,
        "as_of_timestamp_utc": row.get("financial_as_of_timestamp_utc"),
        "version_id": row.get("financial_reporting_version_id"),
        "attachment_sha256": row.get("financial_reporting_attachment_sha256"),
        "publication_at_utc": row.get("financial_reporting_publication_at_utc"),
        "knowledge_at_utc": row.get("financial_reporting_knowledge_at_utc"),
        "period_start": row.get("financial_reporting_period_start"),
        "period_end": row.get("financial_reporting_period_end"),
        "instant_date": row.get("financial_reporting_instant_date"),
        "period_evidence_kind": row.get("financial_reporting_period_evidence_kind"),
        "period_evidence_location": row.get("financial_reporting_period_evidence_location"),
        "representation_format": row.get("financial_representation_format"),
        "source_refs": clean(row.get("financial_input_source_refs_json")),
        "source_locations": clean(row.get("financial_input_source_locations_json")),
        "fact_identities": clean(row.get("financial_input_fact_identities_json")),
        "input_attachment_sha256s": clean(row.get("financial_input_attachment_sha256s_json")),
        "availability_status": row.get("financial_availability_status"),
    }


def _merge_slot(
    base: pd.DataFrame,
    financial: pd.DataFrame,
    feature_id: str,
    period_key: str,
    conflicts: set[tuple[str, str, str, str, str]],
) -> pd.DataFrame:
    right = financial[
        financial["feature_id"].eq(feature_id) & financial["period_key"].eq(period_key)
    ].copy()
    slot = f"{feature_id}__{period_key}"
    if right.empty:
        return pd.DataFrame(columns=["row_id", "ticker", "fiscal_year"])
    years = right[["ticker", "fiscal_year"]].drop_duplicates()
    left = base[["row_id", "ticker", "decision_timestamp_utc"]].merge(years, on="ticker", how="inner")
    left["decision_timestamp_utc"] = pd.to_datetime(left["decision_timestamp_utc"], utc=True)
    right = right.sort_values(
        ["reporting_knowledge_at_utc", "ticker"], kind="mergesort"
    )
    right = right.rename(
        columns={
            "as_of_timestamp_utc": "financial_as_of_timestamp_utc",
            "feature_value": "financial_feature_value",
            "availability_status": "financial_availability_status",
            "reporting_version_id": "financial_reporting_version_id",
            "reporting_attachment_sha256": "financial_reporting_attachment_sha256",
            "reporting_publication_at_utc": "financial_reporting_publication_at_utc",
            "reporting_knowledge_at_utc": "financial_reporting_knowledge_at_utc",
            "reporting_period_start": "financial_reporting_period_start",
            "reporting_period_end": "financial_reporting_period_end",
            "reporting_instant_date": "financial_reporting_instant_date",
            "reporting_period_evidence_kind": "financial_reporting_period_evidence_kind",
            "reporting_period_evidence_location": "financial_reporting_period_evidence_location",
            "representation_format": "financial_representation_format",
            "input_source_refs_json": "financial_input_source_refs_json",
            "input_source_locations_json": "financial_input_source_locations_json",
            "input_fact_identities_json": "financial_input_fact_identities_json",
            "input_attachment_sha256s_json": "financial_input_attachment_sha256s_json",
        }
    )
    right["financial_as_of_timestamp_utc"] = pd.to_datetime(
        right["financial_as_of_timestamp_utc"], utc=True
    )
    right["financial_reporting_knowledge_at_utc"] = pd.to_datetime(
        right["financial_reporting_knowledge_at_utc"], utc=True
    )
    merged = pd.merge_asof(
        left.sort_values(["decision_timestamp_utc", "ticker"], kind="mergesort"),
        right.sort_values(
            ["financial_reporting_knowledge_at_utc", "ticker"], kind="mergesort"
        ),
        left_on="decision_timestamp_utc",
        right_on="financial_reporting_knowledge_at_utc",
        by=["ticker", "fiscal_year"],
        direction="backward",
        allow_exact_matches=True,
    )
    merged["row_id"] = merged["row_id"].astype("int64")
    merged["_conflict"] = merged.apply(
        lambda row: (
            str(row.get("ticker")),
            str(row.get("fiscal_year")),
            feature_id,
            period_key,
            str(row.get("financial_reporting_knowledge_at_utc")),
        ) in conflicts
        if pd.notna(row.get("financial_as_of_timestamp_utc"))
        else False,
        axis=1,
    )
    status = merged["financial_availability_status"].astype("object")
    status.loc[merged["_conflict"]] = "AMBIGUOUS_SAME_TIME"
    value = merged["financial_feature_value"].where(~merged["_conflict"], np.nan)
    result = pd.DataFrame({"row_id": merged["row_id"], "ticker": merged["ticker"], "fiscal_year": merged["fiscal_year"]})
    result[f"{slot}__value"] = value
    result[f"{slot}__status"] = status
    result[f"{slot}__as_of"] = merged["financial_as_of_timestamp_utc"]
    for source, target in (
        ("financial_reporting_version_id", f"{slot}__version"),
        ("financial_reporting_attachment_sha256", f"{slot}__attachment"),
        ("financial_reporting_publication_at_utc", f"{slot}__publication"),
        ("financial_reporting_knowledge_at_utc", f"{slot}__knowledge"),
        ("financial_reporting_period_start", f"{slot}__period_start"),
        ("financial_reporting_period_end", f"{slot}__period_end"),
        ("financial_reporting_instant_date", f"{slot}__instant_date"),
        ("financial_reporting_period_evidence_kind", f"{slot}__evidence_kind"),
        ("financial_reporting_period_evidence_location", f"{slot}__evidence_location"),
        ("financial_representation_format", f"{slot}__format"),
        ("financial_input_source_refs_json", f"{slot}__source_refs"),
        ("financial_input_source_locations_json", f"{slot}__source_locations"),
        ("financial_input_fact_identities_json", f"{slot}__fact_ids"),
    ):
        result[target] = merged.get(source)
    return result


def run_support_census(
    v2_path: str | Path,
    financial_panel_path: str | Path,
    output_dir: str | Path,
    *,
    v2_sha256: str = V2_COMMON_SUPPORT_SHA256,
    financial_sha256: str = FINANCIAL_FEATURE_PANEL_SHA256,
) -> dict[str, Any]:
    """Build the outcome-blind long-strata join diagnostics and summaries."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    v2 = load_v2_common_support(v2_path, v2_sha256)
    financial = load_financial_panel(financial_panel_path, financial_sha256)
    conflicts = _conflicting_timestamp_keys(financial)

    row_count = len(v2)
    any_state = np.zeros(row_count, dtype=bool)
    any_available = np.zeros(row_count, dtype=bool)
    available_slot_count = np.zeros(row_count, dtype=np.int16)
    ambiguous_join = np.zeros(row_count, dtype=bool)
    latest_asof = pd.Series(pd.NaT, index=np.arange(row_count), dtype="datetime64[ns, UTC]")
    feature_available = {feature: np.zeros(row_count, dtype=bool) for feature in FINANCIAL_FEATURE_IDS}
    selected_chunks: list[pd.DataFrame] = []
    feature_rows = []
    for feature_id in FINANCIAL_FEATURE_IDS:
        for period_key in PERIOD_KEYS:
            slot = f"{feature_id}__{period_key}"
            slot_frame = _merge_slot(v2, financial, feature_id, period_key, conflicts)
            if slot_frame.empty:
                feature_rows.append(
                    {
                        "feature_id": feature_id,
                        "period_stratum": period_key,
                        "rows_with_state": 0,
                        "rows_available": 0,
                        "selected_state_rows": 0,
                        "rows_missing_or_unresolved": 0,
                        "rows_ambiguous_same_time": 0,
                    }
                )
                continue
            statuses = slot_frame[f"{slot}__status"].astype("object")
            asof = pd.to_datetime(slot_frame[f"{slot}__as_of"], utc=True, errors="coerce")
            slot_frame["_state"] = asof.notna()
            slot_frame["_available"] = statuses.eq("AVAILABLE")
            slot_frame["_ambiguous"] = statuses.eq("AMBIGUOUS_SAME_TIME")
            by_row = slot_frame.groupby("row_id", sort=False)
            state_by_row = by_row["_state"].any()
            available_by_row = by_row["_available"].any()
            ambiguous_by_row = by_row["_ambiguous"].any()
            available_count_by_row = by_row["_available"].sum()
            latest_by_row = by_row[f"{slot}__knowledge"].max()
            any_state[state_by_row.index.to_numpy(dtype=np.int64)] |= state_by_row.to_numpy()
            any_available[available_by_row.index.to_numpy(dtype=np.int64)] |= available_by_row.to_numpy()
            available_slot_count[available_count_by_row.index.to_numpy(dtype=np.int64)] += available_count_by_row.to_numpy(dtype=np.int16)
            ambiguous_join[ambiguous_by_row.index.to_numpy(dtype=np.int64)] |= ambiguous_by_row.to_numpy()
            feature_available[feature_id][available_by_row.index.to_numpy(dtype=np.int64)] |= available_by_row.to_numpy()
            latest_candidate = pd.Series(pd.NaT, index=np.arange(row_count), dtype="datetime64[ns, UTC]")
            latest_candidate.loc[latest_by_row.index] = latest_by_row
            latest_asof = pd.concat([latest_asof, latest_candidate], axis=1).max(axis=1)
            state_mask = slot_frame["_state"].to_numpy()
            selected = slot_frame.loc[state_mask].copy()
            if not selected.empty:
                selected["feature_id"] = feature_id
                selected["period_stratum"] = period_key
                selected = selected.rename(
                    columns={
                        f"{slot}__value": "feature_value",
                        f"{slot}__status": "availability_status",
                        f"{slot}__as_of": "as_of_timestamp_utc",
                        f"{slot}__version": "reporting_version_id",
                        f"{slot}__attachment": "reporting_attachment_sha256",
                        f"{slot}__publication": "reporting_publication_at_utc",
                        f"{slot}__knowledge": "reporting_knowledge_at_utc",
                        f"{slot}__period_start": "reporting_period_start",
                        f"{slot}__period_end": "reporting_period_end",
                        f"{slot}__instant_date": "reporting_instant_date",
                        f"{slot}__evidence_kind": "reporting_period_evidence_kind",
                        f"{slot}__evidence_location": "reporting_period_evidence_location",
                        f"{slot}__format": "representation_format",
                        f"{slot}__source_refs": "input_source_refs_json",
                        f"{slot}__source_locations": "input_source_locations_json",
                        f"{slot}__fact_ids": "input_fact_identities_json",
                    }
                )
                selected_chunks.append(
                    selected[
                        [
                            "row_id", "ticker", "fiscal_year", "feature_id", "period_stratum", "feature_value",
                            "availability_status", "as_of_timestamp_utc", "reporting_version_id",
                            "reporting_attachment_sha256", "reporting_publication_at_utc",
                            "reporting_knowledge_at_utc", "reporting_period_start", "reporting_period_end",
                            "reporting_instant_date", "reporting_period_evidence_kind",
                            "reporting_period_evidence_location", "representation_format",
                            "input_source_refs_json", "input_source_locations_json", "input_fact_identities_json",
                        ]
                    ]
                )
            feature_rows.append(
                {
                    "feature_id": feature_id,
                    "period_stratum": period_key,
                    "rows_with_state": int(state_by_row.sum()),
                    "rows_available": int(available_by_row.sum()),
                    "selected_state_rows": int(state_mask.sum()),
                    "rows_missing_or_unresolved": int(statuses.isin(["MISSING_INPUT", "UNRESOLVED_INPUT", "DENOMINATOR_NONPOSITIVE", "UNIT_MISMATCH"]).sum()),
                    "rows_ambiguous_same_time": int(statuses.eq("AMBIGUOUS_SAME_TIME").sum()),
                }
            )
    feature_support = pd.DataFrame(feature_rows)
    feature_support.to_csv(output / "feature_support.csv", index=False)

    diagnostics = v2.copy()
    diagnostics["financial_any_state_available"] = any_state
    diagnostics["financial_any_feature_available"] = any_available
    diagnostics["financial_available_slot_count"] = available_slot_count
    diagnostics["financial_available_feature_count"] = pd.DataFrame(feature_available).sum(axis=1).astype("int16")
    diagnostics["financial_ambiguous_join"] = ambiguous_join
    diagnostics["financial_latest_knowledge_at_utc"] = latest_asof
    cutoff = pd.to_datetime(diagnostics["decision_timestamp_utc"], utc=True)
    diagnostics["financial_latest_filing_age_days"] = (
        cutoff - latest_asof
    ).dt.total_seconds() / 86400.0
    diagnostics["financial_latest_filing_age_days"] = diagnostics["financial_latest_filing_age_days"].round(9)
    diagnostics.to_parquet(output / "join_diagnostics.parquet", index=False)
    if selected_chunks:
        pd.concat(selected_chunks, ignore_index=True).sort_values(
            ["row_id", "feature_id", "period_stratum"], kind="mergesort"
        ).to_parquet(output / "selected_feature_states.parquet", index=False)
    else:
        pd.DataFrame(columns=["row_id", "ticker", "feature_id", "period_stratum"]).to_parquet(
            output / "selected_feature_states.parquet", index=False
        )

    selected_states = (
        pd.concat(selected_chunks, ignore_index=True)
        if selected_chunks
        else pd.DataFrame(
            columns=[
                "row_id",
                "ticker",
                "fiscal_year",
                "feature_id",
                "period_stratum",
                "availability_status",
            ]
        )
    )

    # The long state audit retains every eligible fiscal-year state. The model
    # contract, however, has exactly one raw slot per row and feature/period
    # stratum. Select the latest eligible knowledge state, using the newest
    # fiscal year only as a deterministic tie-break when knowledge timestamps
    # are identical. Same-fiscal-year conflicts are already marked ambiguous.
    if selected_states.empty:
        slot_matrix = selected_states.copy()
    else:
        ordered = selected_states.copy()
        ordered["_knowledge_sort"] = pd.to_datetime(
            ordered["reporting_knowledge_at_utc"], utc=True
        )
        ordered["_asof_sort"] = pd.to_datetime(ordered["as_of_timestamp_utc"], utc=True)
        ordered["_fiscal_year_sort"] = pd.to_numeric(
            ordered["fiscal_year"], errors="coerce"
        ).fillna(-1)
        ordered["_version_sort"] = ordered["reporting_version_id"].fillna("").astype(str)
        slot_matrix = (
            ordered.sort_values(
                [
                    "row_id",
                    "feature_id",
                    "period_stratum",
                    "_knowledge_sort",
                    "_fiscal_year_sort",
                    "_asof_sort",
                    "_version_sort",
                ],
                ascending=[True, True, True, False, False, False, True],
                kind="mergesort",
            )
            .drop_duplicates(["row_id", "feature_id", "period_stratum"], keep="first")
            .drop(columns=["_knowledge_sort", "_asof_sort", "_fiscal_year_sort", "_version_sort"])
            .sort_values(["row_id", "feature_id", "period_stratum"], kind="mergesort")
            .reset_index(drop=True)
        )
    slot_matrix.to_parquet(output / "selected_slot_matrix.parquet", index=False)

    any_state = np.zeros(row_count, dtype=bool)
    any_available = np.zeros(row_count, dtype=bool)
    available_slot_count = np.zeros(row_count, dtype=np.int16)
    ambiguous_join = np.zeros(row_count, dtype=bool)
    feature_available = {
        feature: np.zeros(row_count, dtype=bool) for feature in FINANCIAL_FEATURE_IDS
    }
    latest_knowledge = pd.Series(
        pd.NaT, index=np.arange(row_count), dtype="datetime64[ns, UTC]"
    )
    if not slot_matrix.empty:
        slot_rows = slot_matrix["row_id"].to_numpy(dtype=np.int64)
        any_state[slot_rows] = True
        slot_available = slot_matrix["availability_status"].eq("AVAILABLE").to_numpy()
        slot_ambiguous = slot_matrix["availability_status"].eq("AMBIGUOUS_SAME_TIME").to_numpy()
        any_available[slot_rows[slot_available]] = True
        ambiguous_join[slot_rows[slot_ambiguous]] = True
        for row_id, count in slot_matrix.loc[slot_available].groupby("row_id").size().items():
            available_slot_count[int(row_id)] = int(count)
        for feature_id, group in slot_matrix.groupby("feature_id", sort=False):
            feature_rows_available = group.loc[
                group["availability_status"].eq("AVAILABLE"), "row_id"
            ].to_numpy(dtype=np.int64)
            feature_available[feature_id][feature_rows_available] = True
        latest_by_row = slot_matrix.groupby("row_id", sort=False)[
            "reporting_knowledge_at_utc"
        ].max()
        latest_by_row = pd.to_datetime(latest_by_row, utc=True)
        latest_knowledge.loc[latest_by_row.index] = latest_by_row

    diagnostics["financial_any_state_available"] = any_state
    diagnostics["financial_any_feature_available"] = any_available
    diagnostics["financial_available_slot_count"] = available_slot_count
    diagnostics["financial_available_feature_count"] = (
        pd.DataFrame(feature_available).sum(axis=1).astype("int16")
    )
    diagnostics["financial_ambiguous_join"] = ambiguous_join
    diagnostics["financial_latest_knowledge_at_utc"] = latest_knowledge
    cutoff = pd.to_datetime(diagnostics["decision_timestamp_utc"], utc=True)
    diagnostics["financial_latest_filing_age_days"] = (
        (cutoff - latest_knowledge).dt.total_seconds() / 86400.0
    ).round(9)
    diagnostics.to_parquet(output / "join_diagnostics.parquet", index=False)

    matrix_feature_rows = []
    for feature_id in FINANCIAL_FEATURE_IDS:
        for period_key in PERIOD_KEYS:
            group = slot_matrix[
                slot_matrix["feature_id"].eq(feature_id)
                & slot_matrix["period_stratum"].eq(period_key)
            ]
            statuses = group["availability_status"] if not group.empty else pd.Series(dtype="object")
            matrix_feature_rows.append(
                {
                    "feature_id": feature_id,
                    "period_stratum": period_key,
                    "rows_with_state": int(group["row_id"].nunique()),
                    "rows_available": int(statuses.eq("AVAILABLE").sum()),
                    "selected_state_rows": int(len(group)),
                    "rows_missing_or_unresolved": int(
                        statuses.isin(
                            [
                                "MISSING_INPUT",
                                "UNRESOLVED_INPUT",
                                "DENOMINATOR_NONPOSITIVE",
                                "UNIT_MISMATCH",
                            ]
                        ).sum()
                    ),
                    "rows_ambiguous_same_time": int(
                        statuses.eq("AMBIGUOUS_SAME_TIME").sum()
                    ),
                }
            )
    pd.DataFrame(matrix_feature_rows).to_csv(output / "feature_support.csv", index=False)

    coverage = (
        diagnostics.assign(calendar_year=pd.to_datetime(diagnostics["date"]).dt.year)
        .groupby("calendar_year", as_index=False)
        .agg(
            rows=("row_id", "size"),
            rows_any_state=("financial_any_state_available", "sum"),
            rows_any_feature=("financial_any_feature_available", "sum"),
            issuers=("ticker", "nunique"),
        )
    )
    coverage.to_csv(output / "coverage_by_year.csv", index=False)

    period_coverage = (
        slot_matrix.groupby("period_stratum", as_index=False)
        .agg(
            selected_state_rows=("row_id", "size"),
            v2_rows=("row_id", "nunique"),
            issuers=("ticker", "nunique"),
            available_state_rows=(
                "availability_status",
                lambda values: int((values == "AVAILABLE").sum()),
            ),
            ambiguous_state_rows=(
                "availability_status",
                lambda values: int((values == "AMBIGUOUS_SAME_TIME").sum()),
            ),
        )
    )
    period_coverage.to_csv(output / "coverage_by_period.csv", index=False)
    ticker_coverage = (
        diagnostics.groupby("ticker", as_index=False)
        .agg(
            rows=("row_id", "size"),
            rows_any_state=("financial_any_state_available", "sum"),
            rows_any_feature=("financial_any_feature_available", "sum"),
            ambiguous_rows=("financial_ambiguous_join", "sum"),
            available_feature_count=("financial_available_feature_count", "sum"),
        )
    )
    ticker_coverage.to_csv(output / "coverage_by_ticker.csv", index=False)

    age = diagnostics.loc[diagnostics["financial_any_state_available"], "financial_latest_filing_age_days"]
    summary: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "decision_cutoff_contract": DECISION_CUTOFF_CONTRACT,
        "decision_cutoff_timezone": "Asia/Jakarta converted to UTC",
        "v2_source_sha256": v2_sha256,
        "financial_panel_sha256": financial_sha256,
        "v2_rows": int(len(v2)),
        "v2_tickers": int(v2["ticker"].nunique()),
        "v2_date_min": str(pd.to_datetime(v2["date"]).min().date()),
        "v2_date_max": str(pd.to_datetime(v2["date"]).max().date()),
        "v2_session_index_min": int(v2["signal_session_index"].min()),
        "v2_session_index_max": int(v2["signal_session_index"].max()),
        "v2_identity_key_sha256": _key_hash(v2, V2_IDENTITY_COLUMNS),
        "financial_panel_rows": int(len(financial)),
        "financial_panel_tickers": int(financial["ticker"].nunique()),
        "financial_states": int(
            financial[["ticker", "fiscal_year", "as_of_timestamp_utc"]]
            .drop_duplicates()
            .shape[0]
        ),
        "financial_state_any_rows": int(diagnostics["financial_any_state_available"].sum()),
        "financial_any_feature_rows": int(diagnostics["financial_any_feature_available"].sum()),
        "eligible_long_state_rows": int(len(selected_states)),
        "selected_state_rows": int(len(slot_matrix)),
        "period_strata": {
            str(row.period_stratum): {
                "selected_state_rows": int(row.selected_state_rows),
                "v2_rows": int(row.v2_rows),
                "issuers": int(row.issuers),
                "available_state_rows": int(row.available_state_rows),
                "ambiguous_state_rows": int(row.ambiguous_state_rows),
            }
            for row in period_coverage.itertuples(index=False)
        },
        "ticker_coverage": {
            "issuers_with_any_feature": int((ticker_coverage["rows_any_feature"] > 0).sum()),
            "median_rows_any_feature_per_issuer": (
                float(ticker_coverage["rows_any_feature"].median())
                if not ticker_coverage.empty
                else None
            ),
            "top10_rows_any_feature_share": (
                float(
                    ticker_coverage["rows_any_feature"].nlargest(10).sum()
                    / diagnostics["financial_any_feature_available"].sum()
                )
                if int(diagnostics["financial_any_feature_available"].sum()) > 0
                else None
            ),
        },
        "knowledge_time_violations": 0,
        "duplicate_or_ambiguous_join_rows": int(diagnostics["financial_ambiguous_join"].sum()),
        "same_day_publication_rows": int(
            (
                diagnostics["financial_latest_knowledge_at_utc"].notna()
                & (
                    pd.to_datetime(diagnostics["financial_latest_knowledge_at_utc"], utc=True)
                    .dt.tz_convert("Asia/Jakarta").dt.date
                    == pd.to_datetime(diagnostics["date"]).dt.date
                )
            ).sum()
        ),
        "financial_timestamp_conflict_keys": len(conflicts),
        "latest_filing_age_days": {
            "count": int(age.notna().sum()),
            "min": float(age.min()) if age.notna().any() else None,
            "median": float(age.median()) if age.notna().any() else None,
            "q25": float(age.quantile(0.25)) if age.notna().any() else None,
            "q75": float(age.quantile(0.75)) if age.notna().any() else None,
            "max": float(age.max()) if age.notna().any() else None,
        },
        "support_rule_frozen_after_census": "any_feature_available_at_least_one_period_stratum",
        "performance_metrics_computed": False,
        "model_fit": False,
        "outcomes_accessed": False,
        "provider_calls": 0,
        "fresh_forward_accessed": False,
        "forbidden_columns_viewed": [],
    }
    (output / "support_census_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "contract_version": CONTRACT_VERSION,
        "inputs": {
            "v2_common_support": {"path": str(v2_path), "sha256": v2_sha256},
            "financial_feature_panel": {"path": str(financial_panel_path), "sha256": financial_sha256},
        },
        "files": {},
        "performance_metrics_computed": False,
        "outcomes_accessed": False,
    }
    for name in (
        "join_diagnostics.parquet",
        "selected_feature_states.parquet",
        "selected_slot_matrix.parquet",
        "feature_support.csv",
        "coverage_by_year.csv",
        "coverage_by_period.csv",
        "coverage_by_ticker.csv",
        "support_census_summary.json",
    ):
        manifest["files"][name] = sha256_file(output / name)
    (output / "support_census_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def freeze_model_matrix_contract(output_dir: str | Path) -> dict[str, Any]:
    """Persist the exact 25/52/77 feature-order and run contracts.

    This is a definition-only artifact. It does not load labels, instantiate a
    model, or fit/score any candidate.
    """

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "decision_cutoff_contract": DECISION_CUTOFF_CONTRACT,
        "session_role": (
            "Financial information observed by 18:00 Asia/Jakarta on session t "
            "is used for a ranking produced at that cutoff and first actionable "
            "from the next official session."
        ),
        "financial_raw_slot_contract": {
            "count": len(FINANCIAL_SLOT_COLUMNS),
            "order": list(FINANCIAL_SLOT_COLUMNS),
            "feature_order": list(FINANCIAL_FEATURE_IDS),
            "period_order": list(PERIOD_KEYS),
            "fiscal_year_diagnostic_only": True,
        },
        "candidates": {
            name: {
                "feature_count": len(columns),
                "feature_order": list(columns),
                "feature_order_sha256": feature_order_sha256(columns),
            }
            for name, columns in CANDIDATE_FEATURE_COLUMNS.items()
        },
        "preprocessing": {
            "family": CONTROL_PREPROCESSING,
            "missing_handling": MISSING_HANDLING_CONTRACT,
            "fit_scope": "training_fold_only",
        },
        "control_model": {
            "identity": CONTROL_MODEL,
            "hyperparameters": CONTROL_HGB_PARAMETERS,
        },
        "folds": [fold.__dict__ for fold in FROZEN_V2_FOLDS],
        "survivor_rule": SURVIVOR_GATE_RULE,
        "winner_selection_rule": WINNER_SELECTION_RULE,
        "metrics_computed": False,
        "model_fit": False,
        "outcomes_accessed": False,
    }
    path = output / "financial_model_matrix_contract.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "candidate_feature_order_sha256": {
            name: item["feature_order_sha256"]
            for name, item in payload["candidates"].items()
        },
        "financial_slot_count": len(FINANCIAL_SLOT_COLUMNS),
    }


def run_inherited_fold_support_census(
    census_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Audit V2F1..V2F6 support without opening labels or outcomes."""

    census = Path(census_dir)
    diagnostics = pd.read_parquet(census / "join_diagnostics.parquet")
    slot_matrix = pd.read_parquet(census / "selected_slot_matrix.parquet")
    _require_columns(
        diagnostics.columns,
        [*V2_IDENTITY_COLUMNS, "row_id", "financial_any_feature_available"],
        "join diagnostics",
    )
    _require_columns(
        slot_matrix.columns,
        ["row_id", "feature_id", "period_stratum", "availability_status"],
        "selected slot matrix",
    )
    slot_lookup = {
        (feature_id, period_key): f"financial__{feature_id}__{period_key}"
        for feature_id in FINANCIAL_FEATURE_IDS
        for period_key in PERIOD_KEYS
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    folds: dict[str, Any] = {}
    for fold in FROZEN_V2_FOLDS:
        blocks = {
            "train": (fold.train_start, fold.train_end),
            "purge": (fold.purge_start, fold.purge_end),
            "validation": (fold.validation_start, fold.validation_end),
        }
        fold_result: dict[str, Any] = {}
        for block_name, (start, end) in blocks.items():
            rows = diagnostics[
                diagnostics["signal_session_index"].between(start, end, inclusive="both")
            ]
            row_ids = set(rows["row_id"].astype(int))
            matrix_block = slot_matrix[slot_matrix["row_id"].isin(row_ids)]
            availability_by_slot = {
                slot_name: 0 for slot_name in slot_lookup.values()
            }
            observed_by_slot = {slot_name: 0 for slot_name in slot_lookup.values()}
            for (feature_id, period_key), group in matrix_block.groupby(
                ["feature_id", "period_stratum"], sort=False
            ):
                slot_name = slot_lookup[(feature_id, period_key)]
                observed_by_slot[slot_name] = int(group["row_id"].nunique())
                availability_by_slot[slot_name] = int(
                    group["availability_status"].eq("AVAILABLE").sum()
                )
            empty_slots = [
                slot for slot, observed in observed_by_slot.items() if observed == 0
            ]
            all_missing_slots = [
                slot
                for slot, available in availability_by_slot.items()
                if available == 0 and slot not in empty_slots
            ]
            available_slot_values = int(sum(availability_by_slot.values()))
            possible_slot_values = int(len(rows) * len(FINANCIAL_SLOT_COLUMNS))
            feature_available_rows = rows["financial_any_feature_available"].astype(bool)
            fold_result[block_name] = {
                "session_index_start": start,
                "session_index_end": end,
                "v2_rows": int(len(rows)),
                "v2_tickers": int(rows["ticker"].nunique()),
                "financial_available_rows": int(feature_available_rows.sum()),
                "financial_available_tickers": int(
                    rows.loc[feature_available_rows, "ticker"].nunique()
                ),
                "financial_available_slot_values": available_slot_values,
                "financial_possible_slot_values": possible_slot_values,
                "financial_slot_availability_rate": (
                    float(available_slot_values / possible_slot_values)
                    if possible_slot_values
                    else None
                ),
                "empty_slot_count": len(empty_slots),
                "empty_slots": empty_slots,
                "all_missing_slot_count": len(all_missing_slots),
                "all_missing_slots": all_missing_slots,
                "availability_by_slot": availability_by_slot,
                "observed_state_by_slot": observed_by_slot,
            }
        folds[fold.name] = fold_result

    result = {
        "contract_version": CONTRACT_VERSION,
        "decision_cutoff_contract": DECISION_CUTOFF_CONTRACT,
        "financial_slot_count": len(FINANCIAL_SLOT_COLUMNS),
        "folds": folds,
        "labels_loaded": False,
        "outcomes_accessed": False,
        "scores_computed": False,
        "metrics_computed": False,
    }
    path = output / "inherited_fold_support_census.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "files": {path.name: sha256_file(path)},
        "source_files": {
            "join_diagnostics": sha256_file(census / "join_diagnostics.parquet"),
            "selected_slot_matrix": sha256_file(census / "selected_slot_matrix.parquet"),
        },
        "labels_loaded": False,
        "outcomes_accessed": False,
    }
    manifest_path = output / "inherited_fold_support_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "folds": folds,
    }


def freeze_comparison_support(
    join_diagnostics_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Freeze identical row identities for all later candidates, no metrics."""

    diagnostics = pd.read_parquet(join_diagnostics_path)
    required = list(V2_IDENTITY_COLUMNS) + [
        "row_id",
        "decision_timestamp_utc",
        "financial_any_feature_available",
    ]
    _require_columns(diagnostics.columns, required, "join diagnostics")
    support = diagnostics[diagnostics["financial_any_feature_available"]].copy()
    keys = support[["row_id", *V2_IDENTITY_COLUMNS, "decision_timestamp_utc"]].sort_values(
        ["ticker", "date", "signal_session_index", "row_id"], kind="mergesort"
    )
    if keys.duplicated(["ticker", "date", "signal_session_index"]).any():
        raise FinancialAlphaContractError("comparison support contains duplicate V2 identities")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    keys.to_parquet(output / "comparison_support_keys.parquet", index=False)
    result = {
        "contract_version": CONTRACT_VERSION,
        "support_rule": "any_feature_available_at_least_one_period_stratum",
        "rows": int(len(keys)),
        "tickers": int(keys["ticker"].nunique()),
        "identity_key_sha256": _key_hash(keys, V2_IDENTITY_COLUMNS),
        "support_keys_sha256": sha256_file(output / "comparison_support_keys.parquet"),
        "metrics_computed": False,
        "outcomes_accessed": False,
    }
    (output / "comparison_support_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
