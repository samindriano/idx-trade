from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .provenance import sha256_file
from .research_v2_models import ALL_RANKING_V2_MODELS, V1_HGB_CONTROL, V2_CANDIDATES
from .research_v2_validation import comparison_to_control, select_v2_champion


def integrate_v2_results(*, metric_paths: list[Path], output_dir: Path) -> dict[str, object]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("Ranking V2 integration output directory must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    if len(metric_paths) != len(ALL_RANKING_V2_MODELS):
        raise ValueError(f"expected {len(ALL_RANKING_V2_MODELS)} metric files")

    frames: list[pd.DataFrame] = []
    input_hashes: dict[str, str] = {}
    for path in metric_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        if "candidate" not in frame.columns:
            raise ValueError(f"metrics file has no candidate column: {path}")
        if frame["candidate"].nunique() != 1:
            raise ValueError(f"metrics file contains multiple candidates: {path}")
        frames.append(frame)
        input_hashes[str(path)] = sha256_file(path)

    metrics = pd.concat(frames, ignore_index=True)
    actual = set(metrics["candidate"].astype(str))
    expected = set(ALL_RANKING_V2_MODELS)
    if actual != expected:
        raise ValueError(f"candidate set mismatch: expected={sorted(expected)} actual={sorted(actual)}")

    decision, champion, aggregate = select_v2_champion(metrics)
    comparison = comparison_to_control(aggregate)

    all_metrics_path = output_dir / "ranking_v2_all_fold_metrics.csv"
    aggregate_path = output_dir / "ranking_v2_candidate_aggregate.csv"
    comparison_path = output_dir / "ranking_v2_comparison_to_v1_control.csv"
    metrics.sort_values(["candidate", "fold"]).to_csv(all_metrics_path, index=False)
    aggregate.to_csv(aggregate_path, index=False)
    comparison.to_csv(comparison_path, index=False)

    output_hashes = {
        all_metrics_path.name: sha256_file(all_metrics_path),
        aggregate_path.name: sha256_file(aggregate_path),
        comparison_path.name: sha256_file(comparison_path),
    }
    summary = {
        "status": decision,
        "historical_development_champion": champion,
        "eligible_candidates": aggregate.loc[aggregate["eligible"].astype(bool), "candidate"].tolist(),
        "control_candidate": V1_HGB_CONTROL,
        "v2_candidates": list(V2_CANDIDATES),
        "input_metric_sha256": input_hashes,
        "output_sha256": output_hashes,
        "probability_v1_status": "PROBABILITY_V1_NOT_READY_DEFERRED",
        "independent_validation_claim": False,
        "historical_period_through_2026_07_31_is_development_knowledge": True,
        "fresh_forward_validation_required": True,
        "fresh_forward_start_strictly_after": "2026-07-31",
        "stage6_authorized": False,
        "paper_live_authorized": False,
    }
    summary_path = output_dir / "ranking_v2_integration_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Integrate frozen Ranking V2 candidate metrics without rerunning models")
    parser.add_argument("--metric", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = integrate_v2_results(metric_paths=args.metric, output_dir=args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
