"""Frozen Expected Payoff V0 historical feasibility diagnostic.

This module consumes the accepted O2 historical out-of-fold scores.  It does
not fit, refit, or rescore a model and it has no network/provider runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


MAX_ALLOWED_DATE = pd.Timestamp("2026-07-31")
REQUIRED_FOLDS = ("V2F1", "V2F2", "V2F3", "V2F4", "V2F5", "V2F6")
ACCEPTED_OPEN_STATUSES = {"ACCEPTED", "PRESERVED"}


class PayoffDataBlocked(RuntimeError):
    """Raised when a frozen identity or data-readiness contract fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_key_sha256(frame: pd.DataFrame, columns: Iterable[str]) -> str:
    keys = frame.loc[:, list(columns)].copy()
    for column in keys.columns:
        if pd.api.types.is_datetime64_any_dtype(keys[column]):
            keys[column] = keys[column].dt.strftime("%Y-%m-%d")
    keys = keys.sort_values(list(keys.columns), kind="mergesort").reset_index(drop=True)
    payload = keys.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise PayoffDataBlocked(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise PayoffDataBlocked(f"{label} SHA mismatch: expected {expected}, got {actual}")
    return actual


def _dates(frame: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    result = frame.copy()
    result[column] = pd.to_datetime(result[column], errors="coerce")
    if result[column].isna().any():
        raise PayoffDataBlocked(f"invalid dates in {column}")
    return result


def load_calendar(path: Path, expected_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "official calendar")
    calendar = pd.read_csv(path)
    if list(calendar.columns) != ["date"]:
        raise PayoffDataBlocked("official calendar must have exactly one date column")
    calendar = _dates(calendar)
    if calendar.date.duplicated().any() or not calendar.date.is_monotonic_increasing:
        raise PayoffDataBlocked("official calendar is not unique and ordered")
    calendar["session_index"] = np.arange(1, len(calendar) + 1, dtype=int)
    return calendar


def _assert_unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    if frame.duplicated(keys).any():
        raise PayoffDataBlocked(f"duplicate {label} keys: {keys}")


def _finite_positive(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)) and float(value) > 0)
    except (TypeError, ValueError):
        return False


def _lookup(frame: pd.DataFrame, key: tuple[str, pd.Timestamp]):
    try:
        return frame.loc[key]
    except KeyError:
        return None


def load_parent_predictions(path: Path, expected_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "O2 fold predictions")
    parent = pd.read_parquet(path)
    required = {"model", "fold", "ticker", "date", "signal_session_index", "score"}
    if not required.issubset(parent.columns):
        raise PayoffDataBlocked(f"parent prediction schema missing {required - set(parent.columns)}")
    parent = parent.loc[parent.model.eq("O2_OPEN_GEOMETRY")].copy()
    parent = _dates(parent)
    parent["ticker"] = parent.ticker.astype(str).str.upper().str.strip()
    parent["fold"] = parent.fold.astype(str)
    if set(parent.fold) != set(REQUIRED_FOLDS):
        raise PayoffDataBlocked("parent folds do not match frozen six folds")
    if not np.isfinite(parent.score).all():
        raise PayoffDataBlocked("parent contains non-finite scores")
    _assert_unique(parent, ["ticker", "date", "fold"], "parent prediction")
    return parent.sort_values(["signal_session_index", "ticker", "fold"], kind="mergesort").reset_index(drop=True)


def load_features(path: Path, expected_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "canonical feature table")
    features = pd.read_parquet(path, columns=["ticker", "date", "signal_session_index", "atr14_over_close"])
    features = _dates(features)
    features["ticker"] = features.ticker.astype(str).str.upper().str.strip()
    _assert_unique(features, ["ticker", "date"], "canonical feature")
    if not np.isfinite(features.atr14_over_close).all():
        raise PayoffDataBlocked("canonical atr14_over_close contains non-finite values")
    return features


def load_price_frame(path: Path, expected_sha: str, label: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, label)
    frame = pd.read_parquet(path)
    frame = _dates(frame)
    frame["ticker"] = frame.ticker.astype(str).str.upper().str.strip()
    _assert_unique(frame, ["ticker", "date"], label)
    return frame


def load_open_provenance(path: Path, expected_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "accepted Open provenance")
    frame = _dates(pd.read_parquet(path))
    frame["ticker"] = frame.ticker.astype(str).str.upper().str.strip()
    _assert_unique(frame, ["ticker", "date"], "Open provenance")
    if not set(frame.validation_status.dropna().unique()).issubset(ACCEPTED_OPEN_STATUSES | {"UNRESOLVED"}):
        raise PayoffDataBlocked("unknown Open provenance validation status")
    return frame


def load_tradability(path: Path, expected_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "tradability anchors")
    frame = _dates(pd.read_csv(path), "as_of_date").rename(columns={"as_of_date": "date"})
    frame["ticker"] = frame.ticker.astype(str).str.upper().str.strip()
    _assert_unique(frame, ["ticker", "date"], "tradability anchor")
    if set(frame.market.dropna().unique()) != {"REGULAR"}:
        raise PayoffDataBlocked("tradability anchors contain non-Regular market rows")
    return frame


def load_actions(path: Path, expected_sha: str, summary_path: Path, summary_sha: str) -> pd.DataFrame:
    _require_sha(path, expected_sha, "official corporate actions")
    _require_sha(summary_path, summary_sha, "corporate-action summary")
    actions = _dates(pd.read_csv(path), "effective_date").rename(columns={"effective_date": "date"})
    actions["ticker"] = actions.ticker.astype(str).str.upper().str.strip()
    summary = _read_json(summary_path)
    if summary.get("query_complete") is not True:
        raise PayoffDataBlocked("corporate-action query is not complete")
    if set(actions.action.dropna().unique()) - {"stockSplit", "reverseStock", "reverseSplit"}:
        raise PayoffDataBlocked("unexpected corporate-action type")
    return actions


def _spearman(left: pd.Series, right: pd.Series) -> float:
    if len(left) < 2 or left.nunique(dropna=True) < 2 or right.nunique(dropna=True) < 2:
        return float("nan")
    x = left.rank(method="average").to_numpy(dtype=float)
    y = right.rank(method="average").to_numpy(dtype=float)
    return float(np.corrcoef(x, y)[0, 1])


def session_deciles(frame: pd.DataFrame) -> pd.DataFrame:
    """Stable D1..D10 ordinal bins; score ties are resolved by ticker."""
    ordered = frame.sort_values(["score", "ticker"], kind="mergesort", ascending=[True, True]).reset_index(drop=True)
    if ordered.empty:
        return ordered.assign(decile=pd.Series(dtype=int))
    ordinal = np.arange(len(ordered), dtype=int)
    ordered["decile"] = ((ordinal * 10) // len(ordered) + 1).clip(1, 10)
    return ordered


def build_payoff_rows(
    parent: pd.DataFrame,
    features: pd.DataFrame,
    calendar: pd.DataFrame,
    panel: pd.DataFrame,
    open_panel: pd.DataFrame,
    open_provenance: pd.DataFrame,
    tradability: pd.DataFrame,
    actions: pd.DataFrame,
    max_date: pd.Timestamp = MAX_ALLOWED_DATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve every parent row into a coverage ledger and payoff subset."""
    date_to_index = dict(zip(calendar.date, calendar.session_index))
    index_to_date = dict(zip(calendar.session_index, calendar.date))
    feature_map = features.set_index(["ticker", "date"])
    panel_map = panel.set_index(["ticker", "date"])
    open_map = open_panel.set_index(["ticker", "date"])
    prov_map = open_provenance.set_index(["ticker", "date"])
    trade_map = tradability.set_index(["ticker", "date"])
    actions_by_ticker = {ticker: group.date.sort_values().tolist() for ticker, group in actions.groupby("ticker")}

    ledger: list[dict] = []
    for row in parent.itertuples(index=False):
        ticker = str(row.ticker)
        signal_date = pd.Timestamp(row.date)
        record = {
            "ticker": ticker,
            "fold": row.fold,
            "signal_date": signal_date,
            "signal_session_index": int(row.signal_session_index),
            "score": float(row.score),
            "entry_date": pd.NaT,
            "exit_date": pd.NaT,
            "status": "EXCLUDED",
            "exclusion_reason": None,
        }
        expected_signal_index = date_to_index.get(signal_date)
        if expected_signal_index != int(row.signal_session_index):
            record["exclusion_reason"] = "SIGNAL_CALENDAR_IDENTITY_MISMATCH"
            ledger.append(record)
            continue
        entry_index = int(row.signal_session_index) + 1
        exit_index = int(row.signal_session_index) + 10
        entry_date = index_to_date.get(entry_index)
        exit_date = index_to_date.get(exit_index)
        record["entry_date"] = entry_date
        record["exit_date"] = exit_date
        if entry_date is None:
            record["exclusion_reason"] = "MISSING_NEXT_OFFICIAL_SESSION"
            ledger.append(record)
            continue
        if exit_date is None:
            record["exclusion_reason"] = "MISSING_TENTH_OFFICIAL_SESSION"
            ledger.append(record)
            continue
        if signal_date > max_date or entry_date > max_date or exit_date > max_date:
            record["exclusion_reason"] = "POST_CUTOFF_DATE"
            ledger.append(record)
            continue
        if (ticker, signal_date) not in feature_map.index:
            record["exclusion_reason"] = "MISSING_CANONICAL_FEATURE_ROW"
            ledger.append(record)
            continue
        feature = feature_map.loc[(ticker, signal_date)]
        atr_ratio = float(feature.atr14_over_close)
        signal_panel = _lookup(panel_map, (ticker, signal_date))
        if signal_panel is None or not _finite_positive(signal_panel.close):
            record["exclusion_reason"] = "MISSING_SIGNAL_CLOSE"
            ledger.append(record)
            continue
        atr = float(signal_panel.close) * atr_ratio
        if not _finite_positive(atr):
            record["exclusion_reason"] = "INVALID_ATR14"
            ledger.append(record)
            continue
        entry_trade = _lookup(trade_map, (ticker, entry_date))
        exit_trade = _lookup(trade_map, (ticker, exit_date))
        if entry_trade is None or entry_trade.state != "ACTIVE" or entry_trade.market != "REGULAR":
            record["exclusion_reason"] = "ENTRY_NOT_ACTIVE_REGULAR"
            ledger.append(record)
            continue
        if exit_trade is None or exit_trade.state != "ACTIVE" or exit_trade.market != "REGULAR":
            record["exclusion_reason"] = "EXIT_NOT_ACTIVE_REGULAR"
            ledger.append(record)
            continue
        entry_price = _lookup(open_map, (ticker, entry_date))
        entry_prov = _lookup(prov_map, (ticker, entry_date))
        if entry_price is None or entry_prov is None:
            record["exclusion_reason"] = "MISSING_ACCEPTED_OPEN"
            ledger.append(record)
            continue
        if entry_prov.validation_status not in ACCEPTED_OPEN_STATUSES:
            record["exclusion_reason"] = "OPEN_PROVENANCE_NOT_ACCEPTED"
            ledger.append(record)
            continue
        open_value = float(entry_price.open)
        if not _finite_positive(open_value):
            record["exclusion_reason"] = "INVALID_ACCEPTED_OPEN"
            ledger.append(record)
            continue
        exit_price = _lookup(panel_map, (ticker, exit_date))
        if exit_price is None:
            record["exclusion_reason"] = "MISSING_EXIT_CLOSE"
            ledger.append(record)
            continue
        close_value = float(exit_price.close)
        if not _finite_positive(close_value):
            record["exclusion_reason"] = "INVALID_EXIT_CLOSE"
            ledger.append(record)
            continue
        if not bool(exit_price.corporate_action_integrity_verified):
            record["exclusion_reason"] = "EXIT_CORPORATE_ACTION_INTEGRITY_UNVERIFIED"
            ledger.append(record)
            continue
        crossed = [date for date in actions_by_ticker.get(ticker, []) if entry_date <= date <= exit_date]
        if crossed:
            record["exclusion_reason"] = "PRICE_SCALE_CA_CROSSED"
            record["crossed_action_dates"] = ";".join(pd.Timestamp(d).strftime("%Y-%m-%d") for d in crossed)
            ledger.append(record)
            continue
        record.update(
            {
                "status": "RESOLVED",
                "exclusion_reason": "",
                "signal_close": float(signal_panel.close),
                "atr14_over_close": atr_ratio,
                "atr14": atr,
                "entry_open": open_value,
                "exit_close": close_value,
                "entry_gap_pct": open_value / float(signal_panel.close) - 1.0,
                "payoff_atr_gross": (close_value - open_value) / atr,
                "payoff_pct_gross": close_value / open_value - 1.0,
                "entry_open_source": str(entry_prov.open_source),
                "entry_open_validation_status": str(entry_prov.validation_status),
                "entry_open_source_ref": str(entry_prov.source_cache_ref),
                "entry_open_source_raw_sha256": str(entry_prov.source_raw_sha256),
            }
        )
        ledger.append(record)
    ledger_frame = pd.DataFrame(ledger)
    resolved = ledger_frame.loc[ledger_frame.status.eq("RESOLVED")].copy()
    return ledger_frame, resolved


def compute_metrics(resolved: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sessions: list[dict] = []
    deciles: list[dict] = []
    for (fold, date), group in resolved.groupby(["fold", "signal_date"], sort=True):
        scored = group.loc[np.isfinite(group.score) & np.isfinite(group.payoff_atr_gross)].copy()
        eligible = len(scored) >= 30 and scored.score.nunique() > 1 and scored.payoff_atr_gross.nunique() > 1
        record = {
            "fold": fold,
            "signal_date": date,
            "resolved_rows": len(scored),
            "eligible": bool(eligible),
            "session_ic_atr": _spearman(scored.score, scored.payoff_atr_gross) if eligible else np.nan,
            "session_ic_pct": _spearman(scored.score, scored.payoff_pct_gross) if eligible else np.nan,
        }
        ordered = session_deciles(scored)
        if eligible:
            d1 = ordered.loc[ordered.decile.eq(1)]
            d10 = ordered.loc[ordered.decile.eq(10)]
            record.update(
                {
                    "d1_mean_payoff_atr": d1.payoff_atr_gross.mean(),
                    "d10_mean_payoff_atr": d10.payoff_atr_gross.mean(),
                    "session_d10_minus_d1_mean_payoff_atr": d10.payoff_atr_gross.mean() - d1.payoff_atr_gross.mean(),
                    "d1_mean_payoff_pct": d1.payoff_pct_gross.mean(),
                    "d10_mean_payoff_pct": d10.payoff_pct_gross.mean(),
                    "session_d10_minus_d1_mean_payoff_pct": d10.payoff_pct_gross.mean() - d1.payoff_pct_gross.mean(),
                }
            )
            for decile, decile_group in ordered.groupby("decile", sort=True):
                for payoff_name in ("payoff_atr_gross", "payoff_pct_gross"):
                    values = decile_group[payoff_name]
                    deciles.append(
                        {
                            "fold": fold,
                            "signal_date": date,
                            "decile": int(decile),
                            "payoff": payoff_name,
                            "rows": len(values),
                            "mean": values.mean(),
                            "median": values.median(),
                            "q25": values.quantile(0.25),
                            "q75": values.quantile(0.75),
                        }
                    )
        sessions.append(record)
    session_frame = pd.DataFrame(sessions)
    for column in (
        "d1_mean_payoff_atr",
        "d10_mean_payoff_atr",
        "session_d10_minus_d1_mean_payoff_atr",
        "d1_mean_payoff_pct",
        "d10_mean_payoff_pct",
        "session_d10_minus_d1_mean_payoff_pct",
    ):
        if column not in session_frame:
            session_frame[column] = np.nan
    decile_frame = pd.DataFrame(deciles)
    fold_rows: list[dict] = []
    for fold in REQUIRED_FOLDS:
        part = session_frame.loc[(session_frame.fold == fold) & session_frame.eligible]
        ic = part.session_ic_atr.dropna()
        spread = part.session_d10_minus_d1_mean_payoff_atr.dropna()
        def q(frame: pd.Series, quantile: float) -> float:
            return float(frame.quantile(quantile)) if len(frame) else float("nan")
        fold_rows.append(
            {
                "fold": fold,
                "eligible_signal_sessions": len(part),
                "median_session_ic_atr": q(ic, 0.5),
                "mean_session_ic_atr": float(ic.mean()) if len(ic) else np.nan,
                "std_session_ic_atr": float(ic.std(ddof=0)) if len(ic) else np.nan,
                "mean_std_ic_ratio_atr": float(ic.mean() / ic.std(ddof=0)) if len(ic) and ic.std(ddof=0) > 0 else np.nan,
                "median_d10_minus_d1_mean_payoff_atr": q(spread, 0.5),
                "mean_d10_minus_d1_mean_payoff_atr": float(spread.mean()) if len(spread) else np.nan,
                "d1_mean_payoff_atr": float(part.d1_mean_payoff_atr.mean()) if len(part) else np.nan,
                "d10_mean_payoff_atr": float(part.d10_mean_payoff_atr.mean()) if len(part) else np.nan,
                "median_session_ic_pct": float(part.session_ic_pct.median()) if len(part) else np.nan,
                "mean_session_ic_pct": float(part.session_ic_pct.mean()) if len(part) else np.nan,
                "median_d10_minus_d1_mean_payoff_pct": float(part.session_d10_minus_d1_mean_payoff_pct.median()) if len(part) else np.nan,
                "mean_d10_minus_d1_mean_payoff_pct": float(part.session_d10_minus_d1_mean_payoff_pct.mean()) if len(part) else np.nan,
            }
        )
    return session_frame, pd.DataFrame(fold_rows), decile_frame


def _coverage_table(ledger: pd.DataFrame, key: str) -> pd.DataFrame:
    if key == "fold":
        grouped = ledger.groupby("fold", sort=True)
    elif key == "year":
        grouped = ledger.assign(year=ledger.signal_date.dt.year).groupby("year", sort=True)
    else:
        raise ValueError(key)
    result = grouped.agg(parent_rows=("status", "size"), resolved_rows=("status", lambda x: int((x == "RESOLVED").sum())))
    result["coverage_ratio"] = result.resolved_rows / result.parent_rows
    return result.reset_index()


def run_diagnostic(config: dict, output_dir: Path) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PayoffDataBlocked(f"output directory must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.resolve()

    o2_manifest_path = Path(config["o2_manifest_path"])
    _require_sha(o2_manifest_path, config["o2_manifest_sha256"], "O2 artifact manifest")
    o2_manifest = _read_json(o2_manifest_path)
    if o2_manifest.get("status") != "O2_SURVIVOR":
        raise PayoffDataBlocked("O2 parent is not O2_SURVIVOR")
    if o2_manifest.get("preflight_contract", {}).get("fresh_forward_outcomes_accessed") is not False:
        raise PayoffDataBlocked("parent forward-outcome flag is not false")
    parent = load_parent_predictions(Path(config["o2_predictions_path"]), config["o2_predictions_sha256"])
    calendar = load_calendar(Path(config["calendar_path"]), config["calendar_sha256"])
    for name, expected in o2_manifest.get("artifact_sha256", {}).items():
        _require_sha(o2_manifest_path.parent / name, expected, f"O2 manifest artifact {name}")
    _require_sha(Path(config["security_master_path"]), config["security_master_sha256"], "PIT security master")
    _require_sha(Path(config["v3_b_training_table_path"]), config["v3_b_training_table_sha256"], "V3-B training table")
    _require_sha(Path(config["v3_b_manifest_path"]), config["v3_b_manifest_sha256"], "V3-B final manifest")
    panel = load_price_frame(Path(config["panel_path"]), config["panel_sha256"], "immutable panel")
    open_panel = load_price_frame(Path(config["open_panel_path"]), config["open_panel_sha256"], "accepted Open panel")
    open_prov = load_open_provenance(Path(config["open_provenance_path"]), config["open_provenance_sha256"])
    features = load_features(Path(config["feature_path"]), config["feature_sha256"])
    tradability = load_tradability(Path(config["tradability_path"]), config["tradability_sha256"])
    actions = load_actions(
        Path(config["actions_path"]),
        config["actions_sha256"],
        Path(config["actions_summary_path"]),
        config["actions_summary_sha256"],
    )
    for date in parent.date:
        if date > MAX_ALLOWED_DATE:
            raise PayoffDataBlocked("parent contains post-cutoff signal date")
    if int(parent.signal_session_index.max()) + 10 > len(calendar):
        raise PayoffDataBlocked("parent horizon exceeds verified calendar")

    parent_key_columns = ["ticker", "date", "fold", "signal_session_index"]
    parent_key_sha = stable_key_sha256(parent, parent_key_columns)
    ledger, resolved = build_payoff_rows(parent, features, calendar, panel, open_panel, open_prov, tradability, actions)
    resolved_key_sha = stable_key_sha256(resolved, ["ticker", "signal_date", "fold", "signal_session_index"])
    sessions, fold_metrics, deciles = compute_metrics(resolved)
    coverage = _coverage_table(ledger, "fold")
    coverage_year = _coverage_table(ledger, "year")
    reasons = ledger.exclusion_reason.replace({"": np.nan}).fillna("RESOLVED").value_counts().rename_axis("exclusion_reason").reset_index(name="rows")
    fold_metrics = fold_metrics.merge(coverage, on="fold", how="left")
    readiness_by_fold = fold_metrics.coverage_ratio.ge(0.85) & fold_metrics.eligible_signal_sessions.ge(80)
    global_coverage = float(len(resolved) / len(parent)) if len(parent) else 0.0
    data_ready = bool(global_coverage >= 0.90 and readiness_by_fold.all() and parent_key_sha == config["expected_parent_key_sha256"])
    median_ic = float(fold_metrics.median_session_ic_atr.median()) if data_ready else np.nan
    q25_ic = float(fold_metrics.median_session_ic_atr.quantile(0.25)) if data_ready else np.nan
    positive_ic = int((fold_metrics.median_session_ic_atr > 0).sum()) if data_ready else 0
    median_spread = float(fold_metrics.mean_d10_minus_d1_mean_payoff_atr.median()) if data_ready else np.nan
    positive_spread = int((fold_metrics.mean_d10_minus_d1_mean_payoff_atr > 0).sum()) if data_ready else 0
    if not data_ready:
        verdict = "EXPECTED_PAYOFF_V0_DATA_BLOCKED"
    elif median_ic > 0 and q25_ic > 0 and positive_ic >= 4 and median_spread > 0 and positive_spread >= 4:
        verdict = "EXPECTED_PAYOFF_V0_FEASIBILITY_GO"
    else:
        verdict = "EXPECTED_PAYOFF_V0_NO_SIGNAL"

    preflight = {
        "schema": "idx-trade/expected-payoff-v0-feasibility-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_allowed_date": str(MAX_ALLOWED_DATE.date()),
        "o2_manifest_path": str(o2_manifest_path),
        "o2_manifest_sha256": config["o2_manifest_sha256"],
        "o2_predictions_sha256": config["o2_predictions_sha256"],
        "parent_o2_model": "O2_OPEN_GEOMETRY",
        "parent_o2_rows": len(parent),
        "parent_o2_key_sha256": parent_key_sha,
        "expected_parent_key_sha256": config["expected_parent_key_sha256"],
        "canonical_feature_path": config["feature_path"],
        "canonical_feature_sha256": config["feature_sha256"],
        "panel_sha256": config["panel_sha256"],
        "calendar_sha256": config["calendar_sha256"],
        "security_master_sha256": config["security_master_sha256"],
        "v3_b_training_table_sha256": config["v3_b_training_table_sha256"],
        "v3_b_manifest_sha256": config["v3_b_manifest_sha256"],
        "accepted_open_panel_sha256": config["open_panel_sha256"],
        "accepted_open_provenance_sha256": config["open_provenance_sha256"],
        "tradability_sha256": config["tradability_sha256"],
        "corporate_actions_sha256": config["actions_sha256"],
        "corporate_actions_summary_sha256": config["actions_summary_sha256"],
        "corporate_actions_summary_path": config["actions_summary_path"],
        "provider_calls": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "o2_model_modified": False,
        "payoff_model_fit": False,
        "no_price_repair_or_synthesis": True,
    }
    parent_identity = {
        "model": "O2_OPEN_GEOMETRY",
        "rows": len(parent),
        "folds": list(REQUIRED_FOLDS),
        "parent_predictions_sha256": config["o2_predictions_sha256"],
        "stable_parent_key_sha256": parent_key_sha,
        "score_recomputed": False,
        "scores_consumed_exactly": True,
    }
    resolved = resolved.copy()
    for col in ["signal_date", "entry_date", "exit_date"]:
        resolved[col] = pd.to_datetime(resolved[col]).dt.strftime("%Y-%m-%d")
    ledger_out = ledger.copy()
    for col in ["signal_date", "entry_date", "exit_date"]:
        ledger_out[col] = pd.to_datetime(ledger_out[col]).dt.strftime("%Y-%m-%d")
    artifact_frames = {
        "payoff_row_coverage.csv": ledger_out,
        "resolved_payoff_rows.parquet": resolved,
        "coverage_summary.csv": pd.DataFrame([{"parent_rows": len(parent), "resolved_rows": len(resolved), "global_coverage_ratio": global_coverage, "data_ready": data_ready}]),
        "coverage_by_fold.csv": coverage,
        "coverage_by_year.csv": coverage_year,
        "exclusion_reasons.csv": reasons,
        "session_metrics.csv": sessions,
        "fold_metrics.csv": fold_metrics,
        "decile_payoff_summary.csv": deciles,
    }
    (output_dir / "preflight_contract.json").write_text(json.dumps(preflight, indent=2, default=str), encoding="utf-8")
    (output_dir / "parent_o2_predictions_identity.json").write_text(json.dumps(parent_identity, indent=2), encoding="utf-8")
    for name, frame in artifact_frames.items():
        if name.endswith(".parquet"):
            frame.to_parquet(output_dir / name, index=False)
        else:
            frame.to_csv(output_dir / name, index=False)
    aggregate = {
        "schema": "idx-trade/expected-payoff-v0-aggregate-v1",
        "data_ready": data_ready,
        "parent_rows": len(parent),
        "resolved_rows": len(resolved),
        "global_coverage_ratio": global_coverage,
        "median_fold_median_ic_atr": median_ic,
        "q25_fold_median_ic_atr": q25_ic,
        "positive_fold_median_ic_count": positive_ic,
        "median_fold_mean_d10_minus_d1_payoff_atr": median_spread,
        "positive_fold_mean_spread_count": positive_spread,
        "fold_count": 6,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
        "payoff_model_fit": False,
    }
    (output_dir / "aggregate_metrics.json").write_text(json.dumps(aggregate, indent=2, allow_nan=False), encoding="utf-8")
    decision = {
        "verdict": verdict,
        "data_ready": data_ready,
        "readiness_gate": {"global_coverage": global_coverage, "fold_coverage_min": float(fold_metrics.coverage_ratio.min()), "fold_eligible_sessions_min": int(fold_metrics.eligible_signal_sessions.min())},
        "feasibility_gate": {"median_ic": median_ic, "q25_ic": q25_ic, "positive_ic_folds": positive_ic, "median_spread": median_spread, "positive_spread_folds": positive_spread},
        "one_shot": True,
    }
    (output_dir / "survivor_decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False), encoding="utf-8")
    manifest = {}
    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json":
            manifest[path.name] = sha256_file(path)
    artifact_manifest = {
        "schema": "idx-trade/expected-payoff-v0-artifact-manifest-v1",
        "status": verdict,
        "artifact_sha256": manifest,
        "parent_o2_predictions_sha256": config["o2_predictions_sha256"],
        "parent_o2_key_sha256": parent_key_sha,
        "resolved_payoff_key_sha256": resolved_key_sha,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
        "o2_model_modified": False,
        "payoff_model_fit": False,
        "python": sys.version,
        "platform": platform.platform(),
    }
    (output_dir / "artifact_manifest.json").write_text(json.dumps(artifact_manifest, indent=2), encoding="utf-8")
    return {"verdict": verdict, "manifest_sha256": sha256_file(output_dir / "artifact_manifest.json"), "manifest": artifact_manifest, "aggregate": aggregate, "decision": decision}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        result = run_diagnostic(_read_json(args.config), args.output_dir)
    except PayoffDataBlocked as exc:
        print(f"EXPECTED_PAYOFF_V0_DATA_BLOCKED: {exc}")
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
