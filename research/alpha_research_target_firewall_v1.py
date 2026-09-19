"""Research-only target-access firewall for outcome-blind alpha artifacts.

The firewall checks code, schemas, and audit JSON metadata without opening any
protected target or outcome artifact. It is intentionally conservative: a
protected-looking path, network/provider access, forbidden output field, or
true access marker fails the audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pyarrow.parquet as pq


FORBIDDEN_PATH_PATTERNS = (
    r"outcome[_-]?vault",
    r"protected[_-]?(?:outcome|target|forward)",
    r"forward[_-]?(?:return|label|target|outcome)",
    r"prospective[_-]?outcome",
    r"paperstate",
    r"(?:^|[\\/])counter(?:[._-]|$)",
)
FORBIDDEN_IMPORT_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:import|from)\s+(?:requests|urllib|httpx|socket|boto3|cloudflare)\b"
)
FORBIDDEN_HTTP_PATTERN = re.compile(r"(?:requests\.|urllib\.|httpx\.|socket\.|boto3\.|cloudflare\.)")
FORBIDDEN_OUTPUT_TOKEN_PATTERN = re.compile(
    r"(?:^|_|-)(?:target|label|outcome|forward_return|realized_consensus|pnl|nav|sharpe)(?:$|_|-)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def path_is_forbidden(path: Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return any(re.search(pattern, text) for pattern in FORBIDDEN_PATH_PATTERNS)


def code_checks(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    return {
        "no_forbidden_path_literal": not any(
            re.search(pattern, text.replace("\\", "/").lower()) for pattern in FORBIDDEN_PATH_PATTERNS
        ),
        "no_network_import": not bool(FORBIDDEN_IMPORT_PATTERN.search(text)),
        "no_http_provider_call": not bool(FORBIDDEN_HTTP_PATTERN.search(text)),
    }


def schema_checks(path: Path) -> dict[str, bool]:
    columns = list(pq.ParquetFile(path).schema.names)
    return {
        "no_forbidden_output_columns": not any(
            FORBIDDEN_OUTPUT_TOKEN_PATTERN.search(str(column)) for column in columns
        ),
        "schema_non_empty": bool(columns),
    }


def text_checks(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    forbidden_payload_tokens = (
        "realized_return_value",
        "h5_values",
        "h10_values",
        "protected_target_payload",
    )
    return {
        "text_non_empty": bool(text.strip()),
        "no_protected_payload_tokens": not any(token in text.lower() for token in forbidden_payload_tokens),
        "no_forbidden_path_literal": not any(
            re.search(pattern, text.replace("\\", "/").lower())
            for pattern in FORBIDDEN_PATH_PATTERNS
        ),
    }


def json_checks(path: Path) -> dict[str, bool]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    for key in ("outcome_accessed", "target_accessed", "provider_accessed", "incumbent_score_accessed"):
        if key in payload:
            checks[f"{key}_false"] = payload[key] is False
    checks["no_forbidden_path_literal"] = not any(
        re.search(pattern, path.read_text(encoding="utf-8").replace("\\", "/").lower())
        for pattern in FORBIDDEN_PATH_PATTERNS
    )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", action="append", type=Path, default=[])
    parser.add_argument("--parquet", action="append", type=Path, default=[])
    parser.add_argument("--json", action="append", type=Path, default=[])
    parser.add_argument("--text", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checks: dict[str, bool] = {}
    records: dict[str, object] = {"code": {}, "parquet": {}, "json": {}, "text": {}}
    all_inputs = [*args.code, *args.parquet, *args.json, *args.text]
    checks["input_list_non_empty"] = bool(all_inputs)
    checks["no_forbidden_input_path"] = not any(path_is_forbidden(path) for path in all_inputs)

    for path in args.code:
        item = code_checks(path)
        records["code"][str(path)] = {"sha256": sha256_file(path), "checks": item}
        checks.update({f"code:{path.name}:{key}": value for key, value in item.items()})
    for path in args.parquet:
        item = schema_checks(path)
        records["parquet"][str(path)] = {"sha256": sha256_file(path), "checks": item}
        checks.update({f"parquet:{path.name}:{key}": value for key, value in item.items()})
    for path in args.json:
        item = json_checks(path)
        records["json"][str(path)] = {"sha256": sha256_file(path), "checks": item}
        checks.update({f"json:{path.name}:{key}": value for key, value in item.items()})
    for path in args.text:
        item = text_checks(path)
        records["text"][str(path)] = {"sha256": sha256_file(path), "checks": item}
        checks.update({f"text:{path.name}:{key}": value for key, value in item.items()})

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": "OUTCOME_BLIND_RESEARCH_FIREWALL",
        "checks": checks,
        "records": records,
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
