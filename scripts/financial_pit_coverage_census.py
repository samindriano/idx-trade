"""Run the bounded direct-IDX Financial PIT source-readiness census.

Raw JSON and attachments are written only under the external output root. The
repository receives code/tests and the factual checkpoint, never the capture.
"""

from __future__ import annotations

import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idx_trade.financial_pit_adapter import (
    ANNOUNCEMENT_ENDPOINT,
    DirectIdxFinancialPITAdapter,
    CurlCffiTransport,
    ImmutableCaptureStore,
    ResolutionStatus,
    write_json_manifest,
)


PERIODS = {
    2024: ("tw1", "tw2", "tw3", "audit"),
    2025: ("tw1", "tw2", "tw3", "audit"),
    2026: ("tw1", "tw2"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def api_json(transport, store, endpoint, params, capture_name):
    cached_path = store.root / "raw" / f"{capture_name}.json"
    if cached_path.exists():
        content = cached_path.read_bytes()
        try:
            payload = json.loads(content)
        except Exception as exc:
            invalid_path = cached_path.with_name(
                f"{cached_path.stem}__invalid_sha256_{hashlib.sha256(content).hexdigest()[:16]}{cached_path.suffix}"
            )
            if not invalid_path.exists():
                cached_path.replace(invalid_path)
            else:
                cached_path.unlink()
        else:
            return payload, {
                "endpoint": endpoint,
                "params": dict(params),
                "http_status": 200,
                "raw_path": str(cached_path),
                "raw_sha256": hashlib.sha256(content).hexdigest(),
                "row_count": len(payload.get("Results", payload.get("Replies", []))) if isinstance(payload, dict) else None,
                "records_total": payload.get("ResultCount") if isinstance(payload, dict) else None,
                "reused_cached_capture": True,
            }
    response = None
    for attempt in range(4):
        response = transport.get(endpoint, params)
        if response is not None and response.status_code == 200:
            break
        if attempt < 3:
            time.sleep(1.0 * (attempt + 1))
    content = bytes(response.content) if response is not None else b""
    raw_path = None
    raw_sha = None
    if content:
        raw_path, raw_sha = store.put(f"raw/{capture_name}.json", content)
    if response is None or response.status_code != 200:
        return None, {
            "endpoint": endpoint,
            "params": dict(params),
            "http_status": getattr(response, "status_code", None),
            "raw_path": raw_path,
            "raw_sha256": raw_sha,
        }
    try:
        payload = response.json()
    except Exception as exc:
        return None, {
            "endpoint": endpoint,
            "params": dict(params),
            "http_status": response.status_code,
            "raw_path": raw_path,
            "raw_sha256": raw_sha,
            "error": f"invalid JSON: {exc}",
        }
    return payload, {
        "endpoint": endpoint,
        "params": dict(params),
        "http_status": response.status_code,
        "raw_path": raw_path,
        "raw_sha256": raw_sha,
        "row_count": len(payload.get("Results", payload.get("Replies", []))) if isinstance(payload, dict) else None,
        "records_total": payload.get("ResultCount") if isinstance(payload, dict) else None,
    }


def month_ranges(months):
    for year, month in sorted(months):
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        yield start, end


def fetch_complete_announcements(transport, store, months, request_log):
    """Recursively split until every response is self-complete."""
    by_date = defaultdict(list)
    unavailable = {}

    def fetch(start: date, end: date, depth: int = 0):
        if depth > 8:
            raise RuntimeError(f"announcement range split depth exceeded: {start}..{end}")
        cached_path = store.root / "raw" / f"announcements_{start:%Y%m%d}_{end:%Y%m%d}.json"
        if cached_path.exists():
            try:
                json.loads(cached_path.read_bytes())
            except Exception:
                if start < end:
                    midpoint = start + (end - start) // 2
                    fetch(start, midpoint, depth + 1)
                    fetch(midpoint + timedelta(days=1), end, depth + 1)
                    return
        params = {
            "kodeEmiten": "",
            "emitenType": "*",
            "indexFrom": 0,
            "pageSize": 2000,
            "dateFrom": start.strftime("%Y%m%d"),
            "dateTo": end.strftime("%Y%m%d"),
            "lang": "id",
            "keyword": "",
        }
        name = f"announcements_{start:%Y%m%d}_{end:%Y%m%d}"
        if cached_path.exists():
            try:
                cached_payload = json.loads(cached_path.read_bytes())
                cached_total = int(cached_payload.get("ResultCount", -1))
                cached_rows = cached_payload.get("Replies") or []
                if start == end and cached_total != len(cached_rows):
                    name += "__page_size_2000"
            except Exception:
                pass
        payload, request = api_json(transport, store, ANNOUNCEMENT_ENDPOINT, params, name)
        request_log.append(request)
        if payload is None:
            if start >= end:
                unavailable[start.isoformat()] = "HTTP_PROVIDER_FAILURE"
                return
            midpoint = start + (end - start) // 2
            fetch(start, midpoint, depth + 1)
            fetch(midpoint + timedelta(days=1), end, depth + 1)
            return
        replies = payload.get("Replies")
        total = int(payload.get("ResultCount", -1))
        if not isinstance(replies, list):
            raise RuntimeError(f"announcement payload missing Replies for {start}..{end}")
        if total > 2000 or total != len(replies):
            if start >= end:
                unavailable[start.isoformat()] = "INCOMPLETE_PAGINATION"
                return
            midpoint = start + (end - start) // 2
            fetch(start, midpoint, depth + 1)
            fetch(midpoint + timedelta(days=1), end, depth + 1)
            return
        for reply in replies:
            announcement = reply.get("pengumuman") or reply.get("Pengumuman") or {}
            raw_date = str(announcement.get("TglPengumuman") or "")[:10]
            if raw_date:
                by_date[raw_date].append(reply)

    for start, end in month_ranges(months):
        try:
            fetch(start, end)
        except RuntimeError as exc:
            # A bounded census records a provider failure rather than
            # turning the affected issuer-periods into false negatives.
            unavailable[f"{start.isoformat()}..{end.isoformat()}"] = "HTTP_PROVIDER_FAILURE"
    return by_date, unavailable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--as-of", default="20260813")
    args = parser.parse_args()

    universe_path = Path(args.universe)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    tickers = set(pd.read_parquet(universe_path, columns=["ticker"])["ticker"].str.upper())
    if len(tickers) != 737:
        raise RuntimeError(f"unexpected eligible universe size: {len(tickers)}")

    transport = CurlCffiTransport(timeout=90)
    store = ImmutableCaptureStore(output_root)
    adapter = DirectIdxFinancialPITAdapter(transport, capture_store=store)
    request_log = []
    report_rows = []
    report_inventory = {}

    for year, periods in PERIODS.items():
        for period in periods:
            params = {
                "periode": period,
                "year": str(year),
                "indexFrom": 0,
                "pageSize": 1000,
                "reportType": "rdf",
                "kodeEmiten": "",
            }
            payload, request = api_json(transport, store, "/ListedCompany/GetFinancialReport", params, f"financial_reports_{year}_{period}")
            request_log.append(request)
            if payload is None:
                raise RuntimeError(f"financial report request failed: {year} {period}")
            results = payload.get("Results") or []
            total = int(payload.get("ResultCount", -1))
            if total != len(results) or total > 1000:
                raise RuntimeError(f"financial report pagination incomplete: {year} {period}: {total} vs {len(results)}")
            selected = [
                row for row in results
                if str(row.get("KodeEmiten") or "").strip().upper() in tickers
            ]
            for row in selected:
                report_inventory.setdefault((row["KodeEmiten"].strip().upper(), year, period), []).append(row)
                report_rows.append({
                    "ticker": row["KodeEmiten"].strip().upper(),
                    "year": year,
                    "period": period,
                    "report_found": True,
                    "report_modified": row.get("File_Modified"),
                    "report_attachment_count": len(row.get("Attachments") or []),
                })

    months = set()
    for row in report_rows:
        modified = str(row.get("report_modified") or "")[:7]
        if len(modified) == 7:
            months.add(tuple(map(int, modified.split("-"))))
    announcement_by_date, unavailable_dates = fetch_complete_announcements(transport, store, months, request_log)

    expected = []
    results = []
    pending = []
    for ticker in sorted(tickers):
        for year, periods in PERIODS.items():
            for period in periods:
                expected.append((ticker, year, period))
                rows = report_inventory.get((ticker, year, period), [])
                if len(rows) != 1:
                    results.append({
                        "ticker": ticker,
                        "year": year,
                        "period": period,
                        "status": ResolutionStatus.REPORT_NOT_FOUND.value if not rows else ResolutionStatus.REPORT_AMBIGUOUS.value,
                        "report_found": bool(rows),
                        "announcement_found": False,
                        "exact_attachment_join": False,
                        "pit_ready": False,
                    })
                    continue
                row = rows[0]
                day = str(row.get("File_Modified") or "")[:10]
                if day in unavailable_dates or any(day >= key[:10] and day <= key[-10:] for key in unavailable_dates if ".." in key):
                    results.append({
                        "ticker": ticker,
                        "year": year,
                        "period": period,
                        "status": unavailable_dates.get(day, "HTTP_PROVIDER_FAILURE"),
                        "report_found": True,
                        "announcement_found": False,
                        "exact_attachment_join": False,
                        "pit_ready": False,
                        "detail": "announcement response was not complete or unavailable",
                    })
                    continue
                payload = {"ResultCount": len(announcement_by_date.get(day, [])), "Replies": announcement_by_date.get(day, [])}
                pending.append((ticker, year, period, row, payload))

    def resolve_pending(item):
        ticker, year, period, row, payload = item
        # One transport/adapter per worker keeps request state and revision
        # ledgers isolated; results are merged in canonical key order below.
        worker = DirectIdxFinancialPITAdapter(
            CurlCffiTransport(timeout=90), capture_store=store
        )
        return item[:3], worker.resolve_report_row(
            row,
            ticker=ticker,
            year=year,
            period=period,
            announcement_payload=payload,
            download_attachments=True,
        )

    resolved = {}
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="idx-financial-attachment") as pool:
        futures = {pool.submit(resolve_pending, item): item[:3] for item in pending}
        for index, future in enumerate(as_completed(futures), start=1):
            key = futures[future]
            try:
                _, resolution = future.result()
            except Exception as exc:
                resolution = type("FailedResolution", (), {
                    "status": ResolutionStatus.HTTP_FAILURE,
                    "report_found": True,
                    "announcement_found": True,
                    "exact_attachment_join": False,
                    "pit_ready": False,
                    "publication_at_utc": None,
                    "source_sha256": (),
                    "source_refs": (),
                    "detail": str(exc),
                })()
            resolved[key] = resolution
            if index % 250 == 0 or index == len(futures):
                print(f"attachment_resolved={index}/{len(futures)}", flush=True)

    for key in sorted(resolved):
        ticker, year, period = key
        resolution = resolved[key]
        results.append({
            "ticker": ticker,
            "year": year,
            "period": period,
            "status": resolution.status.value,
            "report_found": resolution.report_found,
            "announcement_found": resolution.announcement_found,
            "exact_attachment_join": resolution.exact_attachment_join,
            "pit_ready": resolution.pit_ready,
            "publication_at_utc": resolution.publication_at_utc,
            "source_sha256": list(resolution.source_sha256),
            "source_refs": list(resolution.source_refs),
            "detail": resolution.detail,
        })

    status_counts = Counter(row["status"] for row in results)
    by_period = []
    ordered_results = sorted(results, key=lambda row: (row["year"], row["period"], row["ticker"]))
    for (year, period), group in __import__("itertools").groupby(
        ordered_results,
        key=lambda row: (row["year"], row["period"]),
    ):
        items = list(group)
        by_period.append({
            "year": year,
            "period": period,
            "expected_issuer_periods": len(items),
            "report_found": sum(bool(item["report_found"]) for item in items),
            "announcement_found": sum(bool(item["announcement_found"]) for item in items),
            "exact_attachment_join": sum(bool(item["exact_attachment_join"]) for item in items),
            "pit_ready": sum(bool(item["pit_ready"]) for item in items),
            "missing_publication_linkage": sum(item["status"] in {ResolutionStatus.REPORT_NOT_FOUND.value, ResolutionStatus.ATTACHMENT_NOT_MATCHED.value} for item in items),
            "scope_unresolved": sum(item["status"] == ResolutionStatus.SCOPE_UNRESOLVED.value for item in items),
            "revision_hash_conflicts": sum(item["status"] in {ResolutionStatus.ATTACHMENT_HASH_CONFLICT.value, ResolutionStatus.REVISION_HASH_CONFLICT.value} for item in items),
            "http_provider_failures": sum(item["status"] in {ResolutionStatus.HTTP_FAILURE.value, "HTTP_PROVIDER_FAILURE", ResolutionStatus.INCOMPLETE_PAGINATION.value} for item in items),
            "ambiguous_attachment": sum(item["status"] == ResolutionStatus.ATTACHMENT_AMBIGUOUS.value for item in items),
        })
    summary = {
        "census": "direct IDX Financial PIT source-readiness census",
        "captured_at_utc": datetime.now().astimezone().astimezone(__import__("datetime").timezone.utc).isoformat(),
        "as_of": args.as_of,
        "universe_path": str(universe_path),
        "universe_sha256": sha256(universe_path),
        "eligible_tickers": len(tickers),
        "periods": {str(year): list(periods) for year, periods in PERIODS.items()},
        "expected_issuer_periods": len(expected),
        "result_rows": len(results),
        "status_counts": dict(sorted(status_counts.items())),
        "coverage_by_year_period": by_period,
        "report_found": sum(bool(row["report_found"]) for row in results),
        "announcement_found": sum(bool(row["announcement_found"]) for row in results),
        "exact_attachment_join": sum(bool(row["exact_attachment_join"]) for row in results),
        "pit_ready": sum(bool(row["pit_ready"]) for row in results),
        "requests": len(request_log),
        "raw_request_log": request_log,
        "unavailable_announcement_ranges": unavailable_dates,
    }
    rows_path = output_root / "coverage_rows.jsonl"
    period_path = output_root / "coverage_by_year_period.csv"
    rows_path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in results) + "\n", encoding="utf-8")
    pd.DataFrame(by_period).to_csv(period_path, index=False)
    raw_files = list((output_root / "raw").glob("*") if (output_root / "raw").exists() else [])
    attachment_files = list((output_root / "attachments").glob("*") if (output_root / "attachments").exists() else [])
    summary["immutable_capture_inventory"] = {
        "raw_response_files": len(raw_files),
        "attachment_files": len(attachment_files),
        "raw_response_bytes": sum(path.stat().st_size for path in raw_files),
        "attachment_bytes": sum(path.stat().st_size for path in attachment_files),
    }
    summary["artifact_sha256"] = {
        "coverage_rows_jsonl": sha256(rows_path),
        "coverage_by_year_period_csv": sha256(period_path),
    }
    (output_root / "coverage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_target = output_root / "MANIFEST.json"
    if manifest_target.exists():
        index = 2
        while (output_root / f"MANIFEST__rerun_v{index}.json").exists():
            index += 1
        manifest_target = output_root / f"MANIFEST__rerun_v{index}.json"
    manifest_sha = write_json_manifest(manifest_target, summary)
    print(json.dumps({"summary": summary, "manifest_path": str(manifest_target), "manifest_sha256": manifest_sha}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
