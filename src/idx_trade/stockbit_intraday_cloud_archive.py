from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import os
from typing import Any, Mapping, Sequence

from .stockbit_intraday_cloud_storage import (
    CloudObjectStore,
    ConditionalS3Store,
    LocalConditionalStore,
    canonical_json_bytes,
    sha256_bytes,
)
from .stockbit_stream_archive import StorageImmutabilityConflict


SCHEMA_VERSION = "idx_trade_stockbit_intraday_cloud_slot_v1"
POLICY_SCHEMA_VERSION = "idx_trade_stockbit_intraday_cloud_policy_v1"
SLOTS = ("1830", "1930", "2030")


class StockbitIntradayCloudError(RuntimeError):
    pass


@dataclass(frozen=True)
class IntradaySlotCommit:
    session_date: str
    slot: str
    status: str
    commit_key: str
    commit_sha256: str
    snapshot_key: str
    snapshot_sha256: str
    result_key: str
    result_sha256: str
    payload: dict[str, Any]


def _session(value: str | date) -> str:
    return date.fromisoformat(str(value)).isoformat()


def _slot(value: object) -> str:
    slot = str(value or "").strip()
    if slot not in SLOTS:
        raise StockbitIntradayCloudError(f"STOCKBIT_INTRADAY_SLOT_INVALID:{slot}")
    return slot


def _json(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradayCloudError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise StockbitIntradayCloudError(f"{label}_NOT_OBJECT")
    return value


def build_intraday_store_from_env(env: Mapping[str, str] | None = None) -> CloudObjectStore:
    values = os.environ if env is None else env
    backend = str(values.get("STOCKBIT_INTRADAY_STORAGE_BACKEND", "s3")).strip().lower()
    if backend == "local":
        root = str(values.get("STOCKBIT_INTRADAY_LOCAL_ROOT", "")).strip()
        if not root:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_LOCAL_ROOT_REQUIRED")
        return LocalConditionalStore(root)
    if backend != "s3":
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_STORAGE_BACKEND_INVALID")
    return ConditionalS3Store(
        str(values.get("STOCKBIT_INTRADAY_S3_ENDPOINT", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_BUCKET", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_STORAGE_PREFIX", "stockbit-intraday-v1")).strip("/"),
    )


class StockbitIntradayCloudArchive:
    """Known-key, append-only cloud archive for post-close intraday slots.

    Snapshot/result objects are written first and hash-verified. ``commit.json``
    is written last and is the durable admission marker. A pre-existing commit
    is accepted only when it is byte-equivalent to the caller's recomputation;
    divergent concurrent runners fail closed.
    """

    def __init__(self, store: CloudObjectStore):
        self.store = store

    @staticmethod
    def commit_key(session_date: str | date, slot: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/commit.json"

    @staticmethod
    def snapshot_key(session_date: str | date, slot: str, snapshot_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/snapshots/{snapshot_sha256}.zip"

    @staticmethod
    def result_key(session_date: str | date, slot: str, result_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/results/{result_sha256}.json"

    @staticmethod
    def policy_key(session_date: str | date) -> str:
        return f"policy/checkpoints/{_session(session_date)}.json"

    def existing_slot(self, session_date: str | date, slot: str) -> IntradaySlotCommit | None:
        session = _session(session_date)
        slot = _slot(slot)
        key = self.commit_key(session, slot)
        raw = self.store.read(key)
        if raw is None:
            return None
        payload = _json(raw, label="STOCKBIT_INTRADAY_SLOT_COMMIT")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_SCHEMA_MISMATCH")
        if payload.get("commit_state") != "COMMITTED":
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_NOT_COMMITTED")
        if payload.get("session_date") != session or payload.get("slot") != slot:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_IDENTITY_MISMATCH")
        guards = payload.get("guards")
        if (
            not isinstance(guards, dict)
            or guards.get("synthetic_fill_used") is not False
            or guards.get("retroactive_capture_used") is not False
            or guards.get("outcome_accessed") is not False
        ):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_COMMIT_GUARD_INVALID")
        snapshot = payload.get("snapshot")
        result = payload.get("result")
        if not isinstance(snapshot, dict) or not isinstance(result, dict):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_REF_INVALID")
        snapshot_key = str(snapshot.get("key") or "")
        snapshot_sha = str(snapshot.get("sha256") or "").lower()
        result_key = str(result.get("key") or "")
        result_sha = str(result.get("sha256") or "").lower()
        if len(snapshot_sha) != 64 or len(result_sha) != 64 or not snapshot_key or not result_key:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_REF_INVALID")
        snapshot_raw = self.store.read(snapshot_key)
        result_raw = self.store.read(result_key)
        if snapshot_raw is None or sha256_bytes(snapshot_raw) != snapshot_sha:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_SNAPSHOT_INVALID")
        if result_raw is None or sha256_bytes(result_raw) != result_sha:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_INVALID")
        result_payload = _json(result_raw, label="STOCKBIT_INTRADAY_SLOT_RESULT")
        if (
            result_payload.get("session_date") != session
            or result_payload.get("slot") != slot
            or result_payload.get("status") != payload.get("status")
            or result_payload.get("synthetic_fill_used") is not False
            or result_payload.get("retroactive_capture_used") is not False
            or result_payload.get("outcome_accessed") is not False
        ):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_GUARD_INVALID")
        return IntradaySlotCommit(
            session_date=session,
            slot=slot,
            status=str(payload.get("status") or ""),
            commit_key=key,
            commit_sha256=sha256_bytes(raw),
            snapshot_key=snapshot_key,
            snapshot_sha256=snapshot_sha,
            result_key=result_key,
            result_sha256=result_sha,
            payload=payload,
        )

    def latest_committed_slot_before(
        self,
        session_date: str | date,
        slot: str,
    ) -> IntradaySlotCommit | None:
        target = _slot(slot)
        index = SLOTS.index(target)
        for candidate in reversed(SLOTS[:index]):
            found = self.existing_slot(session_date, candidate)
            if found is not None:
                return found
        return None

    def later_committed_slot_after(
        self,
        session_date: str | date,
        slot: str,
    ) -> IntradaySlotCommit | None:
        target = _slot(slot)
        index = SLOTS.index(target)
        for candidate in SLOTS[index + 1 :]:
            found = self.existing_slot(session_date, candidate)
            if found is not None:
                return found
        return None

    @staticmethod
    def _expected_slot_payload(
        *,
        session: str,
        slot: str,
        status: str,
        snapshot_sha: str,
        snapshot_key: str,
        result_sha: str,
        result_key: str,
        code_identity: Mapping[str, Any],
        eod_manifest_sha256: str | None,
        session_manifest_sha256: str | None,
    ) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "commit_state": "COMMITTED",
            "session_date": session,
            "slot": slot,
            "status": str(status),
            "snapshot": {"key": snapshot_key, "sha256": snapshot_sha},
            "result": {"key": result_key, "sha256": result_sha},
            "eod_manifest_sha256": eod_manifest_sha256,
            "session_manifest_sha256": session_manifest_sha256,
            "code_identity": dict(code_identity),
            "guards": {
                "synthetic_fill_used": False,
                "retroactive_capture_used": False,
                "outcome_accessed": False,
            },
        }

    def commit_slot(
        self,
        *,
        session_date: str | date,
        slot: str,
        status: str,
        snapshot_bytes: bytes,
        result_payload: Mapping[str, Any],
        code_identity: Mapping[str, Any],
        eod_manifest_sha256: str | None,
        session_manifest_sha256: str | None,
    ) -> IntradaySlotCommit:
        session = _session(session_date)
        slot = _slot(slot)
        snapshot_sha = sha256_bytes(snapshot_bytes)
        result = {
            **dict(result_payload),
            "session_date": session,
            "slot": slot,
            "status": str(status),
            "synthetic_fill_used": False,
            "retroactive_capture_used": False,
            "outcome_accessed": False,
        }
        result_bytes = canonical_json_bytes(result)
        result_sha = sha256_bytes(result_bytes)
        snapshot_key = self.snapshot_key(session, slot, snapshot_sha)
        result_key = self.result_key(session, slot, result_sha)
        payload = self._expected_slot_payload(
            session=session,
            slot=slot,
            status=status,
            snapshot_sha=snapshot_sha,
            snapshot_key=snapshot_key,
            result_sha=result_sha,
            result_key=result_key,
            code_identity=code_identity,
            eod_manifest_sha256=eod_manifest_sha256,
            session_manifest_sha256=session_manifest_sha256,
        )
        encoded = canonical_json_bytes(payload)
        expected_commit_sha = sha256_bytes(encoded)

        existing = self.existing_slot(session, slot)
        if existing is not None:
            if existing.commit_sha256 != expected_commit_sha:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_EXISTING_IDENTITY_CONFLICT")
            return existing

        self.store.put_if_absent(snapshot_key, snapshot_bytes, "application/zip")
        self.store.put_if_absent(result_key, result_bytes, "application/json")
        commit_key = self.commit_key(session, slot)
        try:
            self.store.put_if_absent(commit_key, encoded, "application/json")
        except StorageImmutabilityConflict:
            concurrent = self.existing_slot(session, slot)
            if concurrent is None or concurrent.commit_sha256 != expected_commit_sha:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_CONCURRENT_IDENTITY_CONFLICT")
            return concurrent
        committed = self.existing_slot(session, slot)
        if committed is None:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_COMMIT_READBACK_MISSING")
        if committed.commit_sha256 != expected_commit_sha:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_COMMIT_CONFLICT")
        return committed

    def load_policy_checkpoint(self, session_date: str | date) -> dict[str, Any] | None:
        session = _session(session_date)
        raw = self.store.read(self.policy_key(session))
        if raw is None:
            return None
        payload = _json(raw, label="STOCKBIT_INTRADAY_POLICY")
        if (
            payload.get("schema_version") != POLICY_SCHEMA_VERSION
            or payload.get("session_date") != session
            or not isinstance(payload.get("policy"), dict)
        ):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_INVALID")
        manifest_sha = str(payload.get("session_manifest_sha256") or "")
        if len(manifest_sha) != 64:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_MANIFEST_SHA_INVALID")
        return payload

    def latest_policy_checkpoint(
        self,
        session_dates: Sequence[str],
        *,
        before_or_equal: str | date,
    ) -> dict[str, Any] | None:
        boundary = _session(before_or_equal)
        candidates = sorted({str(value) for value in session_dates if str(value) <= boundary})
        for session in reversed(candidates):
            checkpoint = self.load_policy_checkpoint(session)
            if checkpoint is not None:
                return checkpoint
        return None

    def commit_policy_checkpoint(
        self,
        *,
        session_date: str | date,
        session_manifest_sha256: str,
        policy: Mapping[str, Any],
    ) -> dict[str, Any]:
        session = _session(session_date)
        if len(str(session_manifest_sha256)) != 64:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_SESSION_MANIFEST_SHA_INVALID")
        payload = {
            "schema_version": POLICY_SCHEMA_VERSION,
            "session_date": session,
            "session_manifest_sha256": str(session_manifest_sha256).lower(),
            "policy": dict(policy),
        }
        encoded = canonical_json_bytes(payload)
        key = self.policy_key(session)
        self.store.put_if_absent(key, encoded, "application/json")
        confirmed = self.load_policy_checkpoint(session)
        if confirmed is None or canonical_json_bytes(confirmed) != encoded:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_READBACK_MISMATCH")
        return confirmed
