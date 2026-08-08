from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .providers.idx_stock_summary import (
    fetch_stock_summary_payload,
    parse_stock_summary_payload,
    stock_summary_status_to_anchors,
)


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_csv(temp, index=False)
    temp.replace(path)


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)


def run_stock_summary_status_audit(
    date: str | pd.Timestamp,
    output_dir: str | Path,
    *,
    status_mapping: dict[str, str] | None = None,
) -> dict[str, object]:
    """Probe official IDX Stock Summary for explicit tradability-status evidence.

    Runtime market rows stay outside Git. The report records schema/status
    availability and never interprets `Remarks`, price, volume, or row presence
    as ACTIVE. Anchors are emitted only when an explicit audited status mapping
    is supplied by the caller.
    """

    output_dir = Path(output_dir)
    payload, source_ref = fetch_stock_summary_payload(date)
    frame, meta = parse_stock_summary_payload(
        payload,
        requested_date=date,
        source_ref=source_ref,
    )

    raw_rows = payload.get("data")
    raw_field_names = sorted(
        {
            str(key)
            for row in raw_rows
            if isinstance(row, dict)
            for key in row.keys()
        }
    ) if isinstance(raw_rows, list) else []
    status_like_fields = [
        name for name in raw_field_names if "status" in name.lower()
    ]

    anchors = pd.DataFrame()
    diagnostics = pd.DataFrame()
    if status_mapping is not None:
        anchors, diagnostics = stock_summary_status_to_anchors(
            frame,
            status_mapping=status_mapping,
        )

    report = {
        **meta.to_dict(),
        "raw_field_names": raw_field_names,
        "status_like_fields": status_like_fields,
        "status_mapping_supplied": status_mapping is not None,
        "anchor_rows": int(len(anchors)),
        "unresolved_status_rows": int(len(diagnostics)),
        "status": (
            "EXPLICIT_STATUS_AVAILABLE"
            if meta.explicit_security_status_rows > 0
            else "NO_EXPLICIT_STATUS_FIELD"
        ),
        "decision": (
            "Eligible for audited status-mapping review; do not promote anchors until values are verified."
            if meta.explicit_security_status_rows > 0 and status_mapping is None
            else (
                "Anchors created only from caller-supplied audited mappings."
                if status_mapping is not None
                else "Do not use this source as ACTIVE evidence; find another authoritative source."
            )
        ),
    }

    _atomic_csv(frame, output_dir / "idx_stock_summary_status_probe.csv")
    _atomic_csv(anchors, output_dir / "idx_stock_summary_anchors.csv")
    _atomic_csv(diagnostics, output_dir / "idx_stock_summary_status_diagnostics.csv")
    _atomic_json(report, output_dir / "idx_stock_summary_status_audit.json")
    return report
