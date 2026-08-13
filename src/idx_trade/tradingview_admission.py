"""Frozen gate evaluation for the bounded TradingView admission pilot."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd


def _rate(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _at_least(value: Any, threshold: float) -> bool:
    actual = _rate(value)
    return actual is not None and actual >= threshold


def _yearly_rates(metrics: Mapping[str, Any], key: str, years: Sequence[int]) -> dict[int, float | None]:
    source = metrics.get(key, {})
    return {year: _rate(source.get(str(year), source.get(year))) for year in years}


def _range_metrics(metrics: Mapping[str, Any], range_key: str) -> Mapping[str, Any]:
    ranges = metrics.get("ranges", {})
    return ranges.get(range_key, {})


def _base_gate_results(
    metrics: Mapping[str, Any],
    gates: Mapping[str, Any],
    *,
    range_key: str,
    years: Sequence[int],
) -> dict[str, bool]:
    aggregate = _range_metrics(metrics, range_key)
    results: dict[str, bool] = {}
    results["symbol_resolution"] = _at_least(aggregate.get("symbol_resolution_rate"), float(gates["symbol_resolution_min"]))
    results["target_window_availability"] = _at_least(aggregate.get("target_window_availability_rate"), float(gates["target_window_availability_min"]))
    results["deep_reach_2021"] = _at_least(metrics.get("deep_reach_2021_rate"), float(gates["deep_reach_2021_min"]))
    results["certified_session_coverage"] = _at_least(aggregate.get("certified_session_coverage_rate"), float(gates["certified_session_coverage_min"]))
    results["hlc_exact_overall"] = _at_least(aggregate.get("hlc_exact_rate"), float(gates["hlc_exact_overall_min"]))
    results["volume_within_5pct_overall"] = _at_least(aggregate.get("volume_within_5pct_rate"), float(gates["volume_within_5pct_overall_min"]))
    results["tv1d_reference"] = _at_least(aggregate.get("tv1d_reference_exact_rate"), float(gates["tv1d_reference_exact_min"]))
    results["structural_integrity"] = bool(metrics.get("structural_integrity", False))

    coverage = _yearly_rates(metrics, "target_window_availability_by_year", years)
    results.update({f"target_window_availability_{year}": _at_least(value, float(gates["target_window_availability_year_min"])) for year, value in coverage.items()})
    certified = _yearly_rates(metrics, "certified_session_coverage_by_year", years)
    results.update({f"certified_session_coverage_{year}": _at_least(value, float(gates["certified_session_coverage_min"])) for year, value in certified.items()})
    hlc = _yearly_rates(metrics, "hlc_exact_by_year", years)
    results.update({f"hlc_exact_{year}": _at_least(value, float(gates["hlc_exact_year_min"])) for year, value in hlc.items()})
    volume_by_year = metrics.get("volume_within_5pct_by_year", {})
    min_rows = int(gates["minimum_year_matched_rows"])
    for year in years:
        row = volume_by_year.get(str(year), volume_by_year.get(year, {})) or {}
        matched = int(row.get("matched_rows", 0))
        results[f"volume_within_5pct_{year}"] = matched < min_rows or _at_least(row.get("rate"), float(gates["volume_within_5pct_year_min"]))
    tv1d_by_year = _yearly_rates(metrics, "tv1d_reference_exact_by_year", years)
    results.update({f"tv1d_reference_{year}": _at_least(value, float(gates["tv1d_reference_year_min"])) for year, value in tv1d_by_year.items()})
    return results


def evaluate_frozen_verdict(metrics: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the preregistered verdict without post-result manual choices."""
    gates = config["gates"]
    preferred_years = [int(year) for year in gates["preferred_years"]]
    fallback_years = [int(year) for year in gates["fallback_years"]]
    preferred = _base_gate_results(metrics, gates, range_key="2021_2026", years=preferred_years)
    fallback = _base_gate_results(metrics, gates, range_key="2022_2026", years=fallback_years)
    preferred_failures = sorted(key for key, passed in preferred.items() if not passed)
    fallback_failures = sorted(key for key, passed in fallback.items() if not passed)
    preferred_pass = not preferred_failures
    fallback_pass = not fallback_failures
    only_2021_failure = (
        not preferred_pass
        and fallback_pass
        and all(key.endswith("_2021") for key in preferred_failures)
    )

    if preferred_pass:
        selected_range = "2021_2026"
        selected_years = preferred_years
        prefix = "TRADINGVIEW_INTRADAY_ADMIT_2021_2026"
    elif only_2021_failure:
        selected_range = "2022_2026"
        selected_years = fallback_years
        prefix = "TRADINGVIEW_INTRADAY_ADMIT_2022_2026"
    else:
        selected_range = None
        selected_years = []
        prefix = "TRADINGVIEW_INTRADAY_ADMISSION_REJECTED"

    selected = _range_metrics(metrics, selected_range) if selected_range else {}
    open_rate = _rate(selected.get("tv60_open_vs_tv1d_exact_rate"))
    open_full = bool(gates["open_deterministic_convention_explained"]) or (
        open_rate is not None and open_rate >= float(gates["tv60_open_exact_full_ohlcv_min"])
    )
    if selected_range is None:
        verdict = "TRADINGVIEW_INTRADAY_ADMISSION_REJECTED"
    elif open_full:
        verdict = f"{prefix}_FULL_OHLCV" + ("_2021_BLOCKED" if selected_range == "2022_2026" else "")
    else:
        verdict = f"{prefix}_PRICE_PATH_ONLY" + ("_2021_BLOCKED" if selected_range == "2022_2026" else "")

    return {
        "verdict": verdict,
        "preferred_gate_pass": preferred_pass,
        "fallback_gate_pass": fallback_pass,
        "only_2021_failure": only_2021_failure,
        "selected_range": selected_range,
        "selected_years": selected_years,
        "preferred_failures": preferred_failures,
        "fallback_failures": fallback_failures,
        "open_full_ohlcv": open_full,
        "open_rate_for_selected_range": open_rate,
        "preferred_gates": preferred,
        "fallback_gates": fallback,
    }


def verify_input_hashes(expected: Mapping[str, str], actual: Mapping[str, str]) -> None:
    """Fail closed when a preregistered input hash changes."""
    for key, expected_hash in expected.items():
        observed = actual.get(key)
        if observed != expected_hash:
            raise ValueError(f"input hash mismatch for {key}: {observed} != {expected_hash}")


def quarantine_corporate_action_rows(
    comparison: pd.DataFrame,
    evidence_keys: set[tuple[str, str]],
) -> pd.DataFrame:
    """Apply only externally evidenced CA quarantine; never infer from ratios."""
    result = comparison.copy()
    result["corporate_action_quarantined"] = [
        (str(ticker).upper(), str(session_date)) in evidence_keys
        for ticker, session_date in zip(result.get("ticker", []), result.get("session_date", []))
    ]
    return result
