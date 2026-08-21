from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_economic_robustness import (  # noqa: E402
    DecisionEconomicRobustnessError,
    run_six_block_robustness,
)

DEFAULT_COMPARISON_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-economic-comparison-20260822-v1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-root", type=Path, default=DEFAULT_COMPARISON_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise DecisionEconomicRobustnessError(f"REFUSE_OVERWRITE:{output_dir}")

    summary = run_six_block_robustness(args.comparison_root)
    output_dir.mkdir(parents=True, exist_ok=False)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "decision_economic_fixed_6block_robustness_manifest_v1",
        "status": summary["status"],
        "comparison_manifest_sha256": "d33ec5ab0b6c4c7642c5faf42a7f5980f3d5e4d3d7668552d309aea0ed6e2622",
        "development_evidence_only": True,
        "new_outcomes_accessed": False,
        "policy_or_threshold_tuning": False,
        "artifacts": {"summary.json": _sha256(summary_path)},
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    compact = {"status": summary["status"], "manifest": str(manifest_path), "manifest_sha256": _sha256(manifest_path)}
    for horizon in ("H5", "H10"):
        compact[f"{horizon}_common_support_by_block"] = summary["horizons"][horizon]["block_common_support_counts"]
        compact[f"{horizon}_robustness_counts"] = summary["horizons"][horizon]["robustness_counts"]
        compact[f"{horizon}_v2_minus_v3_gross_mean_by_block"] = [
            item["v2_minus_v3"]["gross"]["mean"]
            for item in summary["horizons"][horizon]["blocks"]
        ]
        compact[f"{horizon}_v2_minus_v3_primary_mean_by_block"] = [
            item["v2_minus_v3"]["primary_net_proxy"]["mean"]
            for item in summary["horizons"][horizon]["blocks"]
        ]
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
