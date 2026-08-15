"""Narrow, evidence-backed helpers for the bounded LBRE remediation lane.

These helpers intentionally do not infer a missing current-month value from a
previous-month column.  They only accept the exact two-column values visible in
the labelled free-float summary and deterministic correction markers in official
announcement identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


_SHARE_LABELS = (
    "Jumlah saham Free Float",
    "The amount of Free Float Share",
)
_LISTED_LABELS = (
    "Jumlah saham tercatat di Bursa per akhir bulan",
    "The number of shares listed on the Exchange at the end of the",
)
_PERCENT_LABELS = (
    "% Saham Free Float",
    "% Free Float Share",
)
_SHARE_TOKEN = re.compile(r"(?<![\w(])-?\d{1,3}(?:\.\d{3})+(?![\w.,])|(?<![\w(])-?\d+(?![\w.,])")
_PERCENT_TOKEN = re.compile(r"(?<!\w)\d+(?:[,.]\d+)?(?!\w)")


@dataclass(frozen=True)
class LbreCurrentFields:
    free_float_shares: int
    free_float_pct: float
    total_listed_shares: int
    evidence_locations: tuple[str, ...]


@dataclass(frozen=True)
class LbreParseResult:
    fields: LbreCurrentFields | None
    status: str
    diagnostics: tuple[str, ...]


def classify_revision_kind(
    announcement_no: str,
    title: str,
    declared_revision_kind: str,
) -> str:
    """Respect explicit official correction markers before metadata defaults."""

    marker_text = f"{announcement_no} {title}".upper()
    if "KOREKSI" in marker_text or "CORRECTION" in marker_text:
        return "CORRECTION"
    return declared_revision_kind


def _label_lines(text: str, labels: Iterable[str]) -> list[tuple[int, str]]:
    wanted = tuple(labels)
    return [
        (line_no, line)
        for line_no, line in enumerate(text.splitlines(), start=1)
        if any(line.lstrip().startswith(label) for label in wanted)
    ]


def _current_values(
    lines: Iterable[tuple[int, str]], *, percent: bool
) -> tuple[list[float | int], list[str], list[str]]:
    values: list[float | int] = []
    locations: list[str] = []
    diagnostics: list[str] = []
    token_re = _PERCENT_TOKEN if percent else _SHARE_TOKEN
    for line_no, line in lines:
        tail = line.lstrip()
        tokens = token_re.findall(tail)
        if len(tokens) != 2:
            diagnostics.append(f"line_{line_no}_does_not_expose_two_columns")
            continue
        try:
            if percent:
                parsed = [float(token.replace(",", ".")) for token in tokens]
            else:
                parsed = [int(token.replace(".", "")) for token in tokens]
        except ValueError:
            diagnostics.append(f"line_{line_no}_number_format_ambiguous")
            continue
        values.append(parsed[1])
        locations.append(f"line:{line_no}")
    return values, locations, diagnostics


def _one_consistent_current(
    values: list[float | int], *, field: str
) -> tuple[float | int | None, str | None]:
    if not values:
        return None, f"{field}_current_value_missing"
    if len(set(values)) != 1:
        return None, f"{field}_current_value_conflict"
    return values[0], None


def parse_lbre_current_fields(text: str) -> LbreParseResult:
    """Parse only an explicit current value from the report's summary table.

    A single visible value is treated as the previous-column value because the
    report layout does not establish that it is current.  Narrative lines such
    as ``Saham Free Float menjadi ...`` are deliberately ignored; they are not
    allowed to override the labelled summary table.
    """

    share_values, share_locations, share_diagnostics = _current_values(
        _label_lines(text, _SHARE_LABELS), percent=False
    )
    listed_values, listed_locations, listed_diagnostics = _current_values(
        _label_lines(text, _LISTED_LABELS), percent=False
    )
    pct_values, pct_locations, pct_diagnostics = _current_values(
        _label_lines(text, _PERCENT_LABELS), percent=True
    )
    diagnostics = [
        *share_diagnostics,
        *listed_diagnostics,
        *pct_diagnostics,
    ]
    shares, share_error = _one_consistent_current(share_values, field="free_float_shares")
    listed, listed_error = _one_consistent_current(listed_values, field="total_listed_shares")
    pct, pct_error = _one_consistent_current(pct_values, field="free_float_pct")
    diagnostics.extend(error for error in (share_error, listed_error, pct_error) if error)
    if shares is None or listed is None or pct is None:
        return LbreParseResult(None, "UNRESOLVED", tuple(diagnostics))
    if shares < 0 or listed <= 0 or shares > listed or not 0.0 <= pct <= 100.0:
        return LbreParseResult(None, "UNRESOLVED", (*diagnostics, "invalid_exact_contract"))

    return LbreParseResult(
        LbreCurrentFields(
            free_float_shares=int(shares),
            free_float_pct=float(pct),
            total_listed_shares=int(listed),
            evidence_locations=tuple(
                [*share_locations, *listed_locations, *pct_locations]
            ),
        ),
        "EXACT",
        tuple(diagnostics),
    )
