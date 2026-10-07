# Project context

This repo is a LEARNING ARTIFACT, not a product. The human is a senior engineer
using it to build deep understanding of distributed systems concepts. Optimize
for comprehensibility and conceptual density, NOT for shipping speed, code
cleverness, or line count.

## Non-negotiable rules

1. NO IMPLEMENTATION CODE BEFORE THE ADR IS APPROVED. Phase 1 is docs only.
   Stop and wait for explicit human approval before Phase 2.
2. Leave `TODO(learner)` gaps exactly as specified in the project brief. For
   each: write the signature, the docstring describing intended behavior, the
   surrounding wiring, and a test suite that FAILS until it is implemented.
   Do NOT write the body. Do NOT write a "reference implementation" anywhere
   in the repo, including in comments, docs, or git history.
3. Prefer boring, readable implementations. If you optimize something, comment
   what naive version it replaced and what the measured difference was.
4. No hidden magic. If a library performs a conceptually important operation
   (consistent hashing, offset commit, MVCC snapshot, quorum read), add a
   comment naming the concept so it is not invisible to the reader.
5. Everything must run locally via `docker compose up` with zero cloud
   dependencies. Cloud deployment is a separate, optional, documented step.
6. Instrument from the first commit: Prometheus metrics, structured JSON logs
   with trace IDs, and latency histograms (p50/p95/p99) on every network
   boundary. A component with no metrics is not done.
7. Keep total dependencies minimal and justify each one in the ADR.

## Required deliverables (every project)

- `docs/ADR-000-architecture.md` — format below
- `docs/CONCEPTS.md` — table of every system-design concept this project
  exercises, mapped to the file and function where it appears
- `docs/FAILURE_LAB.md` — numbered chaos experiments for the human to run,
  each with a "write your prediction here" blank BEFORE the expected result
- `docs/QUIZ.md` — 20 questions, answers in a `<details>` block. Questions must
  NOT be answerable by reading comments; only by understanding runtime behavior
- `docs/RUNBOOK.md` — local run, load test, cloud deploy, cost estimate, teardown
- `Makefile` — `up`, `test`, `load`, `chaos`, `down`, `deploy`, `destroy`

## ADR format

Produce 6–12 numbered decisions. For EACH:

- **Context and forces** — what constraint makes this a real decision
- **Options considered** — minimum 3, and must include (a) the one a naive
  implementation would pick, and (b) at least one used by a real production
  system
- **Per option**: mechanism, what it costs, what it buys, where it breaks, and
  a named real system that uses it
- **Decision** with explicit reasons each rejected option was rejected
- **Consequences**, including what this decision makes HARD later
- **Interview framing** — how to explain this trade-off out loud in 90 seconds

## Working style

- Use plan mode for anything spanning more than 3 files.
- Build in vertical slices that are runnable at every commit. Never leave the
  repo in a state where `make up` fails.
- After each slice, output a short "what to look at and why" note pointing the
  human at the 2–3 files that carry the concept.