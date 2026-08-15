from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.joint_setup_readiness_state_v1_1 import (
    ParentProvenance,
    build_joint_setup_readiness_state_v1_1,
)
from idx_trade.joint_setup_readiness_v1_1_runtime import (
    FEATURE_SESSION,
    JOINT_RUNTIME_STATUS,
    SOURCE_SESSION,
    ParentArtifactSpec,
    RuntimeVerificationError,
    _content_hash,
    _immutable_create,
    _load_parent,
    _manifest_bytes,
    _provenance_payload,
    _serialize_frame,
    verify_joint_setup_readiness_snapshot,
)
from idx_trade.joint_setup_readiness_state import (
    FOREIGN_FLOW_STATE_CONTRACT_VERSION,
    PRICE_STATE_CONTRACT_VERSION,
)


SESSIONS = pd.to_datetime(["2026-08-11", "2026-08-12", "2026-08-13"])


def _parents(extra_ff: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    tickers = ["AAA", "BBB"]
    ff_tickers = tickers + (["EXTRA"] if extra_ff else [])
    ff = pd.DataFrame(
        {
            "ticker": ff_tickers,
            "feature_session": [FEATURE_SESSION] * len(ff_tickers),
            "flow_through_session": [SOURCE_SESSION] * len(ff_tickers),
            "setup_label": ["PERSISTENT_ACCUMULATION"] * len(ff_tickers),
            "state_contract_version": [FOREIGN_FLOW_STATE_CONTRACT_VERSION] * len(ff_tickers),
        }
    )
    price = pd.DataFrame(
        {
            "ticker": tickers,
            "source_session": [SOURCE_SESSION] * len(tickers),
            "feature_session": [FEATURE_SESSION] * len(tickers),
            "trend_state": ["UPTREND"] * len(tickers),
            "confirmation_state": ["NO_BREAKOUT"] * len(tickers),
            "state_contract_version": [PRICE_STATE_CONTRACT_VERSION] * len(tickers),
            "outcome_blind": [True] * len(tickers),
            "model_fitted": [False] * len(tickers),
            "model_scoring": [False] * len(tickers),
            "trade_recommendation": [False] * len(tickers),
        }
    )
    return ff, price


def _parent_manifest(path: Path, artifact_sha: str, *, kind: str, row_count: int) -> dict[str, object]:
    common: dict[str, object] = {
        "state_contract_version": (
            FOREIGN_FLOW_STATE_CONTRACT_VERSION
            if kind == "FOREIGN_FLOW_SETUP"
            else PRICE_STATE_CONTRACT_VERSION
        ),
        "status": (
            "FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY"
            if kind == "FOREIGN_FLOW_SETUP"
            else "PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY"
        ),
        "feature_session": FEATURE_SESSION,
        "outcome_blind": True,
        "provider_calls": 0,
        "model_fit": False,
        "model_scoring": False,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "row_count": row_count,
        "prohibited_actions": {
            "fresh_forward_accessed": False,
            "outcomes_or_labels_accessed": False,
            "model_fit": False,
            "model_scoring": False,
        },
    }
    if kind == "FOREIGN_FLOW_SETUP":
        common.update(
            {
                "setup_sidecar_path": str(path),
                "setup_sidecar_sha256": artifact_sha,
                "flow_through_session": SOURCE_SESSION,
            }
        )
    else:
        common.update(
            {
                "artifact_path": str(path),
                "artifact_sha256": artifact_sha,
                "source_session": SOURCE_SESSION,
                "trade_recommendation": False,
            }
        )
    return common


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_fixture(tmp_path: Path, *, extra_ff: bool = False):
    ff, price = _parents(extra_ff=extra_ff)
    ff_path = tmp_path / "parents" / "ff.parquet"
    price_path = tmp_path / "parents" / "price.parquet"
    ff_manifest_path = tmp_path / "parents" / "ff.manifest.json"
    price_manifest_path = tmp_path / "parents" / "price.manifest.json"
    ff_path.parent.mkdir(parents=True, exist_ok=True)
    ff.to_parquet(ff_path, index=False)
    price.to_parquet(price_path, index=False)
    ff_sha = hashlib.sha256(ff_path.read_bytes()).hexdigest()
    price_sha = hashlib.sha256(price_path.read_bytes()).hexdigest()
    _write_json(ff_manifest_path, _parent_manifest(ff_path, ff_sha, kind="FOREIGN_FLOW_SETUP", row_count=len(ff)))
    _write_json(price_manifest_path, _parent_manifest(price_path, price_sha, kind="PRICE_STATE", row_count=len(price)))
    ff_spec = ParentArtifactSpec(
        kind="FOREIGN_FLOW_SETUP",
        artifact_path=ff_path,
        artifact_sha256=ff_sha,
        manifest_path=ff_manifest_path,
        manifest_sha256=hashlib.sha256(ff_manifest_path.read_bytes()).hexdigest(),
        manifest_artifact_path_key="setup_sidecar_path",
        manifest_artifact_sha256_key="setup_sidecar_sha256",
        contract_version=FOREIGN_FLOW_STATE_CONTRACT_VERSION,
        expected_status="FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY",
        source_kind="TEST_FOREIGN_FLOW_SETUP",
    )
    price_spec = ParentArtifactSpec(
        kind="PRICE_STATE",
        artifact_path=price_path,
        artifact_sha256=price_sha,
        manifest_path=price_manifest_path,
        manifest_sha256=hashlib.sha256(price_manifest_path.read_bytes()).hexdigest(),
        manifest_artifact_path_key="artifact_path",
        manifest_artifact_sha256_key="artifact_sha256",
        contract_version=PRICE_STATE_CONTRACT_VERSION,
        expected_status="PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY",
        source_kind="TEST_PRICE_STATE",
    )
    return ff, price, ff_spec, price_spec


def _materialize_fixture(tmp_path: Path, ff_spec: ParentArtifactSpec, price_spec: ParentArtifactSpec) -> Path:
    ff = _load_parent(ff_spec)
    price = _load_parent(price_spec)
    result = build_joint_setup_readiness_state_v1_1(
        ff.frame,
        price.frame,
        official_sessions=SESSIONS,
        foreign_flow_provenance=ff.provenance,
        price_state_provenance=price.provenance,
    )
    output_dir = tmp_path / "joint"
    artifact_path = output_dir / "joint_setup_readiness_state_v1_1.parquet"
    manifest_path = output_dir / "joint_setup_readiness_state_v1_1.manifest.json"
    output = result.frame
    artifact_bytes = _serialize_frame(output)
    artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
    provenance = _provenance_payload(ff=ff, price=price, result=result, artifact_path=artifact_path)
    manifest = {
        "schema": "test/joint-runtime",
        "status": JOINT_RUNTIME_STATUS,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha,
        "manifest_path": str(manifest_path),
        "source_session": SOURCE_SESSION,
        "feature_session": FEATURE_SESSION,
        "foreign_flow_contract_version": ff_spec.contract_version,
        "price_state_contract_version": price_spec.contract_version,
        "v1_fingerprint": "a79e37cacf9ec428e27b4b398a757b9415e6e358b11b0d10edaf78a50c3d3599",
        "v1_1_fingerprint": result.contract_fingerprint,
        "domain": result.domain.as_dict(),
        "row_count": len(output),
        "ticker_count": output["ticker"].nunique(),
        "state_distribution": output["joint_state"].value_counts().sort_index().astype(int).to_dict(),
        "provenance_payload": provenance,
        "provenance_fingerprint": _content_hash(provenance),
        "protected_flags": provenance["protected_flags"],
    }
    _immutable_create(artifact_path, artifact_bytes)
    _immutable_create(manifest_path, _manifest_bytes(manifest))
    return output_dir


def _refresh_output_manifest(manifest_path: Path, mutate) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest["manifest_content_sha256"] = _content_hash(
        {key: value for key, value in manifest.items() if key != "manifest_content_sha256"}
    )
    _write_json(manifest_path, manifest)


def _refresh_parent_spec(spec: ParentArtifactSpec, frame: pd.DataFrame, *, source_column: str | None = None) -> ParentArtifactSpec:
    frame.to_parquet(spec.artifact_path, index=False)
    artifact_sha = hashlib.sha256(spec.artifact_path.read_bytes()).hexdigest()
    manifest = json.loads(spec.manifest_path.read_text(encoding="utf-8"))
    manifest[spec.manifest_artifact_sha256_key] = artifact_sha
    manifest["row_count"] = len(frame)
    if source_column is not None:
        manifest[source_column] = SOURCE_SESSION
    _write_json(spec.manifest_path, manifest)
    return replace(
        spec,
        artifact_sha256=artifact_sha,
        manifest_sha256=hashlib.sha256(spec.manifest_path.read_bytes()).hexdigest(),
    )


def test_valid_snapshot_reopens_and_recomputes_all_parent_and_output_semantics(tmp_path: Path) -> None:
    _, _, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)

    verified = verify_joint_setup_readiness_snapshot(
        output_dir,
        foreign_flow_spec=ff_spec,
        price_state_spec=price_spec,
        official_sessions=SESSIONS,
    )

    assert verified.result.domain.price_only_key_count == 0
    assert len(verified.result.frame) == 2
    assert verified.manifest["status"] == JOINT_RUNTIME_STATUS


@pytest.mark.parametrize("kind", ["foreign", "price"])
def test_parent_artifact_tamper_fails_even_when_parent_manifest_is_rehashed(tmp_path: Path, kind: str) -> None:
    ff, price, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    target = ff_spec if kind == "foreign" else price_spec
    frame = ff if kind == "foreign" else price
    frame = frame.copy()
    frame.loc[0, "ticker"] = "TAMPERED"
    frame.to_parquet(target.artifact_path, index=False)
    manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
    manifest[target.manifest_artifact_sha256_key] = hashlib.sha256(target.artifact_path.read_bytes()).hexdigest()
    _write_json(target.manifest_path, manifest)

    with pytest.raises(RuntimeVerificationError):
        verify_joint_setup_readiness_snapshot(
            output_dir,
            foreign_flow_spec=ff_spec,
            price_state_spec=price_spec,
            official_sessions=SESSIONS,
        )


def test_wrong_parent_manifest_fails_closed(tmp_path: Path) -> None:
    _, _, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    _refresh_output_manifest(ff_spec.manifest_path, lambda manifest: manifest.update({"status": "WRONG"}))

    with pytest.raises(RuntimeVerificationError):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=price_spec, official_sessions=SESSIONS)


def test_missing_required_price_ticker_in_foreign_flow_fails_closed(tmp_path: Path) -> None:
    ff, price, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    missing_spec = _refresh_parent_spec(ff_spec, ff.iloc[:1].copy())

    with pytest.raises(Exception, match="Price State contains keys missing"):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=missing_spec, price_state_spec=price_spec, official_sessions=SESSIONS)


def test_extra_ff_only_ticker_changes_domain_provenance_not_price_output(tmp_path: Path) -> None:
    ff, price, ff_spec, price_spec = _make_fixture(tmp_path, extra_ff=True)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    verified = verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=price_spec, official_sessions=SESSIONS)

    assert len(verified.result.frame) == len(price)
    assert verified.result.domain.foreign_flow_only_keys == (("EXTRA", FEATURE_SESSION),)


def test_wrong_source_or_feature_session_fails_closed(tmp_path: Path) -> None:
    ff, price, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    bad_price = price.copy()
    bad_price.loc[0, "source_session"] = "2026-08-11"
    bad_spec = _refresh_parent_spec(price_spec, bad_price, source_column="source_session")

    with pytest.raises(RuntimeVerificationError, match="source session mismatch"):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=bad_spec, official_sessions=SESSIONS)


def test_v1_1_fingerprint_mismatch_fails_closed(tmp_path: Path) -> None:
    _, _, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    _refresh_output_manifest(output_dir / "joint_setup_readiness_state_v1_1.manifest.json", lambda manifest: manifest.update({"v1_1_fingerprint": "0" * 64}))

    with pytest.raises(RuntimeVerificationError, match="fingerprint"):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=price_spec, official_sessions=SESSIONS)


def test_output_row_or_state_tamper_fails_after_manifest_is_consistently_rehashed(tmp_path: Path) -> None:
    _, _, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    artifact_path = output_dir / "joint_setup_readiness_state_v1_1.parquet"
    frame = pd.read_parquet(artifact_path)
    frame.loc[0, "joint_state"] = "TAMPERED_STATE"
    frame.to_parquet(artifact_path, index=False)
    artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    _refresh_output_manifest(output_dir / "joint_setup_readiness_state_v1_1.manifest.json", lambda manifest: manifest.update({"artifact_sha256": artifact_sha}))

    with pytest.raises(RuntimeVerificationError, match="output rows/state"):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=price_spec, official_sessions=SESSIONS)


def test_manifest_path_substitution_fails_closed(tmp_path: Path) -> None:
    _, _, ff_spec, price_spec = _make_fixture(tmp_path)
    output_dir = _materialize_fixture(tmp_path, ff_spec, price_spec)
    _refresh_output_manifest(output_dir / "joint_setup_readiness_state_v1_1.manifest.json", lambda manifest: manifest.update({"artifact_path": str(tmp_path / "other.parquet")}))

    with pytest.raises(RuntimeVerificationError, match="artifact path"):
        verify_joint_setup_readiness_snapshot(output_dir, foreign_flow_spec=ff_spec, price_state_spec=price_spec, official_sessions=SESSIONS)


def test_immutable_create_is_idempotent_and_rejects_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "immutable.bin"
    assert _immutable_create(path, b"one") is True
    assert _immutable_create(path, b"one") is False
    with pytest.raises(RuntimeVerificationError):
        _immutable_create(path, b"two")
