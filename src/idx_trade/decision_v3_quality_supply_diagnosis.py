from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from .decision_v3_failure_diagnosis import (
    DecisionV3FailureDiagnosisError,
    EXPECTED_ARTIFACT_SHA256,
    EXPECTED_PLAN_DIGEST,
    EXPECTED_SESSIONS,
    load_frozen_v3_structural_ledgers,
)
from .decision_v3_structural_source import (
    EXPECTED_SCORE_ROWS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    canonical_json_sha256,
    load_pinned_v4_x1_source_strict,
    sha256_file,
)

CONTRACT_RELATIVE_PATH = Path("docs/specs/decision_v3_quality_supply_diagnosis_v1.json")
EXPECTED_CONTRACT_CANONICAL_SHA256 = "aa03d5a016354cd0e98c6577a6b67e31fe3a93dc98cf9358c5e24fd6a59e6f21"
EXPECTED_FAILURE_DIAGNOSIS_MANIFEST_SHA256 = "73350606e408f987602575797f67474f83839256debee7e7b74496255beb0cab"
EXPECTED_SEVERE_SESSIONS = 373

B_REASON = "TIER_B_VACANCY_FILL"
C_REASON = "TIER_C_RESIDUAL_VACANCY_FILL"
A_REASON = "TIER_A_VACANCY_FILL"


@dataclass(frozen=True)
class QualitySupplyDiagnosisResult:
    summary: dict[str, Any]
    severe_session_supply: pd.DataFrame
    bc_entrant_path: pd.DataFrame
    block_summary: pd.DataFrame


def verify_quality_supply_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_NOT_OBJECT")
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_CONTRACT_CANONICAL_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"QUALITY_SUPPLY_CONTRACT_SHA_CHANGED:{actual}!={EXPECTED_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_EXECUTION":
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_STATUS_CHANGED")
    if payload.get("execution_authorized") is not False:
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_EXECUTION_FLAG_CHANGED")
    forbidden = payload.get("forbidden", {})
    if not forbidden or not all(value is True for value in forbidden.values()):
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_CONTRACT_FORBIDDEN_GUARD_CHANGED")
    return path


def _targets_by_session(memberships: pd.DataFrame) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for index, block in memberships.groupby("session_index", sort=True):
        result[int(index)] = set(block["ticker"].astype(str))
    return result


def _rank_maps(frame: pd.DataFrame) -> tuple[list[pd.Timestamp], dict[int, dict[str, int]]]:
    dates = sorted(pd.Timestamp(x).normalize() for x in frame["date"].drop_duplicates())
    maps: dict[int, dict[str, int]] = {}
    for index, day in enumerate(dates):
        block = frame.loc[frame["date"].eq(day), ["ticker", "rank_consensus"]]
        maps[index] = {
            str(row.ticker): int(row.rank_consensus)
            for row in block.itertuples(index=False)
        }
    return dates, maps


def classify_top10_supply(
    *,
    current_ranks: dict[str, int],
    previous_ranks: dict[str, int],
    start_holdings: set[str],
) -> dict[str, list[str]]:
    out = {"A": [], "B": [], "C": [], "D": []}
    for ticker, rank in sorted(current_ranks.items(), key=lambda item: (item[1], item[0])):
        if rank > 10 or ticker in start_holdings:
            continue
        previous = previous_ranks.get(ticker)
        if previous is None:
            out["D"].append(ticker)
        elif previous <= 20:
            out["A"].append(ticker)
        elif previous <= 50:
            out["B"].append(ticker)
        else:
            out["C"].append(ticker)
    return out


def _future_quality(
    *,
    ticker: str,
    entry_index: int,
    horizon: int,
    rank_maps: dict[int, dict[str, int]],
) -> tuple[int | None, bool | None]:
    index = entry_index + horizon
    if index not in rank_maps or (index - 1) not in rank_maps:
        return None, None
    current = rank_maps[index].get(ticker)
    previous = rank_maps[index - 1].get(ticker)
    if current is None:
        return None, False
    return current, bool(previous is not None and current <= 10 and previous <= 20)


def run_quality_supply_diagnosis(
    *,
    structural_root: str | Path,
    historical_root: str | Path,
) -> QualitySupplyDiagnosisResult:
    ledgers = load_frozen_v3_structural_ledgers(structural_root)
    source = load_pinned_v4_x1_source_strict(historical_root)

    dates, rank_maps = _rank_maps(source.frame)
    if len(dates) != EXPECTED_SESSIONS:
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_SESSION_COUNT_CHANGED")
    target_by_session = _targets_by_session(ledgers.memberships)
    sessions = ledgers.sessions.set_index(ledgers.sessions["session_index"].astype(int))

    severe_indices = [
        int(index)
        for index, row in sessions.iterrows()
        if int(row["severe_exit_count"]) > 0 and int(index) > 0
    ]
    if len(severe_indices) != EXPECTED_SEVERE_SESSIONS:
        raise DecisionV3FailureDiagnosisError(
            f"QUALITY_SUPPLY_SEVERE_SESSION_COUNT_CHANGED:{len(severe_indices)}"
        )

    supply_rows: list[dict[str, Any]] = []
    for index in severe_indices:
        row = sessions.loc[index]
        record: dict[str, Any] = {
            "session_index": index,
            "date": pd.Timestamp(dates[index]).strftime("%Y-%m-%d"),
            "block": index // 100 + 1,
            "severe_exit_count": int(row["severe_exit_count"]),
            "mandatory_exit_count": int(row["severe_exit_count"])
            + int(row["confirmed_mild_exit_count"])
            + int(row["universe_exit_count"]),
            "actual_tier_a_fill_count": int(row["tier_a_vacancy_fill_count"]),
            "actual_tier_b_fill_count": int(row["tier_b_vacancy_fill_count"]),
            "actual_tier_c_fill_count": int(row["tier_c_vacancy_fill_count"]),
            "actual_target_size": int(row["target_size"]),
        }
        for horizon in range(4):
            j = index + horizon
            if j >= EXPECTED_SESSIONS or j == 0:
                for tier in ("a", "b", "c", "d"):
                    record[f"t_plus_{horizon}_{tier}_unheld_top10_supply"] = None
                record[f"t_plus_{horizon}_a_supply_ge_initial_severe_exits"] = None
                continue
            start_holdings = set(target_by_session.get(j - 1, set()))
            supply = classify_top10_supply(
                current_ranks=rank_maps[j],
                previous_ranks=rank_maps[j - 1],
                start_holdings=start_holdings,
            )
            for tier in ("A", "B", "C", "D"):
                record[f"t_plus_{horizon}_{tier.lower()}_unheld_top10_supply"] = len(supply[tier])
            record[f"t_plus_{horizon}_a_supply_ge_initial_severe_exits"] = (
                len(supply["A"]) >= int(row["severe_exit_count"])
            )
        supply_rows.append(record)

    severe_supply = pd.DataFrame(supply_rows).sort_values(
        ["session_index"], kind="mergesort"
    ).reset_index(drop=True)

    intents = ledgers.intents.loc[
        ledgers.intents["side"].eq("BUY_INTENT")
        & ledgers.intents["reason"].isin([B_REASON, C_REASON])
    ].copy()
    path_rows: list[dict[str, Any]] = []
    for intent in intents.itertuples(index=False):
        entry_index = int(intent.session_index)
        ticker = str(intent.ticker)
        tier = "B" if str(intent.reason) == B_REASON else "C"
        record = {
            "ticker": ticker,
            "entry_index": entry_index,
            "entry_date": str(intent.date),
            "entry_block": entry_index // 100 + 1,
            "entry_tier": tier,
            "entry_rank": int(intent.rank_consensus),
            "entry_severe_session": bool(int(sessions.loc[entry_index]["severe_exit_count"]) > 0),
            "full_horizon_3_available": bool(entry_index + 3 < EXPECTED_SESSIONS),
        }
        first_conversion: int | None = None
        for horizon in (1, 2, 3):
            rank, quality = _future_quality(
                ticker=ticker,
                entry_index=entry_index,
                horizon=horizon,
                rank_maps=rank_maps,
            )
            record[f"t_plus_{horizon}_rank"] = rank
            record[f"t_plus_{horizon}_tier_a_equivalent"] = quality
            if quality is True and first_conversion is None:
                first_conversion = horizon
        record["first_tier_a_equivalent_horizon_1_to_3"] = first_conversion
        path_rows.append(record)
    bc_path = pd.DataFrame(path_rows).sort_values(
        ["entry_index", "entry_tier", "entry_rank", "ticker"], kind="mergesort"
    ).reset_index(drop=True)

    def _rate(series: pd.Series) -> float | None:
        clean = series.dropna()
        return None if clean.empty else float(clean.astype(bool).mean())

    horizon_summary: dict[str, Any] = {}
    for horizon in range(4):
        col = f"t_plus_{horizon}_a_unheld_top10_supply"
        coverage = f"t_plus_{horizon}_a_supply_ge_initial_severe_exits"
        vals = pd.to_numeric(severe_supply[col], errors="coerce").dropna()
        horizon_summary[f"t_plus_{horizon}"] = {
            "observations": int(vals.size),
            "mean_unheld_a_supply": None if vals.empty else float(vals.mean()),
            "median_unheld_a_supply": None if vals.empty else float(vals.median()),
            "share_a_supply_ge_initial_severe_exits": _rate(severe_supply[coverage]),
        }

    entrant_summary: dict[str, Any] = {}
    for tier in ("B", "C"):
        tier_block = bc_path.loc[bc_path["entry_tier"].eq(tier)]
        scopes = {
            "all": tier_block,
            "severe_session_only": tier_block.loc[tier_block["entry_severe_session"].astype(bool)],
            "nonsevere_session_only": tier_block.loc[~tier_block["entry_severe_session"].astype(bool)],
        }
        tier_summary: dict[str, Any] = {}
        for scope_name, block in scopes.items():
            scope_summary: dict[str, Any] = {"entries": int(len(block))}
            for horizon in (1, 2, 3):
                scope_summary[f"tier_a_equivalent_at_t_plus_{horizon}_rate"] = _rate(
                    block[f"t_plus_{horizon}_tier_a_equivalent"]
                )
            eligible = block.loc[block["full_horizon_3_available"].astype(bool)]
            first = pd.to_numeric(
                eligible["first_tier_a_equivalent_horizon_1_to_3"], errors="coerce"
            )
            scope_summary["full_3_session_window_entries"] = int(len(eligible))
            scope_summary["converted_within_3_sessions_rate"] = (
                None if len(eligible) == 0 else float(first.notna().mean())
            )
            tier_summary[scope_name] = scope_summary
        entrant_summary[tier] = tier_summary

    block_rows: list[dict[str, Any]] = []
    for label, blocks in (
        ("STRESS_3_6", {3, 6}),
        ("REFERENCE_1_2_4_5", {1, 2, 4, 5}),
    ):
        ss = severe_supply.loc[severe_supply["block"].isin(blocks)]
        bp = bc_path.loc[bc_path["entry_block"].isin(blocks)]
        rec: dict[str, Any] = {
            "group": label,
            "severe_sessions": int(len(ss)),
            "mean_severe_exits": None if ss.empty else float(ss["severe_exit_count"].mean()),
            "mean_actual_tier_b_fill": None if ss.empty else float(ss["actual_tier_b_fill_count"].mean()),
            "mean_actual_tier_c_fill": None if ss.empty else float(ss["actual_tier_c_fill_count"].mean()),
        }
        for horizon in range(4):
            vals = pd.to_numeric(
                ss[f"t_plus_{horizon}_a_unheld_top10_supply"], errors="coerce"
            ).dropna()
            rec[f"t_plus_{horizon}_mean_unheld_a_supply"] = (
                None if vals.empty else float(vals.mean())
            )
            rec[f"t_plus_{horizon}_share_a_supply_ge_initial_severe"] = _rate(
                ss[f"t_plus_{horizon}_a_supply_ge_initial_severe_exits"]
            )
        for tier in ("B", "C"):
            tb = bp.loc[
                bp["entry_tier"].eq(tier)
                & bp["entry_severe_session"].astype(bool)
            ]
            eligible = tb.loc[tb["full_horizon_3_available"].astype(bool)]
            first = pd.to_numeric(
                eligible["first_tier_a_equivalent_horizon_1_to_3"], errors="coerce"
            )
            rec[f"{tier.lower()}_severe_session_entries"] = int(len(tb))
            rec[f"{tier.lower()}_severe_session_full_3_window_entries"] = int(len(eligible))
            rec[f"{tier.lower()}_severe_session_converted_within_3_rate"] = (
                None if len(eligible) == 0 else float(first.notna().mean())
            )
        block_rows.append(rec)
    block_summary = pd.DataFrame(block_rows)

    summary = {
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_QUALITY_SUPPLY_DIAGNOSIS",
        "scientific_boundary": {
            "decision_v4_implemented_or_replayed": False,
            "counterfactual_wait_policy_simulated": False,
            "hypothetical_portfolio_or_pnl_computed": False,
            "returns_or_outcomes_accessed": False,
            "protected_or_fresh_forward_accessed": False,
            "model_refit_or_retune": False,
            "provider_or_network_called": False,
        },
        "pins": {
            "parent_status": ledgers.manifest.get("status"),
            "parent_plan_digest": EXPECTED_PLAN_DIGEST,
            "parent_artifacts": EXPECTED_ARTIFACT_SHA256,
            "failure_diagnosis_manifest_sha256": EXPECTED_FAILURE_DIAGNOSIS_MANIFEST_SHA256,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "source_score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "sessions": EXPECTED_SESSIONS,
            "rows": EXPECTED_SCORE_ROWS,
        },
        "severe_sessions": int(len(severe_supply)),
        "observed_severe_session_refill": {
            "severe_exits_total": int(severe_supply["severe_exit_count"].sum()),
            "tier_a_fills_total": int(severe_supply["actual_tier_a_fill_count"].sum()),
            "tier_b_fills_total": int(severe_supply["actual_tier_b_fill_count"].sum()),
            "tier_c_fills_total": int(severe_supply["actual_tier_c_fill_count"].sum()),
        },
        "observed_unheld_tier_a_supply_after_severe_session": horizon_summary,
        "actual_v3_b_c_entrant_quality_path": entrant_summary,
        "interpretation_guard": (
            "Supply coverage and later Tier-A-equivalent conversion are descriptive rank-stream "
            "statistics on the already-observed V3 trajectory only. They do not add back B/C names "
            "that a hypothetical wait-policy would have left unheld, and they are not a simulation "
            "of holding cash or waiting N sessions."
        ),
    }
    return QualitySupplyDiagnosisResult(
        summary=summary,
        severe_session_supply=severe_supply,
        bc_entrant_path=bc_path,
        block_summary=block_summary,
    )


def write_quality_supply_artifacts(
    result: QualitySupplyDiagnosisResult,
    output_dir: str | Path,
) -> Path:
    out = Path(output_dir).expanduser().resolve()
    if out.exists():
        raise DecisionV3FailureDiagnosisError(f"QUALITY_SUPPLY_OUTPUT_EXISTS:{out}")
    staging = out.with_name(out.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=False)
    try:
        (staging / "summary.json").write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result.severe_session_supply.to_csv(
            staging / "severe_session_supply.csv", index=False, lineterminator="\n"
        )
        result.bc_entrant_path.to_csv(
            staging / "bc_entrant_path.csv", index=False, lineterminator="\n"
        )
        result.block_summary.to_csv(
            staging / "block_summary.csv", index=False, lineterminator="\n"
        )
        artifacts = {
            name: sha256_file(staging / name)
            for name in (
                "summary.json",
                "severe_session_supply.csv",
                "bc_entrant_path.csv",
                "block_summary.csv",
            )
        }
        manifest = {
            "status": result.summary["status"],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
            "parent_plan_digest": EXPECTED_PLAN_DIGEST,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "source_score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "artifacts": artifacts,
            "guards": result.summary["scientific_boundary"],
        }
        (staging / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.replace(out)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return out / "MANIFEST.json"
