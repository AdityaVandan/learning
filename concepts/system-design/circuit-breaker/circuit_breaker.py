from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Optional, TypeVar


T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    open_duration_seconds: float = 10.0
    half_open_max_calls: int = 1


class CircuitBreakerOpenError(RuntimeError):
    pass


class CircuitBreaker(Generic[T]):
    """
    Minimal circuit breaker reference implementation.

    Trips OPEN on consecutive failures while CLOSED.
    After open_duration, enters HALF_OPEN and allows limited probe calls.
    Closes after enough consecutive probe successes (equal to half_open_max_calls).
    """

    def __init__(
        self,
        *,
        name: str,
        config: CircuitBreakerConfig = CircuitBreakerConfig(),
        is_failure: Optional[Callable[[BaseException], bool]] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if config.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if config.open_duration_seconds <= 0:
            raise ValueError("open_duration_seconds must be > 0")
        if config.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")

        self._name = name
        self._cfg = config
        self._clock = clock
        self._is_failure = is_failure or (lambda _exc: True)

        self._state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0

        self._opened_at: Optional[float] = None
        self._half_open_in_flight_or_used = 0
        self._half_open_successes = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> CircuitBreakerState:
        self._maybe_transition_from_open()
        return self._state

    def allow_request(self) -> bool:
        self._maybe_transition_from_open()
        if self._state == CircuitBreakerState.CLOSED:
            return True
        if self._state == CircuitBreakerState.OPEN:
            return False
        return self._half_open_in_flight_or_used < self._cfg.half_open_max_calls

    def call(self, fn: Callable[[], T], *, fallback: Optional[Callable[[BaseException], T]] = None) -> T:
        if not self.allow_request():
            err = CircuitBreakerOpenError(f"Circuit breaker '{self._name}' is OPEN")
            if fallback is not None:
                return fallback(err)
            raise err

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_in_flight_or_used += 1

        try:
            result = fn()
        except BaseException as exc:
            self._on_failure(exc)
            if fallback is not None:
                return fallback(exc)
            raise
        else:
            self._on_success()
            return result

    def _on_success(self) -> None:
        if self._state == CircuitBreakerState.CLOSED:
            self._consecutive_failures = 0
            return

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self._cfg.half_open_max_calls:
                self._transition_to_closed()

    def _on_failure(self, exc: BaseException) -> None:
        if not self._is_failure(exc):
            return

        if self._state == CircuitBreakerState.CLOSED:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._cfg.failure_threshold:
                self._transition_to_open()
            return

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        self._state = CircuitBreakerState.OPEN
        self._opened_at = self._clock()
        self._consecutive_failures = 0
        self._half_open_in_flight_or_used = 0
        self._half_open_successes = 0

    def _transition_to_half_open(self) -> None:
        self._state = CircuitBreakerState.HALF_OPEN
        self._opened_at = None
        self._half_open_in_flight_or_used = 0
        self._half_open_successes = 0

    def _transition_to_closed(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._opened_at = None
        self._consecutive_failures = 0
        self._half_open_in_flight_or_used = 0
        self._half_open_successes = 0

    def _maybe_transition_from_open(self) -> None:
        if self._state != CircuitBreakerState.OPEN:
            return
        if self._opened_at is None:
            return

        elapsed = self._clock() - self._opened_at
        if elapsed >= self._cfg.open_duration_seconds:
            self._transition_to_half_open()

