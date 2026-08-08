from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .providers.idx_stock_summary import (
    fetch_stock_summary_payload,
    parse_stock_summary_payload,
    stock_summary_regular_trade_anchors,
    stock_summary_status_to_anchors,
)
from .security_master import canonicalize_tradability_anchors


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
    """Audit official Stock Summary for defensible per-ticker state anchors.

    Positive Regular-Market transaction evidence may create ACTIVE anchors.
    Explicit status values may additionally create anchors only through a
    caller-supplied audited mapping. `Remarks`, mere row presence, and zero
    trading activity never imply ACTIVE.
    """

    output_dir = Path(output_dir)
    payload, source_ref = fetch_stock_summary_payload(date)
    frame, meta = parse_stock_summary_payload(
        payload,
        requested_date=date,
        source_ref=source_ref,
    )

    raw_rows = payload.get("data")
    raw_field_names = (
        sorted(
            {
                str(key)
                for row in raw_rows
                if isinstance(row, dict)
                for key in row.keys()
            }
        )
        if isinstance(raw_rows, list)
        else []
    )
    status_like_fields = [
        name for name in raw_field_names if "status" in name.lower()
    ]

    trade_anchors, trade_diagnostics = stock_summary_regular_trade_anchors(frame)
    status_anchors = pd.DataFrame()
    status_diagnostics = pd.DataFrame()
    if status_mapping is not None:
        status_anchors, status_diagnostics = stock_summary_status_to_anchors(
            frame,
            status_mapping=status_mapping,
        )

    anchor_parts = [part for part in (trade_anchors, status_anchors) if not part.empty]
    anchors = (
        canonicalize_tradability_anchors(
            pd.concat(anchor_parts, ignore_index=True)
        )
        if anchor_parts
        else canonicalize_tradability_anchors(pd.DataFrame())
    )

    report = {
        **meta.to_dict(),
        "raw_field_names": raw_field_names,
        "status_like_fields": status_like_fields,
        "status_mapping_supplied": status_mapping is not None,
        "regular_trade_anchor_rows": int(len(trade_anchors)),
        "explicit_status_anchor_rows": int(len(status_anchors)),
        "anchor_rows": int(len(anchors)),
        "regular_trade_unresolved_rows": int(len(trade_diagnostics)),
        "explicit_status_unresolved_rows": int(len(status_diagnostics)),
        "explicit_status_probe": (
            "EXPLICIT_STATUS_AVAILABLE"
            if meta.explicit_security_status_rows > 0
            else "NO_EXPLICIT_STATUS_FIELD"
        ),
        "decision": (
            "Use Regular-Market transaction anchors now; explicit status values need audited mapping before use."
            if len(trade_anchors) > 0 and status_mapping is None
            else (
                "Use only emitted anchors; all unresolved rows remain UNKNOWN."
                if len(anchors) > 0
                else "No authoritative ACTIVE/status anchor was proven by this snapshot."
            )
        ),
    }

    _atomic_csv(frame, output_dir / "idx_stock_summary_status_probe.csv")
    _atomic_csv(anchors, output_dir / "idx_stock_summary_anchors.csv")
    _atomic_csv(
        trade_diagnostics,
        output_dir / "idx_stock_summary_regular_trade_diagnostics.csv",
    )
    _atomic_csv(
        status_diagnostics,
        output_dir / "idx_stock_summary_status_diagnostics.csv",
    )
    _atomic_json(report, output_dir / "idx_stock_summary_status_audit.json")
    return report
