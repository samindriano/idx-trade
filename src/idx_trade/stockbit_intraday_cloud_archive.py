from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
import re
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
CLAIM_SCHEMA_VERSION = "idx_trade_stockbit_intraday_cloud_claim_v1"
PROGRESS_SCHEMA_VERSION = "idx_trade_stockbit_intraday_cloud_progress_v1"
PROVIDER_EVIDENCE_SCHEMA_VERSION = "idx_trade_stockbit_intraday_provider_evidence_v1"
PRODUCTION_STORAGE_PREFIX = "stockbit-intraday-v1"
SLOTS = ("1830", "1930", "2030")
STALE_CLAIM_AFTER_SECONDS = 2 * 60 * 60
_TICKER_PATH = re.compile(r"^[A-Z0-9._-]+$")


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


def _ticker(value: object) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized or _TICKER_PATH.fullmatch(normalized) is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_TICKER_INVALID")
    return normalized


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
    prefix = str(values.get("STOCKBIT_INTRADAY_STORAGE_PREFIX", PRODUCTION_STORAGE_PREFIX)).strip("/")
    if prefix != PRODUCTION_STORAGE_PREFIX:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_STORAGE_PREFIX_INVALID")
    return ConditionalS3Store(
        str(values.get("STOCKBIT_INTRADAY_S3_ENDPOINT", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_BUCKET", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID", "")).strip(),
        str(values.get("STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY", "")).strip(),
        PRODUCTION_STORAGE_PREFIX,
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
    def claim_key(session_date: str | date, slot: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/claim.json"

    @staticmethod
    def snapshot_key(session_date: str | date, slot: str, snapshot_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/snapshots/{snapshot_sha256}.zip"

    @staticmethod
    def result_key(session_date: str | date, slot: str, result_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/results/{result_sha256}.json"

    @staticmethod
    def progress_snapshot_key(session_date: str | date, slot: str, snapshot_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/progress/snapshots/{snapshot_sha256}.zip"

    @staticmethod
    def progress_checkpoint_key(session_date: str | date, slot: str, checkpoint_sha256: str) -> str:
        return f"sessions/{_session(session_date)}/slots/{_slot(slot)}/progress/checkpoints/{checkpoint_sha256}.json"

    @staticmethod
    def provider_evidence_key(
        session_date: str | date, slot: str, ticker: str, evidence_sha256: str
    ) -> str:
        return (
            f"sessions/{_session(session_date)}/slots/{_slot(slot)}/progress/provider/"
            f"{_ticker(ticker)}/{evidence_sha256}.json"
        )

    @staticmethod
    def policy_key(session_date: str | date) -> str:
        return f"policy/checkpoints/{_session(session_date)}.json"

    def _read_claim(self, session_date: str | date, slot: str) -> tuple[dict[str, Any], str] | None:
        key = self.claim_key(session_date, slot)
        raw = self.store.read(key)
        if raw is None:
            return None
        payload = _json(raw, label="STOCKBIT_INTRADAY_SLOT_CLAIM")
        if (
            payload.get("schema_version") != CLAIM_SCHEMA_VERSION
            or payload.get("claim_state") != "CLAIMED"
            or payload.get("session_date") != _session(session_date)
            or payload.get("slot") != _slot(slot)
            or not str(payload.get("claim_id") or "")
            or not isinstance(payload.get("code_identity"), dict)
        ):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_CLAIM_INVALID")
        guards = payload.get("guards")
        if (
            not isinstance(guards, dict)
            or guards.get("synthetic_fill_used") is not False
            or guards.get("retroactive_capture_used") is not False
            or guards.get("outcome_accessed") is not False
        ):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_CLAIM_GUARD_INVALID")
        return payload, sha256_bytes(raw)

    def existing_claim(self, session_date: str | date, slot: str) -> tuple[dict[str, Any], str] | None:
        return self._read_claim(session_date, slot)

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
        if snapshot_key != self.snapshot_key(session, slot, snapshot_sha):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_SNAPSHOT_KEY_MISMATCH")
        if result_key != self.result_key(session, slot, result_sha):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_KEY_MISMATCH")
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

    def claim_slot(
        self,
        *,
        session_date: str | date,
        slot: str,
        claimed_at_utc: str,
        code_identity: Mapping[str, Any],
        claim_id: str,
        resume_if_stale: bool = False,
        stale_after_seconds: float = STALE_CLAIM_AFTER_SECONDS,
    ) -> str:
        """Reserve a slot before any provider-stage work begins.

        The claim is immutable and create-only.  A concurrent/restarted caller
        must observe the claim and fail closed until the slot has a committed
        result; it may never run a second provider history for the same key.
        """
        session = _session(session_date)
        normalized_slot = _slot(slot)
        payload = {
            "schema_version": CLAIM_SCHEMA_VERSION,
            "claim_state": "CLAIMED",
            "session_date": session,
            "slot": normalized_slot,
            "claim_id": str(claim_id),
            "claimed_at_utc": str(claimed_at_utc),
            "code_identity": dict(code_identity),
            "guards": {
                "synthetic_fill_used": False,
                "retroactive_capture_used": False,
                "outcome_accessed": False,
            },
        }
        encoded = canonical_json_bytes(payload)
        key = self.claim_key(session, normalized_slot)
        existing = self._read_claim(session, normalized_slot)
        if existing is not None:
            existing_payload, existing_sha = existing
            if not resume_if_stale:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED")
            progress = self.latest_progress(session, normalized_slot)
            if progress is None:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED")
            try:
                claimed_at = datetime.fromisoformat(str(progress[0].get("captured_at_utc") or ""))
                current_at = datetime.fromisoformat(str(claimed_at_utc))
                if claimed_at.tzinfo is None or current_at.tzinfo is None:
                    raise ValueError
                age = (current_at.astimezone(timezone.utc) - claimed_at.astimezone(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError) as exc:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_TIMESTAMP_INVALID") from exc
            if age < float(stale_after_seconds):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED")
            if progress[0].get("claim_sha256") != existing_sha:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_CLAIM_MISMATCH")
            return existing_sha
        try:
            result = self.store.put_if_absent(key, encoded, "application/json")
        except StorageImmutabilityConflict as exc:
            raise StockbitIntradayCloudError(
                "STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED"
            ) from exc
        confirmed = self.store.read(key)
        if confirmed is None or confirmed != encoded:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_CLAIM_READBACK_MISMATCH")
        return result.sha256

    def persist_provider_evidence(
        self,
        *,
        session_date: str | date,
        slot: str,
        ticker: str,
        payload: object | None,
        request_meta: Mapping[str, Any],
        captured_at_utc: str,
        claim_sha256: str,
        code_identity: Mapping[str, Any],
    ) -> str:
        session = _session(session_date)
        normalized_slot = _slot(slot)
        normalized_ticker = _ticker(ticker)
        try:
            timestamp = datetime.fromisoformat(str(captured_at_utc))
        except (TypeError, ValueError) as exc:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_TIMESTAMP_INVALID") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_TIMESTAMP_INVALID")
        safe_meta = {
            "attempts": request_meta.get("attempts"),
            "retries": request_meta.get("retries"),
            "rate_limit_events": request_meta.get("rate_limit_events"),
            "errors": list(request_meta.get("errors") or []),
            "safe_headers": dict(request_meta.get("safe_headers") or {}),
            "rate_limit_window": request_meta.get("rate_limit_window"),
        }
        record = {
            "schema_version": PROVIDER_EVIDENCE_SCHEMA_VERSION,
            "session_date": session,
            "slot": normalized_slot,
            "ticker": normalized_ticker,
            "captured_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
            "claim_sha256": str(claim_sha256).lower(),
            "code_identity": dict(code_identity),
            "payload": payload,
            "request_meta": safe_meta,
        }
        encoded = canonical_json_bytes(record)
        digest = sha256_bytes(encoded)
        key = self.provider_evidence_key(session, normalized_slot, normalized_ticker, digest)
        self.store.put_if_absent(key, encoded, "application/json")
        confirmed = self.store.read(key)
        if confirmed != encoded:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_READBACK_MISMATCH")
        return digest

    def latest_provider_evidence(
        self,
        session_date: str | date,
        slot: str,
        ticker: str,
        *,
        claim_sha256: str,
        code_identity: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        prefix = (
            f"sessions/{_session(session_date)}/slots/{_slot(slot)}/progress/provider/"
            f"{_ticker(ticker)}/"
        )
        records: list[tuple[dict[str, Any], str]] = []
        for key in self.store.list_keys(prefix):
            raw = self.store.read(key)
            if raw is None:
                continue
            payload = _json(raw, label="STOCKBIT_INTRADAY_PROVIDER_EVIDENCE")
            if (
                payload.get("schema_version") != PROVIDER_EVIDENCE_SCHEMA_VERSION
                or payload.get("session_date") != _session(session_date)
                or payload.get("slot") != _slot(slot)
                or payload.get("ticker") != _ticker(ticker)
                or payload.get("claim_sha256") != str(claim_sha256).lower()
                or payload.get("code_identity") != dict(code_identity)
            ):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_IDENTITY_MISMATCH")
            if sha256_bytes(raw) != key.rsplit("/", 1)[-1].removesuffix(".json"):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_HASH_MISMATCH")
            records.append((payload, key.rsplit("/", 1)[-1].removesuffix(".json")))
        if not records:
            return None
        records.sort(key=lambda item: str(item[0].get("captured_at_utc") or ""))
        latest_timestamp = str(records[-1][0].get("captured_at_utc") or "")
        latest = [item for item in records if str(item[0].get("captured_at_utc") or "") == latest_timestamp]
        if len(latest) > 1:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROVIDER_EVIDENCE_TIMESTAMP_CONFLICT")
        return latest[0][0]

    def persist_progress(
        self,
        *,
        session_date: str | date,
        slot: str,
        snapshot_bytes: bytes,
        sequence: int,
        captured_at_utc: str,
        claim_sha256: str,
        code_identity: Mapping[str, Any],
        source_slot: str | None = None,
    ) -> dict[str, Any]:
        session = _session(session_date)
        normalized_slot = _slot(slot)
        if sequence < 0:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SEQUENCE_INVALID")
        try:
            timestamp = datetime.fromisoformat(str(captured_at_utc))
        except (TypeError, ValueError) as exc:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_TIMESTAMP_INVALID") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_TIMESTAMP_INVALID")
        snapshot_sha = sha256_bytes(snapshot_bytes)
        snapshot_key = self.progress_snapshot_key(session, normalized_slot, snapshot_sha)
        checkpoint = {
            "schema_version": PROGRESS_SCHEMA_VERSION,
            "checkpoint_state": "DURABLE_PROGRESS",
            "session_date": session,
            "slot": normalized_slot,
            "source_slot": _slot(source_slot) if source_slot is not None else normalized_slot,
            "sequence": int(sequence),
            "captured_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
            "claim_sha256": str(claim_sha256).lower(),
            "code_identity": dict(code_identity),
            "snapshot": {"key": snapshot_key, "sha256": snapshot_sha},
            "guards": {"synthetic_fill_used": False, "retroactive_capture_used": False, "outcome_accessed": False},
        }
        encoded = canonical_json_bytes(checkpoint)
        checkpoint_sha = sha256_bytes(encoded)
        checkpoint_key = self.progress_checkpoint_key(session, normalized_slot, checkpoint_sha)
        self.store.put_if_absent(snapshot_key, snapshot_bytes, "application/zip")
        self.store.put_if_absent(checkpoint_key, encoded, "application/json")
        if self.store.read(snapshot_key) != snapshot_bytes or self.store.read(checkpoint_key) != encoded:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_READBACK_MISMATCH")
        return {**checkpoint, "checkpoint_key": checkpoint_key, "checkpoint_sha256": checkpoint_sha}

    def latest_progress(self, session_date: str | date, slot: str) -> tuple[dict[str, Any], bytes] | None:
        session = _session(session_date)
        normalized_slot = _slot(slot)
        prefix = f"sessions/{session}/slots/{normalized_slot}/progress/checkpoints/"
        candidates: list[tuple[dict[str, Any], bytes]] = []
        for key in self.store.list_keys(prefix):
            if not key.endswith(".json"):
                continue
            raw = self.store.read(key)
            if raw is None:
                continue
            payload = _json(raw, label="STOCKBIT_INTRADAY_PROGRESS")
            snapshot = payload.get("snapshot")
            guards = payload.get("guards")
            if (
                payload.get("schema_version") != PROGRESS_SCHEMA_VERSION
                or payload.get("checkpoint_state") != "DURABLE_PROGRESS"
                or payload.get("session_date") != session
                or payload.get("slot") != normalized_slot
                or not isinstance(snapshot, dict)
                or not isinstance(guards, dict)
                or guards.get("synthetic_fill_used") is not False
                or guards.get("retroactive_capture_used") is not False
                or guards.get("outcome_accessed") is not False
            ):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_INVALID")
            try:
                sequence = int(payload.get("sequence"))
            except (TypeError, ValueError) as exc:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SEQUENCE_INVALID") from exc
            if sequence < 0 or sha256_bytes(raw) != key.rsplit("/", 1)[-1].removesuffix(".json"):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_HASH_INVALID")
            snapshot_key = str(snapshot.get("key") or "")
            snapshot_sha = str(snapshot.get("sha256") or "").lower()
            if snapshot_key != self.progress_snapshot_key(session, normalized_slot, snapshot_sha):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SNAPSHOT_KEY_MISMATCH")
            snapshot_raw = self.store.read(snapshot_key)
            if snapshot_raw is None or sha256_bytes(snapshot_raw) != snapshot_sha:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SNAPSHOT_INVALID")
            candidates.append((payload, snapshot_raw))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (int(item[0]["sequence"]), str(item[0].get("captured_at_utc") or "")))
        best = candidates[-1]
        if len([item for item in candidates if int(item[0]["sequence"]) == int(best[0]["sequence"])]) > 1:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SEQUENCE_CONFLICT")
        return best

    def latest_progress_before(self, session_date: str | date, slot: str) -> tuple[dict[str, Any], bytes] | None:
        normalized_slot = _slot(slot)
        for candidate in reversed(SLOTS[: SLOTS.index(normalized_slot)]):
            latest = self.latest_progress(session_date, candidate)
            if latest is not None:
                return latest
        return None

    def latest_committed_slot_before(self, session_date: str | date, slot: str) -> IntradaySlotCommit | None:
        target = _slot(slot)
        index = SLOTS.index(target)
        for candidate in reversed(SLOTS[:index]):
            found = self.existing_slot(session_date, candidate)
            if found is not None:
                return found
        return None

    def later_committed_slot_after(self, session_date: str | date, slot: str) -> IntradaySlotCommit | None:
        target = _slot(slot)
        index = SLOTS.index(target)
        for candidate in SLOTS[index + 1 :]:
            found = self.existing_slot(session_date, candidate)
            if found is not None:
                return found
        return None

    @staticmethod
    def _expected_slot_payload(
        *, session: str, slot: str, status: str, snapshot_sha: str, snapshot_key: str,
        result_sha: str, result_key: str, code_identity: Mapping[str, Any],
        eod_manifest_sha256: str | None, session_manifest_sha256: str | None,
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
            "guards": {"synthetic_fill_used": False, "retroactive_capture_used": False, "outcome_accessed": False},
        }

    def commit_slot(
        self, *, session_date: str | date, slot: str, status: str, snapshot_bytes: bytes,
        result_payload: Mapping[str, Any], code_identity: Mapping[str, Any],
        eod_manifest_sha256: str | None, session_manifest_sha256: str | None,
        claim_sha256: str | None = None,
    ) -> IntradaySlotCommit:
        session = _session(session_date)
        slot = _slot(slot)
        snapshot_sha = sha256_bytes(snapshot_bytes)
        result = {**dict(result_payload), "session_date": session, "slot": slot, "status": str(status), "synthetic_fill_used": False, "retroactive_capture_used": False, "outcome_accessed": False}
        result_bytes = canonical_json_bytes(result)
        result_sha = sha256_bytes(result_bytes)
        snapshot_key = self.snapshot_key(session, slot, snapshot_sha)
        result_key = self.result_key(session, slot, result_sha)
        payload = self._expected_slot_payload(session=session, slot=slot, status=status, snapshot_sha=snapshot_sha, snapshot_key=snapshot_key, result_sha=result_sha, result_key=result_key, code_identity=code_identity, eod_manifest_sha256=eod_manifest_sha256, session_manifest_sha256=session_manifest_sha256)
        if claim_sha256 is not None:
            payload["claim_sha256"] = str(claim_sha256).lower()
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
        if payload.get("schema_version") != POLICY_SCHEMA_VERSION or payload.get("session_date") != session or not isinstance(payload.get("policy"), dict):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_INVALID")
        manifest_sha = str(payload.get("session_manifest_sha256") or "")
        if len(manifest_sha) != 64:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_MANIFEST_SHA_INVALID")
        return payload

    def latest_policy_checkpoint(self, session_dates: Sequence[str], *, before_or_equal: str | date) -> dict[str, Any] | None:
        boundary = _session(before_or_equal)
        candidates = sorted({str(value) for value in session_dates if str(value) <= boundary})
        for session in reversed(candidates):
            checkpoint = self.load_policy_checkpoint(session)
            if checkpoint is not None:
                return checkpoint
        return None

    def commit_policy_checkpoint(self, *, session_date: str | date, session_manifest_sha256: str, policy: Mapping[str, Any]) -> dict[str, Any]:
        session = _session(session_date)
        if len(str(session_manifest_sha256)) != 64:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_SESSION_MANIFEST_SHA_INVALID")
        payload = {"schema_version": POLICY_SCHEMA_VERSION, "session_date": session, "session_manifest_sha256": str(session_manifest_sha256).lower(), "policy": dict(policy)}
        encoded = canonical_json_bytes(payload)
        key = self.policy_key(session)
        self.store.put_if_absent(key, encoded, "application/json")
        confirmed = self.load_policy_checkpoint(session)
        if confirmed is None or canonical_json_bytes(confirmed) != encoded:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_POLICY_READBACK_MISMATCH")
        return confirmed
