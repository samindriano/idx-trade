"""Cloud E2E PAPER V2 adapter with causal runtime security-master bootstrap.

V1 remains the accepted orchestration engine. This adapter changes one
operational boundary only: before V1 invokes the canonical POST_EOD pipeline on
an ephemeral runner, it refreshes ``forward/listings/security_master.csv`` from
official IDX identity/reference data, anchored against the frozen clean
security master. PREOPEN behavior is unchanged.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.e2e_cloud_security_master_v1 import (  # noqa: E402
    refresh_cloud_runtime_security_master,
)
from idx_trade import v4_x1_clean_forward_score as clean_x1  # noqa: E402
from idx_trade.v4_x1_population_admission_v1 import (  # noqa: E402
    PopulationScoreGate,
    V1PopulationNotProvable,
)
from scripts import run_e2e_paper_cloud_v1 as v1  # noqa: E402


_LAST_SECURITY_MASTER_REFRESH: dict[str, object] | None = None
_LAST_POPULATION_ADMISSION: dict[str, object] | None = None


def _with_runtime_security_master(
    original_pipeline: Callable[..., dict[str, Any]],
    runtime_root: str | Path,
    model_root: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    global _LAST_SECURITY_MASTER_REFRESH, _LAST_POPULATION_ADMISSION

    observed_by = str(kwargs.get("observed_by") or "")
    if not observed_by:
        raise RuntimeError("CLOUD_RUNTIME_SECURITY_MASTER_OBSERVED_AT_MISSING")
    observed_at = datetime.fromisoformat(observed_by)
    if observed_at.tzinfo is None:
        raise RuntimeError("CLOUD_RUNTIME_SECURITY_MASTER_OBSERVED_AT_NOT_TIMEZONE_AWARE")
    baseline_master = kwargs.get("clean_security_master")
    if baseline_master is None:
        raise RuntimeError("CLOUD_RUNTIME_SECURITY_MASTER_BASELINE_MISSING")

    _LAST_SECURITY_MASTER_REFRESH = refresh_cloud_runtime_security_master(
        runtime_root,
        baseline_master=baseline_master,
        observed_at=observed_at,
    )
    pipeline_kwargs = dict(kwargs)
    input_manifest_sha256 = str(
        pipeline_kwargs.pop("population_input_manifest_sha256", "")
    )
    gate = PopulationScoreGate(
        clean_x1,
        runtime_root=runtime_root,
        clean_panel=kwargs.get("clean_panel"),
        clean_security_master=baseline_master,
        model_root=model_root,
        repo_root=kwargs.get("repo_root", REPO_ROOT),
        observed_by=observed_by,
        input_manifest_sha256=input_manifest_sha256,
        runner_path=Path(__file__).resolve(),
        expected_baseline_sha256=clean_x1.EXPECTED_CLEAN_SECURITY_MASTER_SHA256,
        expected_model_manifest_sha256=clean_x1.EXPECTED_MODEL_MANIFEST_SHA256,
    )
    try:
        with gate:
            result = original_pipeline(runtime_root, model_root, **pipeline_kwargs)
    except V1PopulationNotProvable as error:
        # The frozen pipeline has already persisted PIPELINE_FAILED, including
        # its successful EOD capture result.  Keep the controller on its
        # existing fail-closed waiting path and never enter PaperState.
        result = {
            "status": "PIPELINE_FAILED",
            "x1_score_attempted": False,
            "provider_calls_from_x1": False,
            "protected_outcome_accessed": False,
            "model_refit": False,
            "population_admission": error.admission.to_dict(),
            "error_code": "V1_POPULATION_NOT_PROVABLE",
            "error_message": V1PopulationNotProvable.__name__,
        }
    _LAST_POPULATION_ADMISSION = (
        gate.last_admission.to_dict() if gate.last_admission is not None else None
    )
    return dict(result)


def _result_payload_with_refresh(
    original_builder: Callable[..., dict[str, object]],
    **kwargs: Any,
) -> dict[str, object]:
    result = dict(original_builder(**kwargs))
    if str(kwargs.get("stage") or "") == "POST_EOD":
        if _LAST_SECURITY_MASTER_REFRESH is None:
            raise RuntimeError("CLOUD_RUNTIME_SECURITY_MASTER_REFRESH_EVIDENCE_MISSING")
        result["cloud_runtime_security_master_refresh"] = dict(
            _LAST_SECURITY_MASTER_REFRESH
        )
        if _LAST_POPULATION_ADMISSION is not None:
            result["v1_population_admission"] = dict(_LAST_POPULATION_ADMISSION)
    return result


@contextmanager
def _patched_v1_runtime() -> Iterator[None]:
    original_pipeline = v1.run_clean_eod_pipeline
    original_result_builder = v1._result_payload

    def pipeline_adapter(
        runtime_root: str | Path,
        model_root: str | Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return _with_runtime_security_master(
            original_pipeline,
            runtime_root,
            model_root,
            **kwargs,
        )

    def result_adapter(**kwargs: Any) -> dict[str, object]:
        return _result_payload_with_refresh(original_result_builder, **kwargs)

    v1.run_clean_eod_pipeline = pipeline_adapter
    v1._result_payload = result_adapter
    try:
        yield
    finally:
        v1.run_clean_eod_pipeline = original_pipeline
        v1._result_payload = original_result_builder


def run_once(*, phase: str | None = None, session_date: str | None = None) -> dict[str, object]:
    global _LAST_SECURITY_MASTER_REFRESH, _LAST_POPULATION_ADMISSION
    _LAST_SECURITY_MASTER_REFRESH = None
    _LAST_POPULATION_ADMISSION = None
    with _patched_v1_runtime():
        return v1.run_once(phase=phase, session_date=session_date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("auto", "POST_EOD", "PREOPEN"), default="auto")
    parser.add_argument("--session-date")
    args = parser.parse_args()
    try:
        result = run_once(
            phase=None if args.phase == "auto" else args.phase,
            session_date=args.session_date,
        )
    except Exception as exc:
        result = {
            "status": "FAILED",
            "controller_status": "FAIL_CLOSED",
            "error_code": type(exc).__name__.upper(),
            "error_message": str(exc),
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("status") in {"COMMITTED", "ALREADY_COMMITTED", "WAITING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
