# Chat Interface — System Design Notes

How consumer chat apps (ChatGPT, Claude, and similar) take a user message from the UI through auth, orchestration, models, tools, and streaming back to the screen.

## Start here

**[ChatInterfaceWorkflow.md](./ChatInterfaceWorkflow.md)** — end-to-end diagrams, sequence of a turn, and index of every layer.

## Component notes (read in order)

| # | File | Layer |
|---|------|--------|
| 01 | [01-frontend-client.md](./01-frontend-client.md) | Web/mobile client, optimistic UI, rendering |
| 02 | [02-edge-api-gateway.md](./02-edge-api-gateway.md) | CDN, TLS, WAF, API gateway |
| 03 | [03-auth-sessions-quotas.md](./03-auth-sessions-quotas.md) | Identity, rate limits, billing gates |
| 04 | [04-conversation-orchestration.md](./04-conversation-orchestration.md) | Turn owner / chat service |
| 05 | [05-prompt-context-assembly.md](./05-prompt-context-assembly.md) | System prompt, history, RAG, memory |
| 06 | [06-model-routing.md](./06-model-routing.md) | Auto router, failover, canaries |
| 07 | [07-inference-serving.md](./07-inference-serving.md) | Prefill/decode, KV cache, batching |
| 08 | [08-streaming-protocol.md](./08-streaming-protocol.md) | SSE/WebSocket, cancel, backpressure |
| 09 | [09-tools-agents.md](./09-tools-agents.md) | Function calling, sandboxes, agents |
| 10 | [10-safety-moderation.md](./10-safety-moderation.md) | Input/output/policy pipeline |
| 11 | [11-storage-persistence.md](./11-storage-persistence.md) | Threads, files, deletion |
| 12 | [12-observability-reliability.md](./12-observability-reliability.md) | Metrics, traces, feedback loops |

## Related in this repo

- Transformer internals: `concepts/ai/machine-learning/attention/transformer_attention_notes.md`
- Prompting craft: `concepts/ai/prompting/`
- MCP tools: `concepts/ai/agentic-coding/mcp.md`
