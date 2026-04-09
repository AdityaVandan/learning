# Diagrams: three levels of prompting

Visual companions to `prompt-post.md` / `prompt-post-v2.md`. Render Mermaid in any Markdown viewer that supports it.

---

## 1. Where precision leaks (conversational vs structured)

```mermaid
flowchart LR
  subgraph L1["Level 1 — Conversational"]
    A[Vague goal] --> B[Model fills gaps]
    B --> C[Hidden assumptions]
  end

  subgraph L2["Level 2 — Structured"]
    D[Named sections] --> E[Explicit slots]
    E --> F[Fewer surprise defaults]
  end

  L1 -.->|more variance| X[Output quality]
  L2 -.->|tighter distribution| X
```

**Reading:** unstructured prompts force the model to invent structure; structured prompts reserve the creative work for the task, not for guessing your unstated rules.

---

## 2. Stack of specificity (levels as layers)

```mermaid
flowchart TB
  subgraph L3["Level 3 — Contract"]
    C1[Definition of done]
    C2[Output schema]
    C3[Iteration / A-B tests]
  end

  subgraph L2b["Level 2 — Structure"]
    S1[Role / context / task]
    S2[Tags or headings]
    S3[Examples separated]
  end

  subgraph L1b["Level 1 — Chat"]
    T1[Single paragraph goal]
  end

  L1b --> L2b --> L3
```

**Reading:** each layer adds something the next layer can rely on—structure first, then verifiable “correct,” then machine-checkable shape.

---

## 3. Prompt as API (Level 3 mental model)

```mermaid
flowchart LR
  subgraph Input["Request"]
    I1[Role]
    I2[Context + artifacts]
    I3[Task + constraints]
    I4[Acceptance criteria]
  end

  subgraph Model["Model"]
    M[Weights + context window]
  end

  subgraph Output["Response"]
    O1[Required format]
    O2[Checkable claims]
  end

  Input --> Model --> Output
```

**Reading:** downstream consumers (you, tests, another agent) shouldn’t parse natural language soup; they should validate against declared format and criteria.

---

## 4. Iteration loop (same as any system component)

```mermaid
flowchart LR
  P[Prompt] --> R[Response]
  R --> E{Meets criteria?}
  E -->|no| V[Change one variable]
  V --> P
  E -->|yes| S[Ship / chain]
```

**Reading:** change role, constraints, examples, or output format **one at a time** so you know what moved the needle.

---

## 5. ASCII: single paragraph vs sections (the “one concrete thing”)

**Single blob (harder to attend consistently):**

```text
+----------------------------------------------------------+
|  everything in one paragraph — role, task, and hope      |
+----------------------------------------------------------+
```

**Sectioned (even without fancy tags):**

```text
+-------------+  +-------------+  +-------------+  +-------------+
|    Role     |  |  Context    |  |    Task     |  | Constraints |
+-------------+  +-------------+  +-------------+  +-------------+
```

**Reading:** boundaries help both humans and models route attention; tags or headings are just visible boundaries.
