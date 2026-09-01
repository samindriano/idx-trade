"""Provider-free early completion probe for the canonical Intraday archive.

The probe is only a read-only storage adapter around
``StockbitIntradayCloudArchive.existing_complete_slot``. It deliberately does
not import the capture runner, install project dependencies, or call a
market-data provider. Missing completion is a normal result; malformed or
conflicting existing evidence fails closed.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.stockbit_intraday_cloud_archive import (  # noqa: E402
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)


JAKARTA = ZoneInfo("Asia/Jakarta")
PREFIX = "stockbit-intraday-v1"


class CompletionProbeError(RuntimeError):
    pass


def _safe_key(value: Any, label: str) -> str:
    key = str(value or "").replace("\\", "/")
    if not key or key.startswith("/") or any(part in {"", ".", ".."} for part in key.split("/")):
        raise CompletionProbeError(f"{label}_KEY_INVALID")
    return key


class ReadOnlyObjectStore:
    """Read-only CloudObjectStore adapter for local tests or AWS CLI/R2."""

    def __init__(self, args: argparse.Namespace, temp_root: Path) -> None:
        self.temp_root = temp_root
        self.local_root = Path(args.local_root).expanduser().resolve() if args.local_root else None
        if args.storage_prefix.strip("/") != PREFIX:
            raise CompletionProbeError("STOCKBIT_INTRADAY_STORAGE_PREFIX_INVALID")
        if self.local_root is None:
            self.aws = args.aws_exe or shutil.which("aws")
            if not self.aws:
                raise CompletionProbeError("AWS_CLI_REQUIRED_FOR_EARLY_COMPLETION_CHECK")
            for name in ("STOCKBIT_INTRADAY_S3_ENDPOINT", "STOCKBIT_INTRADAY_S3_BUCKET"):
                if not os.environ.get(name, "").strip():
                    raise CompletionProbeError(f"{name}_REQUIRED")

    def read(self, key: str) -> bytes | None:
        relative_key = _safe_key(key, "ARCHIVE")
        full_key = f"{PREFIX}/{relative_key}"
        if self.local_root is not None:
            path = self.local_root.joinpath(*relative_key.split("/"))
            return path.read_bytes() if path.is_file() else None

        output = self.temp_root / hashlib.sha256(full_key.encode("utf-8")).hexdigest()
        command = [
            self.aws,
            "s3api",
            "get-object",
            "--bucket",
            os.environ["STOCKBIT_INTRADAY_S3_BUCKET"].strip(),
            "--key",
            full_key,
            "--endpoint-url",
            os.environ["STOCKBIT_INTRADAY_S3_ENDPOINT"].strip(),
            str(output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            error = f"{completed.stdout}\n{completed.stderr}".lower()
            if "nosuchkey" in error or "not found" in error or "404" in error:
                return None
            raise CompletionProbeError("STOCKBIT_INTRADAY_COMPLETION_STORAGE_READ_FAILED")
        try:
            return output.read_bytes()
        except OSError as exc:
            raise CompletionProbeError("STOCKBIT_INTRADAY_COMPLETION_READBACK_FAILED") from exc

    def put_if_absent(self, key: str, payload: bytes, content_type: str):
        del key, payload, content_type
        raise CompletionProbeError("STOCKBIT_INTRADAY_COMPLETION_READ_ONLY")

    def list_keys(self, prefix: str) -> list[str]:
        del prefix
        return []


# Kept as a narrow compatibility name for local tests and reviewers.
ObjectReader = ReadOnlyObjectStore


def validate_completion(
    reader: ReadOnlyObjectStore,
    *,
    session: str,
    slot: str,
    expected_code_ref: str | None = None,
) -> dict[str, Any]:
    """Validate only the existing canonical archive completion.

    ``expected_code_ref`` is accepted for callers from the first draft but is
    intentionally not used: a valid durable observation remains complete when
    a later documentation-only main commit changes the workflow SHA.
    """

    del expected_code_ref
    try:
        commit = StockbitIntradayCloudArchive(reader).existing_complete_slot(session, slot)
    except StockbitIntradayCloudError as exc:
        raise CompletionProbeError(str(exc)) from exc
    if commit is None:
        return {"status": "NOT_COMPLETE", "capture_complete": False, "provider_calls": 0}

    return {
        "status": "COMPLETE",
        "capture_complete": True,
        "completion_grain": "session_recovery_objective",
        "session_date": commit.session_date,
        "slot": commit.slot,
        "commit_key": commit.commit_key,
        "commit_sha256": commit.commit_sha256,
        "eod_manifest_sha256": commit.payload["eod_manifest_sha256"],
        "session_manifest_sha256": commit.payload["session_manifest_sha256"],
        "provider_calls": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-date", default="")
    parser.add_argument("--slot", choices=("1830", "1930", "2030"), required=True)
    parser.add_argument("--local-root")
    parser.add_argument("--storage-prefix", default=PREFIX)
    parser.add_argument("--aws-exe")
    args = parser.parse_args(argv)
    session = args.session_date or datetime.now(JAKARTA).date().isoformat()
    try:
        with tempfile.TemporaryDirectory(prefix="idx-trade-completion-check-") as temp:
            result = validate_completion(
                ReadOnlyObjectStore(args, Path(temp)),
                session=session,
                slot=args.slot,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CompletionProbeError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "capture_complete": False, "provider_calls": 0, "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
