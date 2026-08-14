from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import re

import pandas as pd
import requests

from ..security_master import normalise_ticker


IDX_HOME_URL = "https://www.idx.id/id"
IDX_SESSION_VALIDATION_URL = "https://www.idx.id/primary/home/GetIndexList"
IDX_COMPANY_PROFILE_LIST_URL = "https://www.idx.id/primary/ListedCompany/GetCompanyProfiles"
IDX_COMPANY_PROFILE_DETAIL_URL = "https://www.idx.id/primary/ListedCompany/GetCompanyProfilesDetail"
IDX_STOCK_CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,5}$")

COMPANY_HOLDER_COLUMNS = (
    "ticker",
    "snapshot_date",
    "holder_name",
    "holding_shares",
    "holding_pct",
    "is_controller",
    "holder_category",
    "investor_type",
    "local_foreign",
    "nationality",
    "domicile",
    "holdings_scripless",
    "holdings_scrip",
    "source_type",
    "source_ref",
)

GT1_REQUIRED_COLUMNS = {
    "DATE",
    "SHARE_CODE",
    "ISSUER_NAME",
    "INVESTOR_NAME",
    "INVESTOR_TYPE",
    "LOCAL_FOREIGN",
    "NATIONALITY",
    "DOMICILE",
    "HOLDINGS_SCRIPLESS",
    "HOLDINGS_SCRIP",
    "TOTAL_HOLDING_SHARES",
    "PERCENTAGE",
}


@dataclass(frozen=True)
class OwnershipPayloadCapture:
    ticker: str
    payload: dict[str, object]
    source_ref: str
    raw_bytes: bytes
    endpoint: str
    params: dict[str, str]
    retrieval_started_at_utc: str
    observed_available_at_utc: str

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("raw_bytes", None)
        result["raw_sha256"] = self.raw_sha256
        return result


@dataclass(frozen=True)
class OwnershipSnapshotMeta:
    ticker: str | None
    snapshot_date: str | None
    source_type: str
    source_ref: str
    rows: int
    raw_sha256: str
    retrieved_at_utc: str | None = None
    reported_free_float_pct: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _browser_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.id/",
        "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        "X-Requested-With": "XMLHttpRequest",
    }


def _ticker(value: object) -> str:
    ticker = normalise_ticker(value)
    if not ticker or not IDX_STOCK_CODE_PATTERN.fullmatch(ticker):
        raise ValueError(f"invalid IDX ticker: {value!r}")
    return ticker


def _clean_optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _parse_shares(value: object, *, field: str) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"{field} is missing")
    if isinstance(value, bool):
        raise ValueError(f"{field} is not a share count")
    if isinstance(value, int):
        parsed = int(value)
    elif isinstance(value, float):
        if not float(value).is_integer():
            raise ValueError(f"{field} is fractional")
        parsed = int(value)
    else:
        text = str(value).strip().replace(" ", "")
        if not text:
            raise ValueError(f"{field} is empty")
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", text):
            text = text.replace(".", "").replace(",", "")
        elif not re.fullmatch(r"\d+", text):
            raise ValueError(f"{field} is not an integer share count: {value!r}")
        parsed = int(text)
    if parsed < 0:
        raise ValueError(f"{field} cannot be negative")
    return parsed


def _parse_percentage(value: object, *, field: str) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"{field} is missing")
    if isinstance(value, bool):
        raise ValueError(f"{field} is not a percentage")
    if isinstance(value, (int, float)):
        parsed = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(" ", "")
        if not text:
            raise ValueError(f"{field} is empty")
        if "," in text and "." not in text:
            text = text.replace(",", ".")
        elif "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        try:
            parsed = float(text)
        except ValueError as exc:
            raise ValueError(f"{field} is not numeric: {value!r}") from exc
    if not 0.0 <= parsed <= 100.0:
        raise ValueError(f"{field} must be between 0 and 100")
    return parsed


def _parse_optional_bool(value: object, *, field: str) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "ya", "y"}:
        return True
    if text in {"false", "0", "no", "tidak", "n"}:
        return False
    raise ValueError(f"{field} has an unrecognized boolean value: {value!r}")


def _payload_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def fetch_company_ownership_payload_capture(
    ticker: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
    language: str = "id-id",
    prepare_session: bool = True,
) -> OwnershipPayloadCapture:
    """Fetch the current official IDX Company Profile Detail payload.

    This endpoint is a current snapshot. It must not be backdated or treated
    as a historical free-float series. Raw response bytes and observation time
    are retained so prospective snapshots can be frozen immutably by callers.
    """

    code = _ticker(ticker)
    client = session or requests.Session()
    headers = _browser_headers()
    started = _utc_now()
    if prepare_session:
        home = client.get(IDX_HOME_URL, headers=headers, timeout=timeout)
        home.raise_for_status()
        validation = client.get(
            IDX_SESSION_VALIDATION_URL,
            headers=headers,
            timeout=timeout,
        )
        validation.raise_for_status()

    params = {"KodeEmiten": code, "language": language}
    response = client.get(
        IDX_COMPANY_PROFILE_DETAIL_URL,
        params=params,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    raw_bytes = bytes(response.content)
    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError("IDX Company Profile Detail response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("IDX Company Profile Detail response is not an object")
    observed = _utc_now()
    return OwnershipPayloadCapture(
        ticker=code,
        payload=payload,
        source_ref=str(getattr(response, "url", "") or IDX_COMPANY_PROFILE_DETAIL_URL),
        raw_bytes=raw_bytes,
        endpoint=IDX_COMPANY_PROFILE_DETAIL_URL,
        params=params,
        retrieval_started_at_utc=started,
        observed_available_at_utc=observed,
    )


def parse_idx_company_ownership_payload(
    payload: Mapping[str, object],
    *,
    ticker: str,
    source_ref: str,
    raw_bytes: bytes | None = None,
    observed_available_at_utc: str | None = None,
) -> tuple[pd.DataFrame, OwnershipSnapshotMeta]:
    """Normalize named holders from IDX ``GetCompanyProfilesDetail``.

    ``PemegangSaham`` is treated as a named-holder snapshot only. No free-float
    percentage is inferred from its complement or from holder categories.
    """

    code = _ticker(ticker)
    if "PemegangSaham" not in payload:
        raise ValueError("IDX Company Profile Detail is missing PemegangSaham")
    holders = payload.get("PemegangSaham")
    if not isinstance(holders, list):
        raise ValueError("IDX Company Profile Detail PemegangSaham is not a list")

    normalized: list[dict[str, object]] = []
    for position, holder in enumerate(holders):
        if not isinstance(holder, Mapping):
            raise ValueError(f"PemegangSaham row {position} is not an object")
        name = _clean_optional_text(holder.get("Nama"))
        if not name:
            raise ValueError(f"PemegangSaham row {position} has no holder name")
        shares = _parse_shares(holder.get("Jumlah"), field=f"PemegangSaham[{position}].Jumlah")
        pct = _parse_percentage(
            holder.get("Persentase"), field=f"PemegangSaham[{position}].Persentase"
        )
        normalized.append(
            {
                "ticker": code,
                "snapshot_date": pd.NaT,
                "holder_name": name,
                "holding_shares": shares,
                "holding_pct": pct,
                "is_controller": _parse_optional_bool(
                    holder.get("Pengendali"), field=f"PemegangSaham[{position}].Pengendali"
                ),
                "holder_category": _clean_optional_text(holder.get("Kategori")),
                "investor_type": None,
                "local_foreign": None,
                "nationality": None,
                "domicile": None,
                "holdings_scripless": None,
                "holdings_scrip": None,
                "source_type": "IDX_COMPANY_PROFILE_NAMED_HOLDER",
                "source_ref": source_ref,
            }
        )

    frame = pd.DataFrame(normalized, columns=COMPANY_HOLDER_COLUMNS)
    if not frame.empty and frame.duplicated(
        ["ticker", "holder_name", "holding_shares", "holding_pct"]
    ).any():
        raise ValueError("IDX Company Profile Detail contains duplicate holder rows")

    raw = raw_bytes if raw_bytes is not None else _payload_bytes(payload)
    meta = OwnershipSnapshotMeta(
        ticker=code,
        snapshot_date=None,
        source_type="IDX_COMPANY_PROFILE_NAMED_HOLDER",
        source_ref=source_ref,
        rows=len(frame),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        retrieved_at_utc=observed_available_at_utc,
        reported_free_float_pct=None,
    )
    return frame, meta


def parse_gt1_ownership_csv(
    raw_bytes: bytes,
    *,
    source_ref: str,
) -> tuple[pd.DataFrame, OwnershipSnapshotMeta]:
    """Parse a one-date >1% ownership snapshot such as KSEI-derived exports.

    The authoritative as-of date is the ``DATE`` column inside the bytes. File
    names are deliberately ignored because stale/misleading names have been
    observed in public research mirrors. The resulting rows are concentration
    evidence, not statutory or effective free-float ground truth.
    """

    try:
        source = pd.read_csv(BytesIO(raw_bytes), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError("ownership >1% snapshot is not valid CSV") from exc
    missing = GT1_REQUIRED_COLUMNS - set(source.columns)
    if missing:
        raise ValueError(f"ownership >1% snapshot missing columns: {sorted(missing)}")
    if source.empty:
        raise ValueError("ownership >1% snapshot is empty")

    dates = pd.to_datetime(source["DATE"].astype(str).str.strip(), errors="coerce", dayfirst=True)
    if dates.isna().any():
        raise ValueError("ownership >1% snapshot has invalid DATE values")
    normalized_dates = dates.dt.normalize()
    unique_dates = normalized_dates.drop_duplicates().tolist()
    if len(unique_dates) != 1:
        raise ValueError("ownership >1% file must contain exactly one snapshot DATE")
    snapshot_date = pd.Timestamp(unique_dates[0]).normalize()

    rows: list[dict[str, object]] = []
    for position, row in source.iterrows():
        ticker = _ticker(row["SHARE_CODE"])
        total = _parse_shares(
            row["TOTAL_HOLDING_SHARES"], field=f"row[{position}].TOTAL_HOLDING_SHARES"
        )
        scripless = _parse_shares(
            row["HOLDINGS_SCRIPLESS"], field=f"row[{position}].HOLDINGS_SCRIPLESS"
        )
        scrip = _parse_shares(row["HOLDINGS_SCRIP"], field=f"row[{position}].HOLDINGS_SCRIP")
        if scripless + scrip != total:
            raise ValueError(
                f"ownership >1% row {position} holding reconciliation failed: "
                f"scripless+scrip={scripless + scrip} total={total}"
            )
        name = _clean_optional_text(row["INVESTOR_NAME"])
        if not name:
            raise ValueError(f"ownership >1% row {position} has no investor name")
        pct = _parse_percentage(row["PERCENTAGE"], field=f"row[{position}].PERCENTAGE")
        rows.append(
            {
                "ticker": ticker,
                "snapshot_date": snapshot_date,
                "holder_name": name,
                "holding_shares": total,
                "holding_pct": pct,
                "is_controller": None,
                "holder_category": None,
                "investor_type": _clean_optional_text(row["INVESTOR_TYPE"]),
                "local_foreign": _clean_optional_text(row["LOCAL_FOREIGN"]),
                "nationality": _clean_optional_text(row["NATIONALITY"]),
                "domicile": _clean_optional_text(row["DOMICILE"]),
                "holdings_scripless": scripless,
                "holdings_scrip": scrip,
                "source_type": "OWNERSHIP_GT1_SNAPSHOT",
                "source_ref": source_ref,
            }
        )

    frame = pd.DataFrame(rows, columns=COMPANY_HOLDER_COLUMNS).sort_values(
        ["ticker", "holding_pct", "holder_name"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    exact_key = [
        "ticker",
        "snapshot_date",
        "holder_name",
        "investor_type",
        "local_foreign",
        "holding_shares",
        "holding_pct",
    ]
    if frame.duplicated(exact_key).any():
        raise ValueError("ownership >1% snapshot contains exact duplicate holder rows")

    meta = OwnershipSnapshotMeta(
        ticker=None,
        snapshot_date=snapshot_date.date().isoformat(),
        source_type="OWNERSHIP_GT1_SNAPSHOT",
        source_ref=source_ref,
        rows=len(frame),
        raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        retrieved_at_utc=None,
        reported_free_float_pct=None,
    )
    return frame, meta


def fetch_company_ownership_snapshot(
    ticker: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[pd.DataFrame, OwnershipSnapshotMeta, OwnershipPayloadCapture]:
    capture = fetch_company_ownership_payload_capture(
        ticker,
        session=session,
        timeout=timeout,
    )
    frame, meta = parse_idx_company_ownership_payload(
        capture.payload,
        ticker=capture.ticker,
        source_ref=capture.source_ref,
        raw_bytes=capture.raw_bytes,
        observed_available_at_utc=capture.observed_available_at_utc,
    )
    return frame, meta, capture
