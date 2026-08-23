from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.historical_e2e_replay_readiness_v1 import run_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Outcome-blind historical E2E data-readiness audit")
    parser.add_argument("--structural-root", type=Path, default=Path(r"D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"))
    parser.add_argument("--panel", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_final_20260820_v2\model_safe_signal_research_panel_1260_final_clean.parquet"))
    parser.add_argument("--calendar", type=Path, default=Path(r"D:\Documents\Project\idx-v4-x1-clean-historical-input-stage-r2-20260820\official_exchange_sessions_1260.csv"))
    parser.add_argument("--ca-window-root", type=Path, default=Path(r"D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v3"))
    parser.add_argument("--dividend-root", type=Path, default=Path(r"D:\Documents\Project\idx-e2e-forward-dividend-v1-2-offline-replay-20260823-v5"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run_audit(
        structural_root=args.structural_root.resolve(), panel_path=args.panel.resolve(), calendar_path=args.calendar.resolve(),
        ca_window_root=args.ca_window_root.resolve(), dividend_root=args.dividend_root.resolve(), output_dir=args.output_dir.resolve()
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

