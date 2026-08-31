"""Offline fail-closed validator for a future licensed CA vendor sample.

This is an audit utility, not a provider client and not a production gate. It
reads a local sample directory and validates the minimum evidence contract
identified by the INC-001 source-authority reconnaissance. No network,
credentials, outcome data, or runtime state is touched.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FILES = ("scope.csv", "coverage.csv", "snapshot.csv", "final_snapshot.csv", "deltas.csv")
SCOPE_COLUMNS = {"identity_id", "event_family", "interval_start", "interval_end"}
COVERAGE_COLUMNS = {
    "identity_id",
    "event_family",
    "interval_start",
    "interval_end",
    "coverage_status",
    "knowledge_asof",
    "observed_through",
    "source_ref",
    "source_sha256",
}
EVENT_COLUMNS = {
    "identity_id",
    "event_id",
    "event_family",
    "version",
    "announcement_time",
    "effective_date",
    "source_ref",
    "source_sha256",
}
DELTA_COLUMNS = {
    "sequence",
    "op",
    "event_id",
    "identity_id",
    "event_family",
    "version",
    "previous_version",
    "announcement_time",
    "effective_date",
    "source_ref",
    "source_sha256",
}
EVENT_KEYS = (
    "identity_id",
    "event_id",
    "event_family",
    "version",
    "announcement_time",
    "effective_date",
    "source_ref",
    "source_sha256",
)


class VendorSampleContractError(ValueError):
    """Raised when a sample is missing or violates an admission contract."""


def _fail(message: str) -> None:
    raise VendorSampleContractError(message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip().lower()))


def _read_csv(root: Path, filename: str, *, allow_empty: bool = False) -> list[dict[str, str]]:
    path = root / filename
    if not path.is_file():
        _fail(f"MISSING_FILE:{filename}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            _fail(f"EMPTY_FILE:{filename}")
        rows = list(reader)
    if not rows and not allow_empty:
        _fail(f"EMPTY_FILE:{filename}")
    return [{str(key): "" if value is None else str(value).strip() for key, value in row.items()} for row in rows]


def _csv_columns(root: Path, filename: str) -> set[str]:
    path = root / filename
    with path.open(encoding="utf-8-sig", newline="") as handle:
        columns = next(csv.reader(handle), [])
    return {str(column).strip() for column in columns if str(column).strip()}


def _require_columns(
    rows: Sequence[Mapping[str, str]], required: set[str], filename: str, *, columns: set[str] | None = None
) -> None:
    columns = columns if columns is not None else (set(rows[0]) if rows else set())
    missing = required - columns
    if missing:
        _fail(f"MISSING_COLUMNS:{filename}:{','.join(sorted(missing))}")


def _aware_timestamp(value: str, label: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        _fail(f"MISSING_TIMESTAMP:{label}")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail(f"MALFORMED_TIMESTAMP:{label}:{raw}")
    if parsed.tzinfo is None:
        _fail(f"NAIVE_TIMESTAMP:{label}:{raw}")
    return parsed.astimezone(timezone.utc)


def _iso_date(value: str, label: str) -> date:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        _fail(f"MALFORMED_DATE:{label}:{raw}")


def _nonempty(value: str, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        _fail(f"MISSING_VALUE:{label}")
    return result


def _positive_int(value: str, label: str) -> int:
    try:
        parsed = int(str(value).strip())
    except ValueError:
        _fail(f"MALFORMED_INTEGER:{label}:{value}")
    if parsed < 1:
        _fail(f"NONPOSITIVE_INTEGER:{label}:{value}")
    return parsed


def _manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        _fail("MISSING_FILE:manifest.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"MALFORMED_MANIFEST:{exc}")
    if not isinstance(value, dict):
        _fail("MALFORMED_MANIFEST:object_required")
    required = {
        "schema_version",
        "source_id",
        "source_version",
        "coverage_start",
        "coverage_end",
        "observed_through",
        "knowledge_asof",
        "coverage_complete",
        "scope_sha256",
        "scope_row_count",
        "coverage_sha256",
        "coverage_row_count",
        "snapshot_sha256",
        "snapshot_row_count",
        "final_snapshot_sha256",
        "final_snapshot_row_count",
        "deltas_sha256",
        "deltas_row_count",
    }
    missing = required - set(value)
    if missing:
        _fail(f"MANIFEST_MISSING_FIELDS:{','.join(sorted(missing))}")
    if str(value["schema_version"]) != "INC001_VENDOR_SAMPLE_CONTRACT_V1":
        _fail("UNSUPPORTED_MANIFEST_SCHEMA")
    if value["coverage_complete"] is not True:
        _fail("COVERAGE_NOT_EXPLICITLY_COMPLETE")
    _nonempty(str(value["source_id"]), "manifest.source_id")
    _nonempty(str(value["source_version"]), "manifest.source_version")
    coverage_start = _iso_date(str(value["coverage_start"]), "manifest.coverage_start")
    coverage_end = _iso_date(str(value["coverage_end"]), "manifest.coverage_end")
    if coverage_start > coverage_end:
        _fail("MANIFEST_COVERAGE_START_AFTER_END")
    observed_through = _aware_timestamp(str(value["observed_through"]), "manifest.observed_through")
    knowledge_asof = _aware_timestamp(str(value["knowledge_asof"]), "manifest.knowledge_asof")
    if knowledge_asof > observed_through:
        _fail("KNOWLEDGE_ASOF_AFTER_OBSERVED_THROUGH")
    for filename in REQUIRED_FILES:
        expected_hash = str(value[f"{filename.removesuffix('.csv')}_sha256"] or "").lower()
        if not _valid_sha(expected_hash):
            _fail(f"MALFORMED_MANIFEST_HASH:{filename}")
        try:
            expected_rows = int(str(value[f"{filename.removesuffix('.csv')}_row_count"]).strip())
        except ValueError:
            _fail(f"MALFORMED_INTEGER:manifest.{filename}.row_count")
        if expected_rows < 0:
            _fail(f"NEGATIVE_INTEGER:manifest.{filename}.row_count")
        path = root / filename
        actual_hash = _sha256_file(path) if path.is_file() else ""
        if actual_hash != expected_hash:
            _fail(f"MANIFEST_HASH_MISMATCH:{filename}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            actual_rows = max(sum(1 for _ in handle) - 1, 0)
        if actual_rows != expected_rows:
            _fail(f"MANIFEST_ROW_COUNT_MISMATCH:{filename}:{actual_rows}!={expected_rows}")
    return value


def _provenance(row: Mapping[str, str], label: str) -> None:
    _nonempty(row.get("source_ref", ""), f"{label}.source_ref")
    if not _valid_sha(row.get("source_sha256", "")):
        _fail(f"MALFORMED_SOURCE_SHA:{label}")


def _scope_and_coverage(root: Path, manifest: Mapping[str, Any]) -> tuple[set[tuple[str, str, date, date]], list[dict[str, str]]]:
    scope = _read_csv(root, "scope.csv")
    coverage = _read_csv(root, "coverage.csv")
    _require_columns(scope, SCOPE_COLUMNS, "scope.csv")
    _require_columns(coverage, COVERAGE_COLUMNS, "coverage.csv")
    expected: set[tuple[str, str, date, date]] = set()
    for index, row in enumerate(scope, start=1):
        identity = _nonempty(row["identity_id"], f"scope[{index}].identity_id")
        family = _nonempty(row["event_family"], f"scope[{index}].event_family")
        start = _iso_date(row["interval_start"], f"scope[{index}].interval_start")
        end = _iso_date(row["interval_end"], f"scope[{index}].interval_end")
        if start > end:
            _fail(f"SCOPE_INTERVAL_REVERSED:{index}")
        key = (identity, family, start, end)
        if key in expected:
            _fail(f"DUPLICATE_SCOPE_UNIT:{identity}:{family}:{start}:{end}")
        expected.add(key)
    manifest_asof = _aware_timestamp(str(manifest["knowledge_asof"]), "manifest.knowledge_asof")
    observed = _aware_timestamp(str(manifest["observed_through"]), "manifest.observed_through")
    seen: set[tuple[str, str, date, date]] = set()
    for index, row in enumerate(coverage, start=1):
        identity = _nonempty(row["identity_id"], f"coverage[{index}].identity_id")
        family = _nonempty(row["event_family"], f"coverage[{index}].event_family")
        start = _iso_date(row["interval_start"], f"coverage[{index}].interval_start")
        end = _iso_date(row["interval_end"], f"coverage[{index}].interval_end")
        key = (identity, family, start, end)
        if key in seen:
            _fail(f"DUPLICATE_COVERAGE_UNIT:{identity}:{family}:{start}:{end}")
        seen.add(key)
        if key not in expected:
            _fail(f"COVERAGE_UNIT_NOT_IN_SCOPE:{identity}:{family}:{start}:{end}")
        status = row["coverage_status"].upper()
        if status not in {"EVENTS_PRESENT", "NO_EVENT"}:
            _fail(f"NONEXPLICIT_COVERAGE_STATUS:{index}:{status}")
        unit_asof = _aware_timestamp(row["knowledge_asof"], f"coverage[{index}].knowledge_asof")
        unit_observed = _aware_timestamp(row["observed_through"], f"coverage[{index}].observed_through")
        if unit_asof > manifest_asof or unit_asof > unit_observed or unit_observed > observed:
            _fail(f"TEMPORAL_COVERAGE_BOUNDARY_INVALID:{index}")
        _provenance(row, f"coverage[{index}]")
    if seen != expected:
        _fail(f"SCOPE_COVERAGE_SET_MISMATCH:missing={len(expected-seen)}:extra={len(seen-expected)}")
    return expected, coverage


def _event_rows(root: Path, filename: str) -> list[dict[str, str]]:
    rows = _read_csv(root, filename)
    _require_columns(rows, EVENT_COLUMNS, filename)
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        event_id = _nonempty(row["event_id"], f"{filename}[{index}].event_id")
        if event_id in seen:
            _fail(f"DUPLICATE_EVENT_ID:{filename}:{event_id}")
        seen.add(event_id)
        _nonempty(row["identity_id"], f"{filename}[{index}].identity_id")
        _nonempty(row["event_family"], f"{filename}[{index}].event_family")
        version = _positive_int(row["version"], f"{filename}[{index}].version")
        if version < 1:
            _fail(f"INVALID_EVENT_VERSION:{filename}:{index}")
        _aware_timestamp(row["announcement_time"], f"{filename}[{index}].announcement_time")
        _iso_date(row["effective_date"], f"{filename}[{index}].effective_date")
        _provenance(row, f"{filename}[{index}]")
    return rows


def _replay_and_validate(
    root: Path,
    snapshot: Sequence[Mapping[str, str]],
    final_snapshot: Sequence[Mapping[str, str]],
    manifest: Mapping[str, Any],
) -> int:
    deltas = _read_csv(root, "deltas.csv", allow_empty=True)
    _require_columns(deltas, DELTA_COLUMNS, "deltas.csv", columns=_csv_columns(root, "deltas.csv"))
    max_knowledge = _aware_timestamp(str(manifest["knowledge_asof"]), "manifest.knowledge_asof")
    for row in list(snapshot) + list(final_snapshot):
        if _aware_timestamp(row["announcement_time"], "event.announcement_time") > max_knowledge:
            _fail("EVENT_PUBLISHED_AFTER_KNOWLEDGE_ASOF")
    state: dict[str, dict[str, str]] = {str(row["event_id"]): dict(row) for row in snapshot}
    sequences: set[int] = set()
    ordered: list[tuple[int, dict[str, str]]] = []
    input_sequences: list[int] = []
    for index, raw in enumerate(deltas, start=1):
        sequence = _positive_int(raw["sequence"], f"deltas[{index}].sequence")
        if sequence in sequences:
            _fail(f"DUPLICATE_DELTA_SEQUENCE:{sequence}")
        sequences.add(sequence)
        input_sequences.append(sequence)
        row = dict(raw)
        event_id = _nonempty(row["event_id"], f"deltas[{index}].event_id")
        identity = _nonempty(row["identity_id"], f"deltas[{index}].identity_id")
        family = _nonempty(row["event_family"], f"deltas[{index}].event_family")
        op = row["op"].upper()
        if op not in {"I", "U", "D"}:
            _fail(f"INVALID_DELTA_OP:{index}:{op}")
        version = _positive_int(row["version"], f"deltas[{index}].version")
        previous = row["previous_version"].strip()
        announcement_time = _aware_timestamp(row["announcement_time"], f"deltas[{index}].announcement_time")
        if announcement_time > max_knowledge:
            _fail("EVENT_PUBLISHED_AFTER_KNOWLEDGE_ASOF")
        _iso_date(row["effective_date"], f"deltas[{index}].effective_date")
        _provenance(row, f"deltas[{index}]")
        row["op"] = op
        ordered.append((sequence, row))
    if input_sequences != list(range(1, len(input_sequences) + 1)):
        _fail("DELTA_SEQUENCE_NOT_CONTIGUOUS_OR_ORDERED")
    for index, (_, row) in enumerate(ordered, start=1):
        event_id = row["event_id"]
        op = row["op"]
        current = state.get(event_id)
        previous = row["previous_version"].strip()
        version = int(row["version"])
        if op == "I":
            if current is not None or previous or version != 1:
                _fail(f"INVALID_DELTA_INSERT:{index}")
        elif current is None or previous != str(current["version"]) or version <= int(current["version"]):
            _fail(f"INVALID_DELTA_PRECONDITION:{index}")
        elif row["identity_id"] != current["identity_id"] or row["event_family"] != current["event_family"]:
            _fail(f"INVALID_DELTA_IDENTITY_LINEAGE:{index}")
        if op == "D":
            state.pop(event_id, None)
        else:
            state[event_id] = {key: row[key] for key in EVENT_KEYS}
    final = {str(row["event_id"]): dict(row) for row in final_snapshot}
    if set(state) != set(final):
        _fail(f"DELTA_REPLAY_EVENT_SET_MISMATCH:state={len(state)}:final={len(final)}")
    for event_id, row in final.items():
        actual = state[event_id]
        for key in EVENT_KEYS:
            if str(actual[key]) != str(row[key]):
                _fail(f"DELTA_REPLAY_VALUE_MISMATCH:{event_id}:{key}")
    return len(deltas)


def _validate_event_scope(
    rows: Sequence[Mapping[str, str]],
    expected: set[tuple[str, str, date, date]],
    units_with_events: set[tuple[str, str, date, date]],
    coverage_asof: Mapping[tuple[str, str, date, date], datetime],
    label: str,
) -> None:
    for row in rows:
        event_date = _iso_date(row["effective_date"], f"{label}.effective_date")
        matches = [
            unit
            for unit in expected
            if unit[0] == row["identity_id"]
            and unit[1] == row["event_family"]
            and unit[2] <= event_date <= unit[3]
        ]
        if not matches:
            _fail(f"EVENT_OUTSIDE_DECLARED_SCOPE:{row['event_id']}")
        if any(unit not in units_with_events for unit in matches):
            _fail(f"EVENT_IN_NO_EVENT_UNIT:{row['event_id']}")
        announcement = _aware_timestamp(row["announcement_time"], f"{label}.announcement_time")
        if any(announcement > coverage_asof[unit] for unit in matches):
            _fail(f"EVENT_PUBLISHED_AFTER_COVERAGE_ASOF:{row['event_id']}")


def validate_sample(root: Path) -> dict[str, Any]:
    """Validate a local sample and return a deterministic summary."""

    root = Path(root).resolve()
    if not root.is_dir():
        _fail(f"MISSING_SAMPLE_ROOT:{root}")
    manifest = _manifest(root)
    expected, coverage = _scope_and_coverage(root, manifest)
    snapshot = _event_rows(root, "snapshot.csv")
    final_snapshot = _event_rows(root, "final_snapshot.csv")
    delta_count = _replay_and_validate(root, snapshot, final_snapshot, manifest)
    units_with_events = {
        (row["identity_id"], row["event_family"], _iso_date(row["interval_start"], "coverage.interval_start"), _iso_date(row["interval_end"], "coverage.interval_end"))
        for row in coverage
        if row["coverage_status"].upper() == "EVENTS_PRESENT"
    }
    coverage_asof = {
        (row["identity_id"], row["event_family"], _iso_date(row["interval_start"], "coverage.interval_start"), _iso_date(row["interval_end"], "coverage.interval_end")): _aware_timestamp(row["knowledge_asof"], "coverage.knowledge_asof")
        for row in coverage
    }
    _validate_event_scope(snapshot, expected, units_with_events, coverage_asof, "snapshot")
    _validate_event_scope(final_snapshot, expected, units_with_events, coverage_asof, "final_snapshot")
    for unit in expected:
        has_event = any(
            row["identity_id"] == unit[0]
            and row["event_family"] == unit[1]
            and unit[2] <= _iso_date(row["effective_date"], "final_snapshot.effective_date") <= unit[3]
            for row in final_snapshot
        )
        declared = unit in units_with_events
        if has_event != declared:
            _fail(f"EVENT_COVERAGE_POLARITY_MISMATCH:{unit[0]}:{unit[1]}")
    return {
        "status": "PASS",
        "schema_version": str(manifest["schema_version"]),
        "source_id": str(manifest["source_id"]),
        "source_version": str(manifest["source_version"]),
        "scope_units": len(expected),
        "coverage_units": len(coverage),
        "snapshot_events": len(snapshot),
        "final_snapshot_events": len(final_snapshot),
        "delta_rows": delta_count,
        "explicit_no_event_units": sum(row["coverage_status"].upper() == "NO_EVENT" for row in coverage),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_root", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate_sample(args.sample_root), indent=2, sort_keys=True))
    except VendorSampleContractError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
