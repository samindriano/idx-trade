from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v2_2_evaluation import (  # noqa: E402
    DecisionV22EvaluationError,
    run_v2_2_evaluation,
)


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise DecisionV22EvaluationError(f"REFUSE_OVERWRITE:{output}")

    summary, outcomes, turnover = run_v2_2_evaluation(str(args.historical_root))
    output.mkdir(parents=True, exist_ok=False)
    summary_path = output / "summary.json"
    outcomes_path = output / "daily_economic_targets.csv"
    turnover_path = output / "turnover_cost_proxy.csv"
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outcomes.to_csv(outcomes_path, index=False, lineterminator="\n")
    turnover.to_csv(turnover_path, index=False, lineterminator="\n")

    manifest = {
        "schema_version": "decision_v2_2_coherent_vacancy_admission_evaluation_manifest_v1",
        "status": summary["status"],
        "rule_id": summary["rule"]["rule_id"],
        "source": summary["source"],
        "single_candidate_only": True,
        "threshold_sweep": False,
        "alpha_refit_or_rescore": False,
        "executable_historical_nav": False,
        "artifacts": {
            "summary.json": _sha256(summary_path),
            "daily_economic_targets.csv": _sha256(outcomes_path),
            "turnover_cost_proxy.csv": _sha256(turnover_path),
        },
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    structural = summary["structural"]
    compact = {
        "status": summary["status"],
        "rule_id": summary["rule"]["rule_id"],
        "v2_replacements": structural["DECISION_V2"]["total_replacements_excluding_bootstrap"],
        "v2_2_replacements": structural["DECISION_V2_2"]["total_replacements_excluding_bootstrap"],
        "v2_mean_target_rank": structural["DECISION_V2"]["mean_target_rank"],
        "v2_2_mean_target_rank": structural["DECISION_V2_2"]["mean_target_rank"],
        "v2_underfilled_sessions": structural["DECISION_V2"]["underfilled_sessions"],
        "v2_2_underfilled_sessions": structural["DECISION_V2_2"]["underfilled_sessions"],
        "v2_vacancy_days": structural["DECISION_V2"]["vacancy_days"],
        "v2_2_vacancy_days": structural["DECISION_V2_2"]["vacancy_days"],
        "v2_rank_gt50_name_days": structural["DECISION_V2"]["target_rank_gt50_name_days"],
        "v2_2_rank_gt50_name_days": structural["DECISION_V2_2"]["target_rank_gt50_name_days"],
        "v2_2_coherent_vacancy_fills": structural["DECISION_V2_2"]["coherent_vacancy_fills"],
        "v2_2_soft_replacement_buys": structural["DECISION_V2_2"]["ordinary_soft_replacement_buys"],
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
    }
    for horizon in ("H5", "H10"):
        direct = summary["economic"][horizon]["V2_2_MINUS_V2"]
        vs_naive = summary["economic"][horizon]["V2_2_MINUS_NAIVE"]
        compact[f"{horizon}_v2_2_vs_v2_common_support_dates"] = direct["common_support_dates"]
        compact[f"{horizon}_v2_2_minus_v2_gross_mean"] = direct["gross_delta_mean"]
        compact[f"{horizon}_v2_2_minus_v2_primary_mean"] = direct["primary_delta_mean"]
        compact[f"{horizon}_v2_2_vs_v2_gross_win_share"] = direct["gross_win_share"]
        compact[f"{horizon}_v2_2_minus_naive_gross_mean"] = vs_naive["gross_delta_mean"]
        compact[f"{horizon}_v2_2_minus_naive_primary_mean"] = vs_naive["primary_delta_mean"]
    print(json.dumps(_json_safe(compact), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
