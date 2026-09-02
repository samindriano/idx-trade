"""Cloud E2E PAPER V4 operational recovery adapter.

V3 remains the accepted PREOPEN_CA continuity implementation.  This adapter
repairs three operational contract bugs without changing frozen science:

* the current cloud observation time is still used for mutable runtime identity
  refresh/population admission, while the downstream prospective scorer keeps
  its preregistered frozen ``DEFAULT_OBSERVED_BY`` boundary;
* a legitimate ``V4_X1_NO_ELIGIBLE_SAME_DAY_SCORE`` result is interpreted as a
  semantic waiting state before any score-manifest path is dereferenced;
* PREOPEN consumes Official Open through the successor admission contract that
  recognises only native GitHub schedules or producer-verified trusted external
  scheduler attestations. Arbitrary/manual dispatch remains forbidden.

No model, feature, target, outcome, refit, score formula, sizing, execution, or
retroactive rule is changed here.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
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

import idx_trade.e2e_paper_operational_controller_v1 as controller_v1  # noqa: E402
from idx_trade import v4_x1_clean_forward_score as clean_x1  # noqa: E402
from idx_trade.e2e_official_open_admission_v2 import (  # noqa: E402
    materialize_official_open_from_cloud_v2,
)
from idx_trade.v4_x1_eod_pipeline import NO_SCORE_ERRORS  # noqa: E402
from scripts import run_e2e_paper_cloud_v1 as v1  # noqa: E402
from scripts import run_e2e_paper_cloud_v2 as v2  # noqa: E402
from scripts import run_e2e_paper_cloud_v3 as v3  # noqa: E402


_ORIGINAL_WITH_RUNTIME_SECURITY_MASTER = v2._with_runtime_security_master
_ORIGINAL_VERIFY_SCORE_POINTER = controller_v1._verify_score_pointer
_ORIGINAL_MATERIALIZE_OFFICIAL_OPEN = v1.materialize_official_open_from_cloud
_SCORE_MANIFEST_STATUSES = frozenset(
    {
        "V4_X1_SCORE_ALREADY_DONE_VERIFIED",
        "V4_X1_PROSPECTIVE_SCORE_DONE",
    }
)
_NO_ELIGIBLE_STATUS = "V4_X1_NO_ELIGIBLE_SAME_DAY_SCORE"
_NO_ELIGIBLE_FALSE_GUARDS = (
    "provider_calls",
    "protected_outcome_accessed",
    "model_refit",
    "model_retuned",
)


def _with_split_observation_clock(
    original_pipeline: Callable[..., dict[str, Any]],
    runtime_root: str | Path,
    model_root: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Keep runtime-now outside science while preserving V2 operational work.

    V1 supplies its current execution timestamp as ``observed_by``.  V2 needs
    that timestamp for mutable runtime identity refresh and population admission,
    so it remains untouched at the V2 boundary.  Only the call into the frozen
    EOD/scoring pipeline is rebound to the preregistered clean-model boundary.
    """

    def frozen_pipeline(
        downstream_runtime_root: str | Path,
        downstream_model_root: str | Path,
        **pipeline_kwargs: Any,
    ) -> dict[str, Any]:
        forwarded = dict(pipeline_kwargs)
        forwarded["observed_by"] = clean_x1.DEFAULT_OBSERVED_BY
        return original_pipeline(
            downstream_runtime_root,
            downstream_model_root,
            **forwarded,
        )

    return _ORIGINAL_WITH_RUNTIME_SECURITY_MASTER(
        frozen_pipeline,
        runtime_root,
        model_root,
        **kwargs,
    )


def _verify_score_pointer_semantic_first(
    pointer: dict[str, Any],
    session: str,
    *,
    expected_forward_root: Path | None = None,
) -> dict[str, Any]:
    """Classify score state before applying manifest-path integrity guards."""

    score = pointer.get("x1_score")
    if not isinstance(score, dict):
        raise controller_v1.E2EOperationalGuardError(
            "E2E_OPERATIONAL_SCORE_POINTER_MISSING"
        )
    status = str(score.get("status") or "")
    if status == _NO_ELIGIBLE_STATUS:
        reason = str(score.get("reason") or "")
        if reason not in NO_SCORE_ERRORS:
            raise controller_v1.E2EOperationalGuardError(
                "E2E_OPERATIONAL_NO_ELIGIBLE_SCORE_REASON_INVALID"
            )
        if any(score.get(field) is not False for field in _NO_ELIGIBLE_FALSE_GUARDS):
            raise controller_v1.E2EOperationalGuardError(
                "E2E_OPERATIONAL_NO_ELIGIBLE_SCORE_GUARDS_INVALID"
            )
        return score
    if status not in _SCORE_MANIFEST_STATUSES:
        raise controller_v1.E2EOperationalGuardError(
            "E2E_OPERATIONAL_SCORE_STATUS_INVALID"
        )
    return _ORIGINAL_VERIFY_SCORE_POINTER(
        pointer,
        session,
        expected_forward_root=expected_forward_root,
    )


@contextmanager
def _patched_v3_operational_contracts() -> Iterator[None]:
    original_with_runtime = v2._with_runtime_security_master
    original_verify_score = controller_v1._verify_score_pointer
    original_materialize_open = v1.materialize_official_open_from_cloud
    v2._with_runtime_security_master = _with_split_observation_clock
    controller_v1._verify_score_pointer = _verify_score_pointer_semantic_first
    v1.materialize_official_open_from_cloud = materialize_official_open_from_cloud_v2
    try:
        yield
    finally:
        v2._with_runtime_security_master = original_with_runtime
        controller_v1._verify_score_pointer = original_verify_score
        v1.materialize_official_open_from_cloud = original_materialize_open


def run_once(*, phase: str | None = None, session_date: str | None = None) -> dict[str, object]:
    with _patched_v3_operational_contracts():
        return v3.run_once(phase=phase, session_date=session_date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("auto", "POST_EOD", "PREOPEN", "PREOPEN_CA"),
        default="auto",
    )
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
            **v3._guard_result(),
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("status") in {
        "COMMITTED",
        "ALREADY_COMMITTED",
        "ALREADY_CHECKPOINTED",
        "WAITING",
        "NOOP",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
