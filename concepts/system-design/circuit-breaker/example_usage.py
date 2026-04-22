import random
import time

from circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError


class DownstreamError(RuntimeError):
    pass


def flaky_dependency_factory(*, fail_for_seconds: float):
    start = time.monotonic()

    def call() -> str:
        now = time.monotonic()
        if now - start < fail_for_seconds:
            raise DownstreamError("dependency is failing")
        return "OK"

    return call


def main() -> None:
    dependency = flaky_dependency_factory(fail_for_seconds=5.0)

    cb = CircuitBreaker(
        name="payment-service",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            open_duration_seconds=2.0,
            half_open_max_calls=2,
        ),
        is_failure=lambda exc: not isinstance(exc, ValueError),
    )

    def fallback(exc: BaseException) -> str:
        if isinstance(exc, CircuitBreakerOpenError):
            return "FALLBACK (open breaker): returning cached/stale response"
        return f"FALLBACK (call failed): {type(exc).__name__}"

    for i in range(1, 25):
        time.sleep(0.35)

        def attempt() -> str:
            # Simulate occasional caller error that should not trip the breaker
            if random.random() < 0.05:
                raise ValueError("caller bug (should not count as downstream failure)")
            return dependency()

        try:
            out = cb.call(attempt, fallback=fallback)
            print(f"{i:02d} state={cb.state.value:9s} -> {out}")
        except Exception as e:
            print(f"{i:02d} state={cb.state.value:9s} -> EXCEPTION: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

