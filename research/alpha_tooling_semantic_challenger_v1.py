"""Independent synthetic challenger for the outcome-blind research firewall.

The challenger does not change the production verifier. It creates temporary
fixtures to make known false-green surfaces explicit: disguised semantic fields
and unrecognized nested packet fields. It also checks that canonical JSON
serialization can be deterministic and whether the authority packet carries an
expected verifier-version pin.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    firewall = load_module(
        "alpha_research_target_firewall_v1",
        ROOT / "research" / "alpha_research_target_firewall_v1.py",
    )
    packet_verifier = load_module(
        "verify_alpha_data_authority_packet_v1",
        ROOT / "research" / "verify_alpha_data_authority_packet_v1.py",
    )
    packet = json.loads(
        (ROOT / "research_knowledge" / "data_authority_packet_v1.json").read_text(encoding="utf-8")
    )

    with tempfile.TemporaryDirectory(prefix="idx-alpha-semantic-challenger-") as temp:
        temp_root = Path(temp)
        disguised_text = temp_root / "disguised.txt"
        disguised_text.write_text("future_ret5_value = fixture\n", encoding="utf-8")
        text_checks = firewall.text_checks(disguised_text)

        disguised_schema = temp_root / "disguised.parquet"
        pq.write_table(
            pa.table(
                {
                    "ticker": ["AAA"],
                    "date": ["2026-01-01"],
                    "future_ret5_value": [0.1],
                    "secret_signal": [1.0],
                }
            ),
            disguised_schema,
        )
        schema_checks = firewall.schema_checks(disguised_schema)

    nested_mutation = copy.deepcopy(packet)
    nested_mutation["candidate_matrix"]["C1"]["unexpected_safe_field"] = "fixture"
    nested_result = packet_verifier.validate(nested_mutation, ROOT)

    top_level_mutation = copy.deepcopy(packet)
    top_level_mutation["unexpected_top_level_field"] = "fixture"
    top_level_result = packet_verifier.validate(top_level_mutation, ROOT)

    ordered_a = {"b": 2, "a": 1}
    ordered_b = {"a": 1, "b": 2}
    canonical_a = json.dumps(ordered_a, sort_keys=True, separators=(",", ":"))
    canonical_b = json.dumps(ordered_b, sort_keys=True, separators=(",", ":"))

    verifier_audit = packet.get("verifier_audit", {})
    verifier_version_pin_present = any(
        "verifier" in str(key).lower() and "sha" in str(key).lower()
        for key in verifier_audit
    )

    false_greens = {
        "disguised_text_passes": all(text_checks.values()),
        "disguised_schema_passes": all(schema_checks.values()),
        "nested_unknown_packet_field_passes": nested_result["status"] == "PASS",
    }
    expected_guards = {
        "top_level_unknown_packet_field_fails": top_level_result["status"] == "FAIL",
        "canonical_json_order_independent": canonical_a == canonical_b,
        "verifier_version_pin_absent_is_recorded": not verifier_version_pin_present,
    }
    result = {
        "schema_version": "IDX_TRADE_TOOLING_SEMANTIC_CHALLENGER_V1",
        "experiment_id": "TOOLING-038",
        "status": "PASS_KNOWN_FALSE_GREENS_EXPOSED"
        if all(false_greens.values()) and all(expected_guards.values())
        else "FAIL",
        "scope": "OUTCOME_BLIND_SYNTHETIC_FIXTURES_ONLY",
        "false_green_surfaces": false_greens,
        "expected_guard_results": expected_guards,
        "raw_checks": {
            "disguised_text": text_checks,
            "disguised_schema": schema_checks,
            "nested_packet": nested_result,
            "top_level_packet": top_level_result,
        },
        "interpretation": [
            "The denylist firewall is not a semantic allowlist.",
            "The authority packet rejects unknown top-level fields but permits unknown nested fields unless protected-key patterns match.",
            "Canonical JSON can be made deterministic by explicit sorted serialization; this is not currently a packet semantic guarantee.",
            "The packet verifier audit metadata does not carry an expected verifier-version hash pin.",
        ],
        "no_provider_or_protected_access": True,
        "reopen_trigger": "A separately reviewed semantic schema allowlist, independent formula challenger, or explicit verifier-version contract.",
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.resolve().write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
