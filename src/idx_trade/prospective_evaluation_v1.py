from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd


PROTOCOL_STATUS = "V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND"
PROTOCOL_COMMIT = "ed719dd67ae93b6b20f02579df80fd67eec331dd"
MODEL_NAME = "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
MODEL_GENERATION = "V4-X1-CLEAN"
MODEL_FINGERPRINT = "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
ANNUALIZATION_SESSIONS = 252
BOOTSTRAP_BLOCK_LENGTH = 5
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20_260_824

DEVELOPMENT_DATA_CLASSIFICATIONS = frozenset({"SYNTHETIC", "AUTHORIZED_NON_PROSPECTIVE"})
ALLOWED_LEDGER_STATES = frozenset(
    {
        "EVALUABLE",
        "LEGITIMATE_PENDING_OPEN",
        "OPERATIONAL_FAILURE",
        "DATA_INCOMPLETE",
        "EXCLUDED_IMPLEMENTATION_DEFECT",
        "NOT_YET_TARGET_MATURED",
        "MARKET_NONTRADING",
    }
)


class ProspectiveEvaluationBlocked(RuntimeError):
    """Raised when the frozen evaluator contract cannot be applied safely."""


def _require_columns(frame: pd.DataFrame, required: Iterable[str], *, label: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ProspectiveEvaluationBlocked(f"{label} missing columns: {missing}")


def _normalize_dates(values: Sequence[object] | pd.Series, *, label: str) -> pd.Series:
    dates = pd.to_datetime(pd.Series(values), errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    if dates.isna().any():
        raise ProspectiveEvaluationBlocked(f"{label} contains invalid dates")
    return dates


def _finite_numeric(values: Sequence[object] | pd.Series, *, label: str) -> np.ndarray:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    if numeric.size == 0 or not np.isfinite(numeric).all():
        raise ProspectiveEvaluationBlocked(f"{label} must be non-empty and finite")
    return numeric


def _sample_std(values: np.ndarray) -> float:
    if values.size < 2:
        return math.nan
    return float(np.std(values, ddof=1))


def validate_development_identity(
    *,
    data_classification: str,
    model_name: str,
    model_generation: str,
    model_fingerprint: str,
    canonical_target_id: str,
    canonical_target_resolved: bool,
) -> None:
    """Fail closed before any development evaluation can touch protected outcomes.

    V1 deliberately supports only synthetic or separately authorized non-prospective
    fixtures. A future protected-outcome runner must be a separately committed gate
    adapter; the metric code in this module does not need to change.
    """

    classification = str(data_classification).strip().upper()
    if classification not in DEVELOPMENT_DATA_CLASSIFICATIONS:
        raise ProspectiveEvaluationBlocked(
            "protected prospective data is not accepted by the development evaluator; "
            "use a separately committed pre-outcome access-gate adapter"
        )
    if model_name != MODEL_NAME:
        raise ProspectiveEvaluationBlocked("model name does not match frozen V4-X1 identity")
    if model_generation != MODEL_GENERATION:
        raise ProspectiveEvaluationBlocked("model generation does not match frozen V4-X1 identity")
    if model_fingerprint != MODEL_FINGERPRINT:
        raise ProspectiveEvaluationBlocked("model fingerprint does not match frozen V4-X1 identity")
    if not canonical_target_resolved or not str(canonical_target_id).strip():
        raise ProspectiveEvaluationBlocked("canonical V4-X1 outcome target is ambiguous or unresolved")


def validate_alpha_session_alignment(
    alpha_frame: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    *,
    session_col: str = "session_date",
    index_col: str = "session_index",
) -> pd.DataFrame:
    """Require exact signal-session/date-index alignment before alpha evaluation."""

    _require_columns(alpha_frame, {session_col, index_col}, label="alpha frame")
    _require_columns(expected_sessions, {session_col, index_col}, label="expected session inventory")
    data = alpha_frame[[session_col, index_col]].copy()
    expected = expected_sessions[[session_col, index_col]].copy()
    data[session_col] = _normalize_dates(data[session_col], label="alpha frame")
    expected[session_col] = _normalize_dates(expected[session_col], label="expected session inventory")
    data[index_col] = pd.to_numeric(data[index_col], errors="raise").astype(int)
    expected[index_col] = pd.to_numeric(expected[index_col], errors="raise").astype(int)
    if expected.duplicated([session_col, index_col]).any():
        raise ProspectiveEvaluationBlocked("expected session inventory contains duplicate keys")
    per_date_index_count = data.groupby(session_col, sort=False)[index_col].nunique(dropna=False)
    if (per_date_index_count != 1).any():
        raise ProspectiveEvaluationBlocked("alpha rows map one session date to multiple session indices")
    actual = data.drop_duplicates([session_col, index_col])
    merged = expected.merge(actual, on=[session_col, index_col], how="outer", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ProspectiveEvaluationBlocked("alpha rows do not exactly align to expected session date/index inventory")
    return actual.sort_values([index_col, session_col], kind="mergesort").reset_index(drop=True)


def spearman_rank_correlation(x: Sequence[object] | pd.Series, y: Sequence[object] | pd.Series) -> float:
    """Spearman rank correlation with average ranks for ties, without SciPy."""

    x_values = _finite_numeric(x, label="Spearman x")
    y_values = _finite_numeric(y, label="Spearman y")
    if x_values.size != y_values.size:
        raise ProspectiveEvaluationBlocked("Spearman inputs have different lengths")
    if x_values.size < 2:
        raise ProspectiveEvaluationBlocked("Spearman requires at least two rows")

    x_rank = pd.Series(x_values).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y_values).rank(method="average").to_numpy(dtype=float)
    x_std = _sample_std(x_rank)
    y_std = _sample_std(y_rank)
    if not np.isfinite(x_std) or not np.isfinite(y_std) or x_std == 0.0 or y_std == 0.0:
        raise ProspectiveEvaluationBlocked("Spearman is undefined for a constant ranked input")
    return float(np.corrcoef(x_rank, y_rank)[0, 1])


def deterministic_rank(
    frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    ticker_col: str = "ticker",
    score_col: str = "alpha_consensus",
) -> pd.DataFrame:
    """Reproduce frozen rank order: alpha_consensus DESC, ticker ASC."""

    _require_columns(frame, {session_col, ticker_col, score_col}, label="rank frame")
    data = frame.copy()
    data[session_col] = _normalize_dates(data[session_col], label="rank frame")
    data[ticker_col] = data[ticker_col].astype(str).str.upper().str.strip()
    if data[ticker_col].eq("").any():
        raise ProspectiveEvaluationBlocked("rank frame contains blank ticker")
    data[score_col] = pd.to_numeric(data[score_col], errors="coerce")
    if not np.isfinite(data[score_col].to_numpy(dtype=float)).all():
        raise ProspectiveEvaluationBlocked("rank frame contains non-finite scores")
    if data.duplicated([session_col, ticker_col]).any():
        raise ProspectiveEvaluationBlocked("rank frame contains duplicate session/ticker keys")

    data = data.sort_values([session_col, score_col, ticker_col], ascending=[True, False, True], kind="mergesort")
    data["rank"] = data.groupby(session_col, sort=False).cumcount() + 1
    return data.reset_index(drop=True)


def _moving_block_sample_indices(
    n: int,
    *,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if n < block_length:
        raise ProspectiveEvaluationBlocked(
            f"moving-block bootstrap requires at least {block_length} observations"
        )
    block_count = math.ceil(n / block_length)
    starts = rng.integers(0, n - block_length + 1, size=block_count)
    pieces = [np.arange(start, start + block_length, dtype=int) for start in starts]
    return np.concatenate(pieces)[:n]


def moving_block_bootstrap_distribution(
    values: Sequence[object] | pd.Series,
    statistic: Callable[[np.ndarray], float],
    *,
    block_length: int = BOOTSTRAP_BLOCK_LENGTH,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[np.ndarray, int]:
    """Return deterministic ordered-session moving-block bootstrap statistics."""

    sample = _finite_numeric(values, label="bootstrap values")
    if block_length != BOOTSTRAP_BLOCK_LENGTH:
        raise ProspectiveEvaluationBlocked("confirmatory bootstrap block length is frozen at 5")
    if replicates != BOOTSTRAP_REPLICATES:
        raise ProspectiveEvaluationBlocked("confirmatory bootstrap replicate count is frozen at 10000")
    if seed != BOOTSTRAP_SEED:
        raise ProspectiveEvaluationBlocked("confirmatory bootstrap seed is frozen at 20260824")

    rng = np.random.default_rng(seed)
    result = np.empty(replicates, dtype=float)
    nonfinite = 0
    for idx in range(replicates):
        positions = _moving_block_sample_indices(sample.size, block_length=block_length, rng=rng)
        value = float(statistic(sample[positions]))
        result[idx] = value
        if not np.isfinite(value):
            nonfinite += 1
    return result, nonfinite


def bootstrap_interval(distribution: np.ndarray) -> tuple[float, float]:
    finite = distribution[np.isfinite(distribution)]
    if finite.size == 0:
        raise ProspectiveEvaluationBlocked("bootstrap distribution contains no finite values")
    low, high = np.percentile(finite, [2.5, 97.5])
    return float(low), float(high)


def _session_ic_table(
    alpha_frame: pd.DataFrame,
    *,
    session_col: str,
    ticker_col: str,
    score_col: str,
    target_col: str,
) -> pd.DataFrame:
    _require_columns(alpha_frame, {session_col, ticker_col, score_col, target_col}, label="alpha frame")
    data = alpha_frame.copy()
    data[session_col] = _normalize_dates(data[session_col], label="alpha frame")
    data[ticker_col] = data[ticker_col].astype(str).str.upper().str.strip()
    if data[ticker_col].eq("").any() or data.duplicated([session_col, ticker_col]).any():
        raise ProspectiveEvaluationBlocked("alpha frame contains invalid or duplicate session/ticker keys")
    data[score_col] = pd.to_numeric(data[score_col], errors="coerce")
    data[target_col] = pd.to_numeric(data[target_col], errors="coerce")
    if not np.isfinite(data[[score_col, target_col]].to_numpy(dtype=float)).all():
        raise ProspectiveEvaluationBlocked("alpha frame contains non-finite score/target values")

    rows: list[dict[str, Any]] = []
    for session_date, group in data.groupby(session_col, sort=True):
        if len(group) < 2:
            raise ProspectiveEvaluationBlocked(f"alpha session {session_date.date()} has fewer than two rows")
        ic = spearman_rank_correlation(group[score_col], group[target_col])
        rows.append({"session_date": session_date, "row_count": int(len(group)), "ic": ic})
    if not rows:
        raise ProspectiveEvaluationBlocked("alpha frame contains no sessions")
    return pd.DataFrame(rows).sort_values("session_date", kind="mergesort").reset_index(drop=True)


def rank_bucket_summary(
    alpha_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    ticker_col: str = "ticker",
    score_col: str = "alpha_consensus",
    target_col: str = "canonical_target",
) -> dict[str, dict[str, float | int]]:
    ranked = deterministic_rank(
        alpha_frame,
        session_col=session_col,
        ticker_col=ticker_col,
        score_col=score_col,
    )
    ranked[target_col] = pd.to_numeric(ranked[target_col], errors="coerce")
    if not np.isfinite(ranked[target_col].to_numpy(dtype=float)).all():
        raise ProspectiveEvaluationBlocked("rank-bucket target values must be finite")

    def bucket(rank: int) -> str:
        if rank <= 10:
            return "RANK_1_10"
        if rank <= 20:
            return "RANK_11_20"
        if rank <= 50:
            return "RANK_21_50"
        return "RANK_GT50"

    ranked["bucket"] = ranked["rank"].map(bucket)
    per_session = (
        ranked.groupby([session_col, "bucket"], sort=True, observed=True)[target_col]
        .agg(["mean", "size"])
        .reset_index()
    )
    result: dict[str, dict[str, float | int]] = {}
    for name in ("RANK_1_10", "RANK_11_20", "RANK_21_50", "RANK_GT50"):
        subset = per_session.loc[per_session["bucket"].eq(name)]
        session_values = subset["mean"].to_numpy(dtype=float)
        result[name] = {
            "session_count": int(session_values.size),
            "row_count": int(subset["size"].sum()) if not subset.empty else 0,
            "mean": float(np.mean(session_values)) if session_values.size else math.nan,
            "median": float(np.median(session_values)) if session_values.size else math.nan,
        }
    return result


def top_k_summary(
    alpha_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    ticker_col: str = "ticker",
    score_col: str = "alpha_consensus",
    target_col: str = "canonical_target",
) -> dict[str, dict[str, Any]]:
    """Session-aggregate frozen top-10/top-20 outcomes with block-bootstrap uncertainty."""

    ranked = deterministic_rank(
        alpha_frame,
        session_col=session_col,
        ticker_col=ticker_col,
        score_col=score_col,
    )
    ranked[target_col] = pd.to_numeric(ranked[target_col], errors="coerce")
    if not np.isfinite(ranked[target_col].to_numpy(dtype=float)).all():
        raise ProspectiveEvaluationBlocked("top-k target values must be finite")

    result: dict[str, dict[str, Any]] = {}
    for k in (10, 20):
        per_session = (
            ranked.loc[ranked["rank"] <= k]
            .groupby(session_col, sort=True)[target_col]
            .mean()
            .to_numpy(dtype=float)
        )
        if per_session.size < BOOTSTRAP_BLOCK_LENGTH:
            raise ProspectiveEvaluationBlocked(f"top-{k} summary requires at least 5 sessions")
        distribution, nonfinite = moving_block_bootstrap_distribution(
            per_session,
            lambda sample: float(np.mean(sample)),
        )
        if np.isfinite(distribution).any():
            ci_low, ci_high = bootstrap_interval(distribution)
        else:
            ci_low, ci_high = math.nan, math.nan
        result[f"TOP_{k}"] = {
            "session_count": int(per_session.size),
            "mean": float(np.mean(per_session)),
            "median": float(np.median(per_session)),
            "bootstrap_ci_95": [ci_low, ci_high],
            "bootstrap_nonfinite_replicates": int(nonfinite),
        }
    return result


def evaluate_alpha_metrics(
    alpha_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    ticker_col: str = "ticker",
    score_col: str = "alpha_consensus",
    target_col: str = "canonical_target",
) -> dict[str, Any]:
    session_ic = _session_ic_table(
        alpha_frame,
        session_col=session_col,
        ticker_col=ticker_col,
        score_col=score_col,
        target_col=target_col,
    )
    ic_values = session_ic["ic"].to_numpy(dtype=float)
    mean_ic = float(np.mean(ic_values))
    std_ic = _sample_std(ic_values)
    icir = mean_ic / std_ic if np.isfinite(std_ic) and std_ic > 0 else math.nan
    distribution, nonfinite = moving_block_bootstrap_distribution(ic_values, lambda sample: float(np.mean(sample)))
    if np.isfinite(distribution).any():
        ci_low, ci_high = bootstrap_interval(distribution)
    else:
        ci_low, ci_high = math.nan, math.nan
    return {
        "session_count": int(len(session_ic)),
        "row_count": int(session_ic["row_count"].sum()),
        "mean_ic": mean_ic,
        "median_ic": float(np.median(ic_values)),
        "std_ic": std_ic,
        "positive_ic_fraction": float(np.mean(ic_values > 0.0)),
        "icir": float(icir),
        "bootstrap_ci_95": [ci_low, ci_high],
        "bootstrap_nonfinite_replicates": int(nonfinite),
        "bootstrap_status": "INCONCLUSIVE_STATISTICS" if nonfinite else "VALID",
        "session_ic": session_ic,
        "rank_buckets": rank_bucket_summary(
            alpha_frame,
            session_col=session_col,
            ticker_col=ticker_col,
            score_col=score_col,
            target_col=target_col,
        ),
        "top_k": top_k_summary(
            alpha_frame,
            session_col=session_col,
            ticker_col=ticker_col,
            score_col=score_col,
            target_col=target_col,
        ),
    }


def nav_daily_returns(
    nav_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    nav_col: str = "nav",
) -> pd.DataFrame:
    _require_columns(nav_frame, {session_col, nav_col}, label="NAV frame")
    data = nav_frame[[session_col, nav_col]].copy()
    data[session_col] = _normalize_dates(data[session_col], label="NAV frame")
    if data[session_col].duplicated().any():
        raise ProspectiveEvaluationBlocked("NAV frame contains duplicate sessions")
    data[nav_col] = pd.to_numeric(data[nav_col], errors="coerce")
    if not np.isfinite(data[nav_col].to_numpy(dtype=float)).all() or (data[nav_col] <= 0).any():
        raise ProspectiveEvaluationBlocked("NAV must be finite and strictly positive")
    data = data.sort_values(session_col, kind="mergesort").reset_index(drop=True)
    if len(data) < 2:
        raise ProspectiveEvaluationBlocked("NAV frame requires at least two marking sessions")
    result = data.copy()
    result["daily_return"] = result[nav_col].pct_change(fill_method=None)
    return result.iloc[1:].reset_index(drop=True)


def max_drawdown_metrics(
    nav_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    nav_col: str = "nav",
) -> dict[str, Any]:
    _require_columns(nav_frame, {session_col, nav_col}, label="NAV frame")
    data = nav_frame[[session_col, nav_col]].copy()
    data[session_col] = _normalize_dates(data[session_col], label="NAV frame")
    data[nav_col] = pd.to_numeric(data[nav_col], errors="coerce")
    if data[session_col].duplicated().any():
        raise ProspectiveEvaluationBlocked("NAV frame contains duplicate sessions")
    if not np.isfinite(data[nav_col].to_numpy(dtype=float)).all() or (data[nav_col] <= 0).any():
        raise ProspectiveEvaluationBlocked("NAV must be finite and strictly positive")
    data = data.sort_values(session_col, kind="mergesort").reset_index(drop=True)
    running_peak = data[nav_col].cummax()
    drawdown = data[nav_col] / running_peak - 1.0
    trough_pos = int(drawdown.to_numpy(dtype=float).argmin())
    max_drawdown = float(drawdown.iloc[trough_pos])
    peak_value = float(running_peak.iloc[trough_pos])
    peak_candidates = data.loc[:trough_pos, nav_col].eq(peak_value)
    peak_pos = int(np.flatnonzero(peak_candidates.to_numpy())[0])

    recovered = False
    recovery_date: str | None = None
    if max_drawdown < 0:
        after = data.loc[trough_pos + 1 :]
        recovered_rows = after.loc[after[nav_col] >= peak_value]
        if not recovered_rows.empty:
            recovered = True
            recovery_date = recovered_rows.iloc[0][session_col].date().isoformat()
    else:
        recovered = True
        recovery_date = data.iloc[trough_pos][session_col].date().isoformat()

    return {
        "max_drawdown": max_drawdown,
        "peak_date": data.iloc[peak_pos][session_col].date().isoformat(),
        "trough_date": data.iloc[trough_pos][session_col].date().isoformat(),
        "recovered": recovered,
        "recovery_date": recovery_date,
    }


def _sharpe_zero(returns: np.ndarray) -> float:
    std = _sample_std(returns)
    if not np.isfinite(std) or std == 0.0:
        return math.nan
    return float(np.mean(returns) / std * math.sqrt(ANNUALIZATION_SESSIONS))


def _sortino_zero(returns: np.ndarray) -> float:
    downside = np.minimum(returns, 0.0)
    downside_dev = float(np.sqrt(np.mean(np.square(downside))))
    mean_return = float(np.mean(returns))
    if downside_dev == 0.0:
        if mean_return > 0:
            return math.inf
        return math.nan
    return float(mean_return / downside_dev * math.sqrt(ANNUALIZATION_SESSIONS))


def evaluate_portfolio_metrics(
    nav_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    nav_col: str = "nav",
) -> dict[str, Any]:
    _require_columns(nav_frame, {session_col, nav_col}, label="NAV frame")
    ordered = nav_frame[[session_col, nav_col]].copy()
    ordered[session_col] = _normalize_dates(ordered[session_col], label="NAV frame")
    ordered[nav_col] = pd.to_numeric(ordered[nav_col], errors="coerce")
    if ordered[session_col].duplicated().any():
        raise ProspectiveEvaluationBlocked("NAV frame contains duplicate sessions")
    if not np.isfinite(ordered[nav_col].to_numpy(dtype=float)).all() or (ordered[nav_col] <= 0).any():
        raise ProspectiveEvaluationBlocked("NAV must be finite and strictly positive")
    ordered = ordered.sort_values(session_col, kind="mergesort").reset_index(drop=True)
    if len(ordered) < 2:
        raise ProspectiveEvaluationBlocked("NAV frame requires at least two marking sessions")

    returns_frame = nav_daily_returns(ordered, session_col=session_col, nav_col=nav_col)
    returns = returns_frame["daily_return"].to_numpy(dtype=float)
    start_nav = float(ordered.iloc[0][nav_col])
    end_nav = float(ordered.iloc[-1][nav_col])
    total_return = end_nav / start_nav - 1.0
    std = _sample_std(returns)
    annualized_vol = std * math.sqrt(ANNUALIZATION_SESSIONS) if np.isfinite(std) else math.nan
    n = int(returns.size)
    annualized_geometric = (end_nav / start_nav) ** (ANNUALIZATION_SESSIONS / n) - 1.0
    drawdown = max_drawdown_metrics(ordered, session_col=session_col, nav_col=nav_col)
    max_dd = float(drawdown["max_drawdown"])
    calmar = annualized_geometric / abs(max_dd) if max_dd < 0.0 else math.nan

    bootstrap_compounded, nonfinite_compounded = moving_block_bootstrap_distribution(
        returns,
        lambda sample: float(np.prod(1.0 + sample) - 1.0),
    )
    bootstrap_mean, nonfinite_mean = moving_block_bootstrap_distribution(
        returns,
        lambda sample: float(np.mean(sample)),
    )
    bootstrap_sharpe, nonfinite_sharpe = moving_block_bootstrap_distribution(returns, _sharpe_zero)

    compounded_ci = bootstrap_interval(bootstrap_compounded)
    mean_ci = bootstrap_interval(bootstrap_mean)
    sharpe_ci = bootstrap_interval(bootstrap_sharpe) if np.isfinite(bootstrap_sharpe).any() else (math.nan, math.nan)

    return {
        "starting_nav": start_nav,
        "ending_nav": end_nav,
        "transition_count": n,
        "net_total_return": float(total_return),
        "mean_daily_return": float(np.mean(returns)),
        "annualized_volatility": float(annualized_vol),
        "sharpe_0": _sharpe_zero(returns),
        "sortino_0": _sortino_zero(returns),
        "annualized_geometric_return": float(annualized_geometric),
        "calmar": float(calmar),
        **drawdown,
        "bootstrap": {
            "compounded_return_ci_95": [float(compounded_ci[0]), float(compounded_ci[1])],
            "mean_daily_return_ci_95": [float(mean_ci[0]), float(mean_ci[1])],
            "sharpe_0_ci_95": [float(sharpe_ci[0]), float(sharpe_ci[1])],
            "nonfinite_compounded_replicates": int(nonfinite_compounded),
            "nonfinite_mean_replicates": int(nonfinite_mean),
            "nonfinite_sharpe_replicates": int(nonfinite_sharpe),
            "status": (
                "INCONCLUSIVE_STATISTICS"
                if any((nonfinite_compounded, nonfinite_mean, nonfinite_sharpe))
                else "VALID"
            ),
        },
        "daily_returns": returns_frame,
    }


def evaluate_turnover(
    execution_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    buy_col: str = "gross_buy_notional",
    sell_col: str = "gross_sell_notional",
    prior_nav_col: str = "nav_prev",
) -> dict[str, Any]:
    _require_columns(execution_frame, {session_col, buy_col, sell_col, prior_nav_col}, label="execution frame")
    data = execution_frame[[session_col, buy_col, sell_col, prior_nav_col]].copy()
    data[session_col] = _normalize_dates(data[session_col], label="execution frame")
    if data[session_col].duplicated().any():
        raise ProspectiveEvaluationBlocked("execution turnover frame contains duplicate sessions")
    for column in (buy_col, sell_col, prior_nav_col):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if not np.isfinite(data[[buy_col, sell_col, prior_nav_col]].to_numpy(dtype=float)).all():
        raise ProspectiveEvaluationBlocked("execution turnover inputs must be finite")
    if (data[[buy_col, sell_col]] < 0).any().any() or (data[prior_nav_col] <= 0).any():
        raise ProspectiveEvaluationBlocked("turnover notionals must be nonnegative and prior NAV positive")
    data = data.sort_values(session_col, kind="mergesort").reset_index(drop=True)
    data["turnover"] = (data[buy_col] + data[sell_col]) / data[prior_nav_col]
    return {
        "aggregate_turnover": float(data["turnover"].sum()),
        "mean_daily_turnover": float(data["turnover"].mean()),
        "median_daily_turnover": float(data["turnover"].median()),
        "daily": data,
    }


def evaluate_pending_orders(
    order_frame: pd.DataFrame,
    *,
    requires_open_col: str = "requires_open_decision",
    pending_col: str = "pending_due_to_unavailable_open",
) -> dict[str, float | int]:
    _require_columns(order_frame, {requires_open_col, pending_col}, label="order frame")
    requires = order_frame[requires_open_col].astype(bool).to_numpy()
    pending = order_frame[pending_col].astype(bool).to_numpy()
    if np.any(pending & ~requires):
        raise ProspectiveEvaluationBlocked("pending Open leg cannot sit outside the Open-decision denominator")
    denominator = int(requires.sum())
    numerator = int((pending & requires).sum())
    rate = numerator / denominator if denominator else math.nan
    return {
        "prepared_open_leg_count": denominator,
        "pending_open_leg_count": numerator,
        "pending_order_rate": float(rate),
    }


def evaluate_benchmark(
    nav_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame,
    *,
    session_col: str = "session_date",
    nav_col: str = "nav",
    benchmark_close_col: str = "benchmark_close",
) -> dict[str, float | str]:
    _require_columns(nav_frame, {session_col, nav_col}, label="NAV frame")
    _require_columns(benchmark_frame, {session_col, benchmark_close_col}, label="benchmark frame")

    nav = nav_frame[[session_col, nav_col]].copy()
    nav[session_col] = _normalize_dates(nav[session_col], label="NAV frame")
    nav[nav_col] = pd.to_numeric(nav[nav_col], errors="coerce")
    if nav[session_col].duplicated().any() or len(nav) < 2:
        raise ProspectiveEvaluationBlocked("benchmark comparison requires unique NAV sessions")
    nav = nav.sort_values(session_col, kind="mergesort").reset_index(drop=True)

    benchmark = benchmark_frame[[session_col, benchmark_close_col]].copy()
    benchmark[session_col] = _normalize_dates(benchmark[session_col], label="benchmark frame")
    benchmark[benchmark_close_col] = pd.to_numeric(benchmark[benchmark_close_col], errors="coerce")
    if benchmark[session_col].duplicated().any():
        raise ProspectiveEvaluationBlocked("benchmark frame contains duplicate sessions")
    if not np.isfinite(benchmark[benchmark_close_col].to_numpy(dtype=float)).all() or (
        benchmark[benchmark_close_col] <= 0
    ).any():
        raise ProspectiveEvaluationBlocked("benchmark closes must be finite and positive")

    start_date = nav.iloc[0][session_col]
    end_date = nav.iloc[-1][session_col]
    selected = benchmark.loc[benchmark[session_col].isin([start_date, end_date])].sort_values(session_col)
    if len(selected) != 2 or selected.iloc[0][session_col] != start_date or selected.iloc[-1][session_col] != end_date:
        raise ProspectiveEvaluationBlocked("benchmark does not align to exact strategy start/end marking sessions")

    strategy_return = float(nav.iloc[-1][nav_col] / nav.iloc[0][nav_col] - 1.0)
    benchmark_return = float(selected.iloc[-1][benchmark_close_col] / selected.iloc[0][benchmark_close_col] - 1.0)
    excess = strategy_return - benchmark_return
    return {
        "benchmark_status": "BENCHMARK_OUTPERFORM" if excess > 0 else "BENCHMARK_NOT_OUTPERFORM",
        "benchmark_return": benchmark_return,
        "net_excess_return_vs_benchmark": float(excess),
    }


def validate_exclusion_ledger(
    ledger: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    *,
    session_col: str = "session_date",
    index_col: str = "session_index",
    state_col: str = "state",
    reason_col: str = "reason",
) -> pd.DataFrame:
    _require_columns(ledger, {session_col, index_col, state_col, reason_col}, label="evaluation ledger")
    _require_columns(expected_sessions, {session_col, index_col}, label="expected session inventory")

    data = ledger[[session_col, index_col, state_col, reason_col]].copy()
    expected = expected_sessions[[session_col, index_col]].copy()
    data[session_col] = _normalize_dates(data[session_col], label="evaluation ledger")
    expected[session_col] = _normalize_dates(expected[session_col], label="expected session inventory")
    data[index_col] = pd.to_numeric(data[index_col], errors="raise").astype(int)
    expected[index_col] = pd.to_numeric(expected[index_col], errors="raise").astype(int)
    if data.duplicated([session_col, index_col]).any() or expected.duplicated([session_col, index_col]).any():
        raise ProspectiveEvaluationBlocked("evaluation ledger/session inventory contains duplicate keys")
    if not set(data[state_col].astype(str)).issubset(ALLOWED_LEDGER_STATES):
        invalid = sorted(set(data[state_col].astype(str)) - ALLOWED_LEDGER_STATES)
        raise ProspectiveEvaluationBlocked(f"evaluation ledger contains invalid states: {invalid}")
    merged = expected.merge(data[[session_col, index_col]], on=[session_col, index_col], how="outer", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ProspectiveEvaluationBlocked("evaluation ledger does not exactly cover expected sessions")
    return data.sort_values([index_col, session_col], kind="mergesort").reset_index(drop=True)


def alpha_verdict(*, mean_ic: float, ci_low: float, valid: bool = True) -> str:
    if not valid:
        return "ALPHA_INVALID"
    if not np.isfinite(mean_ic) or not np.isfinite(ci_low):
        return "ALPHA_INVALID"
    if mean_ic <= 0.0:
        return "ALPHA_FAIL"
    if ci_low > 0.0:
        return "ALPHA_CONFIRMED_POSITIVE"
    return "ALPHA_DIRECTIONALLY_POSITIVE"


def economic_verdict(*, net_total_return: float, sharpe_0: float, valid: bool = True) -> str:
    if not valid or not np.isfinite(net_total_return) or not np.isfinite(sharpe_0):
        raise ProspectiveEvaluationBlocked("economic verdict requires finite valid primary statistics")
    return_positive = net_total_return > 0.0
    sharpe_positive = sharpe_0 > 0.0
    if return_positive and sharpe_positive:
        return "ECONOMIC_POSITIVE"
    if return_positive != sharpe_positive:
        return "ECONOMIC_MIXED"
    return "ECONOMIC_FAIL"


def execution_verdict(*, invariants_valid: bool, state_reconstructable: bool, material_drag: bool = False) -> str:
    if not invariants_valid or not state_reconstructable:
        return "EXECUTION_BROKEN"
    if material_drag:
        return "EXECUTION_MATERIAL_DRAG"
    return "EXECUTION_HEALTHY"


def overall_verdict(
    *,
    operational_valid: bool,
    alpha: str,
    economics: str,
    execution: str,
) -> str:
    if not operational_valid or alpha == "ALPHA_INVALID" or execution == "EXECUTION_BROKEN":
        return "PROSPECTIVE_INVALID_OPERATIONAL"
    if (
        alpha == "ALPHA_CONFIRMED_POSITIVE"
        and economics == "ECONOMIC_POSITIVE"
        and execution != "EXECUTION_BROKEN"
    ):
        return "PROSPECTIVE_PASS"
    if alpha == "ALPHA_FAIL" and economics in {"ECONOMIC_FAIL", "ECONOMIC_MIXED"}:
        return "PROSPECTIVE_FAIL"
    return "PROSPECTIVE_MIXED"


def evaluate_prospective_v1(
    *,
    alpha_frame: pd.DataFrame,
    nav_frame: pd.DataFrame,
    ledger: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    data_classification: str,
    canonical_target_id: str,
    canonical_target_resolved: bool,
    model_name: str = MODEL_NAME,
    model_generation: str = MODEL_GENERATION,
    model_fingerprint: str = MODEL_FINGERPRINT,
    paperstate_continuity_valid: bool = True,
    execution_invariants_valid: bool = True,
    execution_material_drag: bool = False,
    execution_frame: pd.DataFrame | None = None,
    order_frame: pd.DataFrame | None = None,
    benchmark_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Run the frozen metric engine only on development-safe fixtures.

    This function performs no file/network access and never writes an outcome-access
    marker. It therefore cannot unlock the prospective vault. The future protected
    runner must validate the external gate before calling the same pure metric layer.
    """

    validate_development_identity(
        data_classification=data_classification,
        model_name=model_name,
        model_generation=model_generation,
        model_fingerprint=model_fingerprint,
        canonical_target_id=canonical_target_id,
        canonical_target_resolved=canonical_target_resolved,
    )
    validated_ledger = validate_exclusion_ledger(ledger, expected_sessions)
    validate_alpha_session_alignment(alpha_frame, expected_sessions)
    ledger_operational_valid = not validated_ledger["state"].isin(
        {"OPERATIONAL_FAILURE", "DATA_INCOMPLETE", "EXCLUDED_IMPLEMENTATION_DEFECT", "NOT_YET_TARGET_MATURED"}
    ).any()

    alpha = evaluate_alpha_metrics(alpha_frame)
    portfolio = evaluate_portfolio_metrics(nav_frame)
    alpha_status = alpha_verdict(
        mean_ic=float(alpha["mean_ic"]),
        ci_low=float(alpha["bootstrap_ci_95"][0]),
        valid=True,
    )
    execution_status = execution_verdict(
        invariants_valid=execution_invariants_valid,
        state_reconstructable=paperstate_continuity_valid,
        material_drag=execution_material_drag,
    )
    portfolio_valid = paperstate_continuity_valid and execution_status != "EXECUTION_BROKEN"
    economics_status = (
        economic_verdict(
            net_total_return=float(portfolio["net_total_return"]),
            sharpe_0=float(portfolio["sharpe_0"]),
            valid=True,
        )
        if portfolio_valid
        else "ECONOMIC_INVALID_OPERATIONAL"
    )
    operational_valid = bool(ledger_operational_valid and portfolio_valid)

    diagnostics: dict[str, Any] = {}
    if execution_frame is not None:
        diagnostics["turnover"] = evaluate_turnover(execution_frame)
    if order_frame is not None:
        diagnostics["pending_orders"] = evaluate_pending_orders(order_frame)
    if benchmark_frame is not None:
        diagnostics["benchmark"] = evaluate_benchmark(nav_frame, benchmark_frame)
    else:
        diagnostics["benchmark"] = {"benchmark_status": "BENCHMARK_UNAVAILABLE"}

    overall = overall_verdict(
        operational_valid=operational_valid,
        alpha=alpha_status,
        economics=economics_status,
        execution=execution_status,
    )
    return {
        "protocol_status": PROTOCOL_STATUS,
        "protocol_commit": PROTOCOL_COMMIT,
        "model": {
            "name": MODEL_NAME,
            "generation": MODEL_GENERATION,
            "fingerprint": MODEL_FINGERPRINT,
        },
        "data_classification": str(data_classification).strip().upper(),
        "canonical_target_id": canonical_target_id,
        "operational_valid": bool(operational_valid),
        "ledger": validated_ledger,
        "alpha": alpha,
        "portfolio": portfolio,
        "diagnostics": diagnostics,
        "verdicts": {
            "alpha": alpha_status,
            "economics": economics_status,
            "execution": execution_status,
            "overall": overall,
        },
    }
