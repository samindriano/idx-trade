"""Strict prospective runtime adapter for Joint Setup Readiness State V1.1.

This adapter materializes one already-authorized, outcome-blind parent pair. It
does not call providers, schedule work, inspect outcomes, fit/score models, or
change the frozen V1.1 classifier. Parent bytes and manifests are re-hashed
before the V1.1 domain contract is evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from . import joint_setup_readiness_state as v1
from .joint_setup_readiness_state_v1_1 import (
    OUTPUT_COLUMNS,
    ParentProvenance,
    JointSetupReadinessV1_1Result,
    build_joint_setup_readiness_state_v1_1,
    joint_contract_fingerprint_v1_1,
)


SOURCE_SESSION = "2026-08-12"
FEATURE_SESSION = "2026-08-13"
V1_1_FINGERPRINT = "c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de"
EXPECTED_DOMAIN = {
    "foreign_flow_key_count": 963,
    "price_state_key_count": 836,
    "overlap_key_count": 836,
    "price_only_key_count": 0,
    "foreign_flow_only_key_count": 127,
}
EXPECTED_STATE_DISTRIBUTION = {
    "IGNORE": 697,
    "WATCH": 84,
    "READY": 54,
    "ENTRY_ELIGIBLE": 1,
}
JOINT_RUNTIME_STATUS = "JOINT_SETUP_READINESS_V1_1_CONTROLLED_SMOKE_VERIFIED"


class RuntimeVerificationError(RuntimeError):
    """Fail-closed runtime or provenance verification failure."""


@dataclass(frozen=True)
class ParentArtifactSpec:
    kind: str
    artifact_path: Path
    artifact_sha256: str
    manifest_path: Path
    manifest_sha256: str
    manifest_artifact_path_key: str
    manifest_artifact_sha256_key: str
    contract_version: str
    expected_status: str
    source_kind: str


@dataclass(frozen=True)
class VerifiedParent:
    spec: ParentArtifactSpec
    frame: pd.DataFrame
    manifest: dict[str, Any]
    provenance: ParentProvenance


@dataclass(frozen=True)
class VerifiedJointSnapshot:
    artifact_path: Path
    artifact_sha256: str
    manifest_path: Path
    manifest_sha256: str
    result: JointSetupReadinessV1_1Result
    manifest: dict[str, Any]


@dataclass(frozen=True)
class SmokeRun:
    status: str
    created: bool
    strict_verified: bool
    artifact_path: Path
    artifact_sha256: str
    manifest_path: Path
    manifest_sha256: str
    rows: int
    tickers: int
    source_session: str
    feature_session: str
    domain: dict[str, Any]
    state_distribution: dict[str, int]
    provider_calls: int
    outcome_blind: bool
    forward_outcomes_accessed: bool
    outcomes_or_labels_accessed: bool
    model_fitted: bool
    model_scoring: bool
    trade_recommendation: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RuntimeVerificationError(f"cannot read artifact: {path}") from error
    return digest.hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _content_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _path_equal(actual: object, expected: Path) -> bool:
    if not isinstance(actual, str):
        return False
    try:
        return Path(actual).resolve() == expected.resolve()
    except OSError:
        return False


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeVerificationError(message)


def _manifest_flag(manifest: Mapping[str, Any], key: str, *, aliases: tuple[str, ...] = ()) -> object:
    if key in manifest:
        return manifest[key]
    for alias in aliases:
        if alias in manifest:
            return manifest[alias]
    raise RuntimeVerificationError(f"parent manifest missing explicit flag: {key}")


def _validate_protected_manifest_flags(manifest: Mapping[str, Any], *, label: str) -> None:
    _require(manifest.get("outcome_blind") is True, f"{label} outcome_blind is not true")
    _require(int(manifest.get("provider_calls", -1)) == 0, f"{label} provider_calls is not zero")
    _require(_manifest_flag(manifest, "model_fitted", aliases=("model_fit",)) is False, f"{label} model flag is not false")
    _require(_manifest_flag(manifest, "model_scoring") is False, f"{label} model_scoring is not false")
    for key in ("forward_outcomes_accessed", "outcomes_or_labels_accessed", "trade_recommendation"):
        if key in manifest:
            _require(manifest[key] is False, f"{label} {key} is not false")
    prohibited = manifest.get("prohibited_actions")
    if prohibited is not None:
        _require(isinstance(prohibited, Mapping), f"{label} prohibited_actions malformed")
        for key in ("fresh_forward_accessed", "outcomes_or_labels_accessed", "model_fit", "model_scoring"):
            if key in prohibited:
                _require(prohibited[key] is False, f"{label} prohibited flag {key} is not false")


def _reject_outcome_columns(frame: pd.DataFrame, *, label: str) -> None:
    forbidden_tokens = (
        "binary_target",
        "label_status",
        "tp_first",
        "sl_first",
        "realized",
        "forward_return",
        "future_return",
        "target_return",
        "prediction",
        "score",
    )
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).lower() for token in forbidden_tokens)
        and str(column)
        not in {"outcome_blind", "forward_outcomes_accessed", "outcomes_or_labels_accessed"}
    ]
    _require(not forbidden, f"{label} contains outcome/model columns: {sorted(forbidden)}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeVerificationError(f"invalid JSON manifest: {path}") from error
    _require(isinstance(value, dict), f"manifest is not an object: {path}")
    return value


def _load_parent(spec: ParentArtifactSpec) -> VerifiedParent:
    _require(spec.artifact_path.is_file(), f"missing {spec.kind} artifact: {spec.artifact_path}")
    _require(spec.manifest_path.is_file(), f"missing {spec.kind} manifest: {spec.manifest_path}")
    actual_artifact_sha = sha256_file(spec.artifact_path)
    actual_manifest_sha = sha256_file(spec.manifest_path)
    _require(actual_artifact_sha == spec.artifact_sha256, f"{spec.kind} artifact SHA mismatch")
    _require(actual_manifest_sha == spec.manifest_sha256, f"{spec.kind} manifest SHA mismatch")
    manifest = _read_json(spec.manifest_path)
    _require(
        _path_equal(manifest.get(spec.manifest_artifact_path_key), spec.artifact_path),
        f"{spec.kind} manifest artifact path mismatch",
    )
    _require(
        manifest.get(spec.manifest_artifact_sha256_key) == spec.artifact_sha256,
        f"{spec.kind} manifest artifact SHA declaration mismatch",
    )
    _require(manifest.get("state_contract_version") == spec.contract_version, f"{spec.kind} contract mismatch")
    _require(manifest.get("status") == spec.expected_status, f"{spec.kind} status mismatch")
    _validate_protected_manifest_flags(manifest, label=spec.kind)

    try:
        frame = pd.read_parquet(spec.artifact_path)
    except Exception as error:  # pragma: no cover - provider/runtime corruption path
        raise RuntimeVerificationError(f"cannot read {spec.kind} parquet") from error
    _reject_outcome_columns(frame, label=spec.kind)
    required = {"ticker", "feature_session", "state_contract_version"}
    if spec.kind == "FOREIGN_FLOW_SETUP":
        required |= {"flow_through_session", "setup_label"}
        source_column = "flow_through_session"
    else:
        required |= {"source_session", "trend_state", "confirmation_state"}
        source_column = "source_session"
    _require(required <= set(frame.columns), f"{spec.kind} parent schema incomplete")
    _require(not frame[["ticker", "feature_session"]].isna().any().any(), f"{spec.kind} null identity")
    _require(not frame.duplicated(["ticker", "feature_session"]).any(), f"{spec.kind} duplicate identity")
    _require(frame["state_contract_version"].eq(spec.contract_version).all(), f"{spec.kind} row contract mismatch")
    _require(frame["feature_session"].astype(str).eq(FEATURE_SESSION).all(), f"{spec.kind} feature session mismatch")
    _require(frame[source_column].astype(str).eq(SOURCE_SESSION).all(), f"{spec.kind} source session mismatch")
    if "row_count" in manifest:
        _require(int(manifest["row_count"]) == len(frame), f"{spec.kind} manifest row count mismatch")
    source_kind = spec.source_kind
    provenance = ParentProvenance(
        artifact_sha256=actual_artifact_sha,
        manifest_sha256=actual_manifest_sha,
        contract_version=spec.contract_version,
        source_kind=source_kind,
        outcome_blind=True,
        provider_calls=0,
        model_fitted=False,
        model_scoring=False,
        trade_recommendation=False,
        forward_outcomes_accessed=False,
        outcomes_or_labels_accessed=False,
    )
    return VerifiedParent(spec=spec, frame=frame, manifest=manifest, provenance=provenance)


def _parent_specs(runtime_root: Path) -> tuple[ParentArtifactSpec, ParentArtifactSpec]:
    ff_dir = runtime_root / "forward_monitoring" / "prospective" / "foreign_flow_representation_v2" / FEATURE_SESSION
    price_dir = runtime_root / "forward_monitoring" / "prospective" / "price_trend_confirmation_state_v1" / FEATURE_SESSION
    return (
        ParentArtifactSpec(
            kind="FOREIGN_FLOW_SETUP",
            artifact_path=ff_dir / "idx_foreign_flow_setup.parquet",
            artifact_sha256="b8791011659b33c62cf0890340e86de4abfb397eaa1b99c3639a6c240b682284",
            manifest_path=ff_dir / "idx_foreign_flow_setup.manifest.json",
            manifest_sha256="3c94eede15c35e4997643ef931538779940d6839136f7afca4b819402f17caed",
            manifest_artifact_path_key="setup_sidecar_path",
            manifest_artifact_sha256_key="setup_sidecar_sha256",
            contract_version="FOREIGN_FLOW_SETUP_STATE_V1",
            expected_status="FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY",
            source_kind="FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_SMOKE",
        ),
        ParentArtifactSpec(
            kind="PRICE_STATE",
            artifact_path=price_dir / "price_trend_confirmation_state_v1.parquet",
            artifact_sha256="8dab4a1d532c42cb46f9a9b86c5f853f99f00e13677222c7ae1e1ab0ca1901af",
            manifest_path=price_dir / "price_trend_confirmation_state_v1.manifest.json",
            manifest_sha256="aad51b933ba8a8868c050e17fec52330a3b6c66002ba29d0ddd4ba84949cbd6f",
            manifest_artifact_path_key="artifact_path",
            manifest_artifact_sha256_key="artifact_sha256",
            contract_version="PRICE_TREND_CONFIRMATION_STATE_V1",
            expected_status="PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY",
            source_kind="PRICE_TREND_CONFIRMATION_STATE_PROSPECTIVE_SMOKE",
        ),
    )


def _calendar(runtime_root: Path) -> pd.Series:
    path = runtime_root / "forward_monitoring" / "context_bridge" / "calendar" / "ranges" / "2026-07-31_2026-08-13" / "exchange_sessions.csv"
    _require(path.is_file(), f"missing accepted bridge calendar: {path}")
    _require(sha256_file(path) == "51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e", "bridge calendar SHA mismatch")
    calendar = pd.read_csv(path)
    column = "session_date" if "session_date" in calendar.columns else calendar.columns[0]
    return calendar[column]


def _expected_output(result: JointSetupReadinessV1_1Result) -> pd.DataFrame:
    frame = result.frame.copy()
    return frame.loc[:, list(OUTPUT_COLUMNS)].sort_values(["feature_session", "ticker"], kind="mergesort").reset_index(drop=True)


def _domain_payload(result: JointSetupReadinessV1_1Result) -> dict[str, Any]:
    return result.domain.as_dict()


def _provenance_payload(
    *,
    ff: VerifiedParent,
    price: VerifiedParent,
    result: JointSetupReadinessV1_1Result,
    artifact_path: Path,
) -> dict[str, Any]:
    return {
        "foreign_flow_artifact_path": str(ff.spec.artifact_path),
        "foreign_flow_artifact_sha256": ff.provenance.artifact_sha256,
        "foreign_flow_manifest_path": str(ff.spec.manifest_path),
        "foreign_flow_manifest_sha256": ff.provenance.manifest_sha256,
        "price_state_artifact_path": str(price.spec.artifact_path),
        "price_state_artifact_sha256": price.provenance.artifact_sha256,
        "price_state_manifest_path": str(price.spec.manifest_path),
        "price_state_manifest_sha256": price.provenance.manifest_sha256,
        "source_session": SOURCE_SESSION,
        "feature_session": FEATURE_SESSION,
        "v1_fingerprint": v1.joint_contract_fingerprint(),
        "v1_1_fingerprint": result.contract_fingerprint,
        "domain": _domain_payload(result),
        "output_artifact_path": str(artifact_path),
        "protected_flags": {
            "provider_calls": 0,
            "outcome_blind": True,
            "forward_outcomes_accessed": False,
            "outcomes_or_labels_accessed": False,
            "model_fitted": False,
            "model_scoring": False,
            "trade_recommendation": False,
        },
    }


def _serialize_frame(frame: pd.DataFrame) -> bytes:
    stream = BytesIO()
    frame.to_parquet(stream, index=False)
    return stream.getvalue()


def _immutable_create(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        _require(path.read_bytes() == payload, f"immutable artifact differs: {path}")
        return False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return True


def _manifest_bytes(payload: dict[str, Any]) -> bytes:
    content = dict(payload)
    content["manifest_content_sha256"] = _content_hash(payload)
    return (json.dumps(content, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def verify_joint_setup_readiness_snapshot(
    output_dir: Path,
    *,
    foreign_flow_spec: ParentArtifactSpec,
    price_state_spec: ParentArtifactSpec,
    official_sessions: pd.Series | list[object],
    expected_fingerprint: str = V1_1_FINGERPRINT,
) -> VerifiedJointSnapshot:
    """Reopen and strictly verify both parents, output, manifest, and hashes."""

    artifact_path = output_dir / "joint_setup_readiness_state_v1_1.parquet"
    manifest_path = output_dir / "joint_setup_readiness_state_v1_1.manifest.json"
    _require(artifact_path.is_file() and manifest_path.is_file(), "joint V1.1 artifact pair is incomplete")
    ff = _load_parent(foreign_flow_spec)
    price = _load_parent(price_state_spec)
    result = build_joint_setup_readiness_state_v1_1(
        ff.frame,
        price.frame,
        official_sessions=official_sessions,
        foreign_flow_provenance=ff.provenance,
        price_state_provenance=price.provenance,
    )
    _require(result.contract_fingerprint == expected_fingerprint, "V1.1 contract fingerprint mismatch")
    actual_artifact_sha = sha256_file(artifact_path)
    actual_manifest_sha = sha256_file(manifest_path)
    manifest = _read_json(manifest_path)
    _require(_path_equal(manifest.get("artifact_path"), artifact_path), "joint manifest artifact path mismatch")
    _require(manifest.get("artifact_sha256") == actual_artifact_sha, "joint artifact SHA declaration mismatch")
    _require(manifest.get("manifest_content_sha256") == _content_hash({k: v for k, v in manifest.items() if k != "manifest_content_sha256"}), "joint manifest content hash mismatch")
    _require(manifest.get("status") == JOINT_RUNTIME_STATUS, "joint status mismatch")
    _require(_path_equal(manifest.get("manifest_path"), manifest_path), "joint manifest path mismatch")
    _require(manifest.get("source_session") == SOURCE_SESSION, "joint source session mismatch")
    _require(manifest.get("feature_session") == FEATURE_SESSION, "joint feature session mismatch")
    _require(manifest.get("foreign_flow_contract_version") == foreign_flow_spec.contract_version, "joint Foreign Flow contract mismatch")
    _require(manifest.get("price_state_contract_version") == price_state_spec.contract_version, "joint Price State contract mismatch")
    _require(manifest.get("v1_fingerprint") == v1.joint_contract_fingerprint(), "V1 fingerprint mismatch")
    _require(manifest.get("v1_1_fingerprint") == expected_fingerprint, "V1.1 fingerprint mismatch")
    _require(manifest.get("domain") == _domain_payload(result), "joint domain provenance mismatch")
    expected_provenance = _provenance_payload(ff=ff, price=price, result=result, artifact_path=artifact_path)
    _require(manifest.get("provenance_payload") == expected_provenance, "joint parent provenance mismatch")
    _require(manifest.get("state_distribution") == result.frame["joint_state"].value_counts().sort_index().astype(int).to_dict(), "joint state distribution mismatch")
    _require(int(manifest.get("row_count", -1)) == len(result.frame), "joint row count mismatch")
    _require(int(manifest.get("ticker_count", -1)) == result.frame["ticker"].nunique(), "joint ticker count mismatch")
    protected = manifest.get("protected_flags")
    _require(protected == expected_provenance["protected_flags"], "joint protected flags mismatch")
    _require(manifest.get("provenance_fingerprint") == _content_hash(manifest.get("provenance_payload", {})), "joint provenance fingerprint mismatch")
    try:
        frame = pd.read_parquet(artifact_path)
    except Exception as error:  # pragma: no cover - corruption path
        raise RuntimeVerificationError("cannot read joint artifact") from error
    _require(tuple(frame.columns) == tuple(OUTPUT_COLUMNS), "joint output schema mismatch")
    actual = frame.sort_values(["feature_session", "ticker"], kind="mergesort").reset_index(drop=True)
    expected = _expected_output(result)
    try:
        pd.testing.assert_frame_equal(actual, expected, check_exact=True, check_dtype=True)
    except AssertionError as error:
        raise RuntimeVerificationError("joint output rows/state values mismatch") from error
    for column, expected_value in {
        "outcome_blind": True,
        "model_fitted": False,
        "model_scoring": False,
        "trade_recommendation": False,
    }.items():
        _require(actual[column].eq(expected_value).all(), f"joint output protected flag {column} invalid")
    return VerifiedJointSnapshot(
        artifact_path=artifact_path,
        artifact_sha256=actual_artifact_sha,
        manifest_path=manifest_path,
        manifest_sha256=actual_manifest_sha,
        result=result,
        manifest=manifest,
    )


def run_controlled_smoke(runtime_root: Path) -> SmokeRun:
    """Materialize or verify the one frozen 2026-08-12 -> 2026-08-13 smoke."""

    _require(joint_contract_fingerprint_v1_1() == V1_1_FINGERPRINT, "checked-in V1.1 fingerprint does not match frozen identity")
    ff_spec, price_spec = _parent_specs(runtime_root)
    official_sessions = _calendar(runtime_root)
    ff = _load_parent(ff_spec)
    price = _load_parent(price_spec)
    result = build_joint_setup_readiness_state_v1_1(
        ff.frame,
        price.frame,
        official_sessions=official_sessions,
        foreign_flow_provenance=ff.provenance,
        price_state_provenance=price.provenance,
    )
    domain = _domain_payload(result)
    _require(
        {key: domain[key] for key in EXPECTED_DOMAIN} == EXPECTED_DOMAIN,
        "controlled smoke domain differs from frozen expectation",
    )
    distribution = result.frame["joint_state"].value_counts().sort_index().astype(int).to_dict()
    _require(distribution == EXPECTED_STATE_DISTRIBUTION, "controlled smoke state distribution differs from frozen expectation")
    output_dir = runtime_root / "forward_monitoring" / "prospective" / "joint_setup_readiness_state_v1_1" / FEATURE_SESSION
    artifact_path = output_dir / "joint_setup_readiness_state_v1_1.parquet"
    manifest_path = output_dir / "joint_setup_readiness_state_v1_1.manifest.json"
    existing = artifact_path.exists() or manifest_path.exists()
    if existing:
        _require(artifact_path.exists() and manifest_path.exists(), "joint output pair is partially present; refusing repair/overwrite")
        verified = verify_joint_setup_readiness_snapshot(
            output_dir,
            foreign_flow_spec=ff_spec,
            price_state_spec=price_spec,
            official_sessions=official_sessions,
        )
        created = False
    else:
        payload = _serialize_frame(_expected_output(result))
        artifact_sha = hashlib.sha256(payload).hexdigest()
        provenance_payload = _provenance_payload(ff=ff, price=price, result=result, artifact_path=artifact_path)
        manifest_payload: dict[str, Any] = {
            "schema": "idx-trade/joint-setup-readiness-state-v1-1-runtime-v1",
            "status": JOINT_RUNTIME_STATUS,
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_sha,
            "manifest_path": str(manifest_path),
            "source_session": SOURCE_SESSION,
            "feature_session": FEATURE_SESSION,
            "foreign_flow_contract_version": ff.spec.contract_version,
            "price_state_contract_version": price.spec.contract_version,
            "v1_fingerprint": v1.joint_contract_fingerprint(),
            "v1_1_fingerprint": result.contract_fingerprint,
            "domain": _domain_payload(result),
            "row_count": int(len(result.frame)),
            "ticker_count": int(result.frame["ticker"].nunique()),
            "state_distribution": distribution,
            "provenance_payload": provenance_payload,
            "provenance_fingerprint": _content_hash(provenance_payload),
            "protected_flags": provenance_payload["protected_flags"],
        }
        _immutable_create(artifact_path, payload)
        _immutable_create(manifest_path, _manifest_bytes(manifest_payload))
        verified = verify_joint_setup_readiness_snapshot(
            output_dir,
            foreign_flow_spec=ff_spec,
            price_state_spec=price_spec,
            official_sessions=official_sessions,
        )
        created = True
    return SmokeRun(
        status=JOINT_RUNTIME_STATUS,
        created=created,
        strict_verified=True,
        artifact_path=verified.artifact_path,
        artifact_sha256=verified.artifact_sha256,
        manifest_path=verified.manifest_path,
        manifest_sha256=verified.manifest_sha256,
        rows=len(verified.result.frame),
        tickers=verified.result.frame["ticker"].nunique(),
        source_session=SOURCE_SESSION,
        feature_session=FEATURE_SESSION,
        domain=verified.result.domain.as_dict(),
        state_distribution=verified.result.frame["joint_state"].value_counts().sort_index().astype(int).to_dict(),
        provider_calls=0,
        outcome_blind=True,
        forward_outcomes_accessed=False,
        outcomes_or_labels_accessed=False,
        model_fitted=False,
        model_scoring=False,
        trade_recommendation=False,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    args = parser.parse_args()
    first = run_controlled_smoke(args.runtime_root)
    replay = run_controlled_smoke(args.runtime_root)
    _require(not replay.created, "idempotent replay unexpectedly created/rewrote output")
    _require(first.artifact_sha256 == replay.artifact_sha256, "artifact SHA changed on replay")
    _require(first.manifest_sha256 == replay.manifest_sha256, "manifest SHA changed on replay")
    report = {
        "status": replay.status,
        "first_created": first.created,
        "replay_created": replay.created,
        "strict_verified": replay.strict_verified,
        "artifact_path": str(replay.artifact_path),
        "artifact_sha256": replay.artifact_sha256,
        "manifest_path": str(replay.manifest_path),
        "manifest_sha256": replay.manifest_sha256,
        "rows": replay.rows,
        "tickers": replay.tickers,
        "source_session": replay.source_session,
        "feature_session": replay.feature_session,
        "domain": replay.domain,
        "state_distribution": replay.state_distribution,
        "provider_calls": replay.provider_calls,
        "outcome_blind": replay.outcome_blind,
        "forward_outcomes_accessed": replay.forward_outcomes_accessed,
        "outcomes_or_labels_accessed": replay.outcomes_or_labels_accessed,
        "model_fitted": replay.model_fitted,
        "model_scoring": replay.model_scoring,
        "trade_recommendation": replay.trade_recommendation,
    }
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
