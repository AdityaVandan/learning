# Deduplication — Working Code at Every Scale

## What is Deduplication?

Deduplication is the process of identifying and eliminating duplicate items from a dataset or stream. It's a fundamental problem in computer science that appears in many contexts:

- **Data processing pipelines**: Preventing duplicate records from being processed multiple times
- **Event streaming**: Ensuring idempotency when handling events that may be retried
- **Content management**: Identifying duplicate files, documents, or media
- **Caching**: Avoiding redundant computations or network requests
- **Analytics**: Ensuring accurate metrics by counting unique items only once

The challenge lies in choosing the right strategy based on your specific requirements:
- **Scale**: Small in-memory datasets vs. massive distributed systems
- **Accuracy**: Exact matching vs. fuzzy/near-duplicate detection
- **Performance**: Throughput requirements and latency constraints
- **Memory**: Available RAM and storage constraints
- **Persistence**: Whether deduplication state needs to survive restarts

## Overview of Strategies

This repository demonstrates 7 different deduplication strategies, each optimized for specific scenarios:

### 1. Hash Set (`1_hashset/`)
**Use case**: In-memory deduplication for small datasets that fit in RAM
**Approach**: Uses Go's `map[string]struct{}` for O(1) exact duplicate detection
**Tradeoffs**: Fast and 100% accurate, but memory-intensive (~50 bytes per item)

### 2. Bloom Filter (`2_bloomfilter/`)
**Use case**: High-throughput scenarios where occasional false positives are acceptable
**Approach**: Probabilistic data structure using bit arrays and multiple hash functions
**Tradeoffs**: Extremely memory-efficient (~1 byte per item) with ~1% false positive rate

### 3. Sort-Merge (`3_sort_merge/`)
**Use case**: Single-node processing of datasets larger than available RAM
**Approach**: External sort followed by linear scan to identify duplicates
**Tradeoffs**: Handles arbitrarily large data but requires disk I/O and sorting time

### 4. Redis (`4_redis/`)
**Use case**: Distributed deduplication across multiple processes or servers
**Approach**: Uses Redis `SETNX` with TTL for atomic, distributed duplicate checking
**Tradeoffs**: Network latency overhead but provides horizontal scalability

### 5. PostgreSQL (`5_postgres/`)
**Use case**: Transactional deduplication with ACID guarantees
**Approach**: Database constraints with `ON CONFLICT DO NOTHING` for idempotent inserts
**Tradeoffs**: Persistent and reliable but slower than in-memory solutions

### 6. MinHash LSH (`6_minhash_lsh/`)
**Use case**: Fuzzy/near-duplicate detection for similar but not identical content
**Approach**: Locality-sensitive hashing with MinHash signatures for similarity detection
**Tradeoffs**: Finds near-duplicates but requires tuning and has computational overhead

### 7. Windowed Stream (`7_windowed_stream/`)
**Use case**: Real-time deduplication of unbounded data streams
**Approach**: Time-based windows (tumbling, sliding, count) for bounded duplicate detection
**Tradeoffs**: Handles infinite streams but only deduplicates within window boundaries

---

All files are self-contained Go programs. Run any with: `go run main.go`

---

## File Map

| File | Scenario | Key Pattern |
|------|----------|-------------|
| `1_hashset/` | In-memory, small data | `map[string]struct{}` |
| `2_bloomfilter/` | In-memory, large data, high throughput | Bit array + double hashing |
| `3_sort_merge/` | Single node, larger-than-RAM | Sort → linear scan |
| `4_redis/` | Distributed, multi-process | `SET key NX EX ttl` |
| `5_postgres/` | Transactional, persistent | `ON CONFLICT DO NOTHING` |
| `6_minhash_lsh/` | Fuzzy/near-duplicate detection | Shingling → MinHash → LSH banding |
| `7_windowed_stream/` | Unbounded streams | Tumbling / sliding / count windows |

---

## Visual Overview

### Deduplication Strategy Decision Flow

```mermaid
flowchart TD
    A[Start: Need Deduplication?] --> B{Data fits in RAM?}
    B -->|Yes| C{Need exact dedup?}
    B -->|No| D{Single node?}

    C -->|Yes| E["1_hashset / map[string]struct{}"]
    C -->|No| F{Need fuzzy matching?}
    F -->|Yes| G["6_minhash_lsh / MinHash + LSH"]
    F -->|No| H["2_bloomfilter / Space-efficient"]

    D -->|Yes| I{Data > RAM?}
    I -->|Yes| J["3_sort_merge / External sort"]
    I -->|No| H

    B -->|No| K{Distributed?}
    K -->|Yes| L{Need transactions?}
    L -->|Yes| M["5_postgres / ON CONFLICT"]
    L -->|No| N["4_redis / SET NX EX"]

    A --> O{Real-time stream?}
    O -->|Yes| P["7_windowed_stream / Tumbling/Sliding"]

    E --> Q["Exact, O(1) lookup"]
    H --> R["High throughput, ~1% FP"]
    G --> S[Near-duplicate detection]
    J --> T[Larger-than-RAM data]
    M --> U[ACID guarantees]
    N --> V[Distributed cache]
    P --> W[Unbounded streams]
```

### Memory vs Accuracy Tradeoffs

```mermaid
graph LR
    subgraph "Memory Efficiency"
        A["Hash Set / 50 bytes/item / 100% accurate"]
        B["Bloom Filter / 1 byte/item / ~1% false positive"]
        C["MinHash LSH / ~10 bytes/item / Fuzzy matching"]
    end

    subgraph "Scale Characteristics"
        D["Small datasets / < 1M items"]
        E["Medium datasets / 1M-100M items"]
        F["Large datasets / > 100M items"]
    end

    A --> D
    B --> E
    C --> F
```

---

## Choosing the right approach

```
Is the data bounded and small enough for RAM?
  └─ Yes → 1_hashset (exact) or 6_minhash_lsh (fuzzy)
  └─ No, but single node → 3_sort_merge or 2_bloomfilter
  └─ No, distributed → 4_redis (TTL-based) or 5_postgres (transactional)

Is it a real-time stream?
  └─ Yes → 7_windowed_stream (choose window type by your boundary tolerance)

Do you need near-duplicate detection (not exact)?
  └─ Yes → 6_minhash_lsh (adjust similarity threshold 0.5–0.9)

Do you need financial/idempotency guarantees?
  └─ Yes → 5_postgres (ON CONFLICT + idempotency key table)

High throughput, can tolerate rare false positives?
  └─ Yes → 2_bloomfilter or 7_windowed_stream Approach 4 (two-stage)
```

---

## Quick cheat sheet

```go
// 1. Exact, in-memory
seen := make(map[string]struct{})
if _, exists := seen[id]; !exists { seen[id] = struct{}{}; process() }

// 2. Bloom filter (space-efficient, ~1% FP rate)
bf := NewBloomFilter(1_000_000, 0.01)
if !bf.Contains(key) { bf.Add(key); process() }

// 3. Sort-merge (external)
sort.Slice(records, func(i,j int) bool { return records[i].ID < records[j].ID })
// then linear scan, emit first of each group

// 4. Redis distributed
ok, _ := redis.SetNX(ctx, "dedup:"+id, 1, 24*time.Hour)
if ok { process() }

// 5. PostgreSQL
INSERT INTO events (event_id, ...) VALUES ($1, ...)
ON CONFLICT (event_id) DO NOTHING;

// 6. MinHash LSH (fuzzy)
sig := hasher.Signature(wordShingles(text, 3))
index.Add(docID, sig)
candidates := index.CandidatePairs()  // O(n) instead of O(n²)

// 7. Windowed stream
dedup := NewSlidingWindowDedup(5 * time.Minute)
if !dedup.IsDuplicate(event) { process() }
```

---

## Detailed Algorithm Diagrams

### 1. Hash Set Deduplication

```mermaid
flowchart LR
    subgraph "Input Stream"
        A[Event ID: evt_1]
        B[Event ID: evt_2]
        C[Event ID: evt_1]
        D[Event ID: evt_3]
    end

    subgraph "Hash Set Check"
        E{ID in seen?}
        F[Add to seen]
        G[Process event]
        H[Skip duplicate]
    end

    A --> E
    E -->|No| F --> G
    B --> E
    C --> E
    E -->|Yes| H
    D --> E

    style E fill:#f9f,stroke:#333,stroke-width:2px
```

### 2. Bloom Filter Architecture

```mermaid
flowchart TB
    subgraph "Bloom Filter Internals"
        A[Input Key] --> B[Hash Function 1]
        A --> C[Hash Function 2]
        A --> D[Hash Function k]

        B --> E[Bit Position 1]
        C --> F[Bit Position 2]
        D --> G[Bit Position k]

        E --> H[Bit Array]
        F --> H
        G --> H

        H --> I{All bits set?}
        I -->|Yes| J[Probably seen]
        I -->|No| K[Definitely new]
    end

    subgraph "Memory Layout"
        L[64-bit words]
        M["Bits: 0, 1, 2 ... 63"]
        N["Words: 0, 1, 2 ... N"]
    end

    H -.-> L
    L -.-> M
    L -.-> N
```

### 3. Sort-Merge External Deduplication

```mermaid
flowchart TD
    A["Large Dataset / > RAM size"] --> B[External Sort]
    B --> C[Sorted Chunks on Disk]
    C --> D[Merge Pass]
    D --> E[Linear Scan]
    E --> F{Current ID == Previous ID?}
    F -->|No| G[Emit record]
    F -->|Yes| H[Skip duplicate]
    G --> I[Update previous]
    H --> J[Move to next]
    I --> K[More records?]
    J --> K
    K -->|Yes| E
    K -->|No| L[Done]

    style B fill:#ff9,stroke:#333,stroke-width:2px
    style E fill:#9f9,stroke:#333,stroke-width:2px
```

### 4. Redis Distributed Deduplication

```mermaid
sequenceDiagram
    participant P1 as Process 1
    participant R as Redis
    participant P2 as Process 2

    P1->>R: SETNX dedup:evt_1 1 EX 24h
    R-->>P1: OK (success)

    P2->>R: SETNX dedup:evt_1 1 EX 24h
    R-->>P2: 0 (duplicate)

    Note over P1,P2: Atomic operation prevents race conditions across processes

    P1->>R: SETNX dedup:evt_2 1 EX 24h
    R-->>P1: OK (success)

    Note over R: Keys auto-expire after TTL, prevents memory leaks
```

### 5. PostgreSQL Transactional Deduplication

```mermaid
flowchart TB
    A["INSERT INTO events (event_id, ...) VALUES (...)"] --> B{event_id exists?}
    B -->|No| C[Insert new record]
    B -->|Yes| D[ON CONFLICT DO NOTHING]
    C --> E[Commit transaction]
    D --> E
    E --> F[Return success]

    G[Concurrent insert same event_id] --> H[Transaction lock]
    H --> I[Wait for commit]
    I --> B

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#ff9,stroke:#333,stroke-width:2px
```

### 6. MinHash + LSH Pipeline

```mermaid
flowchart LR
    subgraph "Document Processing"
        A[Raw Document] --> B[Normalization]
        B --> C[k-Shingles / overlapping n-grams]
        C --> D[MinHash Signature / fixed-size]
        D --> E[LSH Banding / hash buckets]
    end

    subgraph "Candidate Generation"
        E --> F["Bucket 1 / docs: A, C, F"]
        E --> G["Bucket 2 / docs: B, D"]
        E --> H["Bucket 3 / docs: E, G, H"]
    end

    subgraph "Similarity Check"
        F --> I[Compare A vs C]
        F --> J[Compare A vs F]
        F --> K[Compare C vs F]
        G --> L[Compare B vs D]
        H --> M[Compare E vs G]
        H --> N[Compare E vs H]
        H --> O[Compare G vs H]
    end

    I --> P{Jaccard > threshold?}
    P -->|Yes| Q[Near-duplicate pair]

    style E fill:#9f9,stroke:#333,stroke-width:2px
    style P fill:#f9f,stroke:#333,stroke-width:2px
```

### 7. Windowed Stream Deduplication

```mermaid
graph TD
    subgraph Tumbling["Tumbling Window"]
        T1["00:00-00:59 | evt_1, evt_2"]
        T2["01:00-01:59 | evt_1, evt_3"]
        T3["02:00-02:59 | evt_4"]
        T1 --> T2 --> T3
    end
    subgraph Sliding["Sliding Window"]
        S1["00:00-00:05 | evt_1, evt_2"]
        S2["00:01-00:06 | evt_1, evt_2, evt_3"]
        S3["00:02-00:07 | evt_2, evt_3, evt_4"]
        S1 --> S2 --> S3
    end
```

---

## Production Notes

**Bloom filter observed FP rate** may differ from theoretical if hash functions lack
uniformity. In production use murmur3 or xxhash: `github.com/spaolacci/murmur3`

**Redis** (`4_redis`): replace MockRedis with `github.com/redis/go-redis/v9`

**PostgreSQL** (`5_postgres`): replace MockDB with:
```go
db, _ := sql.Open("postgres", "host=localhost dbname=mydb sslmode=disable")
// then use db.Exec("INSERT ... ON CONFLICT DO NOTHING", args...)
```

**MinHash accuracy** improves with more hash functions (100–200 is typical for production).
Tune bands/rows to adjust the similarity threshold (see `6_minhash_lsh` threshold table).