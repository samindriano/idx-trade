"""Outcome-blind forensic audit of corporate-action price-basis integrity.

This audit consumes only previously accepted local artifacts.  It does not
load target values, outcomes, model binaries, or provider data.  The script
is intentionally a structural evidence producer: it does not mutate any
canonical panel or model artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


EXPECTED_V11_MANIFEST = (
    "62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6"
)
EXPECTED_V12_MANIFEST = (
    "620fbd1f98924365e623919d3339f005abd7960f66631213631b845dcd7061f5"
)
EXPECTED_PARENT_PANEL = (
    "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
)
EXPECTED_COMBINED_MANIFEST = (
    "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
)
EXPECTED_FINAL_REFIT_MANIFEST = (
    "3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094"
)

DEFAULT_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v"
)
DEFAULT_V11 = DEFAULT_ROOT / "tradingview_v2_1_training_basis_impact_v1_1_20260820"
DEFAULT_V12 = DEFAULT_ROOT / "tradingview_v2_1_training_basis_impact_v1_2_20260820"
DEFAULT_PARENT_ROOT = Path(
    r"D:\Documents\Project\idx-v4-3-ca-training-domain-idx-combined-replay-20260819-v1"
)
DEFAULT_REFIT_ROOT = Path(r"D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1")
DEFAULT_CA_ROOT = Path(
    r"D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v1"
)


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def normalize_ticker(value: object) -> str:
    return str(value or "").upper().replace(".JK", "").strip()


def normalize_date(value: object) -> str:
    text = str(value or "").strip()
    if len(text) < 10 or text[:10] != text[:10].replace("/", "-"):
        # The accepted artifacts use ISO dates.  Refuse anything else rather
        # than silently applying locale/date inference.
        raise RuntimeError(f"INVALID_ISO_DATE:{text}")
    date = text[:10]
    parts = date.split("-")
    if len(parts) != 3 or any(not p.isdigit() for p in parts):
        raise RuntimeError(f"INVALID_ISO_DATE:{text}")
    return date


def parse_bool(value: object, *, field: str) -> bool:
    text = str(value).strip().lower()
    if text not in {"true", "false"}:
        raise RuntimeError(f"INVALID_BOOLEAN:{field}:{value}")
    return text == "true"


def parse_int(value: object, *, field: str) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"INVALID_INTEGER:{field}:{value}") from exc
    return parsed


def parse_float(value: object, *, field: str) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"INVALID_FLOAT:{field}:{value}") from exc
    if not math.isfinite(parsed):
        raise RuntimeError(f"NONFINITE_FLOAT:{field}:{value}")
    return parsed


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def register_file(path: Path, *, role: str, expected_sha: str | None = None) -> dict[str, Any]:
    actual = sha256_file(path)
    if expected_sha and actual != expected_sha:
        raise RuntimeError(f"SHA_MISMATCH:{path}:{actual}!={expected_sha}")
    stat = path.stat()
    return {
        "path": str(path),
        "role": role,
        "sha256": actual,
        "bytes": int(stat.st_size),
    }


def verify_small_manifests(
    v11: Path,
    v12: Path,
    parent_root: Path,
    refit_root: Path,
) -> dict[str, Any]:
    v11_manifest = read_json(v11 / "artifact_manifest.json")
    v12_manifest = read_json(v12 / "artifact_manifest.json")
    parent_manifest = read_json(parent_root / "MANIFEST.json")
    refit_manifest = read_json(refit_root / "MANIFEST.json")
    if sha256_file(v11 / "artifact_manifest.json") != EXPECTED_V11_MANIFEST:
        raise RuntimeError("V11_MANIFEST_SHA_MISMATCH")
    if sha256_file(v12 / "artifact_manifest.json") != EXPECTED_V12_MANIFEST:
        raise RuntimeError("V12_MANIFEST_SHA_MISMATCH")
    if sha256_file(parent_root / "MANIFEST.json") != EXPECTED_COMBINED_MANIFEST:
        raise RuntimeError("COMBINED_MANIFEST_SHA_MISMATCH")
    if sha256_file(refit_root / "MANIFEST.json") != EXPECTED_FINAL_REFIT_MANIFEST:
        raise RuntimeError("FINAL_REFIT_MANIFEST_SHA_MISMATCH")
    return {
        "v11": v11_manifest.get("schema_version"),
        "v12": v12_manifest.get("schema_version"),
        "parent": parent_manifest.get("schema_version"),
        "refit": refit_manifest.get("schema_version"),
    }


def load_session_index(combined_path: Path) -> dict[str, int]:
    required = {"ticker", "date", "session_index"}
    result: dict[str, int] = {}
    with combined_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(reader.fieldnames or set()):
            raise RuntimeError(f"COMBINED_COLUMNS_MISSING:{sorted(required)}")
        for row in reader:
            date = normalize_date(row["date"])
            index = parse_int(row["session_index"], field="session_index")
            previous = result.get(date)
            if previous is not None and previous != index:
                raise RuntimeError(f"SESSION_INDEX_CONFLICT:{date}:{previous}:{index}")
            result[date] = index
    if not result:
        raise RuntimeError("EMPTY_SESSION_INDEX")
    return result


def load_final_dates(refit_dates_path: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {"H5": set(), "H10": set()}
    with refit_dates_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"head", "date"}
        if not required.issubset(reader.fieldnames or set()):
            raise RuntimeError("FINAL_DATES_COLUMNS_MISSING")
        for row in reader:
            head = str(row["head"]).strip().upper()
            if head not in result:
                raise RuntimeError(f"UNEXPECTED_FINAL_HEAD:{head}")
            result[head].add(normalize_date(row["date"]))
    if not all(result.values()):
        raise RuntimeError("FINAL_DATES_EMPTY")
    return result


def load_bbca_fit_support(
    combined_path: Path,
    final_dates: dict[str, set[str]],
) -> tuple[dict[str, set[tuple[str, str]]], dict[str, int]]:
    required = {
        "ticker",
        "date",
        "session_index",
        "h5_full_target_support",
        "h10_full_target_support",
    }
    support: dict[str, set[tuple[str, str]]] = {"H5": set(), "H10": set()}
    bbca_flags = Counter()
    with combined_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(reader.fieldnames or set()):
            raise RuntimeError("COMBINED_SUPPORT_COLUMNS_MISSING")
        for row in reader:
            ticker = normalize_ticker(row["ticker"])
            if ticker != "BBCA":
                continue
            date = normalize_date(row["date"])
            for head, column in (
                ("H5", "h5_full_target_support"),
                ("H10", "h10_full_target_support"),
            ):
                flag = parse_bool(row[column], field=column)
                bbca_flags[f"{head}_support_true" if flag else f"{head}_support_false"] += 1
                if flag and date in final_dates[head]:
                    support[head].add((ticker, date))
    return support, dict(bbca_flags)


def build_bbca_trace(
    panel_path: Path,
    session_index: dict[str, int],
    bbca_support: dict[str, set[tuple[str, str]]],
    split_date: str = "2021-10-13",
    horizon_sessions: int = 60,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if split_date not in session_index:
        raise RuntimeError(f"BBCA_SPLIT_DATE_NOT_IN_SESSIONS:{split_date}")
    split_index = session_index[split_date]
    trace_end_date = max(
        date for date, index in session_index.items()
        if split_index <= index <= split_index + horizon_sessions
    )
    fields = [
        "ticker",
        "date",
        "panel_high",
        "panel_low",
        "panel_close",
        "price_provenance",
        "idx_high",
        "idx_low",
        "idx_close",
    ]
    rows: list[dict[str, Any]] = []
    with panel_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(fields).issubset(reader.fieldnames or set()):
            raise RuntimeError("PANEL_BASIS_COLUMNS_MISSING")
        for source in reader:
            if normalize_ticker(source["ticker"]) != "BBCA":
                continue
            date = normalize_date(source["date"])
            if date < split_date or date > trace_end_date:
                continue
            index = session_index.get(date)
            if index is None:
                # The accepted combined support replay starts later than
                # the panel's available history.  Pre-split rows outside the
                # replay's session map are not needed for the bounded trace;
                # any post-split gap is a hard integrity failure.
                raise RuntimeError(f"BBCA_DATE_NOT_IN_SESSIONS:{date}")
            delta = index - split_index
            if delta < 0 or delta > horizon_sessions:
                continue
            record: dict[str, Any] = {
                "ticker": "BBCA",
                "date": date,
                "session_index": index,
                "sessions_since_recorded_split": delta,
                "panel_high": source["panel_high"],
                "panel_low": source["panel_low"],
                "panel_close": source["panel_close"],
                "price_provenance": source["price_provenance"],
                "idx_high": source["idx_high"],
                "idx_low": source["idx_low"],
                "idx_close": source["idx_close"],
                "panel_idx_hlc_exact": source["panel_idx_hlc_exact"],
                "lookback_5_contains_pre_ca": delta < 5,
                "lookback_atr14_contains_pre_ca": delta < 14,
                "lookback_20_contains_pre_ca": delta < 20,
                "lookback_60_contains_pre_ca": delta < 60,
                "h5_exact_final_fit_identity": ("BBCA", date) in bbca_support["H5"],
                "h10_exact_final_fit_identity": ("BBCA", date) in bbca_support["H10"],
            }
            rows.append(record)
    rows.sort(key=lambda row: int(row["session_index"]))
    if not rows:
        raise RuntimeError("BBCA_TRACE_EMPTY")
    summary = {
        "recorded_split_date": split_date,
        "recorded_split_session_index": split_index,
        "recorded_split_ratio": "1:5",
        "rows_traced": len(rows),
        "first_post_split_rows_in_trace": sum(
            1 for row in rows if int(row["sessions_since_recorded_split"]) == 0
        ),
        "window_exposure_rows": {
            "lag5_or_equivalent": sum(row["lookback_5_contains_pre_ca"] for row in rows),
            "atr14": sum(row["lookback_atr14_contains_pre_ca"] for row in rows),
            "rolling20_or_lag20": sum(row["lookback_20_contains_pre_ca"] for row in rows),
            "rolling60": sum(row["lookback_60_contains_pre_ca"] for row in rows),
        },
        "exact_final_fit_rows": {
            "H5": sum(row["h5_exact_final_fit_identity"] for row in rows),
            "H10": sum(row["h10_exact_final_fit_identity"] for row in rows),
        },
        "interpretation": (
            "FEATURE_LAYER_EXPOSURE_PRESENT_BUT_BBCA_EXCLUDED_FROM_EXACT_FINAL_FIT"
            if not any(row["h5_exact_final_fit_identity"] or row["h10_exact_final_fit_identity"] for row in rows)
            else "FEATURE_LAYER_AND_EXACT_FINAL_FIT_EXPOSURE_PRESENT"
        ),
    }
    return rows, summary


def load_affected_tickers(runs_path: Path) -> set[str]:
    with runs_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "ticker" not in (reader.fieldnames or set()):
            raise RuntimeError("STABLE_RUNS_TICKER_MISSING")
        tickers = {normalize_ticker(row["ticker"]) for row in reader}
    if not tickers:
        raise RuntimeError("STABLE_RUNS_EMPTY")
    return tickers


def build_exact_fit_impact(
    combined_path: Path,
    final_dates: dict[str, set[str]],
    v4_impact_path: Path,
    affected_tickers: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    required_combined = {
        "ticker",
        "date",
        "session_index",
        "h5_full_target_support",
        "h10_full_target_support",
    }
    exact_keys: dict[str, dict[tuple[str, str], int]] = {"H5": {}, "H10": {}}
    with combined_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required_combined.issubset(reader.fieldnames or set()):
            raise RuntimeError("COMBINED_EXACT_FIT_COLUMNS_MISSING")
        for row in reader:
            ticker = normalize_ticker(row["ticker"])
            date = normalize_date(row["date"])
            key = (ticker, date)
            for head, column in (
                ("H5", "h5_full_target_support"),
                ("H10", "h10_full_target_support"),
            ):
                if date in final_dates[head] and parse_bool(row[column], field=column):
                    exact_keys[head][key] = parse_int(row["session_index"], field="session_index")

    fields: list[str]
    impact_rows: list[dict[str, Any]] = []
    v4_counts = Counter()
    with v4_impact_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        required = {"ticker", "date", "changed_feature_count", "changed_features"}
        if not required.issubset(set(fields)):
            raise RuntimeError("V4_IMPACT_COLUMNS_MISSING")
        for row in reader:
            changed = parse_int(row["changed_feature_count"], field="changed_feature_count")
            if changed <= 0:
                continue
            ticker = normalize_ticker(row["ticker"])
            date = normalize_date(row["date"])
            key = (ticker, date)
            heads = [head for head in ("H5", "H10") if key in exact_keys[head]]
            if not heads:
                continue
            direct_or_spillover = "DIRECT" if ticker in affected_tickers else "SPILLOVER"
            for head in heads:
                impact_rows.append(
                    {
                        "head": head,
                        "ticker": ticker,
                        "date": date,
                        "session_index": exact_keys[head][key],
                        "direct_or_spillover": direct_or_spillover,
                        "changed_feature_count": changed,
                        "changed_features": row["changed_features"],
                    }
                )
                v4_counts[f"{head}_rows"] += 1
                v4_counts[f"{head}_{direct_or_spillover.lower()}_rows"] += 1
    by_head: dict[str, Any] = {}
    union_keys: set[tuple[str, str]] = set()
    for head in ("H5", "H10"):
        scoped = [row for row in impact_rows if row["head"] == head]
        keys = {(row["ticker"], row["date"]) for row in scoped}
        union_keys.update(keys)
        by_head[head] = {
            "exact_fit_rows": len(exact_keys[head]),
            "changed_rows": len(keys),
            "changed_tickers": len({row["ticker"] for row in scoped}),
            "changed_dates": len({row["date"] for row in scoped}),
            "direct_changed_rows": sum(row["direct_or_spillover"] == "DIRECT" for row in scoped),
            "spillover_changed_rows": sum(row["direct_or_spillover"] == "SPILLOVER" for row in scoped),
        }
    union_scoped = {
        (row["ticker"], row["date"]): row["direct_or_spillover"]
        for row in impact_rows
        if (row["ticker"], row["date"]) in union_keys
    }
    by_head["UNION"] = {
        "exact_fit_rows": len({*exact_keys["H5"], *exact_keys["H10"]}),
        "changed_rows": len(union_scoped),
        "changed_tickers": len({ticker for ticker, _ in union_scoped}),
        "changed_dates": len({date for _, date in union_scoped}),
        "direct_changed_rows": sum(value == "DIRECT" for value in union_scoped.values()),
        "spillover_changed_rows": sum(value == "SPILLOVER" for value in union_scoped.values()),
    }
    return impact_rows, by_head, dict(v4_counts)


def build_spillover_summary(impact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in impact_rows:
        groups[(str(row["head"]), str(row["direct_or_spillover"]))].append(row)
    result = []
    for (head, scope), rows in sorted(groups.items()):
        result.append(
            {
                "head": head,
                "scope": scope,
                "changed_rows": len(rows),
                "changed_tickers": len({row["ticker"] for row in rows}),
                "changed_dates": len({row["date"] for row in rows}),
                "source": "v1.2 exact-fit support-only reconstruction",
            }
        )
    union_rows = {
        (row["ticker"], row["date"]): row["direct_or_spillover"]
        for row in impact_rows
    }
    for scope in ("DIRECT", "SPILLOVER"):
        scoped = [key for key, value in union_rows.items() if value == scope]
        if scoped:
            result.append(
                {
                    "head": "UNION",
                    "scope": scope,
                    "changed_rows": len(scoped),
                    "changed_tickers": len({ticker for ticker, _ in scoped}),
                    "changed_dates": len({date for _, date in scoped}),
                    "source": "v1.2 exact-fit support-only reconstruction",
                }
            )
    return result


def event_census(ca_evidence_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    required = {
        "source_kind",
        "ticker",
        "event_family",
        "candidate_date",
        "effective_date_status",
        "continuity_status",
        "source_action_id",
        "source_ref",
        "source_sha256",
        "published_at_utc",
        "evidence_id",
    }
    rows: list[dict[str, Any]] = []
    with ca_evidence_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(reader.fieldnames or set()):
            raise RuntimeError("CA_EVIDENCE_COLUMNS_MISSING")
        for source in reader:
            rows.append(
                {
                    "source_kind": source["source_kind"],
                    "ticker": normalize_ticker(source["ticker"]),
                    "event_family": source["event_family"],
                    "candidate_date": source["candidate_date"],
                    "effective_date_status": source["effective_date_status"],
                    "continuity_status": source["continuity_status"],
                    "source_action_id": source["source_action_id"],
                    "source_ref": source["source_ref"],
                    "source_sha256": source["source_sha256"],
                    "published_at_utc": source["published_at_utc"],
                    "evidence_id": source["evidence_id"],
                }
            )
    if not rows:
        raise RuntimeError("CA_EVIDENCE_EMPTY")
    counts = Counter(row["event_family"] for row in rows)
    return rows, {"evidence_rows": len(rows), "event_family_counts": dict(sorted(counts.items()))}


def build_summary(
    output: Path,
    input_manifest: dict[str, Any],
    bbca_summary: dict[str, Any],
    bbca_flags: dict[str, int],
    exact_fit: dict[str, Any],
    event_summary: dict[str, Any],
    manifests: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "ca_feature_basis_integrity_audit_v1",
        "status": "AUDIT_COMPLETE_REVIEW_REQUIRED",
        "verdict": {
            "BACKWARD_CA_FEATURE_WINDOW_RISK": "PRESENT_NO_CA_AWARE_BACKWARD_RESET_FOUND",
            "EXACT_FINAL_FIT_IMPACT": "MATERIAL_FOR_ACCEPTED_12_TICKER_BASIS_OVERLAY",
            "BBCA_2021_VERDICT": "EXCLUDED_BEFORE_FIT",
            "MARKET_WIDE_SEVERITY": "MATERIAL_LOCALIZED_AND_UNRESOLVED_MARKET_WIDE_COVERAGE",
            "EXISTING_GUARD_COVERAGE": "TARGET_WINDOW_CONTINUITY_ONLY_NOT_BACKWARD_FEATURE_WINDOWS",
            "REMEDIATION_REQUIRED": "YES_REVIEW_CA_AWARE_FEATURE_WINDOW_POLICY_AND_REVALIDATE_INPUTS",
        },
        "guardrails": {
            "outcome_blind": True,
            "provider_calls": False,
            "target_values_accessed": False,
            "outcomes_accessed": False,
            "model_fit": False,
            "model_scoring": False,
            "canonical_artifacts_mutated": False,
            "feature_definition_mutated": False,
            "v4_x1_contract_mutated": False,
        },
        "bbca_2021": {
            **bbca_summary,
            "combined_support_flags": bbca_flags,
            "source_interpretation": (
                "The recorded 2021-10-13 1:5 split creates raw-basis feature-window exposure. "
                "BBCA is not in exact H5/H10 fit support because CA continuity support remains false."
            ),
        },
        "accepted_overlay_exact_fit_impact": exact_fit,
        "market_ca_event_census": event_summary,
        "lineage": {
            "historical_runner": "scripts/run_v4_3r_historical_one_shot.py@08233877eb1f94e0ddefcd4f35409923f1c7dda5",
            "feature_builder": "src/idx_trade/ranking_v4_3_features.py@c3c3d97bd09b5d97665b12fc9063eb3baf518a55",
            "target_builder": "src/idx_trade/ranking_v4_3_target_execution.py@e659a7362fce8fcf047b612edba27018183c7762",
            "ca_training_domain": "src/idx_trade/ranking_v4_3_ca_training_domain.py@c51ca2a502df0d115417cf67dfc978d59ef30dab",
            "price_basis_remediation": "src/idx_trade/price_basis_remediation.py@c088710037257bcfd63670349be08bc15a52eae8",
            "open_remediation": "src/idx_trade/price_basis_open_remediation.py@efd3e7bfb37951f1f60b0ae8d995bba6e44b38be",
            "clean_consolidation": "src/idx_trade/v4_x_clean_data_consolidation.py@eee928c5e2c81ef1aad755191d50f780b2ad1da4",
        },
        "artifact_root": str(output),
        "input_manifest_sha256": input_manifest["manifest_sha256"],
        "verified_manifests": manifests,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v11-root", type=Path, default=DEFAULT_V11)
    parser.add_argument("--v12-root", type=Path, default=DEFAULT_V12)
    parser.add_argument("--parent-root", type=Path, default=DEFAULT_PARENT_ROOT)
    parser.add_argument("--refit-root", type=Path, default=DEFAULT_REFIT_ROOT)
    parser.add_argument("--ca-root", type=Path, default=DEFAULT_CA_ROOT)
    parser.add_argument("--parent-panel", type=Path, default=Path(
        r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"
    ))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_OUTPUT:{output}")

    v11 = args.v11_root.resolve()
    v12 = args.v12_root.resolve()
    parent = args.parent_root.resolve()
    refit = args.refit_root.resolve()
    ca_root = args.ca_root.resolve()
    panel_path = v11 / "panel_vs_idx_basis_rows.csv"
    combined_path = parent / "v4_3_full_target_support_rows_idx_combined.csv"
    final_dates_path = refit / "v4_x1_final_training_dates.csv"
    v4_impact_path = v11 / "v4_x1_candidate_training_feature_impact_rows.csv"
    runs_path = v11 / "stable_scale_runs.csv"
    ca_evidence_path = ca_root / "event_family_evidence.csv"

    manifests = verify_small_manifests(v11, v12, parent, refit)
    input_files = [
        register_file(v11 / "artifact_manifest.json", role="accepted_v1_1_manifest", expected_sha=EXPECTED_V11_MANIFEST),
        register_file(v12 / "artifact_manifest.json", role="accepted_v1_2_manifest", expected_sha=EXPECTED_V12_MANIFEST),
        register_file(parent / "MANIFEST.json", role="accepted_ca_combined_manifest", expected_sha=EXPECTED_COMBINED_MANIFEST),
        register_file(refit / "MANIFEST.json", role="accepted_final_refit_manifest", expected_sha=EXPECTED_FINAL_REFIT_MANIFEST),
        register_file(args.parent_panel.resolve(), role="frozen_parent_panel", expected_sha=EXPECTED_PARENT_PANEL),
        register_file(panel_path, role="v1_1_panel_basis_rows"),
        register_file(runs_path, role="v1_1_stable_scale_runs"),
        register_file(v4_impact_path, role="v1_1_v4_candidate_feature_impact_rows"),
        register_file(combined_path, role="accepted_support_only_combined_replay"),
        register_file(final_dates_path, role="accepted_final_refit_dates"),
        register_file(ca_evidence_path, role="accepted_ca_event_family_evidence"),
    ]
    input_manifest_payload = {
        "schema_version": "ca_feature_basis_integrity_audit_input_manifest_v1",
        "source_repo": "samindriano/idx-trade",
        "source_main_ref": "origin/main",
        "source_main_sha": "abef0d47b0f728adcffbb7c4e6353b09739fa66f",
        "consumed_files": input_files,
        "scientific_boundaries": {
            "outcome_blind": True,
            "target_values_loaded": False,
            "provider_calls": False,
            "model_fit_or_score": False,
        },
    }
    input_bytes = json.dumps(input_manifest_payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    input_manifest_payload["content_sha256"] = hashlib.sha256(input_bytes).hexdigest()

    session_index = load_session_index(combined_path)
    final_dates = load_final_dates(final_dates_path)
    bbca_support, bbca_flags = load_bbca_fit_support(combined_path, final_dates)
    bbca_rows, bbca_summary = build_bbca_trace(panel_path, session_index, bbca_support)
    affected_tickers = load_affected_tickers(runs_path)
    impact_rows, exact_fit, _ = build_exact_fit_impact(
        combined_path, final_dates, v4_impact_path, affected_tickers
    )
    event_rows, event_summary = event_census(ca_evidence_path)

    output.mkdir(parents=True, exist_ok=False)
    (output / "input_manifest.json").write_text(
        json.dumps(input_manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_csv(
        output / "bbca_2021_trace.csv",
        [
            "ticker",
            "date",
            "session_index",
            "sessions_since_recorded_split",
            "panel_high",
            "panel_low",
            "panel_close",
            "price_provenance",
            "idx_high",
            "idx_low",
            "idx_close",
            "panel_idx_hlc_exact",
            "lookback_5_contains_pre_ca",
            "lookback_atr14_contains_pre_ca",
            "lookback_20_contains_pre_ca",
            "lookback_60_contains_pre_ca",
            "h5_exact_final_fit_identity",
            "h10_exact_final_fit_identity",
        ],
        bbca_rows,
    )
    exposure_rows = []
    exposure_map = [
        ("lag5_or_close_return_5", 5, "close_return_5 = close / close.shift(5) - 1", "lookback_5_contains_pre_ca"),
        ("atr14", 14, "ATR14 rolling true range uses prior close", "lookback_atr14_contains_pre_ca"),
        ("rolling20_or_close_return_20", 20, "close_return_20 and rolling20 high/low", "lookback_20_contains_pre_ca"),
        ("rolling60", 60, "rolling60 high/low and 60-session history", "lookback_60_contains_pre_ca"),
    ]
    for name, window, formula, field in exposure_map:
        exposure_map_rows = [row for row in bbca_rows if row[field]]
        exposure_rows.append(
            {
                "ticker": "BBCA",
                "feature_family": name,
                "window_sessions": window,
                "formula_or_semantics": formula,
                "post_ca_rows_exposed": len(exposure_map_rows),
                "exact_h5_final_fit_rows": sum(row["h5_exact_final_fit_identity"] for row in exposure_map_rows),
                "exact_h10_final_fit_rows": sum(row["h10_exact_final_fit_identity"] for row in exposure_map_rows),
                "status": "EXPOSURE_PRESENT_BUT_EXACT_FIT_EXCLUDED" if exposure_map_rows else "NO_EXPOSURE_IN_TRACE",
            }
        )
    write_csv(
        output / "backward_feature_window_exposure.csv",
        [
            "ticker",
            "feature_family",
            "window_sessions",
            "formula_or_semantics",
            "post_ca_rows_exposed",
            "exact_h5_final_fit_rows",
            "exact_h10_final_fit_rows",
            "status",
        ],
        exposure_rows,
    )
    write_csv(
        output / "final_fit_identity_impact.csv",
        [
            "head",
            "ticker",
            "date",
            "session_index",
            "direct_or_spillover",
            "changed_feature_count",
            "changed_features",
        ],
        impact_rows,
    )
    write_csv(
        output / "cross_sectional_spillover_summary.csv",
        ["head", "scope", "changed_rows", "changed_tickers", "changed_dates", "source"],
        build_spillover_summary(impact_rows),
    )
    write_csv(
        output / "ca_event_census.csv",
        [
            "source_kind",
            "ticker",
            "event_family",
            "candidate_date",
            "effective_date_status",
            "continuity_status",
            "source_action_id",
            "source_ref",
            "source_sha256",
            "published_at_utc",
            "evidence_id",
        ],
        event_rows,
    )

    input_manifest_path = output / "input_manifest.json"
    input_manifest_sha = sha256_file(input_manifest_path)
    summary = build_summary(
        output,
        {"manifest_sha256": input_manifest_sha},
        bbca_summary,
        bbca_flags,
        exact_fit,
        event_summary,
        manifests,
    )
    summary["input_manifest_sha256"] = input_manifest_sha
    summary_path = output / "audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    generated = {}
    for path in sorted(output.iterdir()):
        if path.name == "audit_manifest.json":
            continue
        generated[path.name] = sha256_file(path)
    audit_manifest = {
        "schema_version": "ca_feature_basis_integrity_audit_manifest_v1",
        "status": "AUDIT_COMPLETE_REVIEW_REQUIRED",
        "input_manifest_sha256": input_manifest_sha,
        "generated_artifact_hashes": generated,
        "guardrails": summary["guardrails"],
        "verdict": summary["verdict"],
        "bbca_2021": bbca_summary,
        "exact_fit": exact_fit,
        "event_census": event_summary,
        "no_canonical_artifact_overwrite": True,
    }
    manifest_path = output / "audit_manifest.json"
    manifest_path.write_text(json.dumps(audit_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output_dir": str(output),
        "audit_manifest_sha256": sha256_file(manifest_path),
        "input_manifest_sha256": input_manifest_sha,
        "bbca": bbca_summary,
        "exact_fit": exact_fit,
        "event_census": event_summary,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
