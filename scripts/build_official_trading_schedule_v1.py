"""Build a hash-bound planned IDX trading schedule from a reviewed Bursa calendar.

This tool does not discover holidays.  The operator supplies holiday dates
reviewed from the official source document; the tool copies and hashes that
source, derives weekday sessions deterministically, and writes one immutable
attestation suitable for the live PAPER runtime.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.official_trading_schedule_v1 import (
    AUTHORITY,
    DERIVATION,
    SCHEMA_VERSION,
    SEMANTICS,
    derive_planned_sessions,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"immutable output conflict: {path}")
        return
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp.write_bytes(encoded)
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-document", type=Path, required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--coverage-start", required=True)
    parser.add_argument("--coverage-end", required=True)
    parser.add_argument("--holiday", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.source_document.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"source document missing: {source}")
    source_reference = str(args.source_reference).strip()
    if not source_reference:
        raise SystemExit("source reference is required")

    sessions = derive_planned_sessions(
        coverage_start=args.coverage_start,
        coverage_end=args.coverage_end,
        holiday_dates=list(args.holiday),
    )
    holidays = tuple(sorted(str(value).strip() for value in args.holiday))
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_copy = output / f"official_source{source.suffix.lower() or '.bin'}"
    if source_copy.exists():
        if _sha256(source_copy) != _sha256(source):
            raise SystemExit(f"immutable source conflict: {source_copy}")
    elif source != source_copy:
        shutil.copyfile(source, source_copy)

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "semantics": SEMANTICS,
        "derivation": DERIVATION,
        "source_reference": source_reference,
        "source_document_path": source_copy.name,
        "source_document_sha256": _sha256(source_copy),
        "coverage_start": args.coverage_start,
        "coverage_end": args.coverage_end,
        "holiday_dates": list(holidays),
        "session_dates": list(sessions),
        "built_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "outcome_access": False,
    }
    payload["payload_sha256"] = _canonical_hash(payload)
    target = output / "execution_schedule_attestation.json"
    _atomic_json(target, payload)
    print(
        json.dumps(
            {
                "status": "EXECUTION_SCHEDULE_READY",
                "attestation_path": str(target),
                "attestation_sha256": _sha256(target),
                "source_document_sha256": _sha256(source_copy),
                "sessions": len(sessions),
                "first_session": sessions[0],
                "last_session": sessions[-1],
                "outcome_access": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
