"""Outcome-blind final challenge across the audited IDX runtime boundaries."""

from __future__ import annotations

import json
from typing import Any

from research.idx_execution_evaluation_quantity_boundary_probe_v1 import (
    run_probe as run_execution_evaluation_probe,
)
from research.idx_malformed_latest_snapshot_recovery_probe_v1 import (
    run_probe as run_snapshot_recovery_probe,
)
from research.idx_post_entry_weight_drift_probe_v1 import (
    run_probe as run_post_entry_risk_probe,
)
from research.idx_quantity_obligation_replay_harness_v1 import (
    run_spec_scenario,
)
from research.idx_reconciliation_flag_provenance_probe_v1 import (
    run_probe as run_reconciliation_probe,
)


def run_challenge() -> dict[str, Any]:
    """Compose prior bounded probes without touching production or outcomes."""

    execution_evaluation = run_execution_evaluation_probe()
    obligation_spec = run_spec_scenario()
    reconciliation = run_reconciliation_probe()
    post_entry_risk = run_post_entry_risk_probe()
    snapshot_recovery = run_snapshot_recovery_probe()

    gates = {
        "quantity_boundary_has_no_planned_filled_check": (
            execution_evaluation["quantity_fields_absent_from_execution_validator"]
            and execution_evaluation["quantity_fields_absent_from_state_guard"]
        ),
        "spec_obligation_retains_positive_remainder": (
            obligation_spec["after_first_fill"]["remaining"] == 2_600
        ),
        "reconciliation_false_has_no_detector": (
            reconciliation["mismatch_detector_marker"] is False
        ),
        "post_entry_winner_exceeds_entry_cap": (
            post_entry_risk["winner_exceeds_entry_cap"] is True
            and post_entry_risk["paper_state_has_mark_price_or_weight"] is False
        ),
        "poisoned_latest_has_no_fallback_or_quarantine": (
            snapshot_recovery["both_cases_fail_closed"]
            and snapshot_recovery["latest_files_remain_after_failure"]
            and snapshot_recovery["quarantine_or_fallback_observed"] is False
        ),
    }
    result = {
        "status": "FRONTIER_CHALLENGE_FALSE_GREEN_BOUNDARIES_CONFIRMED",
        "challenge_scope": "synthetic, outcome-blind, exact pinned sources where applicable",
        "gates": gates,
        "systemic_interpretation": {
            "planned_shares": 5_000,
            "first_fill_shares": 2_400,
            "spec_remaining_shares": obligation_spec["after_first_fill"][
                "remaining"
            ],
            "evaluation_turnover_seen": execution_evaluation["filled_turnover"],
            "planned_turnover_reference": execution_evaluation["planned_turnover"],
            "reconciliation_true_provenance_available": reconciliation[
                "mismatch_detector_marker"
            ],
            "post_entry_winner_weight": post_entry_risk[
                "synthetic_winner_weight"
            ],
            "entry_weight_cap": post_entry_risk["max_entry_weight"],
        },
        "protected_outcomes_accessed": False,
        "production_or_canonical_mutation": False,
        "runtime_source_mutation": False,
        "writes_performed": "synthetic temp snapshots only",
    }
    if not all(gates.values()):
        raise AssertionError("FRONTIER_CHALLENGE_GATE_FAILED")
    return result


if __name__ == "__main__":
    print(json.dumps(run_challenge(), indent=2, sort_keys=True))
