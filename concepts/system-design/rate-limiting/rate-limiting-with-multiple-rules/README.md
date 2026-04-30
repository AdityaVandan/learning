## Rate limiting with multiple rules

When a system enforces *more than one* rate-limit rule at the same time (for example: `(maxRequests, intervalWindow)` pairs for **per-user**, **per-IP**, **per-endpoint**, and **global** limits), you need to define:

- **How rules combine** (ALL vs ANY, priority, “most restrictive wins”)
- **What to return** when blocked (which rule(s) triggered, `Retry-After`)
- **How to count** when multiple rules apply (atomicity, fairness, cost)
- **How to scale** (single node vs distributed store)

This folder contains a small reference implementation in TypeScript:

- `multi-rule-rate-limiter.ts`: rule model + evaluation + in-memory store
- `example_usage.ts`: how you’d call it

---

## The core model: a rule is `(maxRequests, intervalWindow)`

A *rule* is typically:

- **maxRequests**: allowed count within the window
- **intervalWindow**: window length (fixed window, sliding window, token bucket, etc.)
- **keying**: what you are limiting (userId, ip, endpoint, org, tenant, API key, etc.)

Example rules you might apply to a single request:

- **Per-user**: 60 requests / 60s keyed by `userId`
- **Per-IP**: 300 requests / 60s keyed by `ip`
- **Per-endpoint per-user**: 10 requests / 10s keyed by `userId + endpoint`
- **Global**: 10k requests / 1s keyed by `service`

---

## How multiple rules combine (the most important decision)

### Option A: **ALL rules must pass** (recommended default)

This is the common “defense in depth” approach: a request is allowed only if **every** applicable rule would allow it.

- **Allow**: only if all rules allow
- **Block**: if any rule blocks
- **Who wins?**: the *most restrictive* rule (the one that blocks) effectively wins

This is what you want for:

- protecting scarce resources (DB, downstream APIs)
- ensuring global safety *and* per-tenant fairness
- stopping abusive clients even if they’re under another threshold

### Option B: **ANY rule may pass**

This is much rarer: allow if **at least one** rule allows. This is sometimes used when rules represent *alternative paths* (e.g., “paid plan OR internal service”).

- **Allow**: if any rule allows
- **Block**: only if all rules block

In practice, “ANY” is more often modeled as **allow-lists / bypass flags** (e.g., trusted service accounts) rather than rate-limit rules.

The reference code supports both as `mode: "ALL" | "ANY"`, but you’ll almost always want `"ALL"`.

---

## Returning the right `Retry-After` when blocked

When a request violates multiple rules, “how long should the client wait?” depends on the combination mode:

### For mode = **ALL**

Overall allow time is when **all violated rules** have recovered, so use:

- **retryAfterMs = max(rule.retryAfterMs for violated rules)**

Reason: the request remains blocked until the *slowest* rule opens up.

### For mode = **ANY**

Overall allow time is when **any** rule recovers, so use:

- **retryAfterMs = min(rule.retryAfterMs for violated rules)**

Reason: as soon as one rule allows, the request is allowed.

Also return **which rule(s)** were violated so clients and operators can understand what to change.

---

## Counting semantics when multiple rules apply

### Two-phase: “check then consume” vs “consume then decide”

You have two common patterns:

- **Check then consume**: evaluate rules first; only if allowed, increment counters.
  - Pros: avoids “charging” rejected requests
  - Cons: race conditions in distributed settings unless you do an atomic multi-update

- **Consume then decide**: increment first and see if you exceeded.
  - Pros: can be implemented as a single atomic increment per rule
  - Cons: rejected requests still consume budget (can be okay, and sometimes desirable)

The reference implementation does:

- **evaluate rules**
- **only consumes if allowed** (in-process atomicity is trivial; distributed needs care)

### Atomicity in distributed stores (important)

If you store counters in Redis/DynamoDB/etc. and you apply multiple rules, you want to avoid “partial updates”:

- Rule A consumed, Rule B rejected → you unintentionally charge one rule but reject anyway.

Solutions:

- **Single-script transaction** (e.g., Redis Lua): evaluate + update all relevant counters atomically
- **Idempotency key per request**: only count a request once across retries
- **Accept partial charges** intentionally (simpler, sometimes fine) and document it

---

## Rule conflicts and precedence

Even in `ALL` mode, you might want a deterministic way to pick a “primary reason” to surface:

- **Most restrictive remaining** (largest `retryAfterMs`)
- **Highest priority rule** (e.g., global safety rules > per-user rules)
- **Most specific rule** (endpoint+user > user > IP > global)

The implementation returns *all violated rules* and also a computed overall `retryAfterMs`, so you can surface whichever “reason” you prefer.

---

## Strategies that scale well in real systems

- **Hierarchical limits**: global → tenant → user → endpoint. Typically evaluated in `ALL` mode.
- **Burst + sustained**: pair a short window (burst) rule with a long window (sustained) rule.
  - Example: 20 req / 1s AND 200 req / 60s
- **Different algorithms per rule**:
  - Token bucket for bursty traffic
  - Sliding window for smooth fairness
  - Fixed window for cheap implementation

The example code implements a simple fixed-window counter per rule (good for learning and many internal services). For production, the same composition ideas apply regardless of the underlying limiter algorithm.
