Build a multi-tenant API gateway with distributed rate limiting, per the rules
in CLAUDE.md.

## Functional scope
- Reverse proxy fronting 3 mock upstream services with different latency and
  error-rate profiles (fast/reliable, slow, flaky)
- Per-tenant and per-endpoint rate limits, configurable at runtime without
  restart
- API key auth resolving to a tenant with a quota tier (free/pro/enterprise)
- Idempotency key support on POST with a replay window
- Request/response logging with a propagated trace ID

## Explicitly in scope for the ADR (do not skip any)
1. Rate limit algorithm: fixed window vs sliding window log vs sliding window
   counter vs token bucket vs leaky bucket. Cover memory cost per tenant,
   burst behavior, and boundary-spike behavior.
2. Counter storage: local in-memory vs Redis centralized vs Redis with local
   pre-allocated batches vs gossip-based approximate counting. Cover the
   accuracy/latency trade-off explicitly with numbers.
3. Behavior when the counter store is unreachable: fail-open vs fail-closed vs
   degrade-to-local. Argue for one and name the business context where the
   other is correct.
4. Limiter sharding: modulo hashing vs consistent hashing with virtual nodes vs
   rendezvous hashing. Quantify key movement on adding a node.
5. Hot key handling when one tenant's traffic concentrates on a single shard.
6. Circuit breaker placement and state machine, including half-open probing.
7. Retry policy and why exponential backoff without jitter causes correlated
   retry storms.
8. Noisy-neighbor isolation: shared thread pool vs per-tenant bulkhead vs
   weighted fair queuing.
9. Idempotency key storage: what is fingerprinted, TTL, and what happens on a
   concurrent duplicate that arrives while the first is still in flight.

## TODO(learner) gaps — write signature, docstring, wiring, and FAILING tests only
- `sliding_window_counter_allow()` — the Lua script body and its Python/Go caller
- `consistent_hash_ring.add_node()` and `.get_node()` including virtual nodes
- `CircuitBreaker.record_result()` — the full state transition logic
- `compute_backoff_delay()` — exponential with full jitter

## Load testing
Provide k6 scripts for: (a) steady state at 80% of limit, (b) a single tenant
bursting to 50x limit, (c) ramp to find the p99 knee, (d) Redis killed mid-test.
The chaos target: prove that one abusive tenant does not move p99 for others.

## Failure lab — include at least these
- Kill Redis under load. Predict the p99 and the error rate first.
- Add 200ms latency to Redis with `tc netem`. Where does it show up?
- Point two gateway instances at desynchronized clocks. What breaks and why?
- Make one upstream return 500s. Watch the breaker trip and recover.
- Send the same idempotency key from two concurrent clients.

Start with docs/ADR-000-architecture.md only. Stop and wait for approval.