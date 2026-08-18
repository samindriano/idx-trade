"""Attest completeness and byte identity of the frozen Stage-2 KSEI corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


EXPECTED_MANIFEST_SHA = "5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c"
EXPECTED_REQUEST_SHA = "96a7a2d6013f6a6f86bc7548c9cda90514eb03a50d9b56039ec15c07969f6155"
EXPECTED_PARSE_AUDIT_SHA = "d7ded2bf29ad8355ff7ce22af89004a4bbe7e7fd0bb01524f582be2ad1e4e796"
EXPECTED_CANDIDATE_DOCUMENTS = 100
EXPECTED_STATUS = "V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"STAGE2_ATTEST_REQUIRED_FILE_MISSING:{label}:{path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"STAGE2_ATTEST_HASH_MISMATCH:{label}:{actual}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _norm_url(value: Any) -> str:
    return str(value or "").strip()


def _resolve_recorded_path(stage2_root: Path, value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_file():
        return path
    fallback = stage2_root / "raw" / "documents" / path.name
    if fallback.is_file():
        return fallback
    return None


def attest_stage2_raw_corpus(stage2_root: Path) -> dict[str, Any]:
    manifest_path = stage2_root / "MANIFEST.json"
    summary_path = stage2_root / "summary.json"
    request_path = stage2_root / "request_records.jsonl"
    parse_path = stage2_root / "schedule_document_parse_audit.csv"

    verify(manifest_path, EXPECTED_MANIFEST_SHA, "manifest")
    verify(request_path, EXPECTED_REQUEST_SHA, "request_records")
    verify(parse_path, EXPECTED_PARSE_AUDIT_SHA, "schedule_document_parse_audit")
    if not summary_path.is_file():
        raise RuntimeError("STAGE2_ATTEST_SUMMARY_MISSING")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest.get("status") != EXPECTED_STATUS or summary.get("status") != EXPECTED_STATUS:
        raise RuntimeError("STAGE2_ATTEST_STATUS_INVALID")
    if summary.get("outcome_blind") is not True or summary.get("source_substitution") is not False:
        raise RuntimeError("STAGE2_ATTEST_PROTECTION_FLAGS_INVALID")
    if int(summary.get("candidate_documents") or -1) != EXPECTED_CANDIDATE_DOCUMENTS:
        raise RuntimeError("STAGE2_ATTEST_CANDIDATE_COUNT_CHANGED")

    parse = pd.read_csv(parse_path, dtype=str).fillna("")
    if len(parse) != EXPECTED_CANDIDATE_DOCUMENTS:
        raise RuntimeError(f"STAGE2_ATTEST_PARSE_ROW_COUNT_CHANGED:{len(parse)}")
    if parse["source_url"].eq("").any() or parse["source_url"].duplicated().any():
        raise RuntimeError("STAGE2_ATTEST_PARSE_URL_IDENTITY_INVALID")

    requests = read_jsonl(request_path)
    document_requests = [
        row for row in requests if str(row.get("request_kind")) == "SCHEDULE_DOCUMENT"
    ]
    by_url: dict[str, list[dict[str, Any]]] = {}
    for row in document_requests:
        for candidate in {
            _norm_url(row.get("requested_url")),
            _norm_url(row.get("final_url")),
        }:
            if candidate:
                by_url.setdefault(candidate, []).append(row)

    successful = 0
    provider_failed = 0
    verified_raw_paths: set[str] = set()
    for row in parse.to_dict("records"):
        url = _norm_url(row.get("source_url"))
        attempts = by_url.get(url, [])
        if not attempts:
            raise RuntimeError(f"STAGE2_ATTEST_DOCUMENT_REQUEST_MISSING:{url}")
        success_attempts = [
            attempt
            for attempt in attempts
            if int(attempt.get("status_code") or 0) == 200
            and int(attempt.get("bytes") or 0) > 0
            and str(attempt.get("sha256") or "")
        ]
        parse_status = str(row.get("parse_status") or "")
        if success_attempts:
            if parse_status == "UNRESOLVED_PROVIDER":
                raise RuntimeError(f"STAGE2_ATTEST_PROVIDER_STATUS_CONTRADICTION:{url}")
            distinct_shas = {str(attempt.get("sha256")) for attempt in success_attempts}
            if len(distinct_shas) != 1:
                raise RuntimeError(f"STAGE2_ATTEST_SUCCESS_SHA_CONFLICT:{url}")
            expected_sha = next(iter(distinct_shas))
            paths = [
                path
                for attempt in success_attempts
                if (path := _resolve_recorded_path(stage2_root, attempt.get("path"))) is not None
            ]
            if not paths:
                raise RuntimeError(f"STAGE2_ATTEST_SUCCESS_RAW_MISSING:{url}")
            actual_shas = {sha256(path) for path in paths}
            if actual_shas != {expected_sha}:
                raise RuntimeError(f"STAGE2_ATTEST_SUCCESS_RAW_SHA_MISMATCH:{url}:{sorted(actual_shas)}")
            parse_sha = str(row.get("source_sha256") or "")
            if parse_sha != expected_sha:
                raise RuntimeError(f"STAGE2_ATTEST_PARSE_SOURCE_SHA_MISMATCH:{url}")
            verified_raw_paths.update(str(path.resolve()) for path in paths)
            successful += 1
        else:
            if parse_status != "UNRESOLVED_PROVIDER":
                raise RuntimeError(f"STAGE2_ATTEST_MISSING_SUCCESS_FOR_PARSED_DOCUMENT:{url}:{parse_status}")
            provider_failed += 1

    if successful + provider_failed != EXPECTED_CANDIDATE_DOCUMENTS:
        raise RuntimeError("STAGE2_ATTEST_ACCOUNTING_FAILURE")

    return {
        "status": "V4_CA_STAGE2_RAW_CORPUS_ATTESTED",
        "candidate_documents": EXPECTED_CANDIDATE_DOCUMENTS,
        "successful_documents": successful,
        "provider_failed_documents": provider_failed,
        "verified_raw_file_paths": len(verified_raw_paths),
        "provider_calls": False,
        "outcome_blind": True,
        "source_substitution": False,
        "manifest_sha256": EXPECTED_MANIFEST_SHA,
        "request_records_sha256": EXPECTED_REQUEST_SHA,
        "parse_audit_sha256": EXPECTED_PARSE_AUDIT_SHA,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage2-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = attest_stage2_raw_corpus(args.stage2_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
