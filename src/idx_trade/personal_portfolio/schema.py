from __future__ import annotations

from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

KSEI_MCP_PIN = "a3dfd3260889d704b75001387b646c25b4b69aa3"
GOKSEI_PIN = "5e51319feb3d373e463c21dfca5c31f971335653"

_ENDPOINT_CLASSES = (
    "PORTFOLIO_SUMMARY",
    "CASH",
    "EQUITY",
    "MUTUAL_FUND",
    "BOND",
    "OTHER",
)


def _endpoint_schema(endpoint_class: str) -> dict[str, Any]:
    return {
        "allOf": [
            {"$ref": "#/$defs/endpoint_evidence"},
            {"properties": {"endpoint_class": {"const": endpoint_class}}},
        ]
    }


PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "idx-trade://schemas/personal-portfolio-snapshot-v1",
    "title": "Personal Portfolio Snapshot V1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "snapshot_at",
        "fetched_at",
        "scope_ref",
        "completeness",
        "endpoint_evidence",
        "positions",
        "cash_balances",
        "provenance",
    ],
    "properties": {
        "schema_version": {"const": "personal-portfolio-snapshot-v1"},
        "snapshot_at": {"type": "string", "format": "date-time"},
        "fetched_at": {"type": "string", "format": "date-time"},
        "scope_ref": {
            "type": "string",
            "pattern": "^ps_[0-9a-f]{32}$",
        },
        "completeness": {"enum": ["COMPLETE", "PARTIAL"]},
        "endpoint_evidence": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "prefixItems": [_endpoint_schema(item) for item in _ENDPOINT_CLASSES],
            "items": False,
        },
        "positions": {
            "type": "array",
            "items": {"$ref": "#/$defs/position"},
        },
        "cash_balances": {
            "type": "array",
            "items": {"$ref": "#/$defs/cash"},
        },
        "provenance": {"$ref": "#/$defs/provenance"},
    },
    "allOf": [
        {
            "if": {"properties": {"completeness": {"const": "COMPLETE"}}},
            "then": {
                "properties": {
                    "endpoint_evidence": {
                        "type": "array",
                        "minItems": 6,
                        "maxItems": 6,
                        "items": {
                            "allOf": [
                                {"$ref": "#/$defs/endpoint_evidence"},
                                {
                                    "properties": {
                                        "succeeded": {"const": True},
                                        "rejected_rows": {"const": 0},
                                        "failure_code": {"type": "null"},
                                    }
                                },
                            ]
                        },
                    }
                }
            },
        },
        {
            "if": {"properties": {"completeness": {"const": "PARTIAL"}}},
            "then": {
                "properties": {
                    "endpoint_evidence": {
                        "contains": {
                            "anyOf": [
                                {"properties": {"succeeded": {"const": False}}},
                                {"properties": {"rejected_rows": {"minimum": 1}}},
                            ]
                        },
                        "minContains": 1,
                    }
                }
            },
        },
    ],
    "$defs": {
        "security": {
            "type": "object",
            "additionalProperties": False,
            "required": ["symbol", "security_name", "security_code"],
            "properties": {
                "symbol": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 24,
                    "pattern": "^[A-Za-z0-9._-]+$",
                },
                "security_name": {
                    "type": ["string", "null"],
                    "maxLength": 160,
                },
                "security_code": {
                    "type": ["string", "null"],
                    "maxLength": 64,
                },
            },
        },
        "position": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "security",
                "asset_class",
                "quantity",
                "currency",
                "broker_or_custodian",
                "subaccount_ref",
            ],
            "properties": {
                "security": {"$ref": "#/$defs/security"},
                "asset_class": {
                    "enum": ["EQUITY", "MUTUAL_FUND", "BOND", "OTHER"]
                },
                "quantity": {
                    "type": "string",
                    "pattern": "^(0|[1-9][0-9]*)(\\.[0-9]*[1-9])?$",
                },
                "currency": {
                    "type": ["string", "null"],
                    "pattern": "^[A-Z]{3}$",
                },
                "broker_or_custodian": {
                    "type": ["string", "null"],
                    "maxLength": 120,
                },
                "subaccount_ref": {
                    "type": ["string", "null"],
                    "pattern": "^ksa_[0-9a-f]{64}$",
                },
            },
        },
        "cash": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "currency",
                "amount",
                "bank_or_custodian",
                "subaccount_ref",
            ],
            "properties": {
                "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
                "amount": {
                    "type": "string",
                    "pattern": "^(0|[1-9][0-9]*)(\\.[0-9]*[1-9])?$",
                },
                "bank_or_custodian": {
                    "type": ["string", "null"],
                    "maxLength": 120,
                },
                "subaccount_ref": {
                    "type": ["string", "null"],
                    "pattern": "^ksa_[0-9a-f]{64}$",
                },
            },
        },
        "endpoint_evidence": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "endpoint_class",
                "succeeded",
                "observed_rows",
                "accepted_rows",
                "rejected_rows",
                "failure_code",
            ],
            "properties": {
                "endpoint_class": {"enum": list(_ENDPOINT_CLASSES)},
                "succeeded": {"type": "boolean"},
                "observed_rows": {"type": "integer", "minimum": 0},
                "accepted_rows": {"type": "integer", "minimum": 0},
                "rejected_rows": {"type": "integer", "minimum": 0},
                "failure_code": {
                    "type": ["string", "null"],
                    "enum": [
                        None,
                        "HTTP_ERROR",
                        "AUTH_REQUIRED",
                        "TIMEOUT",
                        "PROVIDER_UNAVAILABLE",
                        "SCHEMA_MISMATCH",
                        "ROW_VALIDATION_FAILED",
                        "UNKNOWN",
                    ],
                },
            },
        },
        "provenance": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "source",
                "adapter_version",
                "raw_response_sha256",
                "endpoint_set",
                "source_commit_pins",
            ],
            "properties": {
                "source": {"const": "AKSES_KSEI_PERSONAL"},
                "adapter_version": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 64,
                    "pattern": "^[A-Za-z0-9._-]+$",
                },
                "raw_response_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "endpoint_set": {
                    "type": "array",
                    "minItems": 6,
                    "maxItems": 6,
                    "prefixItems": [
                        {"const": endpoint_class} for endpoint_class in _ENDPOINT_CLASSES
                    ],
                    "items": False,
                },
                "source_commit_pins": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nichsedge/ksei-mcp", "chickenzord/goksei"],
                    "properties": {
                        "nichsedge/ksei-mcp": {"const": KSEI_MCP_PIN},
                        "chickenzord/goksei": {"const": GOKSEI_PIN},
                    },
                },
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(
    PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1,
    format_checker=FormatChecker(),
)


def validate_snapshot_payload(payload: Mapping[str, Any]) -> None:
    """Validate canonical snapshot JSON against Draft 2020-12 with formats enabled."""
    errors = sorted(_VALIDATOR.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.absolute_path) or "<root>"
        raise ValueError(f"personal portfolio schema validation failed at {path}: {first.message}")
