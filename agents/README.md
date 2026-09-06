# Agents

One markdown file per specialist. Frontmatter declares the retrieval queries; the body is the prompt.

| Agent | Finds | Needs |
|---|---|---|
| `security.md` | OWASP-framed vulnerabilities with a concrete attack path | nothing |
| `pattern-compliance.md` | Deviations from conventions the codebase itself establishes | best with written standards |
| `requirements-gap.md` | Where the code does not do what the spec says | **acceptance criteria** — useless without them |

## Frontmatter

```yaml
---
name: performance              # output filename and --only selector
description: One line.
queries:                       # retrieval queries; results unioned, cut to --top-k
  - "database query inside a loop, N+1 access pattern"
  - "synchronous IO on a request path"
requires_task_context: false   # optional
---
```

Placeholders filled at run time: `{BUNDLE_DIR}`, `{OUT_DIR}`, `{PROJECT_DESCRIPTION}`.

## Writing a good specialist

- **Give it one domain and tell it what is not its job.** Overlap between specialists produces
  duplicate findings, which the dedup step then has to guess about.
- **Write long.** Specialised prompts run several times the length of a general one; that length is
  where the domain expertise lives.
- **Demand evidence.** Quoted code, an exact `file:line`, and the specific rule or criterion
  violated. A finding without those wastes more time than it saves.
- **Require a `context_limitation` on every finding** — what the agent could not see that would kill
  it. In the reference run this is what let verification resolve findings quickly instead of
  re-deriving them, and one such note correctly predicted its own finding's collapse.
- **Say that zero findings is a valid answer.** Otherwise you get padding, and padding is what
  destroys trust in a review tool.
- **Tell it to cite line numbers exactly as they appear in the bundle headers.** Agents reading from
  a bundle drift on line numbers; the bundles carry the correct ones.

## Turning a recurring finding into an agent

The loop that makes this worth maintaining: review → judge → codify → reuse. When a finding keeps
recurring in your codebase and you have decided it is a real pattern rather than noise, write it
into a specialist — a query so it gets retrieved, and a prompt section so it gets recognised. That
is how the harness comes to know your project's standards instead of guessing them.
