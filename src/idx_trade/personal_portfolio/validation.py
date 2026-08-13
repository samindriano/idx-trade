from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .schema import GOKSEI_PIN, KSEI_MCP_PIN

SCHEMA_VERSION = "personal-portfolio-snapshot-v1"
SOURCE_ID = "AKSES_KSEI_PERSONAL"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
SCOPE_REF_RE = re.compile(r"^ps_[0-9a-f]{32}$")
SUBACCOUNT_REF_RE = re.compile(r"^ksa_[0-9a-f]{64}$")
SYMBOL_RE = re.compile(r"^[A-Za-z0-9._-]{1,24}$")
ADAPTER_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?62|0)8\d{7,12}(?!\d)")
_RAW_ID_RE = re.compile(r"(?<!\d)\d{8,20}(?!\d)")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_AUTH_RE = re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{6,}", re.IGNORECASE)
_CREDENTIAL_RE = re.compile(
    r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_FORBIDDEN_KEYS = {
    "username", "password", "passwd", "secret", "token", "access_token",
    "refresh_token", "api_key", "authorization", "bearer", "nik", "npwp",
    "passport", "email", "phone", "fullname", "full_name", "investorid",
    "investor_id", "sid", "loginid", "login_id", "rekening", "account_number",
    "account_no",
}
REQUIRED_SOURCE_COMMIT_PINS: Mapping[str, str] = MappingProxyType({
    "nichsedge/ksei-mcp": KSEI_MCP_PIN,
    "chickenzord/goksei": GOKSEI_PIN,
})


def require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def require_non_negative(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative Decimal")


def require_currency(value: str) -> None:
    if not CURRENCY_RE.fullmatch(value):
        raise ValueError("currency must be a three-letter uppercase code")


def assert_no_sensitive_string(value: str, field_name: str) -> None:
    if _EMAIL_RE.search(value) or _PHONE_RE.search(value):
        raise ValueError(f"{field_name} must not contain personal identity material")
    if _JWT_RE.search(value) or _AUTH_RE.search(value) or _CREDENTIAL_RE.search(value):
        raise ValueError(f"{field_name} must not contain credential/session material")
    if _RAW_ID_RE.search(value):
        raise ValueError(f"{field_name} must not contain raw account/identity numbers")


def require_safe_text(value: str, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length {max_length}")
    if _CONTROL_RE.search(normalized):
        raise ValueError(f"{field_name} must not contain control characters")
    assert_no_sensitive_string(normalized, field_name)
    return normalized


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite Decimal cannot be canonicalized")
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def new_scope_ref() -> str:
    return f"ps_{secrets.token_hex(16)}"


def derive_subaccount_ref(raw_account_identifier: str, hmac_key: bytes) -> str:
    raw = raw_account_identifier.strip()
    if not raw:
        raise ValueError("raw_account_identifier is required")
    if len(hmac_key) < 32:
        raise ValueError("hmac_key must contain at least 32 bytes of secret material")
    digest = hmac.new(hmac_key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"ksa_{digest}"


def assert_minimized_canonical_payload(value: Any, _path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        forbidden = {item.replace("_", "") for item in _FORBIDDEN_KEYS}
        for key, child in value.items():
            key_text = str(key)
            normalized = key_text.lower().replace("-", "").replace("_", "")
            if normalized in forbidden:
                raise ValueError(f"forbidden sensitive field in canonical payload: {key_text}")
            assert_minimized_canonical_payload(child, _path + (key_text,))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            assert_minimized_canonical_payload(child, _path + (str(index),))
        return
    if isinstance(value, str):
        leaf = _path[-1] if _path else ""
        if leaf == "raw_response_sha256" or "source_commit_pins" in _path:
            return
        if leaf in {"scope_ref", "subaccount_ref", "quantity", "amount"}:
            return
        assert_no_sensitive_string(value, ".".join(_path) or "canonical value")


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value):
        return {field.name: jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(child) for child in value]
    return value
