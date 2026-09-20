"""Outcome-blind Git-history audit for the minimum-20 versus min-periods-60 issue."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


LEGACY_REF = "26aac816"
PROTOCOL_REF = "a02a1547"
STAGE_A_V1_REF = "2b056802"
STAGE_A_V2_REF = "1ebced27"
SECURITY_MASTER_REF = "65233e195"


def git_show(repo: Path, ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def ref_exists(repo: Path, ref: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{commit}}"],
        capture_output=True,
    ).returncode == 0


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def find_int(text: str, name: str) -> int | None:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(\d+)", text)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()

    legacy_path = "src/idx_trade/research_features.py"
    legacy_docs = "docs/RESEARCH_SPECIFICATION_V1.md"
    protocol_path = "docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md"
    stage_a_path = "research/alpha_stage_a_v1.py"
    stage_a_v2_path = "research/alpha_stage_a_v2.py"
    security_path = "src/idx_trade/security_master.py"

    legacy = git_show(repo, LEGACY_REF, legacy_path)
    legacy_spec = git_show(repo, LEGACY_REF, legacy_docs)
    protocol = git_show(repo, PROTOCOL_REF, protocol_path)
    stage_a_v1 = git_show(repo, STAGE_A_V1_REF, stage_a_path)
    stage_a_v2 = git_show(repo, STAGE_A_V2_REF, stage_a_v2_path)
    security_master = git_show(repo, SECURITY_MASTER_REF, security_path)

    legacy_manual_count = all(
        marker in legacy
        for marker in (
            "PRIMARY_LIQUIDITY_LOOKBACK = 60",
            "PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20",
            "min_idx = idx - (PRIMARY_LIQUIDITY_LOOKBACK - 1)",
            "finite = window_values[np.isfinite(window_values)]",
            "len(finite)",
            "liquidity_active_observations_60",
            ">= PRIMARY_MIN_ACTIVE_OBSERVATIONS",
        )
    )
    stage_a_v1_twenty_check = re.search(r"(?:\.ge\(20\)|>=\s*20)", stage_a_v1) is not None
    stage_a_v2_twenty_check = re.search(r"(?:\.ge\(20\)|>=\s*20)", stage_a_v2) is not None

    source_rows: list[dict[str, Any]] = [
        {
            "role": "legacy_primary_liquidity_rule",
            "ref": LEGACY_REF,
            "path": legacy_path,
            "sha256": sha256_text(legacy),
            "lookback_sessions": find_int(legacy, "PRIMARY_LIQUIDITY_LOOKBACK"),
            "minimum_active_observations": find_int(legacy, "PRIMARY_MIN_ACTIVE_OBSERVATIONS"),
            "manual_finite_observation_logic": legacy_manual_count,
            "interpretation": "20 is a finite ACTIVE-observation threshold inside a 60 official-session window; the old implementation does not require 60 finite observations.",
        },
        {
            "role": "legacy_specification",
            "ref": LEGACY_REF,
            "path": legacy_docs,
            "sha256": sha256_text(legacy_spec),
            "mentions_20_in_60_window": (
                ("at least 20 valid ACTIVE observations" in legacy_spec or "at least 20 observations" in legacy_spec)
                and "trailing 60" in legacy_spec
            ),
            "interpretation": "The 20/60 rule was frozen in a pre-19-Sep research specification before the new Stage-A protocol.",
        },
        {
            "role": "new_protocol",
            "ref": PROTOCOL_REF,
            "path": protocol_path,
            "sha256": sha256_text(protocol),
            "mentions_20_in_60_window": "at least 20" in protocol and "trailing-60" in protocol,
            "interpretation": "The 19-Sep protocol inherited the historical 20-in-60 wording; it is not the first local appearance of the rule.",
        },
        {
            "role": "stage_a_v1_implementation",
            "ref": STAGE_A_V1_REF,
            "path": stage_a_path,
            "sha256": sha256_text(stage_a_v1),
            "complete_rolling_min_periods": "min_periods=window" in stage_a_v1,
            "later_minimum_20_check": stage_a_v1_twenty_check,
            "interpretation": "V1 uses complete-window rolling helpers but does not itself contain the later explicit >=20 eligibility mask.",
        },
        {
            "role": "stage_a_v2_implementation",
            "ref": STAGE_A_V2_REF,
            "path": stage_a_v2_path,
            "sha256": sha256_text(stage_a_v2),
            "complete_rolling_min_periods": "min_periods=window" in stage_a_v2,
            "later_minimum_20_check": stage_a_v2_twenty_check,
            "interpretation": "V2 inherits complete-window behavior and adds an explicit >=20 check that is redundant after min_periods=window; this is implementation behavior, not authority for replacing the legacy 20-in-60 rule.",
        },
        {
            "role": "generic_security_master_warmup",
            "ref": SECURITY_MASTER_REF,
            "path": security_path,
            "sha256": sha256_text(security_master),
            "minimum_warmup_sessions": find_int(security_master, "minimum_warmup_sessions"),
            "has_ipo_warmup_reason": "IPO_WARMUP" in security_master,
            "interpretation": "The separate security-master 60-session IPO warm-up is not the liquidity finite-observation threshold.",
        },
    ]

    result = {
        "schema_version": "IDX_TRADE_ELIGIBILITY_PROVENANCE_HISTORY_V1",
        "experiment_id": "ELIGIBILITY-PROVENANCE-039",
        "status": "SUPPORTED_PROVENANCE_NARROWED",
        "scope": "Outcome-blind Git-history/docs/code provenance audit; no panel regeneration, provider access, or protected outcome access.",
        "source_rows": source_rows,
        "conclusion": {
            "minimum_20_historical_provenance": "SUPPORTED_FROM_PRE_PROTOCOL_LEGACY_RULE",
            "lookback_60_historical_provenance": "SUPPORTED_AS_WINDOW_LENGTH",
            "min_periods_60_as_historical_liquidity_policy": "NOT_SUPPORTED_BY_LEGACY_RULE",
            "stage_a_min_periods_60": "CURRENT_IMPLEMENTATION_BEHAVIOR",
            "security_master_warmup_60": "SEPARATE_IPO_WARMUP_CONCEPT",
            "current_policy_binding": "STILL_REQUIRES_EXPLICIT_PROJECT_AUTHORITY_FOR_THIS_NEW_CANDIDATE_PROTOCOL",
            "population_selection_authorized": False,
        },
        "red_team": {
            "legacy_manual_logic_confirmed": legacy_manual_count,
            "stage_a_v1_complete_window_confirmed": "min_periods=window" in stage_a_v1,
            "stage_a_v2_complete_window_confirmed": "min_periods=window" in stage_a_v2,
            "stage_a_v1_explicit_ge_20_check": stage_a_v1_twenty_check,
            "stage_a_v2_explicit_ge_20_check": stage_a_v2_twenty_check,
            "limitations": [
                "Historical source/code provenance narrows the interpretation but does not itself authorize changing the current frozen candidate population.",
                "This audit does not prove the old legacy rule is the current incumbent-specific Data-QA authority.",
                "No predictive outcome or protected payload was read.",
            ],
        },
        "reopen_trigger": "Explicit hash-bound policy decision stating whether the historical 20-in-60 primary liquidity contract governs this new candidate protocol, followed by isolated regeneration/replay.",
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.resolve().write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
