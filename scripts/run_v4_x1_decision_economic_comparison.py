from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_economic_comparison import (  # noqa: E402
    DecisionEconomicComparisonError,
    run_comparison,
    sha256_file,
)

DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_V2_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"
)
DEFAULT_V3_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-graded-evidence-structural-replay-20260821-v2"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    parser.add_argument("--decision-v1-root", type=Path, required=True)
    parser.add_argument("--decision-v2-root", type=Path, default=DEFAULT_V2_ROOT)
    parser.add_argument("--decision-v3-root", type=Path, default=DEFAULT_V3_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _write_text(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise DecisionEconomicComparisonError(f"REFUSE_OVERWRITE:{output_dir}")

    summary, outcomes, turnover = run_comparison(
        args.historical_root,
        args.decision_v1_root,
        args.decision_v2_root,
        args.decision_v3_root,
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    summary_path = output_dir / "summary.json"
    outcome_path = output_dir / "policy_signal_outcomes.csv"
    turnover_path = output_dir / "membership_turnover_cost_proxy.csv"

    _write_text(
        summary_path,
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
    )
    outcomes.to_csv(outcome_path, index=False, lineterminator="\n")
    turnover.to_csv(turnover_path, index=False, lineterminator="\n")

    artifacts = {
        "summary.json": sha256_file(summary_path),
        "policy_signal_outcomes.csv": sha256_file(outcome_path),
        "membership_turnover_cost_proxy.csv": sha256_file(turnover_path),
    }
    manifest = {
        "schema_version": "decision_economic_target_outcome_comparison_manifest_v1",
        "status": summary["status"],
        "development_evidence_only": True,
        "historical_executable_nav_computed": False,
        "policy_or_threshold_tuning": False,
        "alpha_refit_or_retune": False,
        "protected_or_fresh_forward_access": False,
        "provider_or_network_calls": False,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "MANIFEST.json"
    _write_text(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )

    compact = {
        "status": summary["status"],
        "H5_common_support_dates": summary["horizons"]["H5"]["common_support_dates"],
        "H10_common_support_dates": summary["horizons"]["H10"]["common_support_dates"],
        "H5_gross_ranking": summary["horizons"]["H5"]["common_support_rankings"]["GROSS_MEAN"],
        "H5_primary_net_proxy_ranking": summary["horizons"]["H5"]["common_support_rankings"]["NET_PROXY_PRIMARY"],
        "H10_gross_ranking": summary["horizons"]["H10"]["common_support_rankings"]["GROSS_MEAN"],
        "H10_primary_net_proxy_ranking": summary["horizons"]["H10"]["common_support_rankings"]["NET_PROXY_PRIMARY"],
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }
    print(json.dumps(_json_safe(compact), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
