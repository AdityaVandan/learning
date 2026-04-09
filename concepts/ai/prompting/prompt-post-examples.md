# Examples: three levels of prompting

Same underlying ask—**refactor a Python function and preserve behavior**—shown three ways. The task has real constraints: keep public API, add type hints, no new dependencies.

---

## Level 1 — Conversational

```text
Hey, can you refactor this function? It's a bit messy. Thanks!
```

```python
def proc(data):
    out = []
    for x in data:
        if x > 0:
            out.append(x * 2)
    return out
```

**What the model has to guess:** scope (rename? extract helpers? performance?), style (PEP 8? dataclasses?), whether to include tests, what “messy” means, edge cases (empty list? non-numeric elements?).

**Typical failure mode:** a plausible refactor that ignores one of your unstated constraints, or a giant rewrite you didn’t want.

---

## Level 2 — Structured prompting

Structure turns implicit defaults into explicit slots. XML tags are one option; markdown sections work the same way.

```text
<role>
You are a senior Python engineer reviewing code for clarity and maintainability.
</role>

<context>
We have a small data-pipeline helper used in batch jobs. Public name must stay `proc` for now.
</context>

<code language="python">
def proc(data):
    out = []
    for x in data:
        if x > 0:
            out.append(x * 2)
    return out
</code>

<task>
Refactor for readability. Add type hints. Do not add third-party dependencies.
</task>

<constraints>
- Keep the function name `proc`.
- Preserve behavior for valid numeric inputs: positive numbers doubled, non-positive skipped, order preserved.
- Output only the revised function and a one-line summary of what changed.
</constraints>
```

**What improved:** role, artifact, task, and constraints are separable; the model can “fill the form” instead of inventing the form.

---

## Level 3 — Interface contract

Here the prompt specifies **what “correct” means** and **what shape the answer must take**, like an API schema. Same refactor ask, with acceptance criteria and a fixed output envelope.

```text
## Role
Senior Python engineer. Prefer small, reviewable diffs.

## Inputs you will receive
- Python source for `proc` (shown below).

## Task
Refactor `proc` for clarity; add stdlib-only type hints; keep the name `proc`.

## Definition of done (must all be true)
1. For any `list` of `int` | `float`, return value equals the original function’s return value.
2. No imports except `from __future__ import annotations` if needed for forward refs.
3. Function remains a single top-level function named `proc` (no class wrapper).

## Output format (required)
Return exactly two fenced blocks in this order:
1. A python fenced block containing only the full new `proc` implementation.
2. A text fenced block containing 3–6 bullet test cases you would run (inputs → expected output), no prose outside the list.

## Code
[paste same `proc` definition as above]

## Iteration note
If you must assume something ambiguous (e.g., mixed types in `data`), state the assumption in one line inside the `text` block after the bullets.
```

**What improved:** a consumer (you, a script, or a follow-up model) knows where to look; “done” is checkable; iteration can target one clause at a time.

---

## Quick contrast

| Level | Strength | Weak spot |
|-------|----------|-----------|
| 1 | Fast for vague exploration | High variance when constraints pile up |
| 2 | Clear buckets; less accidental omission | Still need explicit “correct” if you grade automatically |
| 3 | Testable outputs; iteration like tuning an API | Upfront cost; overkill for one-off chit-chat |

Use level 1 for disposable thought experiments; use 2 when structure helps; use 3 when the response is part of a pipeline or you care about verifiable correctness.
