from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.forward_price_trend_state import (
    MANIFEST_FILENAME,
    _context_fingerprint,
    produce_session_price_trend_state,
)
from idx_trade.forward_price_trend_state_verifier import (
    verify_prospective_price_trend_state_strict,
)
from idx_trade.provenance import sha256_file


def _write_calendar(path: Path, sessions: pd.DatetimeIndex) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": sessions}).to_csv(path, index=False)
    return sha256_file(path)


def _write_canonical_source(
    runtime: Path,
    source: pd.Timestamp,
    forward_calendar: Path,
) -> Path:
    key = source.date().isoformat()
    directory = runtime / "forward_monitoring" / "sessions" / key
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "date": [source],
            "high": [106.05],
            "low": [103.95],
            "close": [105.0],
            "volume": [2_000_000.0],
            "regular_market_value": [10_000_000_000.0],
        }
    )
    snapshot_path = directory / "model_input.parquet"
    snapshot.to_parquet(snapshot_path, index=False)
    manifest = {
        "status": "DATA_READY",
        "session_date": key,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "snapshot_path": str(snapshot_path.resolve()),
        "snapshot_sha256": sha256_file(snapshot_path),
        "calendar_path": str(forward_calendar.resolve()),
        "calendar_sha256": sha256_file(forward_calendar),
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _fixture(tmp_path: Path) -> dict[str, object]:
    historical_sessions = pd.bdate_range(end="2025-04-03", periods=80)
    closes = np.full(len(historical_sessions), 100.0)
    history = pd.DataFrame(
        {
            "ticker": "TEST",
            "date": historical_sessions,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": 1_000_000.0,
        }
    )
    historical_panel = tmp_path / "historical.parquet"
    history.to_parquet(historical_panel, index=False)
    historical_calendar = tmp_path / "historical_calendar.csv"
    historical_calendar_sha = _write_calendar(historical_calendar, historical_sessions)

    source = pd.Timestamp("2025-04-04")
    target = pd.Timestamp("2025-04-07")
    forward_sessions = pd.DatetimeIndex([source, target])
    forward_calendar = tmp_path / "forward_calendar.csv"
    forward_calendar_sha = _write_calendar(forward_calendar, forward_sessions)

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    parent_manifest = _write_canonical_source(runtime, source, forward_calendar)

    result = produce_session_price_trend_state(
        runtime_root=runtime,
        source_session=source,
        historical_panel_path=historical_panel,
        historical_panel_sha256=sha256_file(historical_panel),
        historical_calendar_path=historical_calendar,
        historical_calendar_sha256=historical_calendar_sha,
        forward_calendar_path=forward_calendar,
        forward_calendar_sha256=forward_calendar_sha,
    )
    manifest_path = Path(result["manifest_path"])
    return {
        "runtime": runtime,
        "source": source,
        "target": target,
        "manifest_path": manifest_path,
        "parent_manifest": parent_manifest,
        "forward_calendar": forward_calendar,
    }


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _refresh_fingerprint(manifest: dict[str, object]) -> None:
    provenance = manifest["input_provenance"]
    assert isinstance(provenance, dict)
    provenance["input_fingerprint"] = _context_fingerprint(
        {key: value for key, value in provenance.items() if key != "input_fingerprint"}
    )


def test_strict_verifier_accepts_fresh_artifact(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    assert verify_prospective_price_trend_state_strict(
        fixture["runtime"], fixture["target"]
    ) is True


def test_strict_verifier_rejects_output_schema_manifest_tamper(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    manifest = _load_manifest(fixture["manifest_path"])
    output_columns = list(manifest["output_columns"])
    manifest["output_columns"] = output_columns[:-1]
    _write_manifest(fixture["manifest_path"], manifest)

    assert verify_prospective_price_trend_state_strict(
        fixture["runtime"], fixture["target"]
    ) is False


def test_strict_verifier_rejects_state_distribution_tamper(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    manifest = _load_manifest(fixture["manifest_path"])
    distributions = manifest["state_distributions"]
    assert isinstance(distributions, dict)
    trend = distributions["trend_state"]
    assert isinstance(trend, dict)
    trend["UPTREND"] = int(trend.get("UPTREND", 0)) + 1
    _write_manifest(fixture["manifest_path"], manifest)

    assert verify_prospective_price_trend_state_strict(
        fixture["runtime"], fixture["target"]
    ) is False


def test_strict_verifier_rejects_parent_semantic_tamper_even_if_rehashed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    parent = _load_manifest(fixture["parent_manifest"])
    parent["status"] = "DATA_FAILED"
    _write_manifest(fixture["parent_manifest"], parent)

    manifest = _load_manifest(fixture["manifest_path"])
    provenance = manifest["input_provenance"]
    assert isinstance(provenance, dict)
    sources = provenance["forward_sources"]
    assert isinstance(sources, list) and len(sources) == 1
    sources[0]["parent_manifest_sha256"] = sha256_file(fixture["parent_manifest"])
    _refresh_fingerprint(manifest)
    _write_manifest(fixture["manifest_path"], manifest)

    assert verify_prospective_price_trend_state_strict(
        fixture["runtime"], fixture["target"]
    ) is False


def test_strict_verifier_recomputes_exact_next_official_session(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    # Insert a fake Saturday between the accepted Friday source and Monday
    # target, then consistently repin the calendar and parent bytes. A
    # hash-only verifier could accept this; semantic t->t+1 verification must not.
    revised_sessions = pd.DatetimeIndex(
        [fixture["source"], pd.Timestamp("2025-04-05"), fixture["target"]]
    )
    new_calendar_sha = _write_calendar(fixture["forward_calendar"], revised_sessions)

    parent = _load_manifest(fixture["parent_manifest"])
    parent["calendar_sha256"] = new_calendar_sha
    _write_manifest(fixture["parent_manifest"], parent)

    manifest = _load_manifest(fixture["manifest_path"])
    provenance = manifest["input_provenance"]
    assert isinstance(provenance, dict)
    provenance["forward_calendar_sha256"] = new_calendar_sha
    sources = provenance["forward_sources"]
    assert isinstance(sources, list) and len(sources) == 1
    sources[0]["parent_manifest_sha256"] = sha256_file(fixture["parent_manifest"])
    _refresh_fingerprint(manifest)
    _write_manifest(fixture["manifest_path"], manifest)

    assert verify_prospective_price_trend_state_strict(
        fixture["runtime"], fixture["target"]
    ) is False
