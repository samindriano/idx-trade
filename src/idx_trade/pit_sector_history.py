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
        suffix = Path(urlparse(final_url).path).suffix or ".bin"
        target = raw_dir / f"{source_id}{suffix}"
        _atomic_write_bytes(target, payload)
        entries.append(
            {
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
                "raw_sha256": _sha256_bytes(payload),
                "bytes": len(payload),
            }
        )

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
    data["pit_from"] = data[["effective_from", "announced_at"]].max(axis=1)

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

    data = data.sort_values(["ticker", "effective_from", "announced_at", "source_id"], kind="mergesort")
    data = data.drop_duplicates(key + ["sector_code"], keep="first").reset_index(drop=True)
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
