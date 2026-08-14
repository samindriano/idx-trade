import dataclasses
import json
import pickle

import pytest

from idx_trade.personal_portfolio.bounded_auth import (
    BOUNDED_AUTH_POLICY_V1,
    ActivationResult,
    BoundedAuthPolicy,
    BoundedAuthRunner,
    BoundedTransportFailure,
    EphemeralCredentials,
    EphemeralSecret,
    KSEI_PORTFOLIO_ENDPOINTS,
    LoginResult,
    ProbeFailureCode,
    ProviderResponse,
    describe_json_shape,
    probe_summary_semantics,
)
from idx_trade.personal_portfolio.types import EndpointClass


class FakeTransport:
    def __init__(self):
        self.activation_calls = 0
        self.login_calls = 0
        self.endpoint_calls = []
        self.closed = 0
        self.credentials_ref = None
        self.transformed_ref = None
        self.session_ref = None
        self.login_status = 200
        self.endpoint_failure = {}
        self.raw_exception_on = None

    def activate(self, credentials, *, timeout_seconds):
        self.activation_calls += 1
        self.credentials_ref = credentials
        if self.raw_exception_on == "ACTIVATION":
            raise RuntimeError("password=must-never-escape")
        self.transformed_ref = EphemeralSecret("transformed-secret")
        return ActivationResult(
            self.transformed_ref,
            ProviderResponse(200, b'{"data":[{"pass":"transformed-secret"}]}'),
        )

    def login(self, credentials, transformed_password, *, timeout_seconds):
        self.login_calls += 1
        if self.raw_exception_on == "LOGIN":
            raise RuntimeError("bearer private-token-must-never-escape")
        self.session_ref = EphemeralSecret("bearer-token")
        return LoginResult(
            self.session_ref,
            ProviderResponse(
                self.login_status,
                b'{"validation":"bearer-token","username":"private-user"}',
            ),
        )

    def fetch_portfolio_endpoint(self, session_token, target, *, timeout_seconds):
        self.endpoint_calls.append(target.endpoint_class)
        configured = self.endpoint_failure.get(target.endpoint_class)
        if isinstance(configured, Exception):
            raise configured
        if isinstance(configured, int):
            return ProviderResponse(configured, b'{"error":"private-provider-message"}')

        if target.endpoint_class == EndpointClass.PORTFOLIO_SUMMARY:
            body = {
                "data": {
                    "summaryValue": 1234567,
                    "summaryResponse": [
                        {"type": "ekuitas", "summaryAmount": "12345", "percent": "50"},
                        {"type": "obligasi", "summaryAmount": "0", "percent": "0"},
                    ],
                }
            }
        else:
            body = {
                "data": [
                    {
                        "rekening": "123456789012",
                        "efek": "BBCA",
                        "jumlah": "999999.25",
                    }
                ]
            }
        return ProviderResponse(200, json.dumps(body).encode("utf-8"))

    def close(self):
        self.closed += 1


def test_policy_is_frozen_and_exact_endpoint_allowlist_excludes_global_identity():
    assert BOUNDED_AUTH_POLICY_V1.max_activation_calls == 1
    assert BOUNDED_AUTH_POLICY_V1.max_login_calls == 1
    assert BOUNDED_AUTH_POLICY_V1.max_calls_per_portfolio_endpoint == 1
    assert BOUNDED_AUTH_POLICY_V1.allow_retries is False
    assert BOUNDED_AUTH_POLICY_V1.persist_credentials is False
    assert BOUNDED_AUTH_POLICY_V1.persist_session_token is False
    assert BOUNDED_AUTH_POLICY_V1.persist_raw_responses is False
    assert BOUNDED_AUTH_POLICY_V1.allow_global_identity is False
    assert BOUNDED_AUTH_POLICY_V1.allow_scheduler is False
    assert BOUNDED_AUTH_POLICY_V1.allow_browser_transport is False
    assert tuple(item.endpoint_class for item in KSEI_PORTFOLIO_ENDPOINTS) == tuple(EndpointClass)
    assert all("global-identity" not in item.path for item in KSEI_PORTFOLIO_ENDPOINTS)
    with pytest.raises(ValueError, match="cannot be relaxed"):
        BoundedAuthPolicy(allow_retries=True)


def test_one_shot_plan_redacts_values_and_clears_ephemeral_secrets():
    credentials = EphemeralCredentials("private-user", "private-pass")
    transport = FakeTransport()

    report = BoundedAuthRunner().run(credentials, transport)
    rendered = report.to_json()

    assert report.completed_call_plan is True
    assert report.failure_stage is None
    assert transport.activation_calls == 1
    assert transport.login_calls == 1
    assert transport.endpoint_calls == [item.endpoint_class for item in KSEI_PORTFOLIO_ENDPOINTS]
    assert transport.closed == 1

    for forbidden in (
        "private-user",
        "private-pass",
        "transformed-secret",
        "bearer-token",
        "123456789012",
        "BBCA",
        "999999.25",
        "1234567",
        "12345",
    ):
        assert forbidden not in rendered

    assert "summaryResponse" in rendered
    assert "rekening" in rendered
    assert credentials.username == credentials.password == ""
    assert transport.transformed_ref.value == ""
    assert transport.session_ref.value == ""


def test_summary_probe_reports_only_zero_state_not_numeric_values():
    payload = {
        "data": {
            "summaryResponse": [
                {"type": "equity", "summaryAmount": "1000000000"},
                {"type": "bond", "summaryAmount": "0"},
            ]
        }
    }
    probe = probe_summary_semantics(payload)
    rendered = json.dumps(probe.to_dict(), sort_keys=True)
    assert probe.rows_detected == 2
    assert probe.zero_value_rows_present is True
    assert probe.zero_value_row_count == 1
    assert "1000000000" not in rendered
    assert "equity" not in rendered
    assert "bond" not in rendered


def test_login_auth_failure_stops_before_portfolio_calls():
    transport = FakeTransport()
    transport.login_status = 401
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    assert report.completed_call_plan is False
    assert report.failure_stage == "LOGIN"
    assert transport.endpoint_calls == []
    assert report.observations[-1].failure_code == ProbeFailureCode.AUTH_REQUIRED


def test_endpoint_auth_failure_stops_remaining_calls_without_retry():
    transport = FakeTransport()
    transport.endpoint_failure[EndpointClass.PORTFOLIO_SUMMARY] = 403
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    assert report.completed_call_plan is False
    assert report.failure_stage == EndpointClass.PORTFOLIO_SUMMARY.value
    assert transport.endpoint_calls == [EndpointClass.PORTFOLIO_SUMMARY]


def test_non_auth_endpoint_failure_continues_once_per_endpoint():
    transport = FakeTransport()
    transport.endpoint_failure[EndpointClass.CASH] = BoundedTransportFailure(
        ProbeFailureCode.TIMEOUT
    )
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    assert report.completed_call_plan is True
    assert transport.endpoint_calls == [item.endpoint_class for item in KSEI_PORTFOLIO_ENDPOINTS]
    cash = next(item for item in report.observations if item.endpoint_class == EndpointClass.CASH.value)
    assert cash.succeeded is False
    assert cash.failure_code == ProbeFailureCode.TIMEOUT


def test_untyped_transport_exception_is_sanitized_without_exception_message():
    transport = FakeTransport()
    transport.raw_exception_on = "ACTIVATION"
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    rendered = report.to_json()
    assert report.failure_stage == "ACTIVATION"
    assert report.observations[0].failure_code == ProbeFailureCode.TRANSPORT_ERROR
    assert "must-never-escape" not in rendered
    assert "password=" not in rendered


def test_dynamic_object_keys_are_redacted_but_fixed_provider_fields_remain_visible():
    shape = describe_json_shape(
        {
            "123456789012": "private-value",
            "0123456789abcdef0123456789abcdef": "private-value",
            "summaryResponse": [],
        }
    ).to_dict()
    rendered = json.dumps(shape, sort_keys=True)
    assert "123456789012" not in rendered
    assert "0123456789abcdef0123456789abcdef" not in rendered
    assert "summaryResponse" in rendered
    assert "private-value" not in rendered


def test_sensitive_containers_are_redacted_non_dataclass_and_not_serializable():
    credentials = EphemeralCredentials("private-user", "private-pass")
    secret = EphemeralSecret("bearer-token")
    response = ProviderResponse(200, b'{"account":"123456789012"}')
    activation = ActivationResult(secret, response)
    assert "private-user" not in repr(credentials)
    assert "private-pass" not in repr(credentials)
    assert "bearer-token" not in repr(secret)
    assert "123456789012" not in repr(response)
    assert dataclasses.is_dataclass(credentials) is False
    assert dataclasses.is_dataclass(secret) is False
    assert dataclasses.is_dataclass(response) is False
    assert dataclasses.is_dataclass(activation) is False
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(credentials)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(secret)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(response)
    with pytest.raises(TypeError):
        dataclasses.asdict(credentials)


def test_invalid_json_body_fails_closed_without_body_echo():
    transport = FakeTransport()
    original = transport.fetch_portfolio_endpoint

    def invalid_json(session_token, target, *, timeout_seconds):
        if target.endpoint_class == EndpointClass.CASH:
            transport.endpoint_calls.append(target.endpoint_class)
            return ProviderResponse(200, b'{"rekening":"123456789012"')
        return original(session_token, target, timeout_seconds=timeout_seconds)

    transport.fetch_portfolio_endpoint = invalid_json
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    cash = next(item for item in report.observations if item.endpoint_class == EndpointClass.CASH.value)
    assert cash.succeeded is False
    assert cash.failure_code == ProbeFailureCode.INVALID_JSON
    assert "123456789012" not in report.to_json()


def test_oversized_body_fails_closed_without_raw_value_copy():
    transport = FakeTransport()
    original = transport.fetch_portfolio_endpoint

    def oversized(session_token, target, *, timeout_seconds):
        if target.endpoint_class == EndpointClass.CASH:
            transport.endpoint_calls.append(target.endpoint_class)
            return ProviderResponse(200, b"x" * (BOUNDED_AUTH_POLICY_V1.max_response_bytes + 1))
        return original(session_token, target, timeout_seconds=timeout_seconds)

    transport.fetch_portfolio_endpoint = oversized
    report = BoundedAuthRunner().run(
        EphemeralCredentials("private-user", "private-pass"),
        transport,
    )
    cash = next(item for item in report.observations if item.endpoint_class == EndpointClass.CASH.value)
    assert cash.succeeded is False
    assert cash.failure_code == ProbeFailureCode.RESPONSE_TOO_LARGE
    assert cash.shape is None
