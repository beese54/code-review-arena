# Adding a specialist

An agent is one markdown file in `agents/`. Frontmatter declares what it retrieves; the body is the
prompt it runs as. Nothing else registers it — `arena.run` picks up every `*.md` in the directory.

```markdown
---
name: performance
description: Finds work done per-item that should be done per-batch.
severities: [high, medium, low]
requires_task_context: false
queries:
  - "database query inside a loop, N+1 access pattern"
  - "synchronous file or network IO on a request path"
  - "unbounded collection growth, cache without eviction"
  - "repeated recomputation of a stable value"
---

You are the PERFORMANCE AGENT in a specialised code-review ensemble.

[prompt body]

Write your findings to `{OUT_DIR}/specialist-performance.md`.
```

Placeholders filled at run time: `{BUNDLE_DIR}`, `{OUT_DIR}`, `{PROJECT_DESCRIPTION}`.

## Writing the queries

The queries *are* the agent's eyes. It will only ever see what they retrieve, so a weak query set is
a blind agent no matter how good the prompt is.

- **Describe the code, not the bug.** Embeddings match text to text. `"database query inside a loop"`
  retrieves loops containing queries. `"performance problems"` retrieves nothing in particular.
- **Write six to ten.** Each returns its own neighbours; the union is what the agent gets. One query
  returns one neighbourhood.
- **Cover the surfaces, not the severities.** Aim at entry points, boundaries, IO, configuration —
  the places the class of bug lives.
- **Vocabulary matters more than syntax.** Use the words the codebase would use.

After adding an agent, check what it actually got:

```bash
python -m arena.run --repo /path/to/repo --target src --only performance
head -40 review-arena-run/bundles/performance.md
```

If the top chunks are not the files you would have opened by hand, the queries are wrong. Fix them
before blaming the prompt. The `(cos …)` score on each heading is a true cosine — in practice a
useful top hit sits around 0.4–0.6 for a short query against a code chunk, so treat the number as a
sanity check on ranking rather than a threshold.

## Writing the prompt body

Four things every specialist prompt needs:

1. **A stated domain, in depth.** The measured advantage of an ensemble over one general reviewer
   comes from each agent having a long, specific domain brief rather than a paragraph. Give it the
   threat model, the failure taxonomy, the vocabulary.
2. **Evidence rules.** Every finding cites `file:line` from the bundle, and the line numbers in the
   bundle headings are real — the agent must copy them, never estimate. Findings without a citation
   do not ship.
3. **A severity scale**, matching the `severities` in the frontmatter.
4. **An explicit output path** — `{OUT_DIR}/specialist-<name>.md`.

Add one more, which costs a line and pays for itself: **tell the agent to report what it could not
assess.** A specialist working from 15% of a codebase has real blind spots, and an agent that says
"I could not evaluate 24 of the 53 acceptance criteria from this slice" is more useful than one that
quietly reports on the 29 it could see.

## When to add one

The best reason is a finding that keeps recurring in your repo. Write it into an agent's brief and
it stops depending on whether a reviewer happens to notice. That is the mechanism by which this
harness learns your project's standards instead of guessing them — and it is worth more over time
than any change to the retrieval settings.

## `requires_task_context`

Set it when the agent is meaningless without written acceptance criteria — as `requirements-gap` is.
`arena.run` warns when no task context was discovered, so the run does not silently produce an agent
measuring against nothing.
