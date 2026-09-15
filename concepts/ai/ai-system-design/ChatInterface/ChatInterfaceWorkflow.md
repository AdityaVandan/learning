# Chat Interface Workflow — End-to-End System Design

How a typical ChatGPT / Claude-style chat product turns a user message into a streamed reply — every major component, in order.

Companion notes in this folder dig into each layer:

| File | Covers |
|------|--------|
| [01-frontend-client.md](./01-frontend-client.md) | App UI, input, local state, streaming render |
| [02-edge-api-gateway.md](./02-edge-api-gateway.md) | CDN, TLS, load balancing, API gateway |
| [03-auth-sessions-quotas.md](./03-auth-sessions-quotas.md) | Auth, sessions, rate limits, billing gates |
| [04-conversation-orchestration.md](./04-conversation-orchestration.md) | Chat service, thread state, request orchestration |
| [05-prompt-context-assembly.md](./05-prompt-context-assembly.md) | System prompt, history, RAG, compression |
| [06-model-routing.md](./06-model-routing.md) | Model picker, routers, A/B, failover |
| [07-inference-serving.md](./07-inference-serving.md) | GPU clusters, batching, KV cache, decoding |
| [08-streaming-protocol.md](./08-streaming-protocol.md) | SSE/WebSocket, token chunks, reconnect |
| [09-tools-agents.md](./09-tools-agents.md) | Function calling, tool loop, MCP-style tools |
| [10-safety-moderation.md](./10-safety-moderation.md) | Input/output filters, policy models |
| [11-storage-persistence.md](./11-storage-persistence.md) | Conversations DB, blobs, search |
| [12-observability-reliability.md](./12-observability-reliability.md) | Logs, traces, evals, SLOs |

---

## 0. Mental model (one sentence)

**Client → Edge/API → Auth & quotas → Chat orchestrator → Prompt assembler → (optional tools/RAG) → Safety → Model router → Inference → Stream tokens back → Persist → Show UI.**

Most of the “magic” is not the model alone — it is orchestration around the model.

---

## 1. Bird’s-eye component map

```mermaid
flowchart TB
  subgraph Client["Client (Web / iOS / Android / Desktop)"]
    UI["Chat UI"]
    LS["Local state + draft"]
    SM["Stream renderer"]
  end

  subgraph Edge["Edge & Ingress"]
    CDN["CDN / static assets"]
    LB["L4/L7 Load balancer"]
    GW["API Gateway"]
    WAF["WAF / DDoS"]
  end

  subgraph Control["Control plane"]
    AUTH["Auth / session"]
    RL["Rate limit / quota"]
    BILL["Billing / plan entitlements"]
  end

  subgraph ChatPlane["Chat application plane"]
    ORCH["Conversation orchestrator"]
    CTX["Context / prompt assembler"]
    TOOLS["Tool / agent runtime"]
    SAFE["Safety classifiers"]
    ROUTE["Model router"]
  end

  subgraph Data["Data plane"]
    CONV[(Conversations DB)]
    USER[(User / org store)]
    VEC[(Vector / search index)]
    OBJ[(Object storage)]
    CACHE[(Redis / caches)]
  end

  subgraph Inference["Inference plane"]
    QUEUE["Request queue / scheduler"]
    ENG["Inference engines<br/>(vLLM / TensorRT-LLM / custom)"]
    GPU["GPU / accelerator fleet"]
  end

  UI --> CDN
  UI --> SM
  SM --> GW
  GW --> WAF --> LB --> AUTH
  AUTH --> RL --> BILL --> ORCH
  ORCH --> CTX
  ORCH --> TOOLS
  ORCH --> SAFE
  ORCH --> ROUTE
  CTX --> CONV
  CTX --> VEC
  CTX --> CACHE
  ROUTE --> QUEUE --> ENG --> GPU
  ENG -->|token stream| ORCH
  ORCH -->|SSE / WS chunks| SM
  ORCH --> CONV
  ORCH --> OBJ
  AUTH --> USER
```

---

## 2. Happy-path timeline (user sends one message)

What happens **after** the user hits Send, before the first token appears, and until the reply finishes.

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant FE as Frontend
  participant GW as API Gateway
  participant Auth as Auth + Quotas
  participant Orch as Chat Orchestrator
  participant Ctx as Prompt Assembler
  participant Safe as Safety
  participant Rt as Model Router
  participant Inf as Inference Engine
  participant DB as Conversation Store

  U->>FE: Type message + Send
  FE->>FE: Optimistic UI (user bubble)
  FE->>GW: POST /v1/chat/completions<br/>(stream=true, conversation_id, message)
  GW->>Auth: Validate session / JWT
  Auth->>Auth: Plan, rate limit, abuse checks
  Auth-->>GW: OK + identity claims
  GW->>Orch: Forward authenticated request

  Orch->>DB: Append user message (pending)
  Orch->>Ctx: Load thread + build prompt
  Ctx->>DB: Fetch history / summary / attachments meta
  Ctx-->>Orch: Messages[] + tools schema + system

  Orch->>Safe: Input moderation
  Safe-->>Orch: Allow / rewrite / block

  alt Blocked
    Orch-->>FE: Policy refusal (streamed or JSON)
  else Allowed
    Orch->>Rt: Select model + cluster
    Rt->>Inf: Forward generation request
    Inf-->>Orch: Stream token deltas
    loop Token stream
      Orch-->>FE: SSE data: {"delta":"..."}
      FE->>FE: Append to assistant bubble
    end
    Inf-->>Orch: finish_reason=stop
    Orch->>Safe: Output moderation (may redact)
    Orch->>DB: Persist assistant message + usage
    Orch-->>FE: [DONE] + usage metadata
  end
```

---

## 3. Layers in order (detailed pipeline)

```mermaid
flowchart LR
  A["1. Capture input"] --> B["2. Transport"]
  B --> C["3. Authenticate"]
  C --> D["4. Authorize & meter"]
  D --> E["5. Orchestrate turn"]
  E --> F["6. Assemble context"]
  F --> G["7. Safety in"]
  G --> H["8. Route model"]
  H --> I["9. Generate tokens"]
  I --> J["10. Stream out"]
  J --> K["11. Safety out"]
  K --> L["12. Persist & index"]
  L --> M["13. Render & feedback"]
```

| Step | Component | Job |
|------|-----------|-----|
| 1 | Frontend | Capture text, files, voice; show optimistic UI |
| 2 | Edge / Gateway | TLS, routing, versioning (`/v1/...`) |
| 3 | Auth | Who is calling? Session / OAuth / API key |
| 4 | Quotas | Rate limits, token budgets, plan features |
| 5 | Orchestrator | Own the “turn”: IDs, retries, tool loops |
| 6 | Prompt assembler | System + history + RAG + tools + memory |
| 7 | Safety (in) | Jailbreak / toxicity / PII / policy |
| 8 | Router | Which model, region, capacity pool |
| 9 | Inference | Autoregressive decode on accelerators |
| 10 | Streaming | Push partial tokens to client |
| 11 | Safety (out) | Filter / rewrite final or mid-stream |
| 12 | Storage | Save messages, usage, embeddings |
| 13 | UI | Markdown, code, citations; thumbs / regen |

---

## 4. Request shape (what the client actually sends)

Conceptual OpenAI-compatible shape (Claude, Gemini, etc. are similar ideas with different field names):

```json
{
  "conversation_id": "conv_abc",
  "parent_message_id": "msg_user_prev",
  "model": "auto",
  "stream": true,
  "messages": [
    { "role": "user", "content": [{ "type": "text", "text": "Explain KV cache" }] }
  ],
  "tools": [],
  "attachments": [],
  "client_metadata": { "timezone": "Asia/Kolkata", "ui_version": "…" }
}
```

Important product details:

- **`conversation_id`** ties the turn to a thread (server often owns canonical history; client may send only the new message).
- **`stream: true`** is the default UX for chat apps.
- **`model: "auto"`** often means “server decides” via a router.
- Multimodal content is an array of parts (text, image, file refs), not a single string.

---

## 5. Response path (streaming)

```mermaid
flowchart TB
  subgraph Engine["Inference"]
    T0["Decode next token"]
    T1["Emit delta"]
  end

  subgraph Orch["Orchestrator"]
    BUF["Buffer / coalesce"]
    EVT["Map to wire events"]
    MOD["Optional mid-stream filter"]
  end

  subgraph Wire["Transport"]
    SSE["SSE: data: {json}\\n\\n"]
    WS["or WebSocket frames"]
  end

  subgraph FE["Frontend"]
    PARSE["Parse events"]
    ACC["Accumulate assistant text"]
    MD["Markdown / syntax highlight"]
  end

  T0 --> T1 --> BUF --> MOD --> EVT --> SSE
  EVT --> WS
  SSE --> PARSE --> ACC --> MD
  WS --> PARSE
```

Typical event types products emit:

| Event | Meaning |
|-------|---------|
| `message.created` | Assistant message id reserved |
| `content.delta` | New text / token chunk |
| `tool_call.delta` | Partial tool JSON arguments |
| `tool_call.completed` | Ready to execute a tool |
| `message.completed` | Final text + finish reason |
| `error` | Recoverable / fatal error |
| `done` | Stream closed |

See [08-streaming-protocol.md](./08-streaming-protocol.md).

---

## 6. Tool / agent turn (when the model calls tools)

Chat products are rarely “one shot.” A single user message can expand into multiple model calls.

```mermaid
flowchart TB
  U["User message"] --> P["Assemble prompt + tool schemas"]
  P --> G1["Generate"]
  G1 --> D{"finish_reason?"}
  D -->|stop| OUT["Final assistant text"]
  D -->|tool_calls| EX["Execute tools<br/>(search, code, browser, APIs)"]
  EX --> APP["Append tool results<br/>as tool messages"]
  APP --> G2["Generate again"]
  G2 --> D
```

Details: [09-tools-agents.md](./09-tools-agents.md).

---

## 7. Where state lives

```mermaid
flowchart LR
  subgraph Ephemeral
    KV["GPU KV cache<br/>(this generation)"]
    RED["Redis: rate limits,<br/>locks, short cache"]
  end

  subgraph Durable
    PG["Postgres / Cosmos:<br/>threads, messages, users"]
    S3["Object store:<br/>files, images, exports"]
    ES["Search / vectors:<br/>memory, RAG"]
  end

  subgraph ClientLocal
    DRAFT["Unsent draft"]
    SCROLL["Scroll / UI prefs"]
    OFF["Offline queue (sometimes)"]
  end
```

Rule of thumb: **canonical conversation state is server-side**; the client is a cache + renderer.

---

## 8. Failure & control-flow variants

```mermaid
flowchart TB
  REQ["Incoming chat turn"] --> AUTH{Auth OK?}
  AUTH -->|no| E401["401 / login"]
  AUTH -->|yes| Q{Quota OK?}
  Q -->|no| E429["429 + retry-after"]
  Q -->|yes| CAP{Capacity?}
  CAP -->|no| QUEUE["Queue / degrade model / 503"]
  CAP -->|yes| SAFE{Input OK?}
  SAFE -->|no| REF["Policy response"]
  SAFE -->|yes| GEN["Generate"]
  GEN --> OK{Stream OK?}
  OK -->|yes| DONE["Complete + persist"]
  OK -->|partial| RETRY["Resume / regenerate / error bubble"]
```

Products often **degrade gracefully**: smaller model, shorter context, disable tools, or queue with ETA.

---

## 9. Multi-diagram index (what to read next)

1. Start here for the full path: this file (sections 1–8).
2. UI & wire format: [01](./01-frontend-client.md) + [08](./08-streaming-protocol.md).
3. Backend “turn owner”: [04](./04-conversation-orchestration.md) + [05](./05-prompt-context-assembly.md).
4. How tokens are produced: [06](./06-model-routing.md) + [07](./07-inference-serving.md).
5. Productized intelligence: [09](./09-tools-agents.md) + [10](./10-safety-moderation.md).
6. What remains after the chat: [11](./11-storage-persistence.md) + [12](./12-observability-reliability.md).

---

## 10. End-to-end “everything” diagram (annotated)

```mermaid
flowchart TB
  U(["User"])

  subgraph FE["1 · Frontend"]
    IN["Composer: text / files / voice"]
    OPT["Optimistic user message"]
    STR["Streaming markdown renderer"]
    ACT["Actions: stop, regen, edit, branch"]
  end

  subgraph EDGE["2 · Edge"]
    TLS["TLS termination"]
    CDN2["Static CDN"]
    APIGW["API Gateway + WAF"]
  end

  subgraph ID["3 · Identity & limits"]
    SSO["OAuth / SSO / API keys"]
    SESS["Session service"]
    LIMIT["Rate limiter"]
    ENT["Entitlements<br/>(model access, tools, limits)"]
  end

  subgraph APP["4 · Chat application"]
    ORC["Turn orchestrator"]
    HIS["History loader"]
    MEM["Memory / RAG retriever"]
    PR["Prompt builder"]
    POL["Policy / safety"]
    TR["Tool runtime"]
    MR["Model router"]
    USG["Usage accounting"]
  end

  subgraph INF["5 · Model serving"]
    SCH["Scheduler / continuous batcher"]
    TOK["Tokenizer"]
    MODL["Transformer weights"]
    KVC["Paged KV cache"]
    SMP["Sampler<br/>(temp, top-p, …)"]
  end

  subgraph DATA["6 · Persistence"]
    MSG[(Messages)]
    FILE[(Files)]
    EMB[(Embeddings)]
    LOG[(Telemetry)]
  end

  U --> IN --> OPT --> APIGW
  CDN2 -.-> FE
  APIGW --> TLS --> SSO --> SESS --> LIMIT --> ENT --> ORC
  ORC --> HIS --> PR
  ORC --> MEM --> PR
  PR --> POL --> MR --> SCH
  SCH --> TOK --> MODL --> KVC --> SMP
  SMP -->|deltas| ORC
  ORC --> TR
  TR -->|tool results| PR
  ORC --> STR
  STR --> U
  ACT --> ORC
  ORC --> MSG
  ORC --> FILE
  MEM --> EMB
  ORC --> USG
  USG --> LOG
  ORC --> LOG
```

---

## 11. What ChatGPT/Claude add on top of “raw LLM API”

A raw completions API is: *messages in → tokens out*.

A chat product adds:

- Persistent **threads** and branching edits
- **Streaming** UX with stop / regenerate
- **Model routing** and capacity management
- **Tools** (web, code, files, connectors)
- **Memory** and personalization
- **Safety** and compliance
- **Billing**, quotas, team workspaces
- **Multimodal** upload pipeline
- **Eval / feedback** loops into training & product

Those layers are why the architecture looks like a distributed system, not a single `model.generate()` call.

---

## 12. Suggested study order

1. Walk section 2’s sequence diagram once with a real product open (watch Network tab → EventStream).
2. Read [07-inference-serving.md](./07-inference-serving.md) to connect tokens ↔ GPUs.
3. Read [09-tools-agents.md](./09-tools-agents.md) to see multi-step turns.
4. Skim [12-observability-reliability.md](./12-observability-reliability.md) so failure modes feel concrete.
