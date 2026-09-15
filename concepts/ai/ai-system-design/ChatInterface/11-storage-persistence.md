# 11 — Storage & Persistence

What remains after tokens finish streaming: threads, files, search indexes, and billing records.

---

## 1. Data domains

```mermaid
flowchart TB
  subgraph Transactional
    USERS[(Users / orgs)]
    CONV[(Conversations / messages)]
    BILL[(Subscriptions / usage)]
  end

  subgraph Blob
    FILES[(Uploaded files)]
    GENF[(Generated images / exports)]
  end

  subgraph Derived
    EMB[(Embeddings)]
    SUM[(Summaries)]
    MEM[(Memory facts)]
  end

  subgraph Telemetry
    LOGS[(Logs / traces)]
    FB[(Feedback)]
  end
```

---

## 2. Conversation store

Requirements:

- Low-latency fetch of recent messages for prompt build
- Branching parent pointers
- Pagination for long threads
- Soft delete / retention jobs
- Strong tenancy isolation

Common design:

| Store | Role |
|-------|------|
| Primary SQL / document DB | Metadata + messages |
| Redis | Hot thread cache |
| Object storage | Large message parts / transcripts |
| Search engine | Title + full-text find |

```mermaid
flowchart LR
  ORCH["Orchestrator"] --> CACHE["Redis hot path"]
  CACHE -->|miss| DB["Primary DB"]
  ORCH --> S3["Attachments in object store"]
```

---

## 3. Write path for a turn

```mermaid
sequenceDiagram
  participant O as Orchestrator
  participant DB as DB
  participant S as Search
  participant E as Embed worker

  O->>DB: INSERT user message
  O->>DB: INSERT assistant placeholder / finalize
  O->>DB: UPDATE usage
  O-->>S: Async index message
  O-->>E: Async embed for memory/RAG
```

Use **outbox / event bus** so search/embeddings stay eventually consistent without slowing TTFT.

---

## 4. File pipeline

```mermaid
flowchart LR
  UP["Client upload"] --> VIR["Malware scan"]
  VIR --> STORE["Object store encrypted"]
  STORE --> META["File metadata row"]
  META --> PARSE["Parse / chunk / thumbnail"]
  PARSE --> IDX["Index for retrieval"]
```

Store hashes for dedupe; never trust client-provided content types.

---

## 5. Temporary / private modes

Products offer “temporary chat” that:

- Skips memory writes
- Skips training datasets
- Applies shorter retention TTL
- May still keep safety logs for a legal minimum window

---

## 6. Export & deletion (GDPR-style)

```mermaid
flowchart TB
  REQ["User delete account"] --> Q["Queue deletion workflow"]
  Q --> C["Delete conversations"]
  Q --> F["Delete blobs"]
  Q --> M["Delete memory + embeddings"]
  Q --> B["Anonymize billing artifacts"]
  Q --> T["Retain only legally required logs"]
```

Hard problem: replicas, backups, derived datasets, and partner subprocessors.

---

## 7. Consistency model

Chat UIs tolerate:

- **Strong** consistency for “did my send persist?”
- **Eventual** for search, titles, memory

After send, read-your-writes is usually achieved by returning server IDs in the stream completion and updating client cache directly (skip re-fetch).

Next: [12-observability-reliability.md](./12-observability-reliability.md).
