# Caching Strategies - Simple Examples

This folder contains minimal Python examples for the most used caching strategies.

Run:

`python3 example.py`

Invalidation demos:

`python3 invalidation_example.py`

## Strategies included

- `cache_aside()` - app checks cache first, then DB on miss
- `read_through()` - app reads from cache layer, cache fetches DB on miss
- `write_through()` - writes go to DB and cache at the same time
- `write_back()` - writes go to cache first, DB updated later (flush)
- `write_around()` - writes go to DB only, cache updates on future reads
- `refresh_ahead()` - refresh cache before TTL expires
- `ttl_expiration()` - key automatically expires after configured time
- `negative_caching()` - cache "not found" to avoid repeated DB misses
- `request_coalescing()` - collapse concurrent cache misses into one DB call
- `two_level_cache()` - L1 in-memory + L2 shared/distributed cache

## Diagrams: Caching Strategies

### 1) Cache Aside
```mermaid
flowchart LR
    A[App] --> C{Cache hit?}
    C -->|Yes| R[Return from Cache]
    C -->|No| D[Read DB]
    D --> W[Write Cache]
    W --> R
```

### 2) Read Through
```mermaid
flowchart LR
    A[App] --> C[Cache Layer]
    C --> H{Hit?}
    H -->|Yes| R[Return value]
    H -->|No| D[Cache fetches DB]
    D --> U[Cache stores value]
    U --> R
```

### 3) Write Through
```mermaid
flowchart LR
    A[App write] --> C[Cache Layer]
    C --> D[Write DB]
    D --> W[Write Cache]
    W --> OK[Ack]
```

### 4) Write Back
```mermaid
flowchart LR
    A[App write] --> C[Write Cache]
    C --> Q[Queue / Dirty flag]
    C --> OK[Fast Ack]
    Q --> F[Async flush]
    F --> D[Write DB later]
```

### 5) Write Around
```mermaid
flowchart LR
    A[App write] --> D[Write DB only]
    D --> X[Invalidate/Delete cache key]
    X --> N[Next read refills cache]
```

### 6) Refresh Ahead
```mermaid
flowchart LR
    T[Background timer] --> K{TTL near expiry?}
    K -->|Yes| D[Fetch fresh value from DB]
    D --> C[Update cache and TTL]
    K -->|No| S[Skip]
```

### 7) TTL Expiration
```mermaid
flowchart LR
    S[Set key with TTL] --> T[Time passes]
    T --> E{TTL expired?}
    E -->|No| H[Cache hit]
    E -->|Yes| M[Cache miss]
```

### 8) Negative Caching
```mermaid
flowchart LR
    A[Read key] --> C{In cache?}
    C -->|NOT_FOUND marker| N[Return not found]
    C -->|Normal value| V[Return value]
    C -->|No| D[Read DB]
    D --> Z{Exists in DB?}
    Z -->|No| M[Cache NOT_FOUND with short TTL]
    Z -->|Yes| U[Cache value]
```

### 9) Request Coalescing (SingleFlight)
```mermaid
flowchart LR
    R1[Req 1 miss] --> L[Acquire per-key lock]
    R2[Req 2 miss] --> L
    R3[Req 3 miss] --> L
    L --> D[One DB read]
    D --> C[Fill cache]
    C --> A[All waiting requests return]
```

### 10) Two-Level Cache (L1 + L2)
```mermaid
flowchart LR
    A[App] --> L1{L1 hit?}
    L1 -->|Yes| R1[Return]
    L1 -->|No| L2{L2 hit?}
    L2 -->|Yes| B[Backfill L1]
    B --> R2[Return]
    L2 -->|No| D[Read DB]
    D --> U2[Write L2]
    U2 --> U1[Write L1]
    U1 --> R3[Return]
```

## Can these strategies be used together?

Yes. In most real systems, these patterns are combined along *orthogonal dimensions*:

1. Read orchestration: `cache_aside()` vs `read_through()` (and often “two-level” on top)
2. Write propagation: `write_through()` vs `write_back()` vs `write_around()`
3. Freshness management: `ttl_expiration()` plus optionally `refresh_ahead()`
4. Miss amplification controls: `negative_caching()` and `request_coalescing()`
5. Cache topology: `two_level_cache()` (and in general, more than one cache layer)

So the space of possible combinations is effectively a cartesian product of choices from these dimensions. Enumerating every exact product is usually not useful, so the README focuses on the *distinct families* of combinations you’ll actually see.

## Combination families (common, “sensible” ways to combine)

### Read-heavy systems (typical backend workloads)
- `cache_aside()` + `ttl_expiration()` + `request_coalescing()`
  - Minimizes DB load on misses; prevents cache stampedes for the same key.
- `cache_aside()` + `ttl_expiration()` + `negative_caching()` + `request_coalescing()`
  - Helps when many keys are absent (sparse IDs, optional resources).
- `cache_aside()` + `ttl_expiration()` + `refresh_ahead()` + `request_coalescing()`
  - Keeps hot keys fresh by refreshing before expiration instead of waiting for misses.

### Strong read-after-write behavior
- `cache_aside()` (read) + `write_through()` (write) + `ttl_expiration()`
  - Reads see updates quickly because writes update cache immediately.
- `read_through()` (read) + `write_through()` (write) + `ttl_expiration()`
  - Both read and write logic are centralized in the “cache layer”.

### Lower write cost / eventual consistency trade-offs
- `cache_aside()` (read) + `write_back()` (write) + `ttl_expiration()`
  - Writes are fast; the DB lags until async flush. Requires careful correctness thinking.
- `cache_aside()` (read) + `write_around()` (write) + `ttl_expiration()`
  - Often implemented as “write DB, then invalidate/expire cache” so future reads refill.

### Multi-level caches
- `two_level_cache()` + `ttl_expiration()` + `request_coalescing()`
  - L1 (fast) misses fall back to L2; coalescing prevents “everyone hits L2/DB” at once.
- `two_level_cache()` + `ttl_expiration()` + `refresh_ahead()`
  - Refresh hot keys in L1 (or L2) before they expire to keep p99 latency stable.
- `two_level_cache()` + `negative_caching()` (often on L2)
  - Avoids repeatedly checking the DB for missing keys across many app instances.

## Gotchas when combining patterns

- `write_back()` + `refresh_ahead()` can serve stale values unless you account for “not-yet-flushed” updates (refresh reads old DB state before the flush finishes).
- `negative_caching()` must handle the moment a previously-missing key becomes present (you typically use a TTL and/or explicit invalidation on writes).
- `request_coalescing()` is usually safe to add anywhere, but make sure the coalescing scope is correct (per-key, across the relevant cache layer).

## Cache Invalidation Strategies

Invalidation is how you ensure cache entries don’t become “wrong” after an update. Invalidation can be explicit (delete/expire) or implicit (versioning/conditional reads).

This folder already demonstrates `ttl_expiration()`. The additional common invalidation strategies below are usually layered on top of your read/write policies.

- Delete on write (a.k.a. “update DB then invalidate cache”)
  - Typical with `cache_aside()`-style reads: after the write, you delete the stale entry so the next read refills it.
- Versioned keys / generation counters (“bust” old entries by key name)
  - Typical when you want to avoid deleting lots of keys: you change the cache key format (or generation) so old values naturally stop being used.
- Tag/namespace invalidation (invalidate a group)
  - Example: “invalidate all `product:123:*` when product changes”.
  - Trade-off: you need to maintain mappings from tags to keys.
- Revalidate on read using an ETag/version
  - Store `(value, version)` in cache; on read, compare with the DB’s current version.
  - Trade-off: you still do a lightweight version check on reads.
- Active invalidation across nodes (pub/sub)
  - When one instance writes, it publishes an invalidation event so other instances drop stale cache.
  - Trade-off: you add operational complexity (a bus, ordering, delivery guarantees).

See `invalidation_example.py` for minimal runnable examples of each strategy.

## Diagrams: Cache Invalidation Strategies

### 1) Delete on Write
```mermaid
flowchart LR
    W[Write request] --> D[Update DB]
    D --> X[Delete cache key]
    X --> N[Next read causes refill]
```

### 2) Versioned Keys / Generation Counters
```mermaid
flowchart LR
    W[Write request] --> D[Update DB + bump version]
    R[Read request] --> K[Build cache key with version]
    K --> C{Key exists?}
    C -->|Yes| V[Return cached value]
    C -->|No| F[Fetch DB and cache under new versioned key]
```

### 3) Tag/Namespace Invalidation
```mermaid
flowchart LR
    A[Cache entries with tag product:123] --> T[Tag index]
    U[Product update] --> I[Invalidate tag product:123]
    I --> D[Delete all keys in tag]
```

### 4) Revalidate on Read (ETag/Version)
```mermaid
flowchart LR
    R[Read request] --> C[Get cached value + cached_version]
    C --> V[Fetch current DB version]
    V --> M{Versions match?}
    M -->|Yes| H[Return cached value]
    M -->|No| F[Fetch fresh value]
    F --> U[Update cache with new version]
```

### 5) Active Invalidation Across Nodes (Pub/Sub)
```mermaid
flowchart LR
    N1[Node 1 write] --> D[Update DB]
    D --> P[Publish invalidation event]
    P --> N2[Node 2 cache deletes key]
    P --> N3[Node 3 cache deletes key]
```

## Why this set?

"All caching strategies" can be interpreted very broadly. This set covers the
core patterns used in most backend systems and interviews.

```mermaid
flowchart TD

    %% Read Path
    A[Request] --> B{Cache Hit?}
    B -->|Yes| C[Fast Response]
    B -->|No| D[Read from DB]
    D --> E[Update Cache]
    E --> C

    %% Write Path
    W[Write Request] --> X[Update DB]
    X --> Y[Invalidate / Update Cache]

    %% Freshness
    subgraph Freshness
        F1[TTL Expiration]
        F2[Refresh Ahead]
    end

    %% Protection
    subgraph Protection
        P1[Request Coalescing]
        P2[Negative Caching]
    end

    %% Connections
    E --> F1
    E --> F2

    D --> P1
    D --> P2
```