from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Mapping

from .official_trading_schedule_v1 import (
    VerifiedOfficialTradingSchedule,
    load_verified_official_trading_schedule,
)
from .stockbit_intraday_eod_context import (
    VerifiedIntradayEodContext,
    load_verified_intraday_eod_context,
)


ACCEPTED_E2E_IMPLEMENTATION_SHA = "043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2"
DEFAULT_E2E_PREFIX = "e2e-paper-v1"
DEFAULT_INPUT_MANIFEST_KEY = "inputs/manifest.json"
_PASSTHROUGH_ENV = (
    "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "LANG", "LC_ALL", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
)


class StockbitIntradayE2EBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class MaterializedE2EContext:
    schedule: VerifiedOfficialTradingSchedule
    eod: VerifiedIntradayEodContext | None
    input_manifest_sha256: str
    post_eod_commit_sha256: str | None


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_GIT_HEAD_UNAVAILABLE")
    return completed.stdout.strip().lower()


def _git_status(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_GIT_STATUS_UNAVAILABLE")
    return completed.stdout.strip()


def validate_accepted_e2e_checkout(root: str | Path) -> Path:
    accepted = Path(root).expanduser().resolve()
    if not accepted.is_dir():
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_ROOT_MISSING")
    if _git_head(accepted) != ACCEPTED_E2E_IMPLEMENTATION_SHA:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_HEAD_MISMATCH")
    if _git_status(accepted):
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_WORKTREE_DIRTY")
    module = accepted / "src" / "idx_trade" / "e2e_paper_cloud_runtime_v1.py"
    if not module.is_file():
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_CLOUD_MODULE_MISSING")
    return accepted


def _child_env(values: Mapping[str, str], accepted: Path) -> dict[str, str]:
    del accepted
    required = (
        "STOCKBIT_INTRADAY_S3_ENDPOINT",
        "STOCKBIT_INTRADAY_S3_BUCKET",
        "STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID",
        "STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY",
    )
    missing = [name for name in required if not str(values.get(name, "")).strip()]
    if missing:
        raise StockbitIntradayE2EBridgeError(
            "STOCKBIT_INTRADAY_E2E_BRIDGE_STORAGE_ENV_MISSING:" + ",".join(missing)
        )
    e2e_prefix = str(values.get("STOCKBIT_INTRADAY_E2E_PREFIX", DEFAULT_E2E_PREFIX)).strip("/")
    if e2e_prefix != DEFAULT_E2E_PREFIX:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_PREFIX_INVALID")
    child = {
        name: str(values[name])
        for name in _PASSTHROUGH_ENV
        if name in values and str(values[name]).strip()
    }
    child["E2E_CLOUD_STORAGE_BACKEND"] = "s3"
    child["E2E_CLOUD_S3_ENDPOINT"] = str(values["STOCKBIT_INTRADAY_S3_ENDPOINT"]).strip()
    child["E2E_CLOUD_S3_BUCKET"] = str(values["STOCKBIT_INTRADAY_S3_BUCKET"]).strip()
    child["E2E_CLOUD_S3_ACCESS_KEY_ID"] = str(values["STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID"]).strip()
    child["E2E_CLOUD_S3_SECRET_ACCESS_KEY"] = str(values["STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY"]).strip()
    child["E2E_CLOUD_STORAGE_PREFIX"] = DEFAULT_E2E_PREFIX
    return child


def _safe_manifest_key(value: object) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_INPUT_MANIFEST_KEY_INVALID")
    return str(path)


def _require_within(path: Path, root: Path, *, label: str) -> Path:
    target = path.expanduser().resolve()
    boundary = root.expanduser().resolve()
    if target != boundary and boundary not in target.parents:
        raise StockbitIntradayE2EBridgeError(f"{label}_OUTSIDE_MATERIALIZATION_ROOT")
    return target


_CHILD_CODE = r'''
from __future__ import annotations
import json
from pathlib import Path
import sys
accepted_src = Path(sys.argv[4]).resolve()
sys.path.insert(0, str(accepted_src))
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    CloudInputBundle, CloudPaperArchive, build_cloud_store_from_env,
    load_schedule_from_bundle, restore_runtime_snapshot,
)
class ReadOnlyStore:
    def __init__(self, inner):
        self.inner = inner
    def read(self, key):
        return self.inner.read(key)
    def put_if_absent(self, key, payload, content_type):
        raise RuntimeError("STOCKBIT_INTRADAY_E2E_BRIDGE_WRITE_FORBIDDEN")
session = sys.argv[1]
root = Path(sys.argv[2]).resolve()
manifest_key = sys.argv[3]
root.mkdir(parents=True, exist_ok=True)
store = ReadOnlyStore(build_cloud_store_from_env())
bundle = CloudInputBundle.load(store, manifest_key)
roles = bundle.materialize(store, root / "inputs")
schedule = load_schedule_from_bundle(bundle, roles)
result = {
    "input_manifest_sha256": bundle.manifest_sha256,
    "schedule_path": str(roles["execution_schedule"]),
    "schedule_sha256": schedule.attestation_sha256,
    "schedule_coverage_start": schedule.coverage_start,
    "schedule_coverage_end": schedule.coverage_end,
    "scheduled_session": session in schedule.session_dates,
    "eod_available": False,
    "post_eod_commit_sha256": None,
    "eod_session_dir": None,
    "read_only_store_guard": True,
}
if session in schedule.session_dates:
    archive = CloudPaperArchive(store)
    commit = archive.existing_commit(session, "POST_EOD")
    if commit is not None:
        if commit.snapshot_key is None or commit.snapshot_sha256 is None:
            raise RuntimeError("POST_EOD_SNAPSHOT_REFERENCE_MISSING")
        raw = store.read(commit.snapshot_key)
        if raw is None:
            raise RuntimeError("POST_EOD_SNAPSHOT_MISSING")
        roots = {
            "paper": root / "e2e" / "paper",
            "forward": root / "e2e" / "forward",
            "official_open": root / "e2e" / "official_open",
            "ca": root / "e2e" / "ca",
        }
        restore_runtime_snapshot(raw, roots, expected_sha256=commit.snapshot_sha256)
        result["eod_available"] = True
        result["post_eod_commit_sha256"] = commit.commit_sha256
        result["eod_session_dir"] = str(roots["forward"] / "forward_monitoring" / "sessions" / session)
print(json.dumps(result, sort_keys=True))
'''


def materialize_accepted_e2e_context(
    *, accepted_runtime_root: str | Path, output_root: str | Path,
    session_date: date, env: Mapping[str, str] | None = None,
) -> MaterializedE2EContext:
    accepted = validate_accepted_e2e_checkout(accepted_runtime_root)
    destination = Path(output_root).expanduser().resolve()
    values = dict(os.environ if env is None else env)
    child_env = _child_env(values, accepted)
    manifest_key = _safe_manifest_key(
        values.get("STOCKBIT_INTRADAY_E2E_INPUT_MANIFEST_KEY", DEFAULT_INPUT_MANIFEST_KEY)
    )
    completed = subprocess.run(
        [
            sys.executable, "-I", "-c", _CHILD_CODE,
            session_date.isoformat(), str(destination), manifest_key, str(accepted / "src"),
        ],
        cwd=str(accepted), env=child_env, check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise StockbitIntradayE2EBridgeError(
            f"STOCKBIT_INTRADAY_ACCEPTED_E2E_BRIDGE_FAILED:exit={completed.returncode}"
        )
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_BRIDGE_OUTPUT_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("read_only_store_guard") is not True:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_BRIDGE_OUTPUT_INVALID")

    schedule_path = _require_within(
        Path(str(payload.get("schedule_path") or "")), destination / "inputs",
        label="STOCKBIT_INTRADAY_E2E_SCHEDULE_PATH",
    )
    schedule_sha = str(payload.get("schedule_sha256") or "").strip().lower()
    schedule = load_verified_official_trading_schedule(schedule_path, expected_sha256=schedule_sha)
    if (
        schedule.coverage_start != payload.get("schedule_coverage_start")
        or schedule.coverage_end != payload.get("schedule_coverage_end")
        or (session_date.isoformat() in schedule.session_dates) is not bool(payload.get("scheduled_session"))
    ):
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_SCHEDULE_CROSSCHECK_FAILED")

    eod: VerifiedIntradayEodContext | None = None
    commit_sha: str | None = None
    if payload.get("eod_available") is True:
        raw_dir = str(payload.get("eod_session_dir") or "").strip()
        commit_sha = str(payload.get("post_eod_commit_sha256") or "").strip().lower()
        if not raw_dir or len(commit_sha) != 64:
            raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_EOD_REFERENCE_INVALID")
        session_dir = _require_within(
            Path(raw_dir), destination / "e2e" / "forward",
            label="STOCKBIT_INTRADAY_E2E_EOD_SESSION_DIR",
        )
        if not session_dir.is_dir():
            raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_EOD_SESSION_DIR_MISSING")
        eod = load_verified_intraday_eod_context(session_dir, expected_date=session_date)
    elif payload.get("eod_available") is not False:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_EOD_AVAILABILITY_INVALID")

    manifest_sha = str(payload.get("input_manifest_sha256") or "").strip().lower()
    if len(manifest_sha) != 64:
        raise StockbitIntradayE2EBridgeError("STOCKBIT_INTRADAY_E2E_INPUT_MANIFEST_SHA_INVALID")
    return MaterializedE2EContext(
        schedule=schedule, eod=eod, input_manifest_sha256=manifest_sha,
        post_eod_commit_sha256=commit_sha,
    )
