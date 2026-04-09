# The interface looks simple. That’s the trap. (v2)

I spent two years calling LLMs “hit or miss” before admitting the miss rate was mostly me.

As engineers we’re trained to be precise with machines: function signatures, typed parameters, explicit contracts. Then we open a chat box and write like we’re pinging a coworker on Slack—“hey, can you refactor this?”—and act surprised when the answer needs three rounds of correction.

**The model isn’t vague. Your instruction is.**

## Three levels, three different outcomes

People don’t use these tools at one skill level. They drift between modes. The gap in output quality between the lowest and highest mode is large—often larger than swapping model names for the same sloppy prompt.

### Level 1 — Conversational

You say what you want in plain prose. That’s fine for throwaway tasks and brainstorming. It falls apart when the work has **multiple constraints**, a **fixed format**, or **context the model must infer** because you never attached it. You’re outsourcing decisions to the model, then faulting it for the ones it makes.

*Concrete examples:* see `prompt-post-examples.md` (Level 1).

### Level 2 — Structured prompting

This is where engineering habits start to pay off. **Named sections matter.** XML-style tags (`<role>`, `<task>`, `<constraints>`, `<examples>`) give the model a schema to complete against—similar to why keyword and typed arguments beat anonymous positional lists. **JSON** helps when you chain tool calls or need predictable shapes. **Markdown headings** chunk long prompts the way headings chunk a design doc. The structure isn’t cosmetic; it changes how attention lands across the prompt.

*Concrete examples:* see `prompt-post-examples.md` (Level 2).

### Level 3 — Prompt as interface contract

You treat the prompt like an API spec: **role first**, **examples separate from rules**, **“correct” defined**, **output shape fixed** so nothing downstream has to guess. You **iterate** the way you’d tune any component—isolate one variable, observe, adjust.

*Concrete examples:* see `prompt-post-examples.md` (Level 3).

## What actually correlates with good results

The engineers who get the most from these systems apply the same rigor as writing a solid API: clear inputs, explicit success criteria, no ambiguous side effects.

## One thing to try this week

Stop defaulting to a single blob of text. Split the prompt into sections—**role**, **context**, **task**, **constraints**—even if you stay in plain English. That single habit often cuts useless output more than chasing the newest model weights.

## Visual summary

Flow and hierarchy are sketched in `prompt-post-diagrams.md`.

---

*Companion files: `prompt-post.md` (original), `prompt-post-examples.md` (level-by-level samples), `prompt-post-diagrams.md` (figures).*
