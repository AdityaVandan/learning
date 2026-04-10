# Rate Limiting

Rate limiting controls how many requests a client can make to a service in a given time period. It protects services from abuse, overload, and ensures fair resource distribution.

---

## Table of Contents

1. [Why Rate Limiting?](#why-rate-limiting)
2. [Implementations](#implementations)
3. [Algorithms Overview](#algorithms-overview)
4. [Token Bucket](#1-token-bucket)
5. [Leaky Bucket](#2-leaky-bucket)
6. [Fixed Window Counter](#3-fixed-window-counter)
7. [Sliding Window Log](#4-sliding-window-log)
8. [Sliding Window Counter](#5-sliding-window-counter-hybrid)
9. [Algorithm Comparison](#algorithm-comparison)
10. [Real-World Caveats](#real-world-caveats)
11. [Distributed Rate Limiting](#distributed-rate-limiting)

---

## Implementations

Each algorithm has implementations in two languages. Both versions implement the same logic and include unsafe (no-lock) variants to expose race conditions, and safe variants protected by the appropriate concurrency primitive.

| Algorithm | TypeScript | Go |
|---|---|---|
| Token Bucket | [token-bucket.ts](algorithms/typescript/token-bucket.ts) | [go/token-bucket/main.go](algorithms/go/token-bucket/main.go) |
| Leaky Bucket | [leaky-bucket.ts](algorithms/typescript/leaky-bucket.ts) | [go/leaky-bucket/main.go](algorithms/go/leaky-bucket/main.go) |
| Fixed Window | [fixed-window.ts](algorithms/typescript/fixed-window.ts) | [go/fixed-window/main.go](algorithms/go/fixed-window/main.go) |
| Sliding Window Log | [sliding-window-log.ts](algorithms/typescript/sliding-window-log.ts) | [go/sliding-window-log/main.go](algorithms/go/sliding-window-log/main.go) |
| Sliding Window Counter | [sliding-window-counter.ts](algorithms/typescript/sliding-window-counter.ts) | [go/sliding-window-counter/main.go](algorithms/go/sliding-window-counter/main.go) |

### Running the Go demos

```bash
cd algorithms/go

# Run any algorithm
go run ./token-bucket/
go run ./leaky-bucket/
go run ./fixed-window/
go run ./sliding-window-log/
go run ./sliding-window-counter/

# Run with Go's race detector — it will flag data races in the Unsafe variants
go run -race ./token-bucket/
go run -race ./fixed-window/
```

### Go vs TypeScript: concurrency model differences

TypeScript runs on a single-threaded event loop. "Concurrency" is cooperative — `async`/`await` yields the event loop at every `await`. A race only occurs if you `await` between a check and a write (e.g., between `redis.get()` and `redis.set()`).

Go uses OS threads via goroutines. Multiple goroutines genuinely run in parallel on separate CPU cores. A race occurs the moment two goroutines touch the same memory without a lock — no `await` required. This makes Go races harder to reproduce and harder to find without the race detector.

```
TypeScript async race:              Go goroutine race:

async function allow() {            func (tb *TokenBucket) Allow() bool {
  const t = await redis.get(key)      // goroutine A reads tb.tokens = 1
  //      ↑ event loop yields here    if tb.tokens >= 1 {
  // other async fn can now run         // goroutine B ALSO reads 1 here
  // and read the same value            // (running on a different CPU core)
  if (t >= 1) {                        tb.tokens--   // both decrement
    await redis.set(key, t - 1)        return true   // both return true
  }                                  }
}                                   }
```

The `UnsafeXxx` structs in each Go file omit `sync.Mutex` and use `runtime.Gosched()` at the critical gap to force the Go scheduler to context-switch to another goroutine at exactly the right moment — making the race reliably visible rather than just theoretically possible.

---

## Why Rate Limiting?

```
Without Rate Limiting:

Client A ──────────────────────────────────────▶ │
Client B ──────────────────────────────────────▶ │  Service
Client C (malicious) ══════════════════════════▶ │  💥 Overloaded
                    unlimited requests            │

With Rate Limiting:

Client A ───── ✓ ✓ ✓ ✗ ✗ (throttled) ─────────▶ │
Client B ───── ✓ ✓ ✓ ✗ ✗ (throttled) ─────────▶ │  Service
Client C ───── ✓ ✗ ✗ ✗ ✗ (blocked)   ─────────▶ │  ✅ Protected
                  per-key enforcement              │
```

---

## Algorithms Overview

```
                    ┌─────────────────────────────────────────────┐
                    │           Rate Limiting Algorithms           │
                    └────────────────────┬────────────────────────┘
                                         │
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
     ┌─────▼──────┐              ┌───────▼───────┐             ┌──────▼──────┐
     │   Bucket   │              │  Fixed Window │             │   Sliding   │
     │  Algorithms│              │   Counter     │             │   Window    │
     └─────┬──────┘              └───────────────┘             └──────┬──────┘
           │                      Simple, O(1)                        │
     ┌─────┴────────┐             Boundary spike!          ┌──────────┴──────────┐
     │              │                                       │                     │
┌────▼─────┐  ┌─────▼─────┐                         ┌──────▼──────┐  ┌──────────▼──────┐
│  Token   │  │  Leaky    │                         │  Sliding    │  │    Sliding      │
│  Bucket  │  │  Bucket   │                         │  Window Log │  │ Window Counter  │
└──────────┘  └───────────┘                         └─────────────┘  └─────────────────┘
 Allows burst  Smooth output                         Accurate, O(n)   Approx, O(1)
 O(1)          O(capacity)                           Memory heavy     Redis-friendly
```

---

## 1. Token Bucket

**TypeScript:** [algorithms/typescript/token-bucket.ts](algorithms/typescript/token-bucket.ts) | **Go:** [algorithms/go/token-bucket/main.go](algorithms/go/token-bucket/main.go)

### Concept

A bucket holds tokens up to a fixed capacity. Tokens are added at a steady refill rate. Each request consumes one (or more) tokens. If insufficient tokens exist, the request is rejected.

```
  Refill: 2 tokens/sec
                │
       ┌────────▼────────┐
       │  ○ ○ ○ ○ ○      │  ← capacity = 5 tokens
       │                 │
       └────────┬────────┘
                │
    Request ────┤  consumes 1 token
                ▼
       Allowed if tokens ≥ 1

Timeline:

t=0s   [○○○○○] 5 tokens full
t=0    Req 1 → [○○○○ ] 4 left  ✓
t=0    Req 2 → [○○○  ] 3 left  ✓
t=0    Req 3 → [○○   ] 2 left  ✓
t=0    Req 4 → [○    ] 1 left  ✓
t=0    Req 5 → [     ] 0 left  ✓ (burst consumed)
t=0    Req 6 → [     ] REJECTED ✗
t=1s   Refill → [○○  ] 2 new tokens
t=1s   Req 7 → [○    ] ✓
t=1s   Req 8 → [     ] ✓
t=1s   Req 9 → [     ] REJECTED ✗
```

### Key Properties

| Property | Value |
|---|---|
| Burst allowed | Yes, up to capacity |
| Output rate | Variable (up to capacity at once) |
| Memory | O(1) per key |
| Complexity | O(1) per request |

### How it works internally

```
allowRequest(key):
  1. mutex.acquire(key)           ← prevent concurrent over-count
  2. now = currentTime()
  3. elapsed = now - lastRefillTime
  4. tokens = min(capacity, tokens + elapsed × refillRate)
  5. lastRefillTime = now
  6. if tokens >= required:
       tokens -= required
       return ALLOW
     else:
       return REJECT
  7. mutex.release(key)
```

---

## 2. Leaky Bucket

**TypeScript:** [algorithms/typescript/leaky-bucket.ts](algorithms/typescript/leaky-bucket.ts) | **Go:** [algorithms/go/leaky-bucket/main.go](algorithms/go/leaky-bucket/main.go)

### Concept

Requests enter a fixed-size queue ("bucket"). A processor drips requests out at a constant rate. If the queue is full when a new request arrives, that request overflows (rejected). Unlike Token Bucket, output is always a steady rate — no bursting downstream.

```
Incoming requests (bursty):                   Outgoing (smooth):
                                               
  ■ ■ ■ ■ ■ ■ ─────────▶  ┌──────────┐  ───drip──▶  ■  (every 200ms)
  (all at once)            │ ■ ■ ■    │
                           │          │  ───drip──▶  ■
                           │  queue   │
              overflow ◀── │ capacity │  ───drip──▶  ■
              (rejected)   │    = 3   │
                           └──────────┘
                           
  Bucket full: incoming ■ ■ → REJECTED immediately
```

### Classical vs Counter Variant

```
Classical (Queue-based):            Counter-based (Simplified):
  
  Request → [enqueue]              Request → check level
  Queue dripped at rate R            level = max(0, level - elapsed×rate)
  Queue full → reject                if level + 1 > capacity → reject
  Queued requests eventually         else level++, allow
  processed (delayed, not lost)      (requests NOT queued, rejected fast)
  
  ✓ Requests smoothed out           ✓ O(1), no actual queue
  ✗ Latency for queued requests     ✗ Still rejects at high load
```

### Key Properties

| Property | Classical Queue | Counter Variant |
|---|---|---|
| Output rate | Perfectly smooth | Not enforced (just counting) |
| Memory | O(capacity) per key | O(1) per key |
| Burst handling | Queued (delayed) | Rejected |
| Latency | Added for queued requests | Immediate |

### How it works internally

```
Classical Queue:
  allowRequest(key):
    1. mutex.acquire(key)
    2. if queue.length >= capacity → REJECT (overflow)
    3. enqueue Promise; start drip timer if not running
    4. mutex.release(key)
    5. return Promise (resolved when drip processes it)
  
  Drip timer (every leakRateMs):
    1. mutex.acquire(key)
    2. dequeue oldest request; resolve its Promise(true)
    3. if queue empty → stop timer
    4. mutex.release(key)
```

---

## 3. Fixed Window Counter

**TypeScript:** [algorithms/typescript/fixed-window.ts](algorithms/typescript/fixed-window.ts) | **Go:** [algorithms/go/fixed-window/main.go](algorithms/go/fixed-window/main.go)

### Concept

Time is divided into fixed-size windows (e.g., every 60 seconds). A counter per key per window tracks requests. When the counter hits the limit, requests are rejected until the window resets.

```
  Window 1 (0s–60s)    Window 2 (60s–120s)   Window 3 (120s–180s)
  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ count: 10/10    │  │ count: 0/10      │  │ count: 0/10      │
  │ (limit reached) │  │ (reset!)         │  │                  │
  └─────────────────┘  └──────────────────┘  └──────────────────┘
        │                      │
     REJECT                  ALLOW (counter reset)
```

### The Boundary Spike Problem

This is the key vulnerability of Fixed Window:

```
  Window 1 (0s-60s)       Window 2 (60s-120s)
  ──────────────────────┬──────────────────────
                        │
                  10 req │ 10 req
               (55s-60s) │ (60s-65s)
                        │
  ←────── 10s span ──────│────────────────────▶
                        │
  In just 10 seconds, 20 requests passed despite a "10/min" limit!
  
  This is a 2× spike at every window boundary.
```

### Key Properties

| Property | Value |
|---|---|
| Boundary spike | Yes (up to 2× limit at boundaries) |
| Memory | O(1) per key |
| Complexity | O(1) |
| Simplicity | Very simple |

### How it works internally

```
allowRequest(key):
  1. mutex.acquire(key)
  2. now = currentTime()
  3. windowStart = floor(now / windowSizeMs) × windowSizeMs
  4. if state.windowStart < windowStart:
       state = { count: 0, windowStart }   ← reset
  5. if state.count >= limit → REJECT
  6. state.count++
  7. mutex.release(key)
  8. return ALLOW
```

---

## 4. Sliding Window Log

**TypeScript:** [algorithms/typescript/sliding-window-log.ts](algorithms/typescript/sliding-window-log.ts) | **Go:** [algorithms/go/sliding-window-log/main.go](algorithms/go/sliding-window-log/main.go)

### Concept

Instead of a counter per window, keep a log of every request's timestamp within the last N seconds. On each new request, evict stale timestamps, then check if the log size is below the limit.

```
  Timestamps log for "user:alice" (limit=4, window=60s):
  
  t=10s: [10]               count=1  ✓
  t=20s: [10, 20]           count=2  ✓
  t=30s: [10, 20, 30]       count=3  ✓
  t=40s: [10, 20, 30, 40]   count=4  ✗ limit reached
  t=50s: [10, 20, 30, 40]   count=4  ✗ still full
  t=71s: evict t=10 (>60s ago)
         [20, 30, 40]        count=3  ✓ 71s added
         [20, 30, 40, 71]    count=4
  t=82s: evict t=20
         [30, 40, 71]        count=3  ✓ 82s added

  Sliding window: always looking back exactly 60s from NOW
  
        NOW - 60s                         NOW
          │                                │
          ├────────────────────────────────┤
          │   only these timestamps count  │
          │                                │
     evicted ──▶  [30]  [40]  [71]  [82]  │
                   ✓     ✓     ✓     ✓   (4 in window)
```

### No Boundary Spike

```
  Fixed Window:                    Sliding Window Log:
  
  ──────────┬──────────            continuously sliding
  9 req     │ 9 req     = 18!      always exactly last N seconds
            │
         boundary                  t=59s: 9 req logged (1s-59s)
                                   t=60s: only 9 req still in window
                                   t=61s: t=1 evicted → 8 req
                                   → NEVER allows 2x burst ✓
```

### Key Properties

| Property | Value |
|---|---|
| Accuracy | Exact (no approximation) |
| Boundary spike | None |
| Memory | O(limit) per key — can be high |
| Complexity | O(log n) eviction (binary search) |

### How it works internally

```
allowRequest(key):
  1. mutex.acquire(key)
  2. cutoff = now - windowMs
  3. evict all timestamps < cutoff (binary search for efficiency)
  4. if log.length >= limit → REJECT
  5. log.push(now)
  6. mutex.release(key)
  7. return ALLOW
```

---

## 5. Sliding Window Counter (Hybrid)

**TypeScript:** [algorithms/typescript/sliding-window-counter.ts](algorithms/typescript/sliding-window-counter.ts) | **Go:** [algorithms/go/sliding-window-counter/main.go](algorithms/go/sliding-window-counter/main.go)

### Concept

A memory-efficient approximation of Sliding Window Log. Instead of storing every timestamp, keep only two counters: one for the previous complete window and one for the current window. Use a weighted formula to approximate the count over the true sliding window.

```
  Formula:
  estimate = prevCount × (1 - elapsedFraction) + currCount

  Where:
    elapsedFraction = (now - currentWindowStart) / windowSize  [0.0 to 1.0]

  Example (limit=100, window=60s):
  ┌────────────────────────────┬──────────────────────────────┐
  │  Previous Window           │  Current Window              │
  │  prevCount = 80            │  currCount = 30              │
  │  (complete)                │  elapsed = 40s (fraction=0.67)│
  └────────────────────────────┴──────────────────────────────┘
  
  estimate = 80 × (1 - 0.67) + 30
           = 80 × 0.33       + 30
           = 26.4             + 30
           = 56.4   ← estimated requests in last 60s
  
  56.4 < 100 → ALLOW ✓
```

### Visual: How the Weight Shifts

```
  As we move through the current window, prev contributes less:

  Elapsed: 0%          25%         50%         75%         100%
           │            │           │            │            │
  Prev     │████████████│▓▓▓▓▓▓▓▓  │▓▓▓▓        │▓▓          │
  weight   │ 100%       │  75%      │  50%       │  25%       │ 0%
           │            │           │            │            │
  Curr     │            │░░░░        │░░░░░░░░    │░░░░░░░░░░░░│████████████
  weight   │ 0%         │  25%      │  50%       │  75%       │ 100%
```

### Key Properties

| Property | Value |
|---|---|
| Accuracy | ~Approximate (assumes even distribution) |
| Memory | O(1) per key (just 2 counters) |
| Complexity | O(1) |
| Scalability | Excellent — used by Redis/Nginx |

### How it works internally

```
allowRequest(key):
  1. mutex.acquire(key)
  2. currentWindowStart = floor(now / windowMs) × windowMs
  3. if new window: roll curr→prev, reset curr=0
  4. elapsedFraction = (now - windowStart) / windowMs
  5. estimate = prevCount × (1 - elapsedFraction) + currCount
  6. if estimate >= limit → REJECT
  7. currCount++
  8. mutex.release(key)
  9. return ALLOW
```

---

## Algorithm Comparison

```
┌───────────────────────┬──────────┬──────────┬─────────────┬───────────────────┬──────────────────────┐
│ Algorithm             │ Memory   │ Time     │ Burst?      │ Accuracy          │ Best For             │
├───────────────────────┼──────────┼──────────┼─────────────┼───────────────────┼──────────────────────┤
│ Token Bucket          │ O(1)     │ O(1)     │ Yes (burst) │ High              │ APIs, allowing bursts│
│ Leaky Bucket          │ O(cap)   │ O(1)     │ No (smooth) │ High              │ Downstream smoothing │
│ Fixed Window Counter  │ O(1)     │ O(1)     │ At boundary │ Low (2× spike)    │ Simple, rough limits │
│ Sliding Window Log    │ O(limit) │ O(log n) │ No          │ Exact             │ Strict accuracy needs│
│ Sliding Window Counter│ O(1)     │ O(1)     │ No          │ Good (~5% error)  │ Scale, distributed   │
└───────────────────────┴──────────┴──────────┴─────────────┴───────────────────┴──────────────────────┘
```

### Decision Guide

```
Need to allow traffic bursts?
  └─ YES → Token Bucket
  └─ NO  → Need smooth output rate?
            └─ YES → Leaky Bucket
            └─ NO  → Memory constrained?
                      └─ YES → Fixed Window or Sliding Window Counter
                      └─ NO  → Need exact accuracy?
                                └─ YES → Sliding Window Log
                                └─ NO  → Sliding Window Counter
```

---

## Real-World Caveats

### 1. Concurrency Race Conditions

**The problem:** In any async system, the check-then-act sequence is NOT atomic:

```
Without mutex (WRONG):

  Goroutine/Promise A:                 Goroutine/Promise B:
  1. reads tokens = 1                  1. reads tokens = 1
  2. passes check (1 >= 1)             2. passes check (1 >= 1)
  3. decrements tokens = 0             3. decrements tokens = 0 (already 0!)
     ✓ allowed                            ✓ allowed  ← OVER-COUNTED!

With mutex (CORRECT):

  Thread A acquires lock
  reads tokens = 1, decrements to 0, releases lock → ✓ allowed
  Thread B acquires lock
  reads tokens = 0, check fails, releases lock → ✗ rejected
```

**Solution in code:** Every `allowRequest` implementation in this folder wraps the read-check-write in a `Mutex`. In Node.js (single-threaded), this matters for async operations that yield the event loop between the check and the write (e.g., async Redis calls).

### 2. Distributed System Race (Multi-Node)

**The problem:** Multiple server instances each have their own in-memory state. A user can hit 10 different nodes and bypass per-node limits:

```
  Node 1: count = 8/10  → allows req (count=9)
  Node 2: count = 8/10  → allows req (count=9)  ← same user!
  Node 3: count = 8/10  → allows req (count=9)

  Actual requests: 27, but each node thinks limit not exceeded!
```

**Solution:** Use a shared atomic store (Redis):

```
Redis INCR pattern (atomic):
  MULTI
  INCR  "ratelimit:{key}:{window}"
  EXPIRE "ratelimit:{key}:{window}" windowSizeSeconds
  EXEC

Redis Lua script for token bucket (truly atomic):
  local tokens = redis.call('GET', key)
  -- refill logic
  -- check and decrement
  -- all in one atomic operation
```

### 3. Clock Skew in Distributed Systems

**The problem:** Different servers have slightly different system clocks. A request at `t=999ms` on Node A and `t=1001ms` on Node B may end up in different windows even though they arrived almost simultaneously.

```
  Node A clock: 12:00:00.999  → Window 1
  Node B clock: 12:00:01.001  → Window 2 (window just reset!)
  
  Result: User effectively gets limit × 2 requests at the boundary
```

**Solutions:**
- Use a centralized time source (Redis `TIME` command)
- Use NTP with tight sync across nodes
- Add small grace periods at window boundaries

### 4. Memory Leaks from Stale State

**The problem:** Rate limiters store state per key. If keys are unique per request (e.g., per-IP), the map grows unbounded:

```
  Attacker sends from 1,000,000 different IPs
  → 1,000,000 entries in your map
  → Out of memory!
```

**Solutions:**
- TTL-based expiry: delete state after `windowMs` of inactivity
- LRU eviction: cap the map size, evict least recently used
- Redis: use `EXPIRE` to auto-delete stale keys

### 5. Thundering Herd at Window Reset

**The problem:** Fixed Window resets all counters simultaneously. All blocked clients retry at the same instant:

```
  t=59.999s: 1000 clients are blocked
  t=60.000s: Window resets!
             → 1000 clients all retry simultaneously
             → Sudden spike: first N pass, rest blocked again
             → Repeat every window boundary
```

**Solutions:**
- Use Sliding Window (eliminates fixed reset points)
- Add jitter to retry logic: `sleep(rand(0, windowMs))`
- Implement exponential backoff in clients

### 6. High Cardinality (Per-User vs Global)

```
  Global limiter: 1 counter for entire service
  ┌────────────────────────────────┐
  │  Total: 1000 req/sec           │
  │  User A uses 999, User B → 1  │
  └────────────────────────────────┘  ← unfair

  Per-user limiter: 1 counter per user
  ┌────────────────────────────────┐
  │  User A: 100 req/sec           │
  │  User B: 100 req/sec           │
  │  User C: 100 req/sec           │
  └────────────────────────────────┘  ← fair, but high memory
  
  Strategy: layered limiting — global + per-user + per-endpoint
```

### 7. Token Bucket: Refill Precision vs. Performance

**The problem:** Computing refill on every request requires reading the current time and doing floating-point math. Under millions of requests/sec, this adds up.

**Solutions:**
- **Lazy refill** (what's implemented here): Refill lazily on each `allowRequest` call instead of on a timer. Accurate and no background goroutine needed.
- **Batch refill**: Use a background timer to refill in bulk (e.g., every 100ms). Simpler but slightly less precise.

### 8. Go: sync.Mutex vs sync.RWMutex vs sync/atomic

Not all locks are the same cost. Choosing the right primitive matters at scale:

```
sync.Mutex      — full exclusive lock, one goroutine at a time
                  Use for: allow() — always reads AND writes state

sync.RWMutex    — multiple concurrent readers OR one writer
                  Use for: status/getEstimate — read-only calls that
                  don't modify state can proceed concurrently
                  Lock()   → write (exclusive)
                  RLock()  → read (shared, parallel safe)

sync/atomic     — lock-free single-variable operations (INCR, CAS)
                  Use for: simple counters that don't have a
                  check-then-act compound step
                  atomic.AddInt64(&count, 1)  // always safe

  Performance (rough ordering, fastest → slowest):
  atomic ops > RLock/RUnlock > Lock/Unlock > channel send/receive
```

The Go implementations use `sync.Mutex` on the per-key state rather than a global lock. This is the **per-key locking** pattern — different users never contend on each other's locks:

```go
// Global lock (BAD at scale):
func (fw *FixedWindow) Allow(key string) bool {
    fw.globalMu.Lock()   // ← all keys serialise here!
    defer fw.globalMu.Unlock()
    ...
}

// Per-key lock via sync.Map (GOOD):
type keyState struct {
    mu    sync.Mutex
    count int64
}
// sync.Map stores *keyState per key; only same-key requests contend
```

### 9. Go Race Detector

Go ships with a built-in data race detector. Run any of the Go demos with `-race` to see it flag the `UnsafeXxx` variants:

```bash
go run -race ./fixed-window/
# OUTPUT:
# ==================
# WARNING: DATA RACE
# Write at 0x00c0001b4010 by goroutine 8:
#   main.(*UnsafeFixedWindow).Allow(...)
# Previous read at 0x00c0001b4010 by goroutine 7:
#   main.(*UnsafeFixedWindow).Allow(...)
# ==================
```

The safe variants produce zero race warnings. Use `-race` in CI to catch any regression.

### 10. Async Event Loop in Node.js

Even though Node.js is single-threaded, **async operations yield the event loop**, creating interleaving:

```
async function allowRequest(key) {
  const state = await redis.get(key);   // ← yields event loop here!
  // Another request can now run and read the SAME state
  if (state.tokens > 0) {
    state.tokens--;
    await redis.set(key, state);         // ← and here!
  }
}
```

**The mutex in this codebase guards against exactly this.** Even though reads/writes are synchronous in the in-memory implementations, the mutex pattern is essential when the storage is async (Redis, database).

---

## Distributed Rate Limiting

For production systems with multiple nodes, here are the standard approaches:

```
  Architecture 1: Centralized Redis

  [Node 1] ─────┐
  [Node 2] ──── │──▶ [Redis] ← single source of truth
  [Node 3] ─────┘    (atomic INCR, Lua scripts)

  ✓ Accurate across all nodes
  ✗ Redis becomes bottleneck / SPOF

  Architecture 2: Redis Cluster with Consistent Hashing

  [Node 1] ──▶ [Redis Shard A]  ← user:alice, user:bob
  [Node 2] ──▶ [Redis Shard B]  ← user:carol, user:dave
  [Node 3] ──▶ [Redis Shard C]  ← user:eve, user:frank

  ✓ Horizontally scalable
  ✓ Still accurate (each key has one owner shard)
  ✗ Resharding complexity

  Architecture 3: Token Bucket with Local + Global Sync

  Each node: local 10 req/sec limit
  Global Redis: 100 req/sec across 10 nodes

  Request flow:
  1. Check local bucket (fast, in-memory)
  2. If local allows, also decrement global counter
  3. Periodically sync local refill from global

  ✓ Low latency (mostly local)
  ✓ Eventual consistency on global limits
  ✗ Brief over-counting possible during sync lag
```

### Redis Implementation Sketch (Sliding Window Counter)

```algorithms/typescript
// Atomic Lua script — Redis executes this as a single transaction
const SLIDING_WINDOW_SCRIPT = `
  local key = KEYS[1]
  local now = tonumber(ARGV[1])
  local window = tonumber(ARGV[2])
  local limit = tonumber(ARGV[3])
  local windowStart = now - (now % window)
  local prevKey = key .. ":" .. (windowStart - window)
  local currKey = key .. ":" .. windowStart
  local prevCount = tonumber(redis.call("GET", prevKey) or 0)
  local currCount = tonumber(redis.call("GET", currKey) or 0)
  local elapsed = (now % window) / window
  local estimate = prevCount * (1 - elapsed) + currCount
  if estimate >= limit then
    return 0  -- rejected
  end
  redis.call("INCR", currKey)
  redis.call("EXPIRE", currKey, math.ceil(window / 1000) * 2)
  return 1  -- allowed
`;
```
