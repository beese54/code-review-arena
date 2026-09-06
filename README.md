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

## How Arm A is built

Two views of the same pipeline. Start with the shape of it:

![How the work gets divided: a codebase is split into whole pieces, then handed to three specialists — security, conventions, and requirements — each of which sees about 15 percent of the code, roughly 40 percent between them. One highlighted band notes that each specialist gets a small slice rather than the whole codebase. A second notes that the spec skips the search and goes to every specialist whole and unfiltered. The findings are then merged, deduplicated and ranked. A closing band titled "The catch" reads: whatever nobody was handed, nobody can find.](docs/how-the-work-divides.svg)

Divide the work by *what you are looking for* rather than by file, ration what each specialist is
given, and let the project's own spec bypass the search entirely. That is the whole idea, and it
transfers to any repo in any language.

Now the same pipeline with the machinery and the real numbers from the reference run:

![Architecture of Arm A: 31 source files are split by the TypeScript compiler into 199 chunks, embedded into 384 numbers each and indexed in Chroma. Three specialists — security, pattern compliance and requirements gap — each issue ten plain-English queries. A shared attention budget of top-k equals 30 cuts each result set by rank, giving every agent 15 percent of the index and 39.7 percent combined. Task context and standards bypass retrieval and are passed whole. The three agents run in isolation, producing 6, 10 and 5 findings, combined into 20 after deduplication and triaged into 6 Action Required and 14 Review Recommended. The costs: 7 of 31 files were never retrieved by any agent, 24 of 53 acceptance criteria could not be assessed, and an absence such as "nothing imports this" can never be retrieved at all.](docs/arm-a-architecture.svg)

Three things the detailed view is trying to make obvious, because all three are easy to get wrong:

- **`top-k` is a budget, not a filter.** It takes exactly 30 chunks by rank. There is no relevance
  threshold anywhere in the pipeline, so the 30th chunk is included because it ranked 30th — in the
  reference run that chunk scored cos 0.284, which is barely related to the query at all.
- **15% is per agent, not per review.** The three query sets pull different neighbourhoods, so the
  ensemble collectively saw 39.7% of the chunks and reached 24 of 31 files. Specialisation buys
  coverage that one narrow view would not have.
- **The spec does not go through retrieval.** Task context and standards are passed whole to every
  agent. That side channel is the only reason a requirements-gap finding is possible, and it is the
  clearest structural difference from a reviewer working from the diff alone.

Both are in [`docs/`](docs/) as SVG and 2x PNG. Arm B needs no diagram: it opens every file and runs
the code, which is rather the point.

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

### Why a compiler, when nothing is being compiled

A TypeScript compiler normally turns TypeScript into JavaScript. Here it is used for something else:
reading.

Before it can translate anything, a compiler has to work out the structure of your code — where each
function starts and ends, what it is called, which lines it occupies. That is the part this harness
uses, and then it stops. Nothing is translated, no JavaScript is produced, and the agents read the
original TypeScript.

Why bother? Because the code has to be cut into pieces before it can be searched, and the pieces need
to be whole functions. Cut by counting lines instead and you hand a reviewer the back half of one
function glued to the front of another. The compiler is the only thing that knows where the real
seams are.

The difference is measurable. Running both chunkers over the same 31 files:

```
compiler AST     198 chunks   median 224 chars   top-k 30 = 15% of the index
regex fallback   131 chunks   median 549 chars   top-k 30 = 23% of the index
```

The fallback misses 71 definitions, and not at random: it finds `function`, `class`, `interface` and
`type`, because those begin with a keyword a pattern can match. It finds **none** of the 43 top-level
`const` declarations, because `const sanitizeSchema = {...}` does not look like a definition to a
regular expression — it looks like an assignment. In the reference run that includes `sanitizeSchema`
itself, which is where the real security bug was, and `printSchema`, the dead control. Neither would
have existed as a retrievable unit.

Chunk count also sets the denominator for the retrieval budget: coarser chunks mean fewer of them, so
the same `top-k` hands over a larger share of the codebase, in bigger pieces that mix several ideas
together. That is dilution arriving through the back door.

Finally, the parser is where the line numbers come from. Every bundle heading carries a real
`file:line-line`, agents are told to copy them rather than estimate, and `check_citations.py` can
only mean something because the source of truth was true to begin with.

For Python the same job is done by Python's own `ast` module. For everything else there is no
equivalent parser bundled here, so the regex fallback is what runs — it works, and it is visibly the
weaker path.

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

## Use it as a Claude Code skill

The repo ships a skill that drives the whole workflow — setting the conditions, building Arm A,
launching the specialists as parallel isolated agents, running your comparison reviewer, and
producing the overlap analysis.

```bash
cp -r .claude/skills/code-review-arena ~/.claude/skills/
```

The skill lives in [`.claude/skills/code-review-arena/`](.claude/skills/code-review-arena/) — GitHub
hides dotfolders from the file list, so that link is the only way to find it by browsing.

Then ask for it by name, or just describe the task:

```
/code-review-arena
compare Claude Code's review against a context-fed ensemble on src/
```

It works in the repo you cloned or on any other repo — point it at a target and it runs there. The
skill carries the two rules that keep the output honest: it will not declare a winner (there is no
ground truth, so precision and recall are unavailable), and it ends by making you *fix* a finding,
because verification passes on findings that are right about the symptom and wrong about the cause.

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
