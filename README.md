# code-review-arena

Run two *architecturally different* AI code reviewers against the same code, and see what each one
structurally cannot find.

Not a benchmark. There is no scoreboard here, because the interesting result isn't which tool wins —
it's how little they overlap.

---

## The result that motivated this

Two AI reviewers. Same 4,265 lines, same commit, same day, same underlying model. The only variable
was *how each reviewer was built*.

```
        Arm A only          shared          Arm B only
    ┌──────────────────┐  ┌────────┐  ┌──────────────────┐
    │       18         │  │   2    │  │       11         │
    └──────────────────┘  └────────┘  └──────────────────┘
                    31 distinct issues
                     overlap: 6.5%
```

- **Arm A** had the project spec and could not execute anything. It found an API field documented in
  the spec that the server silently ignores. Structurally invisible to a reviewer with no spec.
- **Arm B** read every file and ran the code. It proved every footnote link in the app was dead by
  executing the pipeline and pasting the broken output. Structurally impossible for a reviewer that
  cannot execute.

Neither is better. They answer different questions. Full write-up in
[`examples/markdown-visualiser/`](examples/markdown-visualiser/).

---

## What this repo gives you

A harness for **Arm A** — the context-aware ensemble, which is the fiddly one to build:

1. **Structure-aware chunking.** TypeScript/JavaScript via the real TypeScript compiler AST, Python
   via `ast`, and a structural heuristic for Go, Rust, Java, C/C++, C#, Ruby, PHP, Swift, Kotlin and
   friends. Chunks are whole definitions, not line windows.
2. **Selective retrieval.** Local embeddings (`all-MiniLM-L6-v2`, no API key) → Chroma → top-K
   chunks *per agent*. Selective beats full: handing a reviewer the whole codebase dilutes it.
3. **Project context discovery.** Finds your spec, acceptance criteria, engineering standards, lint
   and type config, and README claims — automatically, by convention.
4. **A specialist ensemble.** Three agents by default; adding one is adding a markdown file.
5. **Ready-to-paste prompts**, each pinned to its own bundle.

Plus `check_citations.py`, which works on **any** reviewer's output and answers one objective
question: do the `file:line` citations point at real lines?

**It does not call an LLM.** It writes prompts; you run them in whatever agent runner you like. A
harness that quietly burns tokens is a bad neighbour, and the whole point is to compare *your* tools.

---

## Quickstart

```bash
git clone https://github.com/beese54/code-review-arena && cd code-review-arena
pip install -r requirements.txt
npm install                      # only for the TypeScript AST chunker

python -m arena.run --repo /path/to/your/repo --target src server
```

Output lands in `<repo>/review-arena-run/`:

```
  chunks.json               every chunk, with real line numbers
  bundles/                  one selective context bundle per agent
    security.md
    pattern-compliance.md
    requirements-gap.md
    task-context.md         your spec / acceptance criteria, discovered
    standards.md            your conventions, lint config, README claims
  prompts/                  ready to paste, one per agent
  arm-a/                    where the specialists write their findings
  arm-b/                    where you drop your other reviewer's output
  RUN.md                    exactly what to do next
```

Then run each prompt as its own fresh agent session, run your comparison reviewer on the same
target, and diff the two.

### Useful flags

| Flag | Default | Why you'd change it |
|---|---|---|
| `--target` | `.` | Narrow to the code that matters: `--target src server` |
| `--top-k` | `30` | Chunks per agent. Aim for **~15% of the index** — the tool warns if `--top-k` exceeds the index, which silently turns a selective run into a full-context one |
| `--ext` | broad set | Restrict languages: `--ext .py` |
| `--embedder` | `local` | `openai` uses `text-embedding-3-large` (needs `OPENAI_API_KEY`) |
| `--only` | all | Run a subset: `--only security` |
| `--describe` | auto | One paragraph about your system, injected into every prompt. Worth writing |
| `--task-file` | auto | Point at your spec explicitly if discovery misses it |

---

## Adding your own specialist

Drop a markdown file in `agents/`. Frontmatter declares the retrieval queries; the body is the
prompt.

```markdown
---
name: performance
description: Finds work done per-item that should be done per-batch.
queries:
  - "database query inside a loop, N+1 access pattern"
  - "synchronous IO on a request path"
---

You are the PERFORMANCE AGENT in a specialised code-review ensemble.
...
Write to `{OUT_DIR}/specialist-performance.md`.
```

Placeholders filled at run time: `{BUNDLE_DIR}`, `{OUT_DIR}`, `{PROJECT_DESCRIPTION}`.

This is the mechanism that matters most over time. When a review finding recurs in your codebase,
write it into an agent — that is how the harness learns your project's standards instead of guessing
them.

---

## Three things worth knowing before you trust the output

**1. Retrieval cannot show you an absence.** In the reference run, Arm B found a security control
that was written, documented, and *never imported by anything*. Arm A had that exact file in its
bundle and reasoned about the control as though it were live. You cannot grep for "who calls this"
from inside a bundle, and more retrieved context does not fix it — the evidence needed is a negative
result over the whole repo.

**2. Ensemble agreement is correlated evidence, not independent evidence.** The reference run's only
cross-specialist convergence — the class the method treats as highest-confidence — was the finding
that verification most deflated. Both agents were reasoning from the same absence. Treat convergence
as a prompt to verify, not as proof.

**3. Verification is weaker than fixing.** Both arms passed a verification pass with zero
fabrications. Then the findings were actually fixed, and *both* turned out to be wrong about
mechanism — including the one that had reproduced its bug by running the code. It proved a real
symptom and blamed the wrong cause.

> "Did it find real bugs" is the easy half of the question.
> "Was it right about why" is the half that decides whether your fix closes anything.

---

## Requirements

- Python 3.10+, `chromadb` (bundles a local embedding model — first run downloads ~80 MB)
- Node 18+ and `typescript` — **only** for TypeScript/JavaScript AST chunking; without them TS/JS
  falls back to the structural chunker and the tool says so

## Credit

The methodology — context engine, selective retrieval, specialist ensemble, deduplication, risk
triage — is from the [DeepLearning.AI × Qodo "AI Code Review" course](https://www.deeplearning.ai/).
This is an independent implementation of the ideas that course teaches, for running the comparison
on your own repositories.

**It is not the Qodo product, and nothing here benchmarks it.** The commercial tool's PR
integration, memory layer and cross-repository analysis are not reproduced. If you write about
results from this harness, please describe it as an *architecture* comparison rather than a product
comparison — that is the only claim the setup actually supports.

## Licence

MIT.
