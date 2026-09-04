"""Build the outcome-blind Foreign Flow Behavioral Forensics V1 evidence pack.

This is a research-only materializer.  It reads the already accepted, hash-pinned
offline inputs and writes to the external artifact root.  It does not import the
V2 feature builder, call providers, read outcomes, or modify production state.
"""
from __future__ import annotations

import hashlib
import json
import ntpath
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ART = Path(r"D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001")
OUT = Path(r"D:\Documents\Project\idx-foreign-flow-behavioral-forensics-20260904-v1")
ARCH = Path(r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1")
PANEL_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"
)
CAL_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\official_exchange_sessions_1260.csv"
)
MASTER_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\security_master_1260.csv"
)
CA_PATH = Path(
    r"D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy"
    r"\transition_attestation_ledger.csv"
)
CA_MANIFEST_PATH = CA_PATH.parent / "MANIFEST.json"

PINNED_INPUT_HASHES = {
    "representation_manifest": "4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc",
    "input_manifest": "93e39bb9829413b71965978b39d949ea4bb59c1f4e98bf86bf4486b60b585028",
    "representation_parquet": "0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0",
    "causal_market_context": "085d7628024c3792bd3a021320ac5377b3e869bcb4ad2e8e2e1209234fe4939d",
    "archive_manifest": "fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334",
    "official_sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "security_master": "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9",
    "market_panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "ca_manifest": "3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030",
    "ca_ledger": "d55befea0797de2f8fe47bf7af2727f2484833d686c9b07b63b568c794667054",
}

EXPECTED_OUTPUTS = {
    "REPORT.md",
    "MANIFEST.json",
    "summary.json",
    "representation_recomputation_audit.csv",
    "representation_invariant_audit.csv",
    "source_file_hash_audit.csv",
    "input_provenance_audit.csv",
    "raw_contract_audit.csv",
    "anomaly_case_studies.csv",
    "anomaly_census.csv",
    "anomaly_top_rows.csv",
    "ca_listing_interaction.csv",
    "coverage_census.csv",
    "cross_sectional_structure.csv",
    "effort_vs_result.csv",
    "hypothesis_registry.csv",
    "liquidity_conditioning.csv",
    "listing_lifecycle_summary.csv",
    "persistence_analysis.csv",
    "pit_feature_contract.csv",
    "price_flow_behavior.csv",
    "raw_share_comparability.csv",
    "redundancy_analysis.csv",
    "regime_analysis.csv",
    "rejected_hypotheses.csv",
}

FEATURES = [
    "foreign_participation_1",
    "foreign_participation_mean_5",
    "foreign_flow_shock_1",
    "foreign_flow_shock_mean_5",
    "foreign_flow_shock_mean_20",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_1",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
    "foreign_signed_streak_10",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
]

PRIOR_LIQUIDITY_LOOKBACK = 20
MIN_PRIOR_LIQUIDITY_OBSERVATIONS = 10
HISTORY_PERCENTILE_LOOKBACK = 120
MIN_HISTORY_PERCENTILE_OBSERVATIONS = 60
SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
STREAK_CAP = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def emit(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUT / name, index=False)


def audit_file(path: Path, expected_sha256: str, label: str) -> dict[str, object]:
    if not path.is_file():
        return {
            "label": label,
            "path": str(path),
            "expected_sha256": expected_sha256,
            "observed_sha256": None,
            "observed_bytes": None,
            "verdict": "FAIL_MISSING",
        }
    observed_sha256 = sha256(path)
    observed_bytes = path.stat().st_size
    return {
        "label": label,
        "path": str(path),
        "expected_sha256": expected_sha256,
        "observed_sha256": observed_sha256,
        "observed_bytes": observed_bytes,
        "verdict": "PASS" if observed_sha256 == expected_sha256 else "FAIL_HASH",
    }


def current_git_commit() -> str:
    repository = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def path_key(path: Path) -> str:
    return ntpath.normcase(ntpath.normpath(str(path)))


REPORT_PROVENANCE_START = "<!-- HARDENING_PROVENANCE_START -->"
REPORT_PROVENANCE_END = "<!-- HARDENING_PROVENANCE_END -->"


def refresh_report_provenance(summary: dict[str, object]) -> None:
    report_path = OUT / "REPORT.md"
    text = report_path.read_text(encoding="utf-8")
    start = text.find(REPORT_PROVENANCE_START)
    end = text.find(REPORT_PROVENANCE_END)
    if start < 0 or end < 0 or end < start:
        raise RuntimeError("REPORT.md is missing hardening provenance markers")
    end += len(REPORT_PROVENANCE_END)
    generator = summary["generator"]
    block = "\n".join(
        [
            REPORT_PROVENANCE_START,
            "## Reproducibility hardening provenance",
            f"- Materializer commit: `{generator['commit']}`",
            f"- Materializer path: `{generator['path']}`",
            f"- Materializer SHA-256: `{generator['sha256']}`",
            f"- Generated at (UTC): `{generator['generated_at_utc']}`",
            f"- V2 replay: `{summary['v2_recomputation']['result']}`",
            f"- Raw contract: `{summary['raw_contract']['result']}`",
            f"- Input provenance: `{summary['input_provenance']['result']}`",
            REPORT_PROVENANCE_END,
        ]
    )
    report_path.write_text(text[:start] + block + text[end:], encoding="utf-8")


def rank_corr(frame: pd.DataFrame, left: str, right: str) -> tuple[int, float | None]:
    values = frame[[left, right]].apply(pd.to_numeric, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 3:
        return len(values), None
    return len(values), float(spearmanr(values[left], values[right]).statistic)


def listed_mask(dates: pd.Series, ticker: str, master: pd.DataFrame) -> np.ndarray:
    result = np.zeros(len(dates), dtype=bool)
    for row in master.loc[master["ticker"].eq(ticker)].itertuples(index=False):
        end = pd.Timestamp.max.normalize() if pd.isna(row.listed_to) else row.listed_to
        result |= (dates.to_numpy() >= row.listed_from) & (dates.to_numpy() <= end)
    return result


def historical_percentile(current: float, history: np.ndarray) -> float:
    valid = history[np.isfinite(history)]
    if not np.isfinite(current) or len(valid) < MIN_HISTORY_PERCENTILE_OBSERVATIONS:
        return np.nan
    less = float(np.sum(valid < current))
    equal = float(np.sum(valid == current))
    return (less + 0.5 * equal) / float(len(valid))


def signed_streak(values: np.ndarray) -> float:
    if len(values) == 0 or not np.isfinite(values[-1]):
        return np.nan
    last_sign = float(np.sign(values[-1]))
    if last_sign == 0.0:
        return 0.0
    count = 0
    for value in values[::-1]:
        if not np.isfinite(value) or float(np.sign(value)) != last_sign:
            break
        count += 1
        if count >= STREAK_CAP:
            break
    return last_sign * float(count) / float(STREAK_CAP)


def weighted_persistence(values: np.ndarray) -> float:
    if len(values) == 0 or not np.isfinite(values).all():
        return np.nan
    denominator = float(np.abs(values).sum())
    if denominator == 0.0:
        return 0.0
    return float(values.sum() / denominator)


def independent_v2_recompute(
    expected: pd.DataFrame,
    official: pd.DataFrame,
    panel: pd.DataFrame,
    context: pd.DataFrame,
    master: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Rebuild the accepted V2 fields without importing the V2 implementation."""
    flow_index = official.set_index(["ticker", "session_date"])["foreign_net"]
    volume_index = panel.set_index(["ticker", "date"])["volume"]
    context_index = context.set_index(["ticker", "date"])
    master_tickers = set(master["ticker"])
    rows: list[pd.DataFrame] = []
    source_tickers = set(official["ticker"]) | set(panel["ticker"])
    for ticker in sorted(source_tickers):
        if ticker not in master_tickers:
            continue
        master_rows = master.loc[master["ticker"].eq(ticker)]
        listed = listed_mask(pd.Series(sessions), ticker, master)
        listed_at_feature = np.zeros(len(sessions), dtype=bool)
        listed_at_feature[:-1] = listed[1:]
        key = pd.MultiIndex.from_product([[ticker], sessions], names=["ticker", "date"])
        net = flow_index.reindex(key.set_names(["ticker", "session_date"])).to_numpy(dtype=float)
        volume = volume_index.reindex(key).to_numpy(dtype=float)
        close = context_index["close"].reindex(key).to_numpy(dtype=float)
        regular_value = context_index["regular_market_value"].reindex(key).to_numpy(dtype=float)
        net[~listed] = np.nan
        volume[~listed] = np.nan
        close[~listed] = np.nan
        regular_value[~listed] = np.nan

        participation = np.full(len(sessions), np.nan, dtype=float)
        valid_current = np.isfinite(net) & np.isfinite(volume) & (volume > 0.0)
        participation[valid_current] = net[valid_current] / volume[valid_current]

        shock = np.full(len(sessions), np.nan, dtype=float)
        net_notional = net * close
        for index in range(len(sessions)):
            prior = regular_value[max(0, index - PRIOR_LIQUIDITY_LOOKBACK) : index]
            prior = prior[np.isfinite(prior) & (prior >= 0.0)]
            if len(prior) < MIN_PRIOR_LIQUIDITY_OBSERVATIONS or not np.isfinite(net_notional[index]):
                continue
            baseline = float(np.median(prior))
            if baseline > 0.0:
                shock[index] = net_notional[index] / baseline

        participation_mean_5 = np.full(len(sessions), np.nan, dtype=float)
        shock_mean_5 = np.full(len(sessions), np.nan, dtype=float)
        shock_mean_20 = np.full(len(sessions), np.nan, dtype=float)
        persistence_5 = np.full(len(sessions), np.nan, dtype=float)
        persistence_20 = np.full(len(sessions), np.nan, dtype=float)
        streak_10 = np.full(len(sessions), np.nan, dtype=float)
        percentile_120 = np.full(len(sessions), np.nan, dtype=float)
        for index in range(len(sessions)):
            if index + 1 >= SHORT_WINDOW:
                participation_window = participation[index - SHORT_WINDOW + 1 : index + 1]
                shock_window_5 = shock[index - SHORT_WINDOW + 1 : index + 1]
                if np.isfinite(participation_window).all():
                    participation_mean_5[index] = float(np.mean(participation_window))
                if np.isfinite(shock_window_5).all():
                    shock_mean_5[index] = float(np.mean(shock_window_5))
                    persistence_5[index] = weighted_persistence(shock_window_5)
            if index + 1 >= MEDIUM_WINDOW:
                shock_window_20 = shock[index - MEDIUM_WINDOW + 1 : index + 1]
                if np.isfinite(shock_window_20).all():
                    shock_mean_20[index] = float(np.mean(shock_window_20))
                    persistence_20[index] = weighted_persistence(shock_window_20)
            streak_10[index] = signed_streak(net[max(0, index - STREAK_CAP + 1) : index + 1])
            percentile_120[index] = historical_percentile(
                shock[index], shock[max(0, index - HISTORY_PERCENTILE_LOOKBACK) : index]
            )

        rows.append(
            pd.DataFrame(
                {
                    "ticker": ticker,
                    "source_session": sessions,
                    "listed_at_source_session": listed,
                    "listed_at_feature_session": listed_at_feature,
                    "foreign_participation_1": participation,
                    "foreign_participation_mean_5": participation_mean_5,
                    "foreign_flow_shock_1": shock,
                    "foreign_flow_shock_mean_5": shock_mean_5,
                    "foreign_flow_shock_mean_20": shock_mean_20,
                    "foreign_flow_shock_percentile_120": percentile_120,
                    "foreign_weighted_persistence_5": persistence_5,
                    "foreign_weighted_persistence_20": persistence_20,
                    "foreign_signed_streak_10": streak_10,
                    "foreign_flow_acceleration_5_20": shock_mean_5 - shock_mean_20,
                }
            )
        )

    source = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if source.empty:
        return pd.DataFrame(columns=["ticker", "feature_session", "flow_through_session", *FEATURES])
    source = source.merge(
        context,
        left_on=["ticker", "source_session"],
        right_on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    ).drop(columns=["date"])
    rank_specs = [
        ("foreign_flow_shock_1", "xs_rank_foreign_flow_shock_1"),
        ("foreign_flow_shock_mean_5", "xs_rank_foreign_flow_shock_mean_5"),
        ("foreign_flow_shock_mean_20", "xs_rank_foreign_flow_shock_mean_20"),
        ("close_return_5", "xs_rank_close_return_5_source"),
        ("close_return_20", "xs_rank_close_return_20_source"),
    ]
    for _, output in rank_specs:
        source[output] = np.nan
    primary = source["listed_at_source_session"] & source["universe_primary_liquid"].fillna(False).astype(bool)
    for raw, output in rank_specs:
        ranks = source.loc[primary].groupby("source_session", sort=True)[raw].rank(
            method="average", pct=True
        )
        source.loc[ranks.index, output] = ranks.astype(float)
    source["foreign_flow_price_divergence_5"] = (
        source["xs_rank_foreign_flow_shock_mean_5"] - source["xs_rank_close_return_5_source"]
    )
    source["foreign_flow_price_divergence_20"] = (
        source["xs_rank_foreign_flow_shock_mean_20"] - source["xs_rank_close_return_20_source"]
    )
    next_by_day = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
    source["feature_session"] = source["source_session"].map(next_by_day)
    source = source[
        source["feature_session"].notna()
        & source["listed_at_source_session"]
        & source["listed_at_feature_session"]
    ].copy()
    source = source.rename(columns={"source_session": "flow_through_session"})
    return source[["ticker", "feature_session", "flow_through_session", *FEATURES]].sort_values(
        ["feature_session", "ticker"], kind="mergesort"
    ).reset_index(drop=True)


def compare_recomputed_fields(expected: pd.DataFrame, recomputed: pd.DataFrame) -> list[dict[str, object]]:
    key_columns = ["ticker", "feature_session", "flow_through_session"]
    checks: list[dict[str, object]] = []
    for feature in FEATURES:
        left = expected[key_columns + [feature]].rename(columns={feature: "expected"})
        right = recomputed[key_columns + [feature]].rename(columns={feature: "recomputed"})
        duplicate_expected = int(left.duplicated(key_columns).sum())
        duplicate_recomputed = int(right.duplicated(key_columns).sum())
        a = pd.to_numeric(left["expected"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(right["recomputed"], errors="coerce").to_numpy(dtype=float)
        if duplicate_expected or duplicate_recomputed:
            checks.append(
                {
                    "check": feature,
                    "result": "FAIL",
                    "keys_expected": int(len(left)),
                    "keys_recomputed": int(len(right)),
                    "key_set_mismatches": duplicate_expected + duplicate_recomputed,
                    "duplicate_expected_keys": duplicate_expected,
                    "duplicate_recomputed_keys": duplicate_recomputed,
                    "finite_expected": int(np.isfinite(a).sum()),
                    "finite_recomputed": int(np.isfinite(b).sum()),
                    "finite_value_mismatches": None,
                    "nan_pattern_mismatches": None,
                    "nonfinite_value_mismatches": None,
                    "max_abs_difference": None,
                }
            )
            continue
        aligned = left.merge(right, on=key_columns, how="outer", indicator=True, validate="one_to_one")
        a = pd.to_numeric(aligned["expected"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(aligned["recomputed"], errors="coerce").to_numpy(dtype=float)
        finite_a = np.isfinite(a)
        finite_b = np.isfinite(b)
        both_finite = finite_a & finite_b
        numeric_invalid = (
            (aligned["expected"].notna() & pd.to_numeric(aligned["expected"], errors="coerce").isna())
            | (aligned["recomputed"].notna() & pd.to_numeric(aligned["recomputed"], errors="coerce").isna())
        ).to_numpy()
        infinite_values = np.isinf(a) | np.isinf(b)
        finite_mismatch = both_finite & ~np.isclose(a, b, rtol=0.0, atol=1e-12)
        nan_mismatch = finite_a ^ finite_b
        differences = np.abs(a[both_finite] - b[both_finite])
        key_mismatch = int((aligned["_merge"] != "both").sum())
        nonfinite_mismatch = int(numeric_invalid.sum() + infinite_values.sum())
        checks.append(
            {
                "check": feature,
                "result": "PASS" if key_mismatch == 0 and finite_a.sum() > 0 and not finite_mismatch.any() and not nan_mismatch.any() and nonfinite_mismatch == 0 else "FAIL",
                "keys_expected": int(len(left)),
                "keys_recomputed": int(len(right)),
                "key_set_mismatches": key_mismatch,
                "duplicate_expected_keys": duplicate_expected,
                "duplicate_recomputed_keys": duplicate_recomputed,
                "finite_expected": int(finite_a.sum()),
                "finite_recomputed": int(finite_b.sum()),
                "finite_value_mismatches": int(finite_mismatch.sum()),
                "nan_pattern_mismatches": int(nan_mismatch.sum()),
                "nonfinite_value_mismatches": nonfinite_mismatch,
                "max_abs_difference": float(differences.max()) if len(differences) else None,
            }
        )
    return checks


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    existing_outputs = {path.name for path in OUT.iterdir() if path.is_file()}
    unexpected_outputs = sorted(existing_outputs - EXPECTED_OUTPUTS)
    if unexpected_outputs:
        raise RuntimeError(f"output root contains unexpected/stale files: {unexpected_outputs}")

    input_paths = {
        "representation_manifest": ART / "manifest.json",
        "input_manifest": ART / "input_manifest.json",
        "representation_parquet": ART / "foreign_flow_representation_v2.parquet",
        "causal_market_context": ART / "causal_market_context.parquet",
        "archive_manifest": ARCH / "archive_manifest.json",
        "official_sessions": CAL_PATH,
        "security_master": MASTER_PATH,
        "market_panel": PANEL_PATH,
        "ca_manifest": CA_MANIFEST_PATH,
        "ca_ledger": CA_PATH,
    }
    input_provenance_rows = [
        audit_file(input_paths[label], expected_sha, label)
        for label, expected_sha in PINNED_INPUT_HASHES.items()
    ]
    input_provenance = pd.DataFrame(input_provenance_rows)
    if not (input_provenance["verdict"] == "PASS").all():
        emit(input_provenance, "input_provenance_audit.csv")
        raise RuntimeError("pinned input provenance verification failed")

    input_manifest = json.loads(input_paths["input_manifest"].read_text(encoding="utf-8"))
    representation_manifest = json.loads(
        input_paths["representation_manifest"].read_text(encoding="utf-8")
    )
    representation_artifacts = representation_manifest.get("artifacts", {})
    for label, filename in {
        "representation_parquet": "foreign_flow_representation_v2.parquet",
        "causal_market_context": "causal_market_context.parquet",
        "input_manifest": "input_manifest.json",
    }.items():
        declared_hash = representation_artifacts.get(filename)
        input_provenance_rows.append(
            {
                "label": f"representation_manifest_declares_{label}",
                "path": str(input_paths["representation_manifest"]),
                "expected_sha256": PINNED_INPUT_HASHES[label],
                "observed_sha256": declared_hash,
                "observed_bytes": None,
                "verdict": "PASS" if declared_hash == PINNED_INPUT_HASHES[label] else "FAIL_DECLARATION",
            }
        )
    ca_manifest = json.loads(CA_MANIFEST_PATH.read_text(encoding="utf-8"))
    ca_entry = next(
        (item for item in ca_manifest.get("files", []) if item.get("path") == CA_PATH.name),
        {},
    )
    input_provenance_rows.append(
        {
            "label": "ca_manifest_declares_ca_ledger",
            "path": str(CA_MANIFEST_PATH),
            "expected_sha256": PINNED_INPUT_HASHES["ca_ledger"],
            "observed_sha256": ca_entry.get("sha256"),
            "observed_bytes": None,
            "verdict": "PASS" if ca_entry.get("sha256") == PINNED_INPUT_HASHES["ca_ledger"] else "FAIL_DECLARATION",
        }
    )
    input_provenance = pd.DataFrame(input_provenance_rows)
    if not (input_provenance["verdict"] == "PASS").all():
        emit(input_provenance, "input_provenance_audit.csv")
        raise RuntimeError("source manifests do not declare the pinned input hashes")
    archive_manifest_path = ARCH / "archive_manifest.json"
    archive_manifest = json.loads(archive_manifest_path.read_text(encoding="utf-8"))
    declared_hashes = {
        "archive_manifest": input_manifest["archive_manifest"]["archive_manifest_sha256"],
        "official_sessions": input_manifest["official_sessions"]["sha256"],
        "security_master": input_manifest["security_master"]["sha256"],
        "market_panel": input_manifest["market_panel"]["sha256"],
    }
    declared_hash_rows = [
        {
            "label": f"input_manifest_declares_{label}",
            "path": str(input_paths["input_manifest"]),
            "expected_sha256": expected_sha,
            "observed_sha256": declared_hashes[label],
            "observed_bytes": None,
            "verdict": "PASS" if declared_hashes[label] == expected_sha else "FAIL_DECLARATION",
        }
        for label, expected_sha in {
            "archive_manifest": PINNED_INPUT_HASHES["archive_manifest"],
            "official_sessions": PINNED_INPUT_HASHES["official_sessions"],
            "security_master": PINNED_INPUT_HASHES["security_master"],
            "market_panel": PINNED_INPUT_HASHES["market_panel"],
        }.items()
    ]
    input_provenance = pd.concat([input_provenance, pd.DataFrame(declared_hash_rows)], ignore_index=True)
    if not (input_provenance["verdict"] == "PASS").all():
        emit(input_provenance, "input_provenance_audit.csv")
        raise RuntimeError("input manifest declarations do not match pinned provenance")
    emit(input_provenance, "input_provenance_audit.csv")
    calendar = pd.read_csv(CAL_PATH)
    calendar_dates = pd.to_datetime(calendar["date"], errors="coerce").dt.normalize()
    calendar_valid = bool(
        calendar_dates.notna().all()
        and not calendar_dates.duplicated().any()
        and calendar_dates.is_monotonic_increasing
    )
    if not calendar_valid:
        raise RuntimeError("official calendar must be non-null, unique, and sorted")
    sessions = pd.DatetimeIndex(calendar_dates)
    master = pd.read_csv(MASTER_PATH)
    master["ticker"] = master["ticker"].astype(str).str.upper().str.replace(
        ".JK", "", regex=False
    ).str.strip()
    master["listed_from"] = pd.to_datetime(master["listed_from"]).dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()
    master_invalid_intervals = int(
        (master["listed_from"].isna() | (master["listed_to"].notna() & master["listed_to"].lt(master["listed_from"]))).sum()
    )
    master_overlaps = 0
    for _, rows in master.sort_values(["ticker", "listed_from"], kind="mergesort").groupby("ticker", sort=False):
        previous_end = None
        for row in rows.itertuples(index=False):
            start = row.listed_from
            end = pd.Timestamp.max.normalize() if pd.isna(row.listed_to) else row.listed_to
            if previous_end is not None and pd.notna(start) and start <= previous_end:
                master_overlaps += 1
            previous_end = end if previous_end is None else max(previous_end, end)
    if master_invalid_intervals or master_overlaps:
        raise RuntimeError("security master listing intervals are invalid or overlapping")

    pieces: list[pd.DataFrame] = []
    missing_files: list[str] = []
    source_file_hash_rows: list[dict[str, object]] = []
    manifest_items = archive_manifest.get("artifacts", archive_manifest.get("normalized_artifacts", []))
    normalized_items = [
        item for item in manifest_items if str(item.get("path", "")).endswith("foreign_flow.parquet")
    ]
    archive_root = ARCH.resolve()
    normalized_manifest_keys = [
        path_key((ARCH / str(item["path"])).resolve()) for item in normalized_items
    ]
    normalized_manifest_key_set = set(normalized_manifest_keys)
    actual_normalized_keys = {
        path_key(path.resolve())
        for path in ARCH.rglob("foreign_flow.parquet")
        if path.is_file()
    }
    normalized_duplicate_paths = len(normalized_manifest_keys) - len(normalized_manifest_key_set)
    normalized_missing_paths = len(normalized_manifest_key_set - actual_normalized_keys)
    normalized_unexpected_paths = len(actual_normalized_keys - normalized_manifest_key_set)
    input_normalized_items = input_manifest["archive_manifest"]["archive_normalized_artifacts"]
    input_normalized_keys = [
        path_key((ARCH / str(item["path"])).resolve()) for item in input_normalized_items
    ]
    input_normalized_key_set = set(input_normalized_keys)
    input_normalized_duplicate_paths = len(input_normalized_keys) - len(input_normalized_key_set)
    normalized_declaration_missing_paths = len(
        normalized_manifest_key_set - input_normalized_key_set
    )
    normalized_declaration_unexpected_paths = len(
        input_normalized_key_set - normalized_manifest_key_set
    )
    archive_items_by_key: dict[str, list[dict[str, object]]] = {}
    for key, item in zip(normalized_manifest_keys, normalized_items):
        archive_items_by_key.setdefault(key, []).append(item)
    input_items_by_key: dict[str, list[dict[str, object]]] = {}
    for key, item in zip(input_normalized_keys, input_normalized_items):
        input_items_by_key.setdefault(key, []).append(item)
    normalized_declaration_hash_mismatches = 0
    for key in normalized_manifest_key_set | input_normalized_key_set:
        archive_entries = archive_items_by_key.get(key, [])
        input_entries = input_items_by_key.get(key, [])
        if (
            len(archive_entries) != 1
            or len(input_entries) != 1
            or str(archive_entries[0].get("sha256", ""))
            != str(input_entries[0].get("sha256", ""))
        ):
            normalized_declaration_hash_mismatches += 1
    input_declared_row_count = int(
        input_manifest["archive_manifest"]["archive_normalized_row_count"]
    )
    declared_normalized_rows = int(
        sum(int(item["rows"]) for item in input_normalized_items)
    )
    for item in manifest_items:
        relative = item.get("path")
        if not relative or not str(relative).endswith("foreign_flow.parquet"):
            continue
        source = (ARCH / str(relative)).resolve()
        expected_sha = str(item.get("sha256", ""))
        expected_bytes = item.get("bytes")
        try:
            source.relative_to(archive_root)
            safe_path = True
        except ValueError:
            safe_path = False
        if not safe_path:
            source_file_hash_rows.append(
                {
                    "path": str(relative),
                    "expected_sha256": expected_sha,
                    "observed_sha256": None,
                    "expected_bytes": expected_bytes,
                    "observed_bytes": None,
                    "verdict": "FAIL_PATH_ESCAPE",
                }
            )
            continue
        if not source.exists():
            missing_files.append(str(source))
            source_file_hash_rows.append(
                {
                    "path": str(relative),
                    "expected_sha256": expected_sha,
                    "observed_sha256": None,
                    "expected_bytes": expected_bytes,
                    "observed_bytes": None,
                    "verdict": "FAIL_MISSING",
                }
            )
            continue
        observed_sha = sha256(source)
        observed_bytes = source.stat().st_size
        hash_ok = bool(expected_sha) and observed_sha == expected_sha
        bytes_ok = expected_bytes is None or int(expected_bytes) == observed_bytes
        verdict = "PASS" if hash_ok and bytes_ok else "FAIL_HASH_OR_BYTES"
        source_file_hash_rows.append(
            {
                "path": str(relative),
                "expected_sha256": expected_sha,
                "observed_sha256": observed_sha,
                "expected_bytes": expected_bytes,
                "observed_bytes": observed_bytes,
                "verdict": verdict,
            }
        )
        if verdict == "PASS":
            pieces.append(pd.read_parquet(source))
    flow = pd.concat(pieces, ignore_index=True)
    flow["ticker"] = flow["ticker"].astype(str).str.upper().str.strip()
    flow["session_date"] = pd.to_datetime(flow["session_date"]).dt.normalize()
    official = flow.loc[flow["session_date"].isin(set(sessions))].copy()

    features = pd.read_parquet(ART / "foreign_flow_representation_v2.parquet")
    required_feature_columns = {"ticker", "feature_session", "flow_through_session", *FEATURES}
    missing_feature_columns = required_feature_columns - set(features.columns)
    if missing_feature_columns:
        raise RuntimeError(f"representation parquet is missing columns: {sorted(missing_feature_columns)}")
    features["feature_session"] = pd.to_datetime(features["feature_session"]).dt.normalize()
    features["flow_through_session"] = pd.to_datetime(features["flow_through_session"]).dt.normalize()
    panel = pd.read_parquet(
        PANEL_PATH,
        columns=[
            "ticker",
            "date",
            "high",
            "low",
            "close",
            "volume",
            "regular_market_value",
            "price_provenance",
            "corporate_action_integrity_verified",
        ],
    )
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.replace(
        ".JK", "", regex=False
    ).str.strip()
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("market panel has duplicate ticker/date rows")
    panel = panel.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    panel["prev_close"] = panel.groupby("ticker", sort=False)["close"].shift(1)
    panel["same_session_close_return"] = panel["close"] / panel["prev_close"] - 1.0
    panel["range_fraction"] = (panel["close"] - panel["low"]) / panel["close"]
    panel["intraday_range_fraction"] = (panel["high"] - panel["low"]) / panel["close"]

    context = pd.read_parquet(ART / "causal_market_context.parquet")
    context["ticker"] = context["ticker"].astype(str).str.upper().str.strip()
    context["date"] = pd.to_datetime(context["date"]).dt.normalize()
    if context.duplicated(["ticker", "date"]).any():
        raise RuntimeError("causal market context has duplicate ticker/date rows")
    context["universe_primary_liquid"] = context["universe_primary_liquid"].fillna(False).astype(bool)
    context = context.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    listing_excluded_rows = 0
    listing_excluded_tickers = 0
    master_tickers = set(master["ticker"])
    for ticker, rows in official.groupby("ticker", sort=False):
        if ticker in master_tickers:
            excluded = ~listed_mask(rows["session_date"], ticker, master)
            listing_excluded_rows += int(excluded.sum())
            listing_excluded_tickers += int(excluded.any())

    # This is a full independent reconstruction of every accepted V2 field.
    # No V2 module or helper is imported or called here.
    recalc = independent_v2_recompute(features, official, panel, context, master, sessions)
    checks = compare_recomputed_fields(features, recalc)
    causal = bool(
        (
            features["feature_session"].to_numpy()
            == features["flow_through_session"].map(
                {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
            ).to_numpy()
        ).all()
    )
    checks.append(
        {
            "check": "feature_session_next_official_session",
            "result": "PASS" if causal else "FAIL",
            "keys_expected": int(len(features)),
            "keys_recomputed": int(len(features)),
            "finite_expected": None,
            "finite_recomputed": None,
            "finite_value_mismatches": 0 if causal else int(len(features)),
            "nan_pattern_mismatches": 0,
            "max_abs_difference": None,
        }
    )
    key_columns = ["ticker", "feature_session", "flow_through_session"]
    next_by_session = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
    expected_temporal = features["flow_through_session"].map(next_by_session)
    recomputed_temporal = recalc["flow_through_session"].map(next_by_session)
    expected_unlisted_feature_rows = 0
    for ticker, rows in features.groupby("ticker", sort=False):
        if ticker in master_tickers:
            expected_unlisted_feature_rows += int(
                (~listed_mask(rows["feature_session"], ticker, master)).sum()
            )
    recomputed_unlisted_feature_rows = 0
    for ticker, rows in recalc.groupby("ticker", sort=False):
        if ticker in master_tickers:
            recomputed_unlisted_feature_rows += int(
                (~listed_mask(rows["feature_session"], ticker, master)).sum()
            )
    invariant_rows = [
        {
            "check": "expected_duplicate_output_keys",
            "value": int(features.duplicated(key_columns).sum()),
            "result": "PASS" if not features.duplicated(key_columns).any() else "FAIL",
        },
        {
            "check": "recomputed_duplicate_output_keys",
            "value": int(recalc.duplicated(key_columns).sum()),
            "result": "PASS" if not recalc.duplicated(key_columns).any() else "FAIL",
        },
        {
            "check": "expected_infinity_values",
            "value": int(np.isinf(features[FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).sum()),
            "result": "PASS" if not np.isinf(features[FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).any() else "FAIL",
        },
        {
            "check": "recomputed_infinity_values",
            "value": int(np.isinf(recalc[FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).sum()),
            "result": "PASS" if not np.isinf(recalc[FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).any() else "FAIL",
        },
        {
            "check": "expected_feature_session_shift",
            "value": int((features["feature_session"] != expected_temporal).sum()),
            "result": "PASS" if bool(features["feature_session"].eq(expected_temporal).all()) else "FAIL",
        },
        {
            "check": "recomputed_feature_session_shift",
            "value": int((recalc["feature_session"] != recomputed_temporal).sum()),
            "result": "PASS" if bool(recalc["feature_session"].eq(recomputed_temporal).all()) else "FAIL",
        },
        {
            "check": "expected_strict_chronology",
            "value": int((features["feature_session"] <= features["flow_through_session"]).sum()),
            "result": "PASS" if bool((features["feature_session"] > features["flow_through_session"]).all()) else "FAIL",
        },
        {
            "check": "recomputed_strict_chronology",
            "value": int((recalc["feature_session"] <= recalc["flow_through_session"]).sum()),
            "result": "PASS" if bool((recalc["feature_session"] > recalc["flow_through_session"]).all()) else "FAIL",
        },
        {
            "check": "listing_mask_boundary",
            "value": {
                "raw_excluded": listing_excluded_rows,
                "expected_output_unlisted": expected_unlisted_feature_rows,
                "recomputed_output_unlisted": recomputed_unlisted_feature_rows,
            },
            "result": "PASS" if expected_unlisted_feature_rows == 0 and recomputed_unlisted_feature_rows == 0 else "FAIL",
        },
    ]
    emit(pd.DataFrame(invariant_rows), "representation_invariant_audit.csv")
    emit(pd.DataFrame(checks), "representation_recomputation_audit.csv")

    source_file_hash_audit = pd.DataFrame(source_file_hash_rows)
    source_file_hash_audit["path_key"] = source_file_hash_audit["path"].map(
        lambda value: path_key((ARCH / str(value)).resolve())
    )
    duplicate_keys = set(
        source_file_hash_audit.loc[
            source_file_hash_audit["path_key"].duplicated(keep=False), "path_key"
        ]
    )
    if duplicate_keys:
        source_file_hash_audit.loc[
            source_file_hash_audit["path_key"].isin(duplicate_keys), "verdict"
        ] = "FAIL_DUPLICATE_MANIFEST_PATH"
    source_file_hash_audit = source_file_hash_audit.drop(columns=["path_key"])
    source_hash_failures = int((source_file_hash_audit["verdict"] != "PASS").sum())
    source_population_failures = source_hash_failures + normalized_duplicate_paths + normalized_missing_paths + normalized_unexpected_paths
    emit(source_file_hash_audit, "source_file_hash_audit.csv")
    archive_manifest_sha = sha256(archive_manifest_path)
    net_identity = flow["foreign_net"].eq(flow["foreign_buy"] - flow["foreign_sell"])
    invalid_numeric_counts = {}
    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        values = pd.to_numeric(flow[column], errors="coerce")
        invalid_numeric_counts[column] = int(
            values.isna().sum()
            + (~np.isfinite(values.fillna(0.0))).sum()
            + ((values.dropna() % 1) != 0).sum()
        )
    negative_buy_sell = int((flow[["foreign_buy", "foreign_sell"]] < 0).sum().sum())
    unit_values = sorted(flow["unit"].dropna().astype(str).unique().tolist())
    duplicate_rows = int(flow.duplicated(["ticker", "session_date"]).sum())
    active_zero_volume = 0
    for ticker, rows in panel.groupby("ticker", sort=False):
        if ticker not in set(master["ticker"]):
            continue
        listed = listed_mask(rows["date"], ticker, master)
        values = pd.to_numeric(rows["volume"], errors="coerce").to_numpy(dtype=float)
        active_zero_volume += int((listed & np.isfinite(values) & (values == 0.0)).sum())
    raw_contract = pd.DataFrame(
        [
            {"check": "archive_manifest_sha256", "value": archive_manifest_sha, "status": "PASS" if archive_manifest_sha == PINNED_INPUT_HASHES["archive_manifest"] else "FAIL"},
            {"check": "normalized_archive_file_count_expected", "value": {"expected": len(normalized_items), "declared": input_manifest["archive_manifest"]["archive_normalized_artifact_count"], "actual": len(actual_normalized_keys)}, "status": "PASS" if len(normalized_items) == input_manifest["archive_manifest"]["archive_normalized_artifact_count"] and len(actual_normalized_keys) == len(normalized_manifest_key_set) else "FAIL"},
            {"check": "input_manifest_normalized_path_set", "value": {"archive_manifest": len(normalized_manifest_key_set), "input_manifest": len(input_normalized_key_set), "missing": normalized_declaration_missing_paths, "unexpected": normalized_declaration_unexpected_paths, "duplicate_input": input_normalized_duplicate_paths}, "status": "PASS" if normalized_declaration_missing_paths == 0 and normalized_declaration_unexpected_paths == 0 and input_normalized_duplicate_paths == 0 else "FAIL"},
            {"check": "input_manifest_normalized_hashes", "value": normalized_declaration_hash_mismatches, "status": "PASS" if normalized_declaration_hash_mismatches == 0 else "FAIL"},
            {"check": "normalized_archive_manifest_duplicate_paths", "value": normalized_duplicate_paths, "status": "PASS" if normalized_duplicate_paths == 0 else "FAIL"},
            {"check": "normalized_archive_missing_paths", "value": normalized_missing_paths, "status": "PASS" if normalized_missing_paths == 0 else "FAIL"},
            {"check": "normalized_archive_unexpected_paths", "value": normalized_unexpected_paths, "status": "PASS" if normalized_unexpected_paths == 0 else "FAIL"},
            {"check": "normalized_archive_file_hashes_and_bytes", "value": {"pass": int((source_file_hash_audit["verdict"] == "PASS").sum()), "fail": source_hash_failures}, "status": "PASS" if source_population_failures == 0 else "FAIL"},
            {"check": "normalized_archive_files_loaded", "value": len(pieces), "status": "PASS" if not missing_files and source_population_failures == 0 else "FAIL"},
            {"check": "input_manifest_normalized_row_declaration", "value": {"sum_item_rows": declared_normalized_rows, "declared_total": input_declared_row_count}, "status": "PASS" if declared_normalized_rows == input_declared_row_count else "FAIL"},
            {"check": "raw_flow_rows_all_archive", "value": len(flow), "status": "PASS" if len(flow) == input_declared_row_count else "FAIL"},
            {"check": "raw_flow_rows_official_calendar", "value": len(official), "status": "INFO"},
            {"check": "calendar_sorted_unique", "value": len(sessions), "status": "PASS" if calendar_valid else "FAIL"},
            {"check": "raw_duplicate_ticker_session", "value": duplicate_rows, "status": "PASS" if duplicate_rows == 0 else "FAIL"},
            {"check": "unit", "value": unit_values, "status": "PASS" if unit_values == ["SHARES"] and flow["unit"].notna().all() else "FAIL"},
            {"check": "negative_buy_sell", "value": negative_buy_sell, "status": "PASS" if negative_buy_sell == 0 else "FAIL"},
            {"check": "invalid_numeric_buy_sell_net", "value": invalid_numeric_counts, "status": "PASS" if sum(invalid_numeric_counts.values()) == 0 else "FAIL"},
            {"check": "net_identity_mismatches", "value": int((~net_identity).sum()), "status": "PASS" if bool(net_identity.all()) else "FAIL"},
            {"check": "security_master_invalid_intervals", "value": master_invalid_intervals, "status": "PASS" if master_invalid_intervals == 0 else "FAIL"},
            {"check": "security_master_overlapping_intervals", "value": master_overlaps, "status": "PASS" if master_overlaps == 0 else "FAIL"},
            {"check": "listing_interval_excluded_rows", "value": listing_excluded_rows, "status": "PASS"},
            {"check": "active_zero_volume_rows", "value": active_zero_volume, "status": "PASS" if active_zero_volume == 0 else "FAIL"},
            {"check": "rows_outside_official_calendar", "value": len(flow) - len(official), "status": "INFO"},
            {"check": "outcome_columns_loaded", "value": [], "status": "PASS"},
            {"check": "provider_calls", "value": False, "status": "PASS"},
        ]
    )
    emit(raw_contract, "raw_contract_audit.csv")
    invariant_result = bool((pd.DataFrame(invariant_rows)["result"] == "PASS").all())
    v2_result = bool(all(row["result"] == "PASS" for row in checks) and invariant_result)
    raw_contract_result = bool(raw_contract["status"].isin(["PASS", "INFO"]).all())
    input_provenance_result = bool((input_provenance["verdict"] == "PASS").all())

    flow_analysis = official[["ticker", "session_date", "foreign_buy", "foreign_sell", "foreign_net"]].rename(columns={"session_date": "date"})
    analysis = panel.merge(flow_analysis, on=["ticker", "date"], how="left", validate="one_to_one")
    analysis["abs_net_shares"] = analysis["foreign_net"].abs()
    analysis["abs_net_notional"] = analysis["abs_net_shares"] * analysis["close"]
    analysis["abs_participation"] = analysis["abs_net_shares"] / analysis["volume"].where(analysis["volume"] > 0)
    analysis["abs_rmv_fraction"] = analysis["abs_net_notional"] / analysis["regular_market_value"].where(analysis["regular_market_value"] > 0)
    analysis["abs_shares_x_price"] = analysis["abs_net_shares"] * analysis["close"]
    analysis["flow_sign"] = np.sign(analysis["foreign_net"])
    analysis["price_sign"] = np.sign(analysis["same_session_close_return"])
    analysis["flow_price_agree"] = np.where((analysis["flow_sign"] != 0) & (analysis["price_sign"] != 0), analysis["flow_sign"] == analysis["price_sign"], np.nan)
    merged = features.merge(analysis[["ticker", "date", "close", "volume", "regular_market_value", "same_session_close_return", "range_fraction", "intraday_range_fraction"]], left_on=["ticker", "flow_through_session"], right_on=["ticker", "date"], how="left", validate="one_to_one").drop(columns=["date"])
    merged = merged.merge(flow_analysis.rename(columns={"date": "flow_through_session"}), on=["ticker", "flow_through_session"], how="left", validate="one_to_one")
    merged["abs_shock"] = pd.to_numeric(merged["foreign_flow_shock_1"], errors="coerce").abs()
    merged["abs_participation"] = pd.to_numeric(merged["foreign_participation_1"], errors="coerce").abs()
    merged["flow_abs_rmv_fraction"] = merged["foreign_net"].abs() * merged["close"] / merged["regular_market_value"].where(merged["regular_market_value"] > 0)
    merged["year"] = merged["feature_session"].dt.year

    coverage = features.groupby("flow_through_session").agg(output_rows=("ticker", "size"), output_tickers=("ticker", "nunique")).reset_index()
    raw_coverage = official.groupby("session_date").agg(flow_rows=("ticker", "size"), flow_tickers=("ticker", "nunique"), net_buy_rows=("foreign_net", lambda s: int((s > 0).sum())), net_sell_rows=("foreign_net", lambda s: int((s < 0).sum())), zero_flow_rows=("foreign_net", lambda s: int((s == 0).sum()))).reset_index().rename(columns={"session_date": "flow_through_session"})
    emit(coverage.merge(raw_coverage, on="flow_through_session", how="outer").sort_values("flow_through_session"), "coverage_census.csv")

    sample = analysis.dropna(subset=["abs_net_shares", "close", "volume", "regular_market_value"]).sample(n=min(200000, len(analysis.dropna(subset=["abs_net_shares", "close", "volume", "regular_market_value"]))), random_state=20260904)
    comparable = []
    for left, label in [("abs_net_shares", "absolute net shares"), ("abs_net_notional", "absolute net shares x close"), ("abs_participation", "absolute net / volume"), ("abs_rmv_fraction", "absolute net notional / regular market value")]:
        for right, right_label in [("close", "price level"), ("volume", "ordinary volume"), ("regular_market_value", "market value"), ("same_session_close_return", "same-session return"), ("intraday_range_fraction", "same-session range")]:
            n, correlation = rank_corr(sample, left, right)
            comparable.append({"measure": label, "conditioning_variable": right_label, "n": n, "spearman": correlation, "sample_rows": len(sample)})
    emit(pd.DataFrame(comparable), "raw_share_comparability.csv")

    by_ticker = merged.groupby("ticker").agg(rows=("ticker", "size"), shock_finite=("foreign_flow_shock_1", lambda s: int(s.notna().sum())), extreme_abs_shock_gt5=("abs_shock", lambda s: int((s > 5).sum())), extreme_abs_shock_gt20=("abs_shock", lambda s: int((s > 20).sum())), max_abs_shock=("abs_shock", "max"), max_abs_participation=("abs_participation", "max"), median_close=("close", "median"), median_volume=("volume", "median"), median_rmv=("regular_market_value", "median")).reset_index().sort_values(["max_abs_shock", "ticker"], ascending=[False, True])
    emit(by_ticker.head(200), "anomaly_census.csv")
    anomaly_columns = ["ticker", "flow_through_session", "feature_session", "foreign_buy", "foreign_sell", "foreign_net", "close", "volume", "regular_market_value", "foreign_participation_1", "foreign_flow_shock_1", "foreign_flow_shock_percentile_120", "foreign_flow_price_divergence_5", "same_session_close_return", "intraday_range_fraction"]
    emit(merged.loc[merged["abs_shock"].notna()].nlargest(150, "abs_shock")[anomaly_columns], "anomaly_top_rows.csv")
    requested = ["FUJI", "CASA", "JGLE", "PSKT"] + by_ticker.head(6)["ticker"].tolist()
    cases = merged.loc[merged["ticker"].isin(requested) & merged["abs_shock"].notna()].sort_values(["ticker", "abs_shock"], ascending=[True, False]).groupby("ticker", sort=False).head(8)
    emit(cases[anomaly_columns], "anomaly_case_studies.csv")

    known_ca = pd.read_csv(CA_PATH)
    ca_rows = []
    if not known_ca.empty:
        known_ca["ticker"] = known_ca["ticker"].astype(str).str.upper().str.strip()
        known_ca["transition_date"] = pd.to_datetime(known_ca["transition_date"], errors="coerce").dt.normalize()
        resolved_ca = known_ca.loc[
            known_ca["transition_status"].eq("RESOLVED") & known_ca["transition_date"].notna()
        ].copy()
        for row in resolved_ca.itertuples(index=False):
            window = merged.loc[(merged["ticker"] == row.ticker) & (merged["flow_through_session"] >= row.transition_date - pd.Timedelta(days=7)) & (merged["flow_through_session"] <= row.transition_date + pd.Timedelta(days=7))]
            ca_rows.append({"ticker": row.ticker, "event_family": getattr(row, "event_family", None), "transition_date": row.transition_date.date().isoformat(), "window_rows": len(window), "window_abs_shock_gt5": int((window["abs_shock"] > 5).sum()), "window_max_abs_shock": None if window["abs_shock"].dropna().empty else float(window["abs_shock"].max()), "authority": "bounded resolved transition_attestation_ledger V16", "scope": "not exhaustive; unknown/unresolved CA is not absence"})
    else:
        resolved_ca = known_ca.iloc[0:0].copy()
    emit(pd.DataFrame(ca_rows), "ca_listing_interaction.csv")
    emit(
        pd.DataFrame(
            [
                {"metric": "listing_interval_excluded_rows", "value": listing_excluded_rows, "status": "PASS"},
                {"metric": "listing_interval_excluded_tickers", "value": listing_excluded_tickers, "status": "PASS"},
                {"metric": "security_master_invalid_intervals", "value": master_invalid_intervals, "status": "PASS" if master_invalid_intervals == 0 else "FAIL"},
                {"metric": "security_master_overlapping_intervals", "value": master_overlaps, "status": "PASS" if master_overlaps == 0 else "FAIL"},
                {"metric": "resolved_CA_rows", "value": len(resolved_ca), "status": "PASS"},
                {"metric": "resolved_CA_tickers", "value": int(resolved_ca["ticker"].nunique()), "status": "PASS"},
                {"metric": "resolved_CA_event_families", "value": sorted(resolved_ca["event_family"].dropna().astype(str).unique().tolist()), "status": "PASS"},
                {"metric": "exhaustive_CA_absence", "value": "UNKNOWN", "status": "BLOCKED"},
            ]
        ),
        "listing_lifecycle_summary.csv",
    )

    conditioned = merged.dropna(subset=["foreign_flow_shock_1", "foreign_participation_1", "close", "volume", "regular_market_value"]).copy()
    conditioning_rows = []
    for column, label in [("close", "price"), ("volume", "volume"), ("regular_market_value", "market_value"), ("flow_abs_rmv_fraction", "flow_rmv_fraction")]:
        numeric = pd.to_numeric(conditioned[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        try:
            codes = pd.qcut(numeric, 3, labels=False, duplicates="drop")
            mapping = {0: "LOW", 1: "MID", 2: "HIGH"}
            conditioned["bin"] = codes.map(mapping).fillna("UNAVAILABLE")
        except ValueError:
            # A degenerate proxy (many exact zeros) still gets deterministic
            # distribution bins without inventing values.
            conditioned["bin"] = "UNAVAILABLE"
            valid = numeric.notna()
            if valid.any():
                ranked = numeric.loc[valid].rank(method="first")
                conditioned.loc[valid, "bin"] = pd.qcut(ranked, 3, labels=["LOW", "MID", "HIGH"])
        for group, values in conditioned.groupby("bin", observed=True):
            conditioning_rows.append({"conditioning": label, "bin": str(group), "rows": len(values), "median_abs_shock": float(values["abs_shock"].median()), "p95_abs_shock": float(values["abs_shock"].quantile(0.95)), "median_abs_participation": float(values["abs_participation"].median()), "median_flow_rmv_fraction": float(values["flow_abs_rmv_fraction"].median())})
    emit(pd.DataFrame(conditioning_rows), "liquidity_conditioning.csv")

    regime = merged.groupby("year").agg(rows=("ticker", "size"), shock_finite=("foreign_flow_shock_1", lambda s: int(s.notna().sum())), shock_median=("foreign_flow_shock_1", "median"), shock_p05=("foreign_flow_shock_1", lambda s: float(s.quantile(0.05))), shock_p95=("foreign_flow_shock_1", lambda s: float(s.quantile(0.95))), participation_median=("foreign_participation_1", "median"), abs_participation_p95=("abs_participation", lambda s: float(s.quantile(0.95))), divergence5_finite=("foreign_flow_price_divergence_5", lambda s: int(s.notna().sum()))).reset_index()
    emit(regime, "regime_analysis.csv")
    persistence = merged.groupby("year").agg(rows=("ticker", "size"), streak_median=("foreign_signed_streak_10", "median"), streak_abs_ge_03=("foreign_signed_streak_10", lambda s: int((s.abs() >= 0.3).sum())), persistence5_median=("foreign_weighted_persistence_5", "median"), persistence20_median=("foreign_weighted_persistence_20", "median"), acceleration_median=("foreign_flow_acceleration_5_20", "median")).reset_index()
    emit(persistence, "persistence_analysis.csv")

    cross = official.groupby("session_date").agg(rows=("ticker", "size"), tickers=("ticker", "nunique"), net_buy_breadth=("foreign_net", lambda s: int((s > 0).sum())), net_sell_breadth=("foreign_net", lambda s: int((s < 0).sum())), zero_breadth=("foreign_net", lambda s: int((s == 0).sum())), total_abs_net=("foreign_net", lambda s: float(s.abs().sum())), top10_abs_net_share=("foreign_net", lambda s: float(s.abs().nlargest(10).sum() / s.abs().sum()) if s.abs().sum() else np.nan), net_sum=("foreign_net", "sum")).reset_index()
    cross["buy_breadth_fraction"] = cross["net_buy_breadth"] / cross["tickers"]
    cross["sell_breadth_fraction"] = cross["net_sell_breadth"] / cross["tickers"]
    emit(cross, "cross_sectional_structure.csv")

    behavior = merged.dropna(subset=["foreign_net", "same_session_close_return", "foreign_participation_1", "foreign_flow_shock_1"]).copy()
    behavior["flow_direction"] = np.where(behavior["foreign_net"] > 0, "BUY", np.where(behavior["foreign_net"] < 0, "SELL", "ZERO"))
    behavior["price_direction"] = np.where(behavior["same_session_close_return"] > 0, "UP", np.where(behavior["same_session_close_return"] < 0, "DOWN", "FLAT"))
    behavior["effort_result"] = np.select([(behavior["abs_participation"] >= behavior["abs_participation"].quantile(0.9)) & (behavior["same_session_close_return"].abs() <= behavior["same_session_close_return"].abs().quantile(0.5)), (behavior["abs_participation"] >= behavior["abs_participation"].quantile(0.9)) & (behavior["same_session_close_return"].abs() > behavior["same_session_close_return"].abs().quantile(0.5))], ["HIGH_EFFORT_LOW_RESULT", "HIGH_EFFORT_HIGH_RESULT"], default="OTHER")
    emit(behavior.groupby(["flow_direction", "price_direction"]).agg(rows=("ticker", "size"), median_abs_participation=("abs_participation", "median"), median_abs_shock=("abs_shock", "median"), median_price_return=("same_session_close_return", "median")).reset_index(), "price_flow_behavior.csv")
    emit(behavior.groupby("effort_result").agg(rows=("ticker", "size"), median_abs_participation=("abs_participation", "median"), median_abs_shock=("abs_shock", "median"), median_abs_price_return=("same_session_close_return", lambda s: float(s.abs().median())), median_flow_rmv_fraction=("flow_abs_rmv_fraction", "median")).reset_index(), "effort_vs_result.csv")

    redundancy_cols = ["foreign_participation_1", "foreign_flow_shock_1", "foreign_flow_shock_mean_5", "foreign_flow_shock_mean_20", "foreign_flow_price_divergence_5", "foreign_flow_price_divergence_20", "foreign_weighted_persistence_5", "foreign_signed_streak_10", "foreign_flow_acceleration_5_20", "close", "volume", "regular_market_value", "same_session_close_return", "intraday_range_fraction", "range_fraction"]
    emit(merged[redundancy_cols].replace([np.inf, -np.inf], np.nan).corr(method="spearman", min_periods=1000), "redundancy_analysis.csv")

    emit(pd.DataFrame([
        {"feature_family": "raw net / participation", "source": "Stock Summary EOD t; panel volume", "availability": "t+1 official session", "warmup": "volume > 0", "PIT_status": "EOD-only under pinned source contract"},
        {"feature_family": "shock / persistence / percentile", "source": "flow t + close t + strictly prior RMV history", "availability": "t+1 after lookback", "warmup": "10 prior RMV; 5/20 rolling; 60/120 percentile", "PIT_status": "mechanically causal; historical publication timing UNKNOWN"},
        {"feature_family": "cross-sectional rank / divergence", "source": "primary-liquid source-session context", "availability": "t+1", "warmup": "valid primary cross-section", "PIT_status": "EOD-only; universe/revision risk"},
        {"feature_family": "same-session HLCV", "source": "local market panel session t", "availability": "descriptive contemporaneous", "warmup": "prior close for same-session return", "PIT_status": "behavioral only"},
        {"feature_family": "future outcomes / labels", "source": "not loaded", "availability": "forbidden", "warmup": "n/a", "PIT_status": "BLOCKED_NOT_ACCESSED"},
    ]), "pit_feature_contract.csv")

    emit(pd.DataFrame([
        {"hypothesis_id": "FF-BEH-01", "name": "persistent foreign accumulation", "evidence": "backward persistence exists but is highly redundant with shock history", "confounders": "liquidity, size, CA, listing, source timing", "disposition": "PARKED_MEDIUM"},
        {"hypothesis_id": "FF-BEH-02", "name": "flow-price disagreement / effort-result", "evidence": "same-session descriptive disagreement survives as an observable category", "confounders": "price basis, liquidity, CA, local counterflow", "disposition": "PARKED_MEDIUM"},
        {"hypothesis_id": "FF-BEH-03", "name": "extreme shock / participation", "evidence": "large tails exist but condition strongly on price/liquidity and unresolved CA", "confounders": "share denomination, illiquidity, listing lifecycle, CA", "disposition": "PARKED_LOW"},
        {"hypothesis_id": "FF-BEH-04", "name": "breadth / concentration regime", "evidence": "cross-sectional breadth and concentration are measurable", "confounders": "coverage and universe composition", "disposition": "PARKED_MEDIUM"},
    ]), "hypothesis_registry.csv")
    emit(pd.DataFrame([
        {"hypothesis": "raw shares directly comparable across tickers", "decision": "REJECT_UNSAFE", "reason": "share denomination and size/liquidity make raw counts non-comparable"},
        {"hypothesis": "V2 is independent of volume/liquidity by construction", "decision": "REJECT_UNPROVEN", "reason": "shock uses close-valued shares over prior RMV; participation uses volume; no PIT float series"},
        {"hypothesis": "extreme rows imply predictive alpha", "decision": "REJECT_IN_THIS_PHASE", "reason": "future outcomes and model evaluation are forbidden"},
        {"hypothesis": "no CA contamination around anomalies", "decision": "REJECT_UNSUPPORTED", "reason": "event-level population completeness is UNKNOWN"},
    ]), "rejected_hypotheses.csv")

    materializer_commit = current_git_commit()
    materializer_path = Path(__file__).resolve()
    materializer_sha = sha256(materializer_path)
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    complete = bool(v2_result and raw_contract_result and input_provenance_result)
    summary = {
        "status": "FOREIGN_FLOW_BEHAVIORAL_FORENSICS_V1_OFFLINE_COMPLETE" if complete else "FOREIGN_FLOW_BEHAVIORAL_FORENSICS_V1_BLOCKED",
        "generator": {"commit": materializer_commit, "path": str(materializer_path), "sha256": materializer_sha, "generated_at_utc": generated_at_utc},
        "coverage": {"raw_rows_all_archive": len(flow), "raw_rows_official": len(official), "raw_sessions_official": official["session_date"].nunique(), "raw_tickers": official["ticker"].nunique(), "feature_rows": len(features), "feature_tickers": features["ticker"].nunique(), "feature_sessions": features["feature_session"].nunique(), "panel_rows": len(panel), "panel_tickers": panel["ticker"].nunique()},
        "period": {"official": [sessions.min().date().isoformat(), sessions.max().date().isoformat()], "flow_official": [official["session_date"].min().date().isoformat(), official["session_date"].max().date().isoformat()], "feature": [features["feature_session"].min().date().isoformat(), features["feature_session"].max().date().isoformat()]},
        "v2_recomputation": {"result": "PASS" if v2_result else "FAIL", "checks": checks, "invariant_checks": invariant_rows, "independent_source": "notebooks/foreign_flow/build_behavioral_forensics_artifacts.py"},
        "raw_contract": {"result": "PASS" if raw_contract_result else "FAIL", "unit": "SHARES", "net_identity_mismatches": int((~net_identity).sum()), "archive_manifest_sha256": archive_manifest_sha, "normalized_archive_files_expected": int(len(source_file_hash_audit)), "normalized_archive_files_verified": int((source_file_hash_audit["verdict"] == "PASS").sum()), "normalized_archive_file_failures": source_hash_failures, "normalized_archive_population_failures": source_population_failures, "normalized_archive_manifest_duplicate_paths": normalized_duplicate_paths, "normalized_archive_missing_paths": normalized_missing_paths, "normalized_archive_unexpected_paths": normalized_unexpected_paths, "input_manifest_normalized_path_set_failures": normalized_declaration_missing_paths + normalized_declaration_unexpected_paths + input_normalized_duplicate_paths, "input_manifest_normalized_hash_failures": normalized_declaration_hash_mismatches, "source_file_hash_audit": "source_file_hash_audit.csv"},
        "input_provenance": {"result": "PASS" if input_provenance_result else "FAIL", "verified_files": int((input_provenance["verdict"] == "PASS").sum()), "rows": int(len(input_provenance)), "audit": "input_provenance_audit.csv"},
        "listing": {"excluded_rows": listing_excluded_rows, "excluded_tickers": listing_excluded_tickers, "security_master_invalid_intervals": master_invalid_intervals, "security_master_overlapping_intervals": master_overlaps},
        "ca_scope": {"resolved_rows": int(len(resolved_ca)), "resolved_tickers": int(resolved_ca["ticker"].nunique()), "resolved_event_families": sorted(resolved_ca["event_family"].dropna().astype(str).unique().tolist()), "exhaustive_absence": "UNKNOWN"},
        "outcome_firewall": {"outcomes_loaded": False, "future_returns_loaded": False, "model_fit": False, "provider_calls": False, "production_state_mutation": False},
        "known_ca_scope": "bounded resolved transition attestations only; exhaustive historical CA absence UNKNOWN",
        "decision": "INTERESTING_BUT_TOO_QUALIFIED",
        "predictive_testing_justified": False,
    }
    missing_outputs = sorted((EXPECTED_OUTPUTS - {"MANIFEST.json"}) - {path.name for path in OUT.iterdir() if path.is_file()})
    if missing_outputs:
        raise RuntimeError(f"output root is missing expected generated files: {missing_outputs}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_report_provenance(summary)
    files = {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "MANIFEST.json"}
    manifest = {"schema": "idx-trade/foreign-flow-behavioral-forensics-v1", "status": summary["status"], "created_at": "2026-09-04", "generator": summary["generator"], "source_artifact_manifest": str(ART / "manifest.json"), "source_artifact_manifest_sha256": sha256(ART / "manifest.json"), "input_manifest": str(ART / "input_manifest.json"), "input_manifest_sha256": sha256(ART / "input_manifest.json"), "archive_manifest": str(archive_manifest_path), "archive_manifest_sha256": sha256(archive_manifest_path), "ca_manifest": str(CA_MANIFEST_PATH), "ca_manifest_sha256": PINNED_INPUT_HASHES["ca_manifest"], "ca_ledger": str(CA_PATH), "ca_ledger_sha256": PINNED_INPUT_HASHES["ca_ledger"], "summary": summary, "files": files, "no_provider_calls": True, "outcome_blind": True}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output_root": str(OUT), "manifest_sha256": sha256(OUT / "MANIFEST.json"), "files": len(files), "v2": summary["v2_recomputation"]}, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
