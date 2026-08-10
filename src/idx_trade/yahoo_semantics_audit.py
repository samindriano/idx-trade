from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .providers.idx_corporate_actions import cross_check_yahoo_split_events
from .security_master import normalise_ticker
from .tier2_open_audit import (
    AUDIT_COLUMNS,
    DEFAULT_SAMPLE_SEED,
    PREFERRED_SAMPLE_TICKERS,
    SAMPLE_ROLE_ORDER,
    _as_float,
    _stable_rank,
    _write_csv,
    _write_json,
    audit_provider_rows,
    build_audit_candidates,
    run_yahoo_audit,
)


DEFAULT_YAHOO_SAMPLE_SIZE = 300
DEFAULT_MIN_UNIQUE_TICKERS = 120
DEFAULT_MIN_SPLIT_TICKERS = 30
DEFAULT_MIN_NON_SPLIT_TICKERS = 80
DEFAULT_EXPECTED_PANEL_SHA256 = (
    "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
)
YAHOO_SAMPLE_COLUMNS = (
    *AUDIT_COLUMNS,
    "split_stratum",
    "split_factor_verified",
    "date_stratum",
)


def _normalise_actions(actions: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "effective_date"}
    missing = required - set(actions.columns)
    if missing:
        raise ValueError(f"Corporate-action evidence missing: {sorted(missing)}")
    data = actions.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["effective_date"] = pd.to_datetime(
        data["effective_date"], errors="coerce"
    ).dt.tz_localize(None).dt.normalize()
    if "ratio" not in data.columns:
        data["ratio"] = np.nan
    data["ratio"] = pd.to_numeric(data["ratio"], errors="coerce")
    return data.dropna(subset=["ticker", "effective_date"]).copy()


def _action_sets(actions: pd.DataFrame) -> tuple[set[str], set[str]]:
    data = _normalise_actions(actions)
    action_tickers = set(data["ticker"])
    factor_tickers = set(data.loc[data["ratio"].gt(0), "ticker"])
    return action_tickers, factor_tickers


def _date_strata(data: pd.DataFrame) -> pd.Series:
    dates = pd.to_datetime(data["date"]).dt.normalize()
    first = dates.min()
    last = dates.max()
    if pd.isna(first) or pd.isna(last) or first == last:
        return pd.Series("ALL", index=data.index, dtype="object")
    span = (last - first).days
    early_end = first + pd.Timedelta(days=span / 3)
    mid_end = first + pd.Timedelta(days=2 * span / 3)
    return pd.Series(
        np.select(
            [dates.le(early_end), dates.le(mid_end)],
            ["EARLY", "MID"],
            default="LATE",
        ),
        index=data.index,
        dtype="object",
    )


def build_yahoo_semantics_candidates(
    panel: pd.DataFrame,
    wildan_diagnostics: pd.DataFrame,
    *,
    corporate_actions: pd.DataFrame,
    security_master: pd.DataFrame | None = None,
    tradability_intervals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add frozen split/date strata before any provider query."""

    candidates = build_audit_candidates(
        panel,
        wildan_diagnostics,
        security_master=security_master,
        corporate_actions=corporate_actions,
        tradability_intervals=tradability_intervals,
    ).copy()
    action_tickers, factor_tickers = _action_sets(corporate_actions)
    candidates["split_stratum"] = np.where(
        candidates["ticker"].isin(action_tickers), "SPLIT_EVIDENCE", "NON_SPLIT"
    )
    candidates["split_factor_verified"] = candidates["ticker"].isin(factor_tickers)
    candidates["date_stratum"] = _date_strata(candidates)
    return candidates


def _candidate_rank(data: pd.DataFrame, seed: int) -> pd.DataFrame:
    ranked = data.copy()
    ranked["_rank"] = [
        _stable_rank(seed, ticker, date, role)
        for ticker, date, role in zip(
            ranked["ticker"], ranked["date"], ranked["sample_role"]
        )
    ]
    return ranked.sort_values(
        ["_rank", "ticker", "date"], kind="mergesort"
    ).reset_index(drop=True)


def _nearest_action_distance(
    ticker: str, date: pd.Timestamp, action_dates: Mapping[str, list[pd.Timestamp]]
) -> int:
    dates = action_dates.get(ticker, [])
    if not dates:
        return 10**9
    return min(abs((pd.Timestamp(date) - event).days) for event in dates)


def select_yahoo_semantics_sample(
    candidates: pd.DataFrame,
    corporate_actions: pd.DataFrame,
    *,
    seed: int = DEFAULT_SAMPLE_SEED,
    target_size: int = DEFAULT_YAHOO_SAMPLE_SIZE,
    minimum_unique_tickers: int = DEFAULT_MIN_UNIQUE_TICKERS,
    minimum_split_tickers: int = DEFAULT_MIN_SPLIT_TICKERS,
    minimum_non_split_tickers: int = DEFAULT_MIN_NON_SPLIT_TICKERS,
    minimum_existing: int = 100,
    minimum_wildan_row: int = 100,
    minimum_wildan_no_row: int = 25,
) -> pd.DataFrame:
    """Select a deterministic, provider-outcome-independent broad sample."""

    required = (set(AUDIT_COLUMNS) - {"sample_id"}) | {
        "split_stratum",
        "split_factor_verified",
        "date_stratum",
    }
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Yahoo candidates missing: {sorted(missing)}")
    if target_size < minimum_unique_tickers * 2:
        raise ValueError("target_size must allow at least two rows per required ticker")

    data = candidates.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data = data.dropna(subset=["ticker", "date"])
    data = data.drop_duplicates(["ticker", "date"], keep="last")
    ranked = _candidate_rank(data, seed)
    actions = _normalise_actions(corporate_actions)
    action_dates = {
        ticker: sorted(group["effective_date"].drop_duplicates().tolist())
        for ticker, group in actions.groupby("ticker", sort=True)
    }
    ranked["_action_distance"] = [
        _nearest_action_distance(ticker, date, action_dates)
        for ticker, date in zip(ranked["ticker"], ranked["date"])
    ]
    selected_keys: set[tuple[str, pd.Timestamp]] = set()

    def add_row(row: pd.Series) -> bool:
        key = (normalise_ticker(row["ticker"]), pd.Timestamp(row["date"]).normalize())
        if key in selected_keys or len(selected_keys) >= target_size:
            return False
        selected_keys.add(key)
        return True

    def add_one_per_ticker(
        tickers: Iterable[str], *, nearest_action: bool = False
    ) -> None:
        for ticker in sorted(set(tickers)):
            pool = ranked[ranked["ticker"].eq(ticker)]
            if pool.empty:
                continue
            order = ["_action_distance", "_rank", "date"] if nearest_action else ["_rank", "date"]
            add_row(pool.sort_values(order, kind="mergesort").iloc[0])

    split_tickers = set(ranked.loc[ranked["split_stratum"].eq("SPLIT_EVIDENCE"), "ticker"])
    non_split_tickers = set(ranked.loc[ranked["split_stratum"].eq("NON_SPLIT"), "ticker"])
    if len(split_tickers) < minimum_split_tickers:
        raise ValueError(
            f"insufficient official split-evidence tickers: {len(split_tickers)}"
        )
    if len(non_split_tickers) < minimum_non_split_tickers:
        raise ValueError(
            f"insufficient non-split tickers: {len(non_split_tickers)}"
        )

    # One action-adjacent row per official split-evidence ticker preserves the
    # split stratum without looking at any provider response.
    add_one_per_ticker(split_tickers, nearest_action=True)
    add_one_per_ticker(sorted(non_split_tickers)[:minimum_non_split_tickers])
    add_one_per_ticker(PREFERRED_SAMPLE_TICKERS)

    # Preserve broad temporal coverage before filling role quotas.
    for date_stratum in ("EARLY", "MID", "LATE"):
        pool = ranked[ranked["date_stratum"].eq(date_stratum)]
        current_in_stratum = int(
            sum(
                1
                for ticker, date in selected_keys
                if ((ranked["ticker"].eq(ticker)) & ranked["date"].eq(date) & ranked["date_stratum"].eq(date_stratum)).any()
            )
        )
        for row in pool.sort_values(["_rank", "ticker", "date"], kind="mergesort").itertuples(index=False):
            if current_in_stratum >= min(40, target_size // 3):
                break
            if add_row(pd.Series(row._asdict())):
                current_in_stratum += 1

    def add_role(role: str, minimum: int) -> None:
        current = int(
            sum(
                1
                for ticker, date in selected_keys
                if ((ranked["ticker"].eq(ticker)) & ranked["date"].eq(date) & ranked["sample_role"].eq(role)).any()
            )
        )
        if current >= minimum:
            return
        pool = ranked[ranked["sample_role"].eq(role)]
        for _, row in pool.iterrows():
            if add_row(row):
                current += 1
            if current >= minimum or len(selected_keys) >= target_size:
                break

    add_role("KNOWN_EXISTING_OPEN", minimum_existing)
    add_role("MISSING_OPEN_WILDAN_ROW", minimum_wildan_row)
    add_role("MISSING_OPEN_WILDAN_NO_ROW", minimum_wildan_no_row)

    for _, row in ranked.iterrows():
        if len(selected_keys) >= target_size:
            break
        add_row(row)

    selected = ranked[
        ranked.apply(
            lambda row: (row["ticker"], pd.Timestamp(row["date"]).normalize())
            in selected_keys,
            axis=1,
        )
    ].copy()
    role_order = {role: index for index, role in enumerate(SAMPLE_ROLE_ORDER)}
    selected["_role_order"] = selected["sample_role"].map(role_order).fillna(99)
    selected = selected.sort_values(
        ["_role_order", "split_stratum", "ticker", "date"], kind="mergesort"
    ).reset_index(drop=True)
    selected["sample_id"] = [f"YH-{index:04d}" for index in range(1, len(selected) + 1)]
    selected = selected[list(YAHOO_SAMPLE_COLUMNS)]

    counts = selected["sample_role"].value_counts()
    if len(set(selected["ticker"])) < minimum_unique_tickers:
        raise ValueError("deterministic sample did not reach unique-ticker minimum")
    if int((selected["split_stratum"] == "SPLIT_EVIDENCE").sum()) < minimum_split_tickers:
        raise ValueError("deterministic sample did not retain split-evidence minimum")
    if selected.loc[selected["split_stratum"].eq("SPLIT_EVIDENCE"), "ticker"].nunique() < minimum_split_tickers:
        raise ValueError("deterministic sample did not retain split ticker minimum")
    if selected.loc[selected["split_stratum"].eq("NON_SPLIT"), "ticker"].nunique() < minimum_non_split_tickers:
        raise ValueError("deterministic sample did not retain non-split ticker minimum")
    if len(selected) < 240:
        raise ValueError(f"deterministic sample too small: {len(selected)}")
    for role, minimum in (
        ("KNOWN_EXISTING_OPEN", minimum_existing),
        ("MISSING_OPEN_WILDAN_ROW", minimum_wildan_row),
        ("MISSING_OPEN_WILDAN_NO_ROW", minimum_wildan_no_row),
    ):
        if int(counts.get(role, 0)) < minimum:
            raise ValueError(f"sample role {role} below minimum")
    return selected


def yahoo_sample_manifest_sha256(sample: pd.DataFrame) -> str:
    data = sample[list(YAHOO_SAMPLE_COLUMNS)].copy()
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
    payload = data.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _authoritative_event_map(actions: pd.DataFrame) -> dict[str, dict[pd.Timestamp, float | None]]:
    data = _normalise_actions(actions)
    result: dict[str, dict[pd.Timestamp, float | None]] = {}
    for (ticker, date), group in data.groupby(["ticker", "effective_date"], sort=True):
        valid = sorted(set(float(value) for value in group["ratio"].dropna() if float(value) > 0))
        if len(valid) > 1:
            result.setdefault(ticker, {})[date] = None
        elif valid:
            result.setdefault(ticker, {})[date] = valid[0]
        else:
            result.setdefault(ticker, {})[date] = None
    return result


def authoritative_cumulative_split_factor(
    ticker: str,
    date: object,
    actions: pd.DataFrame,
) -> tuple[float | None, str]:
    """Return only a factor supported by pre-existing official action rows."""

    events = _authoritative_event_map(actions).get(normalise_ticker(ticker), {})
    target = pd.Timestamp(date).normalize()
    future = [(event_date, ratio) for event_date, ratio in events.items() if event_date > target]
    if any(ratio is None for _, ratio in future):
        return None, "FACTOR_UNAVAILABLE_INCOMPLETE_OFFICIAL_ACTION"
    factor = math.prod(float(ratio) for _, ratio in future)
    return float(factor), "NO_FUTURE_SPLIT" if factor == 1.0 else "OFFICIAL_CUMULATIVE_FACTOR"


def reconstruct_split_scale_rows(
    sample: pd.DataFrame,
    provider_audit: pd.DataFrame,
    corporate_actions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run diagnostic reconstruction without changing direct admission."""

    actions = _normalise_actions(corporate_actions)
    rows: list[dict[str, Any]] = []
    for row in provider_audit.itertuples(index=False):
        record = row._asdict()
        factor, factor_status = authoritative_cumulative_split_factor(
            row.ticker, row.date, actions
        )
        raw_open = _as_float(row.raw_open)
        raw_values = {
            name: _as_float(getattr(row, f"raw_{name}"))
            for name in ("open", "high", "low", "close")
        }
        transformed = {
            name: (value * factor if factor is not None else np.nan)
            for name, value in raw_values.items()
        }
        panel_values = {
            "open": _as_float(row.panel_open),
            "high": _as_float(row.panel_high),
            "low": _as_float(row.panel_low),
            "close": _as_float(row.panel_close),
        }
        returned = row.diagnostic != "NO_PROVIDER_ROW"
        split_mismatch = bool(returned and not bool(row.hlc_exact))
        h_l_c_exact = bool(
            factor is not None
            and factor != 1.0
            and all(
                np.isfinite(transformed[name]) and transformed[name] == panel_values[name]
                for name in ("high", "low", "close")
            )
        )
        transformed_open_valid = bool(
            h_l_c_exact
            and np.isfinite(transformed["open"])
            and transformed["open"] > 0
            and panel_values["low"] <= transformed["open"] <= panel_values["high"]
        )
        known = row.sample_role == "KNOWN_EXISTING_OPEN"
        known_exact = (
            bool(transformed_open_valid and transformed["open"] == panel_values["open"])
            if known
            else None
        )
        admissible = bool(transformed_open_valid and not known)
        record.update(
            {
                "official_split_factor": factor,
                "official_split_factor_status": factor_status,
                "split_scale_mismatch": split_mismatch,
                "reconstructed_open": transformed["open"],
                "reconstructed_high": transformed["high"],
                "reconstructed_low": transformed["low"],
                "reconstructed_close": transformed["close"],
                "reconstructed_hlc_exact": h_l_c_exact,
                "reconstructed_known_open_exact": known_exact,
                "reconstructed_admission_status": (
                    "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE" if admissible else "REJECTED"
                ),
                "reconstructed_diagnostic": (
                    "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"
                    if h_l_c_exact and transformed_open_valid
                    else "SPLIT_SCALE_HLC_MISMATCH"
                    if factor is not None and factor != 1.0 and returned
                    else factor_status
                ),
            }
        )
        rows.append(record)
    audit = pd.DataFrame(rows)
    missing = audit[audit["sample_role"] != "KNOWN_EXISTING_OPEN"]
    known = audit[audit["sample_role"] == "KNOWN_EXISTING_OPEN"]
    summary = {
        "split_scale_mismatch_count": int(audit["split_scale_mismatch"].sum()),
        "official_factor_rows": int(audit["official_split_factor"].notna().sum()),
        "reconstructed_hlc_exact_count": int(audit["reconstructed_hlc_exact"].sum()),
        "independently_verified_reconstructable_count": int(
            audit["reconstructed_diagnostic"].eq("SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE").sum()
        ),
        "reconstructed_known_open_comparison_rows": int(known["reconstructed_known_open_exact"].notna().sum()),
        "reconstructed_known_open_exact_count": int(known["reconstructed_known_open_exact"].fillna(False).sum()),
        "reconstructed_missing_open_admissible_count": int(
            missing["reconstructed_admission_status"].eq("SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE").sum()
        ),
    }
    return audit, summary


def _stratum_summary(audit: pd.DataFrame) -> dict[str, dict[str, int | float | None]]:
    result: dict[str, dict[str, int | float | None]] = {}
    for stratum, group in audit.groupby("split_stratum", sort=True):
        returned = group[group["diagnostic"] != "NO_PROVIDER_ROW"]
        known = group[group["sample_role"] == "KNOWN_EXISTING_OPEN"]
        missing = group[group["sample_role"] != "KNOWN_EXISTING_OPEN"]
        result[stratum] = {
            "sample_rows": int(len(group)),
            "unique_tickers": int(group["ticker"].nunique()),
            "returned_rows": int(len(returned)),
            "direct_hlc_exact": int(returned["hlc_exact"].sum()),
            "direct_known_open_exact": int(known["known_open_exact"].fillna(False).sum()),
            "direct_missing_open_admissible": int(
                missing["admission_status"].eq("ADMISSIBLE_OPEN_EVIDENCE").sum()
            ),
            "split_scale_mismatches": int(group["split_scale_mismatch"].sum()),
            "reconstructed_hlc_exact": int(group["reconstructed_hlc_exact"].sum()),
            "reconstructed_known_open_exact": int(
                group["reconstructed_known_open_exact"].fillna(False).sum()
            ),
            "reconstructed_missing_open_admissible": int(
                group["reconstructed_admission_status"].eq("SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE").sum()
            ),
        }
    return result


def run_yahoo_semantics_audit(
    *,
    panel_path: str | Path,
    wildan_diagnostics_path: str | Path,
    official_actions_path: str | Path,
    output_dir: str | Path,
    expected_panel_sha256: str = DEFAULT_EXPECTED_PANEL_SHA256,
    security_master_path: str | Path | None = None,
    tradability_intervals_path: str | Path | None = None,
    seed: int = DEFAULT_SAMPLE_SEED,
) -> dict[str, Any]:
    panel_file = Path(panel_path)
    wildan_file = Path(wildan_diagnostics_path)
    actions_file = Path(official_actions_path)
    output = Path(output_dir)
    for path in (panel_file, wildan_file, actions_file):
        if not path.is_file():
            raise FileNotFoundError(f"required audit input missing: {path}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty audit directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    panel_sha_before = sha256_file(panel_file)
    if panel_sha_before != expected_panel_sha256:
        raise RuntimeError(f"Immutable panel SHA mismatch before runtime: {panel_sha_before}")
    panel = pd.read_parquet(panel_file)
    diagnostics = pd.read_csv(wildan_file)
    actions = pd.read_csv(actions_file, parse_dates=["effective_date", "listing_date"])
    security_master = (
        pd.read_csv(security_master_path, parse_dates=["listed_from", "listed_to"])
        if security_master_path and Path(security_master_path).is_file()
        else None
    )
    intervals = (
        pd.read_csv(
            tradability_intervals_path,
            parse_dates=["effective_from", "effective_to"],
        )
        if tradability_intervals_path and Path(tradability_intervals_path).is_file()
        else None
    )
    candidates = build_yahoo_semantics_candidates(
        panel,
        diagnostics,
        corporate_actions=actions,
        security_master=security_master,
        tradability_intervals=intervals,
    )
    sample = select_yahoo_semantics_sample(candidates, actions, seed=seed)
    sample_hash = yahoo_sample_manifest_sha256(sample)
    _write_csv(sample, output / "yahoo_semantics_sample_manifest.csv")
    _write_json(
        {
            "seed": seed,
            "sample_rows": int(len(sample)),
            "unique_tickers": int(sample["ticker"].nunique()),
            "sample_sha256": sample_hash,
            "role_counts": {str(key): int(value) for key, value in sample["sample_role"].value_counts().items()},
            "split_stratum": {
                str(key): {"rows": int(value), "tickers": int(sample.loc[sample["split_stratum"].eq(key), "ticker"].nunique())}
                for key, value in sample["split_stratum"].value_counts().items()
            },
            "date_stratum_counts": {str(key): int(value) for key, value in sample["date_stratum"].value_counts().items()},
            "panel_outcome_independent": True,
        },
        output / "yahoo_semantics_sample_manifest.json",
    )

    yahoo = run_yahoo_audit(sample)
    direct_audit, direct_summary = audit_provider_rows(
        sample, yahoo["rows"], "YAHOO_YFINANCE"
    )
    reconstructed_audit, reconstruction_summary = reconstruct_split_scale_rows(
        sample, direct_audit, actions
    )
    joined = reconstructed_audit.merge(
        sample[["sample_id", "split_stratum", "split_factor_verified", "date_stratum"]],
        on="sample_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_sample"),
    )
    _write_csv(yahoo["rows"], output / "yahoo_candidate_rows.csv")
    _write_csv(joined, output / "yahoo_semantics_row_audit.csv")
    cross_check = cross_check_yahoo_split_events(actions, yahoo["rows"])
    _write_csv(cross_check, output / "yahoo_split_cross_check.csv")

    returned_tickers = set(yahoo["rows"]["ticker"].dropna().map(normalise_ticker))
    sample_tickers = set(sample["ticker"])
    date_coverage = {}
    for date_stratum, group in joined.groupby("date_stratum", sort=True):
        returned = group[group["diagnostic"] != "NO_PROVIDER_ROW"]
        date_coverage[date_stratum] = {
            "sample_rows": int(len(group)),
            "returned_rows": int(len(returned)),
            "exact_ticker_date_rows": int(len(returned)),
            "direct_hlc_exact": int(returned["hlc_exact"].sum()),
        }

    source_summary = {
        **yahoo["summary"],
        "sample_rows_requested": int(len(sample)),
        "sample_unique_tickers": int(sample["ticker"].nunique()),
        "provider_unique_tickers_returned": int(len(returned_tickers)),
        "ticker_coverage_rate": float(len(returned_tickers) / len(sample_tickers)) if sample_tickers else None,
        "exact_ticker_date_coverage": int(direct_summary["exact_ticker_date_rows"]),
        "direct_hlc_exact": int(direct_summary["hlc_exact_count"]),
        "direct_known_open_exact": int(direct_summary["known_open_exact_count"]),
        "direct_admissible_missing_open": int(direct_summary["admissible_missing_open_rows"]),
        "direct_rejection_breakdown": direct_summary["rejection_breakdown"],
        "split_scale": reconstruction_summary,
        "stratum_metrics": _stratum_summary(joined),
        "date_coverage": date_coverage,
        "fren_masa_mfin": {
            ticker: {
                "sampled": bool(ticker in sample_tickers),
                "provider_rows": int((joined["ticker"].eq(ticker) & joined["diagnostic"].ne("NO_PROVIDER_ROW")).sum()),
                "direct_admissible_missing_open": int(
                    joined.loc[joined["ticker"].eq(ticker), "admission_status"].eq("ADMISSIBLE_OPEN_EVIDENCE").sum()
                ),
                "reconstructed_admissible_missing_open": int(
                    joined.loc[joined["ticker"].eq(ticker), "reconstructed_admission_status"].eq("SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE").sum()
                ),
            }
            for ticker in ("FREN", "MASA", "MFIN")
        },
        "corporate_action_cross_check": {
            "rows": int(len(cross_check)),
            "match": int(cross_check["status"].eq("MATCH").sum()) if not cross_check.empty else 0,
            "mismatch": int(cross_check["status"].eq("MISMATCH").sum()) if not cross_check.empty else 0,
            "yahoo_only": int(cross_check["status"].eq("YAHOO_ONLY").sum()) if not cross_check.empty else 0,
        },
        "potential_recovery_estimate": {
            "estimated_rows": None,
            "reason": "not extrapolated: sample is deliberately stratified by split evidence, Open role, edge, and date",
            "denominator_unresolved_open_rows": int(panel["open"].isna().sum()),
        },
    }
    _write_json(source_summary, output / "yahoo_semantics_summary.json")

    panel_sha_after = sha256_file(panel_file)
    if panel_sha_after != panel_sha_before:
        raise RuntimeError(f"Immutable panel changed during runtime: {panel_sha_after}")
    overall = {
        "status": "OPEN_BACKFILL_YAHOO_SEMANTICS_AUDIT_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "panel_path": str(panel_file),
        "panel_sha256_before": panel_sha_before,
        "panel_sha256_after": panel_sha_after,
        "baseline_null_open_rows": int(panel["open"].isna().sum()),
        "execution_grade_promoted": False,
        "sample_rows": int(len(sample)),
        "sample_unique_tickers": int(sample["ticker"].nunique()),
        "sample_sha256": sample_hash,
        "source": source_summary,
        "prohibited_actions_not_performed": [
            "bulk_446843_row_backfill",
            "immutable_panel_write",
            "adj_close_or_dividend_substitution",
            "stage5_rerun",
            "ranking_v2_change",
            "execution_pnl_claim",
            "main_merge",
        ],
    }
    _write_json(overall, output / "audit_summary.json")
    files = sorted(path for path in output.iterdir() if path.is_file())
    manifest = {
        "runtime": "open_backfill_yahoo_semantics_v1_20260810",
        "files": {path.name: sha256_file(path) for path in files},
    }
    manifest_path = output / "artifact_manifest.json"
    _write_json(manifest, manifest_path)
    return {
        **overall,
        "output_dir": str(output),
        "artifact_hashes": manifest["files"],
        "artifact_manifest_sha256": sha256_file(manifest_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded Yahoo raw Open semantics audit")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--wildan-diagnostics", required=True)
    parser.add_argument("--official-actions", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256", default=DEFAULT_EXPECTED_PANEL_SHA256)
    parser.add_argument("--security-master")
    parser.add_argument("--tradability-intervals")
    parser.add_argument("--seed", type=int, default=DEFAULT_SAMPLE_SEED)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_yahoo_semantics_audit(
        panel_path=args.panel,
        wildan_diagnostics_path=args.wildan_diagnostics,
        official_actions_path=args.official_actions,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
        security_master_path=args.security_master,
        tradability_intervals_path=args.tradability_intervals,
        seed=args.seed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
