# 09 — Tools, Function Calling & Agents

Modern chat apps are not only next-token predictors. The model can **request actions**; the platform executes them and feeds results back. That loop is how browsing, code execution, connectors, and “agents” work.

---

## 1. Core loop

```mermaid
flowchart TB
  U["User message"] --> P["Prompt + tool schemas"]
  P --> M["Model generate"]
  M --> D{"Stop reason"}
  D -->|"end_turn / stop"| F["Final answer"]
  D -->|"tool_use / tool_calls"| X["Tool runtime executes"]
  X --> R["Append tool_result messages"]
  R --> M
```

One user Send may equal **many** model calls.

---

## 2. Tool schema (what the model sees)

Conceptual JSON-schema style:

```json
{
  "name": "web_search",
  "description": "Search the public web",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string" }
    },
    "required": ["query"]
  }
}
```

The model emits a structured call, e.g.:

```json
{ "name": "web_search", "arguments": { "query": "KV cache vLLM" } }
```

Arguments may stream as partial JSON (`tool_call.delta`) before execution.

---

## 3. Tool runtime architecture

```mermaid
flowchart TB
  ORCH["Orchestrator"] --> REG["Tool registry"]
  ORCH --> EXEC["Executor"]
  EXEC --> LOCAL["In-process tools<br/>(计算器, formatters)"]
  EXEC --> SAND["Sandboxes<br/>(code interpreter)"]
  EXEC --> HTTP["HTTP connectors<br/>(Slack, Drive, GitHub)"]
  EXEC --> BROW["Browser service"]
  EXEC --> RETR["Retrieval / RAG tools"]
```

| Tool class | Examples | Risk |
|------------|----------|------|
| Read-only retrieval | Search, file read | Data exfil if mis-scoped |
| Code interpreter | Python in VM | Escape, crypto mining |
| Browser | Headless Chromium | SSRF, malware sites |
| Write connectors | Send email, create issue | Irreversible side effects |
| Soft UI tools | Render chart, ask user | Low |

---

## 4. Parallel tool calls

Models may emit multiple calls in one step:

```mermaid
flowchart LR
  M["Model"] --> T1["search A"]
  M --> T2["search B"]
  M --> T3["read file"]
  T1 --> J["Join results"]
  T2 --> J
  T3 --> J
  J --> M2["Next generate"]
```

Executor runs independent calls concurrently with a concurrency cap.

---

## 5. Safety around tools

```mermaid
flowchart TB
  CALL["Tool call"] --> POL["Policy check:<br/>allowed for plan/user?"]
  POL --> CONF{"Needs confirmation?"}
  CONF -->|yes| UI["Ask user in chat UI"]
  CONF -->|no| RUN["Execute with timeouts"]
  UI -->|approve| RUN
  UI -->|deny| DENY["Return denial to model"]
```

Hardening:

- Allowlists of domains / APIs
- Secrets injected by runtime (model never sees raw API keys ideally)
- SSRF protection for browser/fetch
- CPU/memory/time quotas for sandboxes
- Audit logs for enterprise connectors

---

## 6. Code interpreter path

```mermaid
sequenceDiagram
  participant M as Model
  participant E as Executor
  participant S as Sandbox VM
  participant O as Object store

  M->>E: run_python(code)
  E->>S: Create/reuse session container
  S->>S: Execute with limits
  S-->>E: stdout, files, errors
  E->>O: Persist generated images/files
  E-->>M: tool_result (+ file refs)
```

Session state (variables, installed wheels) may persist across calls in the same chat for UX (“continue in the same notebook”).

---

## 7. Agents vs single-turn tools

| Pattern | Behavior |
|---------|----------|
| Tool-augmented chat | Short loops, user-visible final answer |
| Autonomous agent | Long horizon, planning, many tools, background jobs |
| Human-in-the-loop | Pauses for approval on risky actions |

Products brand these differently (“Deep research”, “Computer use”, “Agent mode”) but share the same substrate: schemas + runtime + loop limits.

```mermaid
flowchart TB
  G["Goal"] --> PLAN["Plan (optional explicit)"]
  PLAN --> ACT["Act via tools"]
  ACT --> OBS["Observe results"]
  OBS --> REFLECT{"Done?"}
  REFLECT -->|no| PLAN
  REFLECT -->|yes| ANS["Answer user"]
```

Guardrails: max steps, max wall time, max spend, deadlock detection.

---

## 8. MCP-style external tools

Platforms increasingly load tools from external **Model Context Protocol** (or similar) servers: standardized discovery + invoke. The orchestrator still owns auth, policy, and the chat loop; MCP is a plug shape for enterprise systems.

Next: [10-safety-moderation.md](./10-safety-moderation.md).
