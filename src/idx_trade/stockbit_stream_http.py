"""Bounded HTTP resilience for the prospective Stockbit/IDX acquisition lane.

Retries are intentionally narrow because every authenticated Zapi REST attempt
consumes monthly quota, including cached/error attempts observed in the live
provider-acceptance audit.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class BoundedRetrySession:
    """Small requests.Session adapter with deterministic bounded retry semantics.

    Retry only transient transport failures and provider 5xx responses. Auth,
    quota, and other 4xx responses are returned immediately so the caller can
    fail closed without multiplying billable attempts.
    """

    session: requests.Session = field(default_factory=requests.Session)
    max_attempts: int = 3
    timeout_seconds: float = 30.0
    backoff_seconds: tuple[float, ...] = (1.0, 2.0)
    attempts: int = 0
    transient_events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.max_attempts > 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def _sleep(self, attempt: int) -> None:
        index = attempt - 1
        delay = self.backoff_seconds[index] if index < len(self.backoff_seconds) else 0.0
        if delay > 0:
            time.sleep(delay)

    def get(self, url: str, *, params: dict[str, Any], headers: dict[str, str], timeout: float | None = None):
        effective_timeout = self.timeout_seconds if timeout is None else timeout
        last_exc: requests.RequestException | None = None

        for attempt in range(1, self.max_attempts + 1):
            self.attempts += 1
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=effective_timeout,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                self.transient_events.append(
                    {
                        "attempt": attempt,
                        "kind": type(exc).__name__,
                        "status_code": None,
                    }
                )
                if attempt == self.max_attempts:
                    raise
                self._sleep(attempt)
                continue

            if 500 <= int(response.status_code) <= 599 and attempt < self.max_attempts:
                self.transient_events.append(
                    {
                        "attempt": attempt,
                        "kind": "HTTP_5XX",
                        "status_code": int(response.status_code),
                    }
                )
                self._sleep(attempt)
                continue

            return response

        if last_exc is not None:  # pragma: no cover - loop exits via raise above
            raise last_exc
        raise RuntimeError("bounded retry loop exhausted without response")
