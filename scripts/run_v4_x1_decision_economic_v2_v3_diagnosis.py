from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_economic_comparison import sha256_file  # noqa: E402
from idx_trade.decision_economic_v2_v3_diagnosis import (  # noqa: E402
    DecisionEconomicV2V3DiagnosisError,
    run_v2_v3_diagnosis,
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
    parser.add_argument("--decision-v2-root", type=Path, default=DEFAULT_V2_ROOT)
    parser.add_argument("--decision-v3-root", type=Path, default=DEFAULT_V3_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir.expanduser().resolve()
    if out.exists():
        raise DecisionEconomicV2V3DiagnosisError(f"REFUSE_OVERWRITE:{out}")

    summary, sessions, details, source, v2, v3 = run_v2_v3_diagnosis(
        args.historical_root,
        args.decision_v2_root,
        args.decision_v3_root,
    )

    out.mkdir(parents=True, exist_ok=False)
    summary_path = out / "summary.json"
    sessions_path = out / "session_decomposition.csv"
    details_path = out / "differential_names.csv"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sessions.to_csv(sessions_path, index=False, lineterminator="\n")
    details.to_csv(details_path, index=False, lineterminator="\n")

    manifest = {
        "schema_version": "decision_economic_v2_v3_focused_diagnosis_manifest_v1",
        "status": summary["status"],
        "development_evidence_only": True,
        "executable_policy_pnl": False,
        "policy_or_threshold_tuning": False,
        "source_manifest_sha256": source.manifest_sha256,
        "source_score_sha256": source.score_sha256,
        "source_target_sha256": source.target_sha256,
        "decision_v2_manifest_sha256": v2.source_manifest_sha256,
        "decision_v3_manifest_sha256": v3.source_manifest_sha256,
        "artifacts": {
            "summary.json": sha256_file(summary_path),
            "session_decomposition.csv": sha256_file(sessions_path),
            "differential_names.csv": sha256_file(details_path),
        },
    }
    manifest_path = out / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    compact = {
        "status": summary["status"],
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }
    for horizon in ("H5", "H10"):
        h = summary["horizons"][horizon]
        full = h["full_target_pure_substitution"]
        under = h["v2_underfill_mixed"]
        compact[f"{horizon}_pairwise_support_dates"] = h[
            "pairwise_complete_support_dates"
        ]
        compact[f"{horizon}_overall_v2_minus_v3_gross_mean"] = h[
            "overall_v2_minus_v3_gross"
        ]["mean"]
        compact[f"{horizon}_full_target_dates"] = full["dates"]
        compact[f"{horizon}_full_target_v2_minus_v3_gross_mean"] = full[
            "v2_minus_v3_gross"
        ]["mean"]
        compact[f"{horizon}_v2_only_retained_return_mean"] = full[
            "v2_only_retained"
        ]["return"]["mean"]
        compact[f"{horizon}_v3_only_new_return_mean"] = full["v3_only_new"][
            "return"
        ]["mean"]
        compact[f"{horizon}_v2_only_retained_rank_band_counts"] = full[
            "v2_only_retained"
        ]["rank_band_counts"]
        compact[f"{horizon}_underfill_dates"] = under["dates"]
        compact[f"{horizon}_underfill_v2_minus_v3_gross_mean"] = under[
            "v2_minus_v3_gross"
        ]["mean"]
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
