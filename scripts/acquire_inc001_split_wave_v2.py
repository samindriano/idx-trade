"""Acquire the explicitly authorized INC-001 split evidence wave.

This is a narrow, outcome-blind acquisition runner. It consumes the
controlling V4 residual ledger and retained KSEI index bytes, and fetches only
the exact official PDF hrefs already evidenced by those retained index pages:
HEAL, SCMA, and the one-event BBRM reverse-split probe. It never retries an
old request, downloads retained HTML again, calls IDX, or touches scientific
outcomes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


AUDIT_DATE = "2026-08-29"
SCHEMA = "inc001_stock_split_acquisition_v2"
V4_ROOT_NAME = "idx-ca-unresolved-economic-gap-decomposition-20260829-v4"
V4_MANIFEST_SHA256 = "3af6a92738f560f26699725e2f8cf6200dc1dff3fcc6a79d899cb9911d6499bc"
PRIOR_ACQUISITION_ROOT = Path(r"D:\Documents\Project\idx-ca-stock-split-acquisition-20260829-v1")
EXPECTED_SPLITS = 21
EXPECTED_REVERSE = 1
EXPECTED_TOTAL = EXPECTED_SPLITS + EXPECTED_REVERSE
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PDF_HREF_RE = re.compile(
    r'<a\s+href=["\']([^"\']+\.pdf)["\'][^>]*>\s*([^<]+?)\s*</a>\s*'
    r'</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',
    re.IGNORECASE | re.DOTALL,
)
REVERSE_RE = re.compile(r"reverse\s+stock", re.IGNORECASE)
SPLIT_RE = re.compile(r"stock\s*split|pemecahan\s+saham", re.IGNORECASE)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_source_ids(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = []
    return [text(item) for item in parsed if text(item)] if isinstance(parsed, list) else []


def load_targets(project_root: Path) -> list[dict[str, Any]]:
    v4 = project_root / V4_ROOT_NAME
    manifest = v4 / "MANIFEST.json"
    if sha256_file(manifest) != V4_MANIFEST_SHA256:
        raise RuntimeError("controlling V4 manifest hash mismatch")
    rows = read_csv(v4 / "unresolved_190_event_ledger.csv")
    paths = {row.get("economic_event_id", ""): row for row in read_csv(v4 / "source_path_matrix.csv")}
    targets: list[dict[str, Any]] = []
    for row in rows:
        family = text(row.get("economic_family"))
        if family not in {"STOCK_SPLIT", "REVERSE_SPLIT"}:
            continue
        source_ids = extract_source_ids(text(row.get("source_event_ids")))
        if len(source_ids) != 1:
            raise RuntimeError(f"target does not have exactly one source id: {row.get('economic_event_id')}")
        targets.append(
            {
                "event_id": text(row.get("economic_event_id")),
                "ticker": text(row.get("ticker")).upper(),
                "event_family": family,
                "source_event_id": source_ids[0],
                "candidate_date": text(row.get("candidate_date")) or text(paths.get(text(row.get("economic_event_id")), {}).get("candidate_date")),
            }
        )
    targets.sort(key=lambda row: (row["ticker"], row["candidate_date"], row["event_id"]))
    if len(targets) != EXPECTED_TOTAL:
        raise RuntimeError(f"V4 target total mismatch: {len(targets)}")
    if sum(row["event_family"] == "STOCK_SPLIT" for row in targets) != EXPECTED_SPLITS:
        raise RuntimeError("V4 STOCK_SPLIT target count mismatch")
    if sum(row["event_family"] == "REVERSE_SPLIT" for row in targets) != EXPECTED_REVERSE:
        raise RuntimeError("V4 REVERSE_SPLIT target count mismatch")
    if len({row["event_id"] for row in targets}) != EXPECTED_TOTAL:
        raise RuntimeError("V4 target event ids are not unique")
    return targets


def retained_index_links(prior_root: Path) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for path in sorted((prior_root / "provider" / "index").glob("*.body")):
        body = path.read_text(encoding="utf-8", errors="replace")
        for href, reference, title, published in PDF_HREF_RE.findall(body):
            href = html.unescape(text(href))
            absolute = "https://web.ksei.co.id" + href if href.startswith("/") else href
            title = " ".join(html.unescape(text(title)).split())
            reference = " ".join(html.unescape(text(reference)).split())
            published = " ".join(html.unescape(text(published)).split())
            if not absolute.startswith("https://web.ksei.co.id/"):
                continue
            if not (SPLIT_RE.search(title) or REVERSE_RE.search(title)):
                continue
            links.append({
                "index_path": str(path),
                "index_sha256": sha256_file(path),
                "href": absolute,
                "reference": reference,
                "title": title,
                "published_date": published,
            })
    unique: dict[str, dict[str, str]] = {}
    for row in links:
        unique.setdefault(row["href"], row)
    return [unique[href] for href in sorted(unique)]


def choose_allowed_links(links: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    allowed: list[dict[str, str]] = []
    for link in links:
        title = text(link.get("title"))
        upper_title = title.upper()
        if "HEAL" in upper_title or "SCMA" in upper_title or "BBRM" in upper_title:
            if ("BBRM" in upper_title and REVERSE_RE.search(title)) or "HEAL" in upper_title or "SCMA" in upper_title:
                allowed.append(dict(link))
    required = {"HEAL", "SCMA", "BBRM"}
    present = {ticker for ticker in required if any(ticker in text(row["title"]).upper() for row in allowed)}
    if present != required:
        raise RuntimeError(f"retained index does not evidence required links: {sorted(present)}")
    return allowed


def prior_document_urls(prior_root: Path) -> set[str]:
    ledger_path = prior_root / "provider" / "document_request_ledger.json"
    return {text(row.get("requested_url")) for row in read_json(ledger_path) if text(row.get("requested_url"))}


def fetch_document(link: Mapping[str, str], raw_path: Path) -> dict[str, Any]:
    started = now_utc()
    row: dict[str, Any] = {
        "requested_url": text(link["href"]), "final_url": "", "request_started_utc": started,
        "request_completed_utc": "", "status_code": "", "reason": "", "bytes": 0,
        "sha256": "", "raw_path": str(raw_path), "retrieval_mode": "NEW_OFFICIAL_DOCUMENT",
        "official_reference_hint": text(link.get("reference")), "index_path": text(link.get("index_path")),
        "index_sha256": text(link.get("index_sha256")), "title": text(link.get("title")),
        "published_date": text(link.get("published_date")), "error": "",
    }
    request = urllib.request.Request(text(link["href"]), headers={"User-Agent": "IDX-Trade/INC001-split-wave-v2"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            raw_path.write_bytes(body)
            row.update({"final_url": response.geturl(), "status_code": int(response.status), "reason": text(response.reason), "bytes": len(body), "sha256": sha256_bytes(body)})
    except urllib.error.HTTPError as exc:
        row.update({"final_url": text(exc.geturl()), "status_code": int(exc.code), "reason": text(exc.reason), "error": "HTTP_ERROR"})
        body = exc.read()
        if body:
            raw_path.write_bytes(body)
            row.update({"bytes": len(body), "sha256": sha256_bytes(body)})
    except (OSError, urllib.error.URLError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["request_completed_utc"] = now_utc()
    return row


def extract_text(raw_path: Path, text_path: Path) -> dict[str, Any]:
    import subprocess

    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        return {"text_path": str(text_path), "text_status": "NO_BYTES", "text_sha256": ""}
    try:
        subprocess.run(["pdftotext", "-enc", "UTF-8", str(raw_path), str(text_path)], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"text_path": str(text_path), "text_status": f"EXTRACTION_FAILED:{type(exc).__name__}", "text_sha256": ""}
    return {"text_path": str(text_path), "text_status": "EXTRACTED", "text_sha256": sha256_file(text_path)}


def classify(target: Mapping[str, Any], documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ticker = text(target["ticker"])
    matches = [row for row in documents if ticker in text(row.get("title")).upper()]
    successful = [row for row in matches if text(row.get("status_code")) == "200" and valid_sha(row.get("sha256"))]
    if ticker in {"HEAL", "SCMA"}:
        if successful:
            return {"result_classification": "RESOLVED_EXACT", "reason": "exact official KSEI stock-split schedule fetched; semantic parser is evaluated in reconciliation"}
        return {"result_classification": "PROVIDER_FAILURE", "reason": "exact retained official href did not return a valid document"}
    if ticker == "BBRM":
        if successful:
            return {"result_classification": "DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT", "reason": "official reverse-stock plan/odd-lot documents do not prove regular-market first-new-basis trading"}
        return {"result_classification": "PROVIDER_FAILURE", "reason": "exact retained official BBRM probe hrefs did not return valid documents"}
    return {"result_classification": "DOCUMENT_NOT_FOUND", "reason": "no exact official PDF href was present in the retained KSEI index scope; absence is not historical negative authority"}


def manifest_for(root: Path, artifact_root: Path) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"manifest_version": f"{SCHEMA}_manifest", "artifact_root": str(artifact_root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": True, "output_hashes_excluding_manifest": outputs, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def build(project_root: Path, output_root: Path, reuse_root: Path | None = None) -> dict[str, Any]:
    staging = output_root.with_name(output_root.name + ".staging")
    if output_root.exists() or staging.exists():
        raise FileExistsError(f"immutable acquisition root already exists: {output_root}")
    staging.mkdir(parents=True)
    try:
        targets = load_targets(project_root)
        links = choose_allowed_links(retained_index_links(PRIOR_ACQUISITION_ROOT))
        old_urls = prior_document_urls(PRIOR_ACQUISITION_ROOT)
        if any(text(row["href"]) in old_urls for row in links):
            raise RuntimeError("allowed document URL is already retained; refusing re-download")
        provider = staging / "provider"
        documents = provider / "documents"
        texts = provider / "text"
        documents.mkdir(parents=True)
        texts.mkdir(parents=True)
        ledger: list[dict[str, Any]] = []
        if reuse_root is not None:
            prior_ledger = read_json(reuse_root / "provider" / "document_request_ledger.json")
            if len(prior_ledger) != len(links):
                raise RuntimeError("reuse root document count differs from retained wave")
            for number, prior in enumerate(prior_ledger, start=1):
                prior_raw = Path(text(prior.get("raw_path"))).resolve()
                prior_text = Path(text(prior.get("text_path"))).resolve()
                if not prior_raw.is_file():
                    prior_raw = reuse_root / "provider" / "documents" / Path(text(prior.get("raw_path"))).name
                if not prior_text.is_file():
                    prior_text = reuse_root / "provider" / "text" / Path(text(prior.get("text_path"))).name
                if not prior_raw.is_file() or not prior_text.is_file():
                    raise RuntimeError(f"reuse root lacks retained bytes: {prior_raw}")
                raw = documents / f"download_{number:03d}_{prior_raw.name.split('_', 2)[-1]}"
                txt = texts / (raw.stem + ".txt")
                shutil.copyfile(prior_raw, raw)
                shutil.copyfile(prior_text, txt)
                row = dict(prior)
                row.update({"raw_path": str(output_root / "provider" / "documents" / raw.name), "text_path": str(output_root / "provider" / "text" / txt.name), "retrieval_mode": "REUSED_PRIOR_WAVE_BYTES", "reused_from_root": str(reuse_root)})
                if sha256_file(raw) != text(row.get("sha256")) or sha256_file(txt) != text(row.get("text_sha256")):
                    raise RuntimeError(f"reused document hash mismatch: {raw}")
                ledger.append(row)
        else:
            for number, link in enumerate(links, start=1):
                slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(link["href"]).name)
                raw = documents / f"download_{number:03d}_{slug}"
                row = fetch_document(link, raw)
                extracted = extract_text(raw, texts / (raw.stem + ".txt"))
                row.update(extracted)
                row.update({"raw_path": str(output_root / "provider" / "documents" / raw.name), "text_path": str(output_root / "provider" / "text" / (raw.stem + ".txt"))})
                ledger.append(row)
        target_results: list[dict[str, Any]] = []
        for target in targets:
            result = classify(target, ledger)
            target_results.append({**target, **result, "probe_scope": "BBRM_SINGLE_EVENT" if target["ticker"] == "BBRM" else "EVENT_TARGET"})
        split_ids = {row["event_id"] for row in targets if row["event_family"] == "STOCK_SPLIT"}
        reverse_ids = {row["event_id"] for row in targets if row["event_family"] == "REVERSE_SPLIT"}
        capability_unit = {
            "unit_id": "CAPABILITY-V11-KSEI-REPRESENTATIVE-3", "status": "CLOSED_PREVIOUSLY_EXECUTED_NO_RETRY",
            "category": "CAPABILITY_VERIFICATION_CLOSED", "tickers": ["AADI", "ADRO", "AALI"],
            "expected_request_count": 0, "reason": "representative KSEI capability work was already executed and retained; this wave does not retry it",
        }
        summary = {
            "schema_version": SCHEMA, "audit_date": AUDIT_DATE,
            "status": "COMPLETE_NARROW_OFFICIAL_SPLIT_WAVE_OUTCOME_BLIND",
            "controlling_v4_manifest_sha256": V4_MANIFEST_SHA256,
            "target_counts": {"stock_split": len(split_ids), "reverse_split": len(reverse_ids), "total": len(targets)},
            "allowed_document_href_count": len(links), "new_document_requests": 0 if reuse_root is not None else len(ledger), "reused_document_rows": len(ledger) if reuse_root is not None else 0,
            "successful_document_requests": sum(text(row.get("status_code")) == "200" and valid_sha(row.get("sha256")) for row in ledger),
            "capability_unit": capability_unit,
            "classification_counts": {key: sum(row["result_classification"] == key for row in target_results) for key in sorted({row["result_classification"] for row in target_results})},
            "guardrails": {"only_v4_split_and_bbrm_probe": True, "aadi_adro_aali_reprobe": False, "ksei_bulk": False, "rights_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
            "authority_blockers_unchanged": {"IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED", "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN", "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN"},
        }
        selection = {
            "schema_version": f"{SCHEMA}_selection", "controlling_input": str(project_root / V4_ROOT_NAME / "unresolved_190_event_ledger.csv"),
            "controlling_input_manifest_sha256": V4_MANIFEST_SHA256, "exact_target_count": len(targets), "targets": targets,
            "retained_index_scope": str(PRIOR_ACQUISITION_ROOT / "provider" / "index"), "allowed_links": links,
            "no_retry_policy": "one request per exact unretained official document href; failures are preserved without retry",
            "future_plan_correction": capability_unit,
        }
        write_json(staging / "selection_manifest.json", selection)
        write_json(provider / "document_request_ledger.json", ledger)
        write_csv(staging / "target_event_results.csv", target_results, ["event_id", "source_event_id", "ticker", "event_family", "candidate_date", "result_classification", "reason", "probe_scope"])
        write_json(staging / "future_acquisition_plan_correction.json", {"closed_units": [capability_unit], "remaining_event_ids": sorted(split_ids | reverse_ids)})
        write_json(staging / "acquisition_summary.json", summary)
        write_json(staging / "MANIFEST.json", manifest_for(staging, output_root))
        staging.rename(output_root)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(r"D:\Documents\Project"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reuse-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.output_root, args.reuse_root), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
