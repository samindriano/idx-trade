from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

from .security_master import normalise_ticker


OFFICIAL_IDX_HOST_SUFFIXES = ("idx.co.id", "idx.id")
SOURCE_STATUSES = {"READY_FOR_ACQUISITION", "DISCOVERY_REQUIRED"}
REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "source_type",
    "announcement_ref",
    "announced_at",
    "effective_from",
    "status",
    "download_url",
}
REQUIRED_EVENT_COLUMNS = {
    "ticker",
    "sector_code",
    "effective_from",
    "announced_at",
    "source_id",
    "source_sha256",
}
REQUIRED_EFFECTIVE_DATE_EVIDENCE_FIELDS = {
    "source_id",
    "source_type",
    "announcement_ref",
    "announced_at",
    "effective_from",
    "download_url",
    "source_sha256",
    "bytes",
    "content_type",
    "linkage",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def is_official_idx_url(url: str) -> bool:
    parsed = urlparse(str(url).strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in OFFICIAL_IDX_HOST_SUFFIXES)


def load_source_inventory(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("PIT sector source inventory must contain a top-level sources list")
    return payload


def _parse_optional_date(value: Any, *, source_id: str, field: str) -> pd.Timestamp | None:
    if value is None or str(value).strip() == "":
        return None
    result = pd.Timestamp(value).normalize()
    if pd.isna(result):
        raise ValueError(f"invalid {field} for {source_id}")
    return result


def validate_effective_date_evidence(source: dict[str, Any]) -> dict[str, Any] | None:
    """Validate a second, official IDX document that dates a canonical event.

    The canonical source remains authoritative for the classification change.
    This nested evidence may establish the effective date only when it is an
    official IDX document, hash-pinned, and explicitly linked to the same
    canonical source and affected ticker(s).

    Supporting evidence may be published after the effective date. In that
    case the historical event is valid, but it is not PIT-knowable until the
    supporting evidence is published. ``knowledge_at`` captures that boundary.
    """

    raw = source.get("effective_date_evidence")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"effective_date_evidence must be an object: {source.get('source_id')}")

    missing = REQUIRED_EFFECTIVE_DATE_EVIDENCE_FIELDS - set(raw)
    if missing:
        raise ValueError(
            f"effective-date evidence missing fields for {source.get('source_id')}: {sorted(missing)}"
        )

    canonical_source_id = str(source.get("source_id") or "").strip()
    canonical_ref = str(source.get("announcement_ref") or "").strip()
    evidence_id = str(raw["source_id"]).strip()
    evidence_ref = str(raw["announcement_ref"]).strip()
    if not evidence_id or evidence_id == canonical_source_id:
        raise ValueError(f"effective-date evidence must have a distinct source_id: {canonical_source_id}")
    if not evidence_ref:
        raise ValueError(f"effective-date evidence has empty announcement_ref: {canonical_source_id}")

    canonical_announced_at = _parse_optional_date(
        source.get("announced_at"), source_id=canonical_source_id, field="announced_at"
    )
    evidence_announced_at = _parse_optional_date(
        raw.get("announced_at"), source_id=evidence_id, field="announced_at"
    )
    evidence_effective_from = _parse_optional_date(
        raw.get("effective_from"), source_id=evidence_id, field="effective_from"
    )
    if canonical_announced_at is None:
        raise ValueError(f"canonical announced_at must be explicit: {canonical_source_id}")
    if evidence_announced_at is None or evidence_effective_from is None:
        raise ValueError(f"effective-date evidence lacks explicit dates: {canonical_source_id}")

    canonical_effective_from = _parse_optional_date(
        source.get("effective_from"), source_id=canonical_source_id, field="effective_from"
    )
    if canonical_effective_from is None:
        raise ValueError(f"canonical effective_from must be explicit: {canonical_source_id}")
    if canonical_effective_from != evidence_effective_from:
        raise ValueError(f"canonical/evidence effective dates disagree: {canonical_source_id}")

    knowledge_at = max(canonical_effective_from, canonical_announced_at, evidence_announced_at)

    download_url = str(raw.get("download_url") or "").strip()
    if not is_official_idx_url(download_url):
        raise ValueError(f"effective-date evidence URL is not official IDX HTTPS: {canonical_source_id}")

    source_sha256 = str(raw.get("source_sha256") or "").strip().lower()
    if not pd.Series([source_sha256]).str.fullmatch(r"[0-9a-f]{64}").iloc[0]:
        raise ValueError(f"effective-date evidence source_sha256 is not 64-hex: {canonical_source_id}")
    if not isinstance(raw.get("bytes"), int) or raw["bytes"] <= 0:
        raise ValueError(f"effective-date evidence bytes must be positive: {canonical_source_id}")
    if not str(raw.get("content_type") or "").strip():
        raise ValueError(f"effective-date evidence content_type is empty: {canonical_source_id}")

    linkage = raw.get("linkage")
    if not isinstance(linkage, dict):
        raise ValueError(f"effective-date evidence linkage must be an object: {canonical_source_id}")
    if str(linkage.get("canonical_source_id") or "").strip() != canonical_source_id:
        raise ValueError(f"effective-date evidence canonical source linkage mismatch: {canonical_source_id}")
    if str(linkage.get("canonical_announcement_ref") or "").strip() != canonical_ref:
        raise ValueError(f"effective-date evidence canonical ref linkage mismatch: {canonical_source_id}")
    linked_tickers = linkage.get("linked_tickers")
    if not isinstance(linked_tickers, list) or not linked_tickers:
        raise ValueError(f"effective-date evidence must list linked_tickers: {canonical_source_id}")
    normalised_tickers = [normalise_ticker(ticker) for ticker in linked_tickers]
    if any(not ticker for ticker in normalised_tickers):
        raise ValueError(f"effective-date evidence contains an empty ticker: {canonical_source_id}")
    if not str(linkage.get("classification_change") or "").strip():
        raise ValueError(f"effective-date evidence lacks classification_change: {canonical_source_id}")
    if not str(linkage.get("linkage_statement") or "").strip():
        raise ValueError(f"effective-date evidence lacks linkage_statement: {canonical_source_id}")

    linked_canonical_sha256 = str(linkage.get("canonical_source_sha256") or "").strip().lower()
    canonical_raw_sha256 = str((source.get("raw_attachment") or {}).get("sha256") or "").strip().lower()
    if linked_canonical_sha256:
        if not pd.Series([linked_canonical_sha256]).str.fullmatch(r"[0-9a-f]{64}").iloc[0]:
            raise ValueError(f"effective-date evidence canonical_source_sha256 is not 64-hex: {canonical_source_id}")
        if canonical_raw_sha256 and linked_canonical_sha256 != canonical_raw_sha256:
            raise ValueError(f"effective-date evidence canonical hash linkage mismatch: {canonical_source_id}")

    return {
        "source_id": evidence_id,
        "announcement_ref": evidence_ref,
        "announced_at": evidence_announced_at,
        "effective_from": evidence_effective_from,
        "knowledge_at": knowledge_at,
        "download_url": download_url,
        "source_sha256": source_sha256,
        "linked_tickers": normalised_tickers,
    }


def validate_source_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source inventory must contain at least one source")

    seen: set[str] = set()
    blockers: list[dict[str, str]] = []
    ready = 0
    for raw in sources:
        if not isinstance(raw, dict):
            raise ValueError("every source inventory row must be an object")
        missing = REQUIRED_SOURCE_FIELDS - set(raw)
        if missing:
            raise ValueError(f"source row missing fields: {sorted(missing)}")

        source_id = str(raw["source_id"]).strip()
        if not source_id or source_id in seen:
            raise ValueError(f"duplicate or empty source_id: {source_id!r}")
        seen.add(source_id)

        status = str(raw["status"]).strip()
        if status not in SOURCE_STATUSES:
            raise ValueError(f"unsupported source status for {source_id}: {status}")

        announced_at = _parse_optional_date(raw.get("announced_at"), source_id=source_id, field="announced_at")
        effective_from = _parse_optional_date(
            raw.get("effective_from"), source_id=source_id, field="effective_from"
        )
        validate_effective_date_evidence(raw)
        url = str(raw.get("download_url") or "").strip()

        if status == "READY_FOR_ACQUISITION":
            if announced_at is None or effective_from is None:
                raise ValueError(f"READY source lacks verified announced/effective date: {source_id}")
            if not url:
                raise ValueError(f"READY source has no download_url: {source_id}")
            if not is_official_idx_url(url):
                raise ValueError(f"READY source URL is not official IDX HTTPS: {source_id}")
            ready += 1
        else:
            blockers.append({"source_id": source_id, "reason": "DISCOVERY_REQUIRED"})

    return {
        "schema_version": payload.get("schema_version"),
        "sources_total": len(sources),
        "sources_ready": ready,
        "sources_blocked": len(blockers),
        "complete_for_acquisition": not blockers,
        "blockers": blockers,
        "effective_date_evidence_validated": sum(
            validate_effective_date_evidence(source) is not None for source in sources
        ),
    }


def _download_one(
    url: str,
    *,
    session: requests.Session,
    timeout: tuple[float, float] = (10.0, 60.0),
    max_redirects: int = 5,
) -> tuple[bytes, str, str | None]:
    current = url
    for _ in range(max_redirects + 1):
        if not is_official_idx_url(current):
            raise RuntimeError(f"non-official IDX URL rejected: {current}")
        response = session.get(current, allow_redirects=False, timeout=timeout)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                raise RuntimeError(f"redirect without Location from {current}")
            current = urljoin(current, location)
            continue
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code} while acquiring {current}")
        payload = bytes(response.content)
        if not payload:
            raise RuntimeError(f"empty response while acquiring {current}")
        return payload, current, response.headers.get("Content-Type")
    raise RuntimeError(f"too many redirects while acquiring {url}")


def acquire_official_sources(
    inventory: dict[str, Any],
    *,
    output_dir: str | Path,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    audit = validate_source_inventory(inventory)
    if not audit["complete_for_acquisition"]:
        raise RuntimeError("source inventory incomplete; discovery blockers must be resolved before acquisition")

    destination = Path(output_dir)
    raw_dir = destination / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    entries: list[dict[str, Any]] = []

    for source in inventory["sources"]:
        source_id = str(source["source_id"])
        payload, final_url, content_type = _download_one(str(source["download_url"]), session=client)
        expected_sha256 = str((source.get("raw_attachment") or {}).get("sha256") or "").strip().lower()
        raw_sha256 = _sha256_bytes(payload)
        if expected_sha256 and raw_sha256 != expected_sha256:
            raise RuntimeError(f"canonical raw SHA-256 mismatch for {source_id}")
        suffix = Path(urlparse(final_url).path).suffix or ".bin"
        target = raw_dir / f"{source_id}{suffix}"
        _atomic_write_bytes(target, payload)
        entry = {
            "source_id": source_id,
            "source_type": source["source_type"],
            "announcement_ref": source["announcement_ref"],
            "announced_at": str(source["announced_at"]),
            "effective_from": str(source["effective_from"]),
            "requested_url": source["download_url"],
            "final_url": final_url,
            "content_type": content_type,
            "retrieved_at_utc": _utc_now(),
            "raw_file": target.name,
            "raw_sha256": raw_sha256,
            "bytes": len(payload),
        }

        effective_date_evidence = validate_effective_date_evidence(source)
        if effective_date_evidence is not None:
            evidence = source["effective_date_evidence"]
            evidence_payload, evidence_final_url, evidence_content_type = _download_one(
                str(evidence["download_url"]), session=client
            )
            evidence_sha256 = _sha256_bytes(evidence_payload)
            if evidence_sha256 != effective_date_evidence["source_sha256"]:
                raise RuntimeError(f"effective-date evidence SHA-256 mismatch for {source_id}")
            evidence_suffix = Path(urlparse(evidence_final_url).path).suffix or ".bin"
            evidence_target = raw_dir / f"{source_id}__effective_date_evidence{evidence_suffix}"
            _atomic_write_bytes(evidence_target, evidence_payload)
            entry["effective_date_evidence"] = {
                "source_id": effective_date_evidence["source_id"],
                "announcement_ref": effective_date_evidence["announcement_ref"],
                "announced_at": str(effective_date_evidence["announced_at"]),
                "effective_from": str(effective_date_evidence["effective_from"]),
                "knowledge_at": str(effective_date_evidence["knowledge_at"]),
                "requested_url": evidence["download_url"],
                "final_url": evidence_final_url,
                "content_type": evidence_content_type,
                "retrieved_at_utc": _utc_now(),
                "raw_file": evidence_target.name,
                "raw_sha256": evidence_sha256,
                "bytes": len(evidence_payload),
            }
        entries.append(entry)

    manifest = {
        "status": "PIT_SECTOR_OFFICIAL_SOURCE_ACQUISITION_COMPLETE",
        "source_count": len(entries),
        "entries": entries,
    }
    _atomic_write_json(destination / "source_manifest.json", manifest)
    return manifest


def normalise_sector_events(events: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_EVENT_COLUMNS - set(events.columns)
    if missing:
        raise ValueError(f"sector event table missing columns: {sorted(missing)}")

    data = events.copy()
    if data["ticker"].isna().any() or data["sector_code"].isna().any():
        raise ValueError("ticker and sector_code must not be null")
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["sector_code"] = data["sector_code"].astype(str).str.strip().str.upper()
    data["effective_from"] = pd.to_datetime(data["effective_from"], errors="raise").dt.normalize()
    data["announced_at"] = pd.to_datetime(data["announced_at"], errors="raise").dt.normalize()
    if "knowledge_at" not in data.columns:
        data["knowledge_at"] = data["announced_at"]
    else:
        data["knowledge_at"] = pd.to_datetime(data["knowledge_at"], errors="raise").dt.normalize()
    if data["knowledge_at"].isna().any():
        raise ValueError("knowledge_at must not be null when provided")
    data["pit_from"] = data[["effective_from", "announced_at", "knowledge_at"]].max(axis=1)

    if data["ticker"].eq("").any() or data["sector_code"].eq("").any():
        raise ValueError("ticker and sector_code must be non-empty")
    valid_sha = data["source_sha256"].astype(str).str.fullmatch(r"[0-9a-fA-F]{64}").fillna(False)
    if not bool(valid_sha.all()):
        raise ValueError("every sector event must carry a 64-hex source_sha256")

    key = ["ticker", "effective_from"]
    conflicts = (
        data.groupby(key, dropna=False)["sector_code"].nunique(dropna=False).reset_index(name="sector_count")
    )
    if conflicts["sector_count"].gt(1).any():
        bad = conflicts.loc[conflicts["sector_count"].gt(1), key].to_dict(orient="records")
        raise ValueError(f"conflicting sector events for same ticker/effective date: {bad}")

    data = data.sort_values(
        ["ticker", "effective_from", "announced_at", "knowledge_at", "source_id"], kind="mergesort"
    )
    data = data.drop_duplicates(key + ["sector_code"], keep="first").reset_index(drop=True)

    # The current interval/as-of implementation assumes that PIT knowledge
    # boundaries preserve the same order as classification effective dates.
    # A late-discovered older event must never be allowed to override a newer
    # already-known classification. Fail closed on that rare topology until a
    # dedicated two-dimensional state resolver is explicitly implemented.
    pit_backstep = data.groupby("ticker", sort=False)["pit_from"].diff().lt(pd.Timedelta(0))
    if bool(pit_backstep.any()):
        bad = data.loc[pit_backstep, ["ticker", "effective_from", "pit_from", "source_id"]].to_dict(
            orient="records"
        )
        raise ValueError(f"non-monotonic PIT knowledge order for effective-date sequence: {bad}")

    return data


def materialize_sector_intervals(events: pd.DataFrame) -> pd.DataFrame:
    data = normalise_sector_events(events)
    data["effective_to"] = data.groupby("ticker")["effective_from"].shift(-1) - pd.Timedelta(days=1)
    data["pit_to"] = data.groupby("ticker")["pit_from"].shift(-1) - pd.Timedelta(days=1)
    return data


def attach_sector_asof(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    *,
    ticker_column: str = "ticker",
    date_column: str = "date",
) -> pd.DataFrame:
    if ticker_column not in signals.columns or date_column not in signals.columns:
        raise ValueError("signals must contain ticker/date columns")

    left = signals.copy()
    left[ticker_column] = left[ticker_column].map(normalise_ticker)
    left[date_column] = pd.to_datetime(left[date_column], errors="raise").dt.normalize()
    left["__row_order"] = range(len(left))

    right = normalise_sector_events(events).rename(columns={"ticker": ticker_column})
    keep = [
        ticker_column,
        "pit_from",
        "sector_code",
        "effective_from",
        "announced_at",
        "knowledge_at",
        "source_id",
        "source_sha256",
    ]
    for optional in ("subsector_code", "industry_code", "subindustry_code"):
        if optional in right.columns:
            keep.append(optional)

    left_sorted = left.sort_values([date_column, ticker_column], kind="mergesort")
    right_sorted = right[keep].sort_values(["pit_from", ticker_column], kind="mergesort")
    merged = pd.merge_asof(
        left_sorted,
        right_sorted,
        left_on=date_column,
        right_on="pit_from",
        by=ticker_column,
        direction="backward",
        allow_exact_matches=True,
    )
    merged["sector_pit_known"] = merged["sector_code"].notna()
    merged = merged.sort_values("__row_order", kind="mergesort").drop(columns=["__row_order"])
    return merged.reset_index(drop=True)


def audit_inventory_file(path: str | Path) -> dict[str, Any]:
    inventory = load_source_inventory(path)
    return validate_source_inventory(inventory)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PIT historical IDX-IC sector source foundation")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--acquire", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    inventory = load_source_inventory(args.inventory)
    audit = validate_source_inventory(inventory)
    if not args.acquire:
        print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if not args.output_dir:
        raise SystemExit("--output-dir is required with --acquire")
    result = acquire_official_sources(inventory, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
