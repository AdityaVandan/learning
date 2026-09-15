# 03 — Auth, Sessions, Quotas & Billing Gates

Before a single token is generated, the platform answers: *who are you, what are you allowed to do, and can you afford this turn?*

---

## 1. Identity modes

```mermaid
flowchart TB
  subgraph Consumer
    OAuth["OAuth / SSO / social login"]
    Sess["Browser session cookie"]
  end
  subgraph Developer
    Key["API key / OAuth client credentials"]
  end
  subgraph Enterprise
    SAML["SAML / OIDC SSO"]
    SCIM["SCIM provisioning"]
  end
  OAuth --> Sess --> Claims["Normalized claims:<br/>user_id, org_id, plan, roles"]
  Key --> Claims
  SAML --> Claims
```

Claims used downstream:

| Claim | Used for |
|-------|----------|
| `user_id` | Ownership of threads |
| `org_id` / `workspace_id` | Team sharing, admin |
| `plan` | Free / Plus / Pro / Team / Enterprise |
| `roles` | Admin vs member |
| `geo` / `data_region` | Residency routing |

---

## 2. Session lifecycle

```mermaid
sequenceDiagram
  participant B as Browser
  participant Auth as Auth service
  participant GW as API Gateway
  participant Chat as Orchestrator

  B->>Auth: Login
  Auth-->>B: Session cookie / tokens
  B->>GW: Chat request + cookie
  GW->>Auth: Validate / introspect
  Auth-->>GW: Claims
  GW->>Chat: Forward + X-User-Id etc.
```

Patterns:

- **Cookie session** for first-party web apps
- **Short-lived access token + refresh** for mobile
- **API keys** for programmatic access (hashed at rest, prefix shown once)

---

## 3. Authorization (beyond login)

Authn ≠ authz.

Examples of authz checks:

- Can this user open `conversation_id`?
- Is this model enabled on their plan?
- Are tools (browser, code interpreter) allowed?
- Is the org under legal hold / retention policy?
- Is the user banned or under abuse probation?

```mermaid
flowchart LR
  REQ --> OWN{"Owns resource?"}
  OWN -->|no| DENY
  OWN -->|yes| PLAN{"Plan allows feature?"}
  PLAN -->|no| UPGRADE["402 / upsell"]
  PLAN -->|yes| ALLOW
```

---

## 4. Rate limiting & quotas

Chat must protect GPUs and prevent abuse.

```mermaid
flowchart TB
  R["Request"] --> L1["IP / edge limit"]
  L1 --> L2["User RPM / TPM"]
  L2 --> L3["Org concurrency"]
  L3 --> L4["Model-specific capacity tokens"]
  L4 --> OK["Proceed"]
```

| Dimension | Example |
|-----------|---------|
| Requests per minute | 20 RPM free tier |
| Tokens per day | Soft cap with slowdown |
| Concurrent streams | Max 3 generations |
| File uploads / day | Abuse control |
| Tool invocations | Cap expensive tools |

Implementation usually: **Redis / DynamoDB counters** with sliding or token-bucket windows. Return `429` + `Retry-After`.

---

## 5. Billing & metering

```mermaid
flowchart LR
  GEN["Generation finished"] --> USG["Usage record:<br/>input tokens, output tokens,<br/>tool seconds, model id"]
  USG --> AGG["Aggregator"]
  AGG --> INV["Invoice / prepaid credits"]
  AGG --> QUOTA["Update remaining quota"]
```

Consumer chat may meter “messages” coarsely; developer APIs meter tokens precisely. Both need **idempotent usage writes** keyed by `request_id` so retries do not double-bill.

---

## 6. Abuse & fraud signals

Layered with safety (see [10](./10-safety-moderation.md)):

- Credential stuffing / stolen cookies
- Automated account farms
- Prompt scraping / model extraction patterns
- Crypto-mining style infinite generations
- Payment fraud on paid plans

Actions: CAPTCHA, step-up auth, shadow bans, hard bans, tool disablement.

---

## 7. Failure UX

| Condition | User-visible |
|-----------|--------------|
| Expired session | Re-login modal |
| Hit rate limit | “You’re sending too fast” |
| Out of credits | Paywall |
| Model not on plan | Upsell or auto-downgrade model |
| Region blocked | Compliance message |

Next: [04-conversation-orchestration.md](./04-conversation-orchestration.md).
