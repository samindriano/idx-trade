"""Fail-closed one-shot design for a future private AKSes KSEI auth probe.

There is deliberately no concrete HTTP/provider client in this module. A future
reviewed server/local transport may be injected only for one bounded run.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from getpass import getpass
from typing import Any, Protocol, runtime_checkable

from .types import EndpointClass

KSEI_SERVICE_BASE = "https://akses.ksei.co.id/service"
ACTIVATION_PATH = "/activation/generated"
LOGIN_PATH = "/login"
_POLICY_VERSION = "personal-ksei-bounded-auth-v1"
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_SHAPE_DEPTH = 4
_MAX_OBJECT_KEYS = 96
_SAFE_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,79}$")
_DYNAMIC_HEX_RE = re.compile(r"^[0-9a-fA-F]{16,}$")


@dataclass(frozen=True, slots=True)
class EndpointTarget:
    endpoint_class: EndpointClass
    path: str


KSEI_PORTFOLIO_ENDPOINTS: tuple[EndpointTarget, ...] = (
    EndpointTarget(EndpointClass.PORTFOLIO_SUMMARY, "/myportofolio/summary"),
    EndpointTarget(EndpointClass.CASH, "/myportofolio/summary-detail/kas"),
    EndpointTarget(EndpointClass.EQUITY, "/myportofolio/summary-detail/ekuitas"),
    EndpointTarget(EndpointClass.MUTUAL_FUND, "/myportofolio/summary-detail/reksadana"),
    EndpointTarget(EndpointClass.BOND, "/myportofolio/summary-detail/obligasi"),
    EndpointTarget(EndpointClass.OTHER, "/myportofolio/summary-detail/lainnya"),
)


@dataclass(frozen=True, slots=True)
class BoundedAuthPolicy:
    max_activation_calls: int = 1
    max_login_calls: int = 1
    max_calls_per_portfolio_endpoint: int = 1
    request_timeout_seconds: float = 15.0
    max_response_bytes: int = _MAX_RESPONSE_BYTES
    allow_retries: bool = False
    persist_credentials: bool = False
    persist_session_token: bool = False
    persist_raw_responses: bool = False
    allow_global_identity: bool = False
    allow_scheduler: bool = False
    allow_browser_transport: bool = False

    def __post_init__(self) -> None:
        if (
            self.max_activation_calls != 1
            or self.max_login_calls != 1
            or self.max_calls_per_portfolio_endpoint != 1
            or self.request_timeout_seconds != 15.0
            or self.max_response_bytes != _MAX_RESPONSE_BYTES
            or self.allow_retries
            or self.persist_credentials
            or self.persist_session_token
            or self.persist_raw_responses
            or self.allow_global_identity
            or self.allow_scheduler
            or self.allow_browser_transport
        ):
            raise ValueError("bounded auth policy V1 is frozen and cannot be relaxed")


BOUNDED_AUTH_POLICY_V1 = BoundedAuthPolicy()


class ProbeFailureCode(StrEnum):
    HTTP_NON_SUCCESS = "HTTP_NON_SUCCESS"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_JSON = "INVALID_JSON"
    SUMMARY_SHAPE_UNRECOGNIZED = "SUMMARY_SHAPE_UNRECOGNIZED"


class _NonSerializableSensitive:
    __slots__ = ()

    def __reduce__(self):
        raise TypeError(f"{type(self).__name__} cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError(f"{type(self).__name__} cannot be serialized")

    def __getstate__(self):
        raise TypeError(f"{type(self).__name__} cannot be serialized")


class EphemeralCredentials(_NonSerializableSensitive):
    __slots__ = ("username", "password")

    def __init__(self, username: str, password: str):
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username is required")
        if not isinstance(password, str) or not password:
            raise ValueError("password is required")
        self.username = username
        self.password = password

    def __repr__(self) -> str:
        return "EphemeralCredentials(<redacted>)"

    __str__ = __repr__

    def clear(self) -> None:
        self.username = ""
        self.password = ""


class EphemeralSecret(_NonSerializableSensitive):
    __slots__ = ("value",)

    def __init__(self, value: str):
        if not isinstance(value, str) or not value:
            raise ValueError("ephemeral secret is required")
        self.value = value

    def __repr__(self) -> str:
        return "EphemeralSecret(<redacted>)"

    __str__ = __repr__

    def clear(self) -> None:
        self.value = ""


def prompt_ephemeral_credentials() -> EphemeralCredentials:
    """Read credentials without command-line arguments or terminal echo."""

    return EphemeralCredentials(
        username=getpass("AKSes username: "),
        password=getpass("AKSes password: "),
    )


class ProviderResponse(_NonSerializableSensitive):
    __slots__ = ("status_code", "body")

    def __init__(self, status_code: int, body: bytes):
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            raise TypeError("status_code must be an integer")
        if not isinstance(body, bytes):
            raise TypeError("body must be bytes")
        self.status_code = status_code
        self.body = body

    def __repr__(self) -> str:
        return f"ProviderResponse(status_code={self.status_code}, body=<redacted {len(self.body)} bytes>)"

    def clear(self) -> None:
        self.body = b""


class ActivationResult(_NonSerializableSensitive):
    __slots__ = ("transformed_password", "response")

    def __init__(self, transformed_password: EphemeralSecret, response: ProviderResponse):
        if not isinstance(transformed_password, EphemeralSecret):
            raise TypeError("transformed_password must be EphemeralSecret")
        if not isinstance(response, ProviderResponse):
            raise TypeError("response must be ProviderResponse")
        self.transformed_password = transformed_password
        self.response = response

    def __repr__(self) -> str:
        return "ActivationResult(<redacted>)"

    def clear(self) -> None:
        self.transformed_password.clear()
        self.response.clear()


class LoginResult(_NonSerializableSensitive):
    __slots__ = ("session_token", "response")

    def __init__(self, session_token: EphemeralSecret, response: ProviderResponse):
        if not isinstance(session_token, EphemeralSecret):
            raise TypeError("session_token must be EphemeralSecret")
        if not isinstance(response, ProviderResponse):
            raise TypeError("response must be ProviderResponse")
        self.session_token = session_token
        self.response = response

    def __repr__(self) -> str:
        return "LoginResult(<redacted>)"

    def clear(self) -> None:
        self.session_token.clear()
        self.response.clear()


class BoundedTransportFailure(Exception):
    def __init__(self, code: ProbeFailureCode):
        super().__init__(code.value)
        self.code = code


@runtime_checkable
class BoundedKseiTransport(Protocol):
    """Server/local-only transport contract. No HTTP implementation lives here."""

    def activate(
        self,
        credentials: EphemeralCredentials,
        *,
        timeout_seconds: float,
    ) -> ActivationResult: ...

    def login(
        self,
        credentials: EphemeralCredentials,
        transformed_password: EphemeralSecret,
        *,
        timeout_seconds: float,
    ) -> LoginResult: ...

    def fetch_portfolio_endpoint(
        self,
        session_token: EphemeralSecret,
        target: EndpointTarget,
        *,
        timeout_seconds: float,
    ) -> ProviderResponse: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class JsonShape:
    kind: str
    count: int | None = None
    fields: tuple[tuple[str, "JsonShape"], ...] = ()
    item_kinds: tuple[str, ...] = ()
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind}
        if self.count is not None:
            result["count"] = self.count
        if self.fields:
            result["fields"] = {name: child.to_dict() for name, child in self.fields}
        if self.item_kinds:
            result["item_kinds"] = list(self.item_kinds)
        if self.truncated:
            result["truncated"] = True
        return result


@dataclass(frozen=True, slots=True)
class SummaryProbe:
    rows_detected: int | None
    zero_value_rows_present: bool | None
    zero_value_row_count: int | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_detected": self.rows_detected,
            "zero_value_rows_present": self.zero_value_rows_present,
            "zero_value_row_count": self.zero_value_row_count,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class SanitizedResponseObservation:
    stage: str
    endpoint_class: str | None
    path: str
    status_code: int | None
    succeeded: bool
    raw_response_sha256: str | None
    body_bytes: int | None
    shape: JsonShape | None
    failure_code: ProbeFailureCode | None = None
    summary_probe: SummaryProbe | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "endpoint_class": self.endpoint_class,
            "path": self.path,
            "status_code": self.status_code,
            "succeeded": self.succeeded,
            "raw_response_sha256": self.raw_response_sha256,
            "body_bytes": self.body_bytes,
            "shape": self.shape.to_dict() if self.shape is not None else None,
            "failure_code": self.failure_code.value if self.failure_code is not None else None,
            "summary_probe": self.summary_probe.to_dict() if self.summary_probe is not None else None,
        }


@dataclass(frozen=True, slots=True)
class BoundedAuthReport:
    completed_call_plan: bool
    observations: tuple[SanitizedResponseObservation, ...]
    failure_stage: str | None = None
    policy_version: str = _POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "completed_call_plan": self.completed_call_plan,
            "failure_stage": self.failure_stage,
            "observations": [item.to_dict() for item in self.observations],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class _CallBudget:
    activation_calls: int = 0
    login_calls: int = 0
    endpoint_calls: dict[EndpointClass, int] = field(default_factory=dict)

    def consume_activation(self) -> None:
        if self.activation_calls:
            raise RuntimeError("bounded auth activation budget exhausted")
        self.activation_calls = 1

    def consume_login(self) -> None:
        if self.login_calls:
            raise RuntimeError("bounded auth login budget exhausted")
        self.login_calls = 1

    def consume_endpoint(self, endpoint_class: EndpointClass) -> None:
        if self.endpoint_calls.get(endpoint_class, 0):
            raise RuntimeError(f"bounded auth endpoint budget exhausted: {endpoint_class.value}")
        self.endpoint_calls[endpoint_class] = 1


def _safe_field_name(value: Any) -> str:
    text = str(value)
    if not _SAFE_FIELD_RE.fullmatch(text):
        return "<redacted-key>"
    if _DYNAMIC_HEX_RE.fullmatch(text) or re.search(r"\d{8,}", text):
        return "<redacted-key>"
    return text


def _kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "unsupported"


def describe_json_shape(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = _MAX_SHAPE_DEPTH,
    max_object_keys: int = _MAX_OBJECT_KEYS,
) -> JsonShape:
    if depth >= max_depth:
        return JsonShape(_kind(value), count=len(value) if isinstance(value, (dict, list)) else None, truncated=True)

    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        selected = items[:max_object_keys]
        return JsonShape(
            "object",
            count=len(value),
            fields=tuple(
                (
                    _safe_field_name(key),
                    describe_json_shape(
                        child,
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_object_keys=max_object_keys,
                    ),
                )
                for key, child in selected
            ),
            truncated=len(items) > max_object_keys,
        )

    if isinstance(value, list):
        object_items = [item for item in value if isinstance(item, dict)]
        fields: tuple[tuple[str, JsonShape], ...] = ()
        truncated = False
        if object_items:
            keys = sorted({str(key) for item in object_items for key in item})
            selected_keys = keys[:max_object_keys]
            truncated = len(keys) > max_object_keys
            fields = tuple(
                (
                    _safe_field_name(key),
                    JsonShape(
                        "union",
                        item_kinds=tuple(
                            sorted({_kind(item[key]) for item in object_items if key in item})
                        ),
                    ),
                )
                for key in selected_keys
            )
        return JsonShape(
            "array",
            count=len(value),
            fields=fields,
            item_kinds=tuple(sorted({_kind(item) for item in value})),
            truncated=truncated,
        )

    return JsonShape(_kind(value))


def _find_named_list(value: Any, key_name: str, depth: int = 0) -> list[Any] | None:
    if depth > 3:
        return None
    if isinstance(value, dict):
        direct = value.get(key_name)
        if isinstance(direct, list):
            return direct
        for child in value.values():
            found = _find_named_list(child, key_name, depth + 1)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_named_list(child, key_name, depth + 1)
            if found is not None:
                return found
    return None


def _numeric_zero(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float, Decimal, str)):
        return None
    try:
        return Decimal(str(value).strip()) == 0
    except (InvalidOperation, ValueError):
        return None


def probe_summary_semantics(payload: Any) -> SummaryProbe:
    rows = _find_named_list(payload, "summaryResponse")
    if rows is None:
        return SummaryProbe(None, None, None, ProbeFailureCode.SUMMARY_SHAPE_UNRECOGNIZED.value)

    zero_rows = 0
    comparable_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        zero_flags = [
            state
            for field_name in ("summaryAmount", "amount", "balance", "value")
            if field_name in row
            for state in [_numeric_zero(row[field_name])]
            if state is not None
        ]
        if zero_flags:
            comparable_rows += 1
            if all(zero_flags):
                zero_rows += 1

    if comparable_rows == 0:
        return SummaryProbe(len(rows), None, None, "ROWS_FOUND_VALUE_STATE_UNAVAILABLE")
    return SummaryProbe(
        len(rows),
        zero_rows > 0,
        zero_rows,
        "ROWS_FOUND_VALUE_STATE_CLASSIFIED",
    )


def _observe_response(
    *,
    stage: str,
    endpoint_class: EndpointClass | None,
    path: str,
    response: ProviderResponse,
    policy: BoundedAuthPolicy,
) -> SanitizedResponseObservation:
    response_hash = hashlib.sha256(response.body).hexdigest()
    body_bytes = len(response.body)
    if not 200 <= response.status_code <= 299:
        failure = (
            ProbeFailureCode.AUTH_REQUIRED
            if response.status_code in {401, 403}
            else ProbeFailureCode.HTTP_NON_SUCCESS
        )
        return SanitizedResponseObservation(
            stage, endpoint_class.value if endpoint_class else None, path,
            response.status_code, False, response_hash, body_bytes, None, failure
        )
    if body_bytes > policy.max_response_bytes:
        return SanitizedResponseObservation(
            stage, endpoint_class.value if endpoint_class else None, path,
            response.status_code, False, response_hash, body_bytes, None,
            ProbeFailureCode.RESPONSE_TOO_LARGE,
        )
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return SanitizedResponseObservation(
            stage, endpoint_class.value if endpoint_class else None, path,
            response.status_code, False, response_hash, body_bytes, None,
            ProbeFailureCode.INVALID_JSON,
        )
    return SanitizedResponseObservation(
        stage=stage,
        endpoint_class=endpoint_class.value if endpoint_class else None,
        path=path,
        status_code=response.status_code,
        succeeded=True,
        raw_response_sha256=response_hash,
        body_bytes=body_bytes,
        shape=describe_json_shape(payload),
        summary_probe=probe_summary_semantics(payload)
        if endpoint_class == EndpointClass.PORTFOLIO_SUMMARY
        else None,
    )


def _failure_observation(
    stage: str,
    endpoint_class: EndpointClass | None,
    path: str,
    code: ProbeFailureCode,
) -> SanitizedResponseObservation:
    return SanitizedResponseObservation(
        stage, endpoint_class.value if endpoint_class else None, path,
        None, False, None, None, None, code,
    )


def _safe_transport_error(exc: Exception) -> ProbeFailureCode:
    if isinstance(exc, BoundedTransportFailure):
        return exc.code
    return ProbeFailureCode.TRANSPORT_ERROR


class BoundedAuthRunner:
    """One-shot future real-auth orchestrator with no concrete network client."""

    def __init__(self, policy: BoundedAuthPolicy = BOUNDED_AUTH_POLICY_V1):
        if policy != BOUNDED_AUTH_POLICY_V1:
            raise ValueError("only the frozen bounded auth policy V1 is accepted")
        self._policy = policy

    def run(
        self,
        credentials: EphemeralCredentials,
        transport: BoundedKseiTransport,
    ) -> BoundedAuthReport:
        budget = _CallBudget()
        observations: list[SanitizedResponseObservation] = []
        activation: ActivationResult | None = None
        login: LoginResult | None = None
        failure_stage: str | None = None

        try:
            budget.consume_activation()
            try:
                activation = transport.activate(
                    credentials,
                    timeout_seconds=self._policy.request_timeout_seconds,
                )
            except Exception as exc:
                observations.append(_failure_observation(
                    "ACTIVATION", None, ACTIVATION_PATH, _safe_transport_error(exc)
                ))
                return BoundedAuthReport(False, tuple(observations), "ACTIVATION")

            activation_obs = _observe_response(
                stage="ACTIVATION",
                endpoint_class=None,
                path=ACTIVATION_PATH,
                response=activation.response,
                policy=self._policy,
            )
            observations.append(activation_obs)
            if not activation_obs.succeeded:
                return BoundedAuthReport(False, tuple(observations), "ACTIVATION")

            budget.consume_login()
            try:
                login = transport.login(
                    credentials,
                    activation.transformed_password,
                    timeout_seconds=self._policy.request_timeout_seconds,
                )
            except Exception as exc:
                observations.append(_failure_observation(
                    "LOGIN", None, LOGIN_PATH, _safe_transport_error(exc)
                ))
                return BoundedAuthReport(False, tuple(observations), "LOGIN")

            login_obs = _observe_response(
                stage="LOGIN",
                endpoint_class=None,
                path=LOGIN_PATH,
                response=login.response,
                policy=self._policy,
            )
            observations.append(login_obs)
            if not login_obs.succeeded:
                return BoundedAuthReport(False, tuple(observations), "LOGIN")

            attempted: set[EndpointClass] = set()
            for target in KSEI_PORTFOLIO_ENDPOINTS:
                budget.consume_endpoint(target.endpoint_class)
                attempted.add(target.endpoint_class)
                try:
                    response = transport.fetch_portfolio_endpoint(
                        login.session_token,
                        target,
                        timeout_seconds=self._policy.request_timeout_seconds,
                    )
                except Exception as exc:
                    code = _safe_transport_error(exc)
                    observations.append(_failure_observation(
                        "PORTFOLIO", target.endpoint_class, target.path, code
                    ))
                    if code == ProbeFailureCode.AUTH_REQUIRED:
                        failure_stage = target.endpoint_class.value
                        break
                    continue

                try:
                    observation = _observe_response(
                        stage="PORTFOLIO",
                        endpoint_class=target.endpoint_class,
                        path=target.path,
                        response=response,
                        policy=self._policy,
                    )
                    observations.append(observation)
                    if observation.failure_code == ProbeFailureCode.AUTH_REQUIRED:
                        failure_stage = target.endpoint_class.value
                        break
                finally:
                    response.clear()

            completed = len(attempted) == len(KSEI_PORTFOLIO_ENDPOINTS)
            if not completed and failure_stage is None:
                failure_stage = "PORTFOLIO"
            return BoundedAuthReport(completed, tuple(observations), failure_stage)
        finally:
            if login is not None:
                login.clear()
            if activation is not None:
                activation.clear()
            credentials.clear()
            try:
                transport.close()
            except Exception:
                pass


__all__ = [
    "ACTIVATION_PATH",
    "BOUNDED_AUTH_POLICY_V1",
    "BoundedAuthPolicy",
    "BoundedAuthReport",
    "BoundedAuthRunner",
    "BoundedKseiTransport",
    "BoundedTransportFailure",
    "EndpointTarget",
    "EphemeralCredentials",
    "EphemeralSecret",
    "KSEI_PORTFOLIO_ENDPOINTS",
    "KSEI_SERVICE_BASE",
    "LOGIN_PATH",
    "ProbeFailureCode",
    "ProviderResponse",
    "SanitizedResponseObservation",
    "SummaryProbe",
    "describe_json_shape",
    "probe_summary_semantics",
    "prompt_ephemeral_credentials",
]
