"""Audit latest-snapshot failure recovery with synthetic runtime artifacts only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
)
RUNTIME_MODULE_RELATIVE = Path("src/idx_trade/forward_dividend_runtime_v1_1.py")
EXPECTED_RUNTIME_SOURCE_SHA256 = (
    "98ebc637340757f03e36c3c8b876f134022ca1282b9bad35cf573b4b784eca23"
)
EXPECTED_RUNTIME_COMMIT = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"


_CHILD = textwrap.dedent(
    r'''
    from __future__ import annotations

    import hashlib
    import json
    from pathlib import Path
    import sys

    runtime_root = Path(sys.argv[1]).resolve()
    exact_runtime = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(exact_runtime / "src"))

    import idx_trade.forward_dividend_execution_v1_1 as gate
    import idx_trade.forward_dividend_runtime_v1_1 as runtime
    import idx_trade.forward_dividend_v1 as fd
    from idx_trade.v4_x1_execution_v1_contract import PaperPortfolioState

    event = fd.CertifiedCashDividend(
        event_id="SYNTHETIC_LATEST_SNAPSHOT_RECOVERY",
        ticker="BBCA",
        announcement_timestamp="2026-08-19T18:31:03",
        gross_dividend_per_share_idr=25.0,
        cum_date="2026-08-28",
        ex_date="2026-08-31",
        record_date="2026-09-01",
        payment_date="2026-09-16",
        source_evidence_sha256="a" * 64,
    )
    review_path = runtime_root / "review.json"
    review_path.write_text('{"status":"synthetic"}\n', encoding="utf-8")
    review_sha256 = hashlib.sha256(review_path.read_bytes()).hexdigest()
    verified = gate.VerifiedCashDividendEvidence(
        event=event,
        review_path=review_path,
        review_sha256=review_sha256,
        announcement_id="synthetic-announcement-id",
        announcement_number="synthetic-announcement-number",
        _verification_token=gate._VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )
    gate.verify_cash_dividend_evidence_for_execution = (
        lambda **kwargs: verified
    )
    registry = runtime.register_verified_cash_dividend_evidence(
        (), verified, attachment_dir=runtime_root / "attachments"
    )
    state_one = fd.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date="2026-08-20",
            cash_idr=1_000_000.0,
            positions=(),
        )
    )
    state_two = fd.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date="2026-08-21",
            cash_idr=999_000.0,
            positions=(),
        )
    )
    first = runtime.write_runtime_snapshot(runtime_root, state_one, registry)
    second = runtime.write_runtime_snapshot(
        runtime_root, state_two, registry, previous_snapshot=first
    )
    latest_path = second.path

    def observe(label: str, mutate) -> dict[str, object]:
        mutate(latest_path)
        errors: list[str] = []
        for _ in range(2):
            try:
                runtime.load_latest_runtime_snapshot(runtime_root)
            except Exception as exc:  # exact runtime error is the evidence
                errors.append(type(exc).__name__ + ":" + str(exc))
            else:
                errors.append("NO_ERROR")
        return {
            "label": label,
            "errors": errors,
            "latest_exists_after_failure": latest_path.is_file(),
            "previous_exists_after_failure": first.path.is_file(),
            "previous_direct_load_succeeds": _direct_load_succeeds(first.path),
            "snapshot_files_after_failure": sorted(
                path.name
                for path in latest_path.parent.glob("*.json")
            ),
        }

    def _direct_load_succeeds(path: Path) -> bool:
        try:
            runtime.load_runtime_snapshot(path)
        except Exception:
            return False
        return True

    malformed = observe(
        "malformed-latest-json",
        lambda path: path.write_text("{\n", encoding="utf-8"),
    )

    # Rebuild a separate synthetic chain for payload tamper so the two cases
    # are independent and the first observation cannot affect the second.
    second_root = runtime_root / "payload-tamper"
    second_root.mkdir(parents=True, exist_ok=True)
    first_two = runtime.write_runtime_snapshot(second_root, state_one, registry)
    second_two = runtime.write_runtime_snapshot(
        second_root, state_two, registry, previous_snapshot=first_two
    )
    tampered_payload = json.loads(second_two.path.read_text(encoding="utf-8"))
    tampered_payload["state"]["base_paper_state"]["cash_idr"] = 2_000_000.0
    tampered_payload["snapshot_payload_sha256"] = tampered_payload[
        "snapshot_payload_sha256"
    ]
    second_two.path.write_text(
        json.dumps(tampered_payload), encoding="utf-8"
    )
    payload_tamper_errors: list[str] = []
    for _ in range(2):
        try:
            runtime.load_latest_runtime_snapshot(second_root)
        except Exception as exc:
            payload_tamper_errors.append(type(exc).__name__ + ":" + str(exc))
        else:
            payload_tamper_errors.append("NO_ERROR")
    payload_tamper = {
        "label": "payload-tamper-latest-json",
        "errors": payload_tamper_errors,
        "latest_exists_after_failure": second_two.path.is_file(),
        "previous_exists_after_failure": first_two.path.is_file(),
        "previous_direct_load_succeeds": _direct_load_succeeds(first_two.path),
        "snapshot_files_after_failure": sorted(
            path.name for path in second_two.path.parent.glob("*.json")
        ),
    }
    print(json.dumps({"malformed": malformed, "payload_tamper": payload_tamper}))
    '''
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_child(sandbox: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(sandbox), str(RUNTIME_ROOT)],
        cwd=RUNTIME_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "CHILD_RUNTIME_PROBE_FAILED:" + completed.stderr[-2000:]
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("CHILD_RUNTIME_PROBE_NON_JSON_OUTPUT") from exc


def run_probe(sandbox: Path | None = None) -> dict[str, Any]:
    source = RUNTIME_ROOT / RUNTIME_MODULE_RELATIVE
    if not RUNTIME_ROOT.is_dir() or not source.is_file():
        raise RuntimeError("PINNED_RUNTIME_CHECKOUT_MISSING")
    source_sha256 = _sha256(source)
    if source_sha256 != EXPECTED_RUNTIME_SOURCE_SHA256:
        raise RuntimeError("PINNED_RUNTIME_SOURCE_CHANGED")
    if sandbox is None:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="idx-latest-snapshot-") as name:
            observations = _run_child(Path(name))
    else:
        sandbox.mkdir(parents=True, exist_ok=True)
        observations = _run_child(sandbox)

    all_errors = [
        error
        for case in observations.values()
        for error in case["errors"]
    ]
    result: dict[str, Any] = {
        "status": "LATEST_SNAPSHOT_FAILURE_NO_RECOVERY",
        "runtime_commit": EXPECTED_RUNTIME_COMMIT,
        "runtime_source_sha256": source_sha256,
        "observations": observations,
        "both_cases_fail_closed": all(
            error != "NO_ERROR" for error in all_errors
        ),
        "latest_files_remain_after_failure": all(
            case["latest_exists_after_failure"]
            for case in observations.values()
        ),
        "previous_files_remain_after_failure": all(
            case["previous_exists_after_failure"]
            for case in observations.values()
        ),
        "previous_direct_load_remains_available": all(
            case["previous_direct_load_succeeds"]
            for case in observations.values()
        ),
        "quarantine_or_fallback_observed": False,
        "writes_performed": "synthetic temp snapshots only",
    }
    if not result["both_cases_fail_closed"]:
        raise AssertionError("LATEST_FAILURE_DID_NOT_FAIL_CLOSED")
    if not result["latest_files_remain_after_failure"]:
        raise AssertionError("LATEST_FAILURE_WAS_QUARANTINED_UNEXPECTEDLY")
    if not result["previous_direct_load_remains_available"]:
        raise AssertionError("VALID_PREVIOUS_SNAPSHOT_NOT_LOADABLE")
    return result


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
