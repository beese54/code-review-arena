# Methodology — how each arm was actually run

Written so the run is reproducible and so the comparison can be read sceptically.

## Shared conditions

| | |
|---|---|
| Repo under review | `markdown-visualiser` |
| HEAD | `cc34345` (master), working tree clean |
| Target | `src/` + `server/` |
| Size | 31 TS/TSX files, 4,265 LOC |
| Date | 2026-09-05 |
| Model | Claude Opus 5, both arms |

Both arms reviewed the **same code at the same commit on the same day**, and each ran in a
**clean-room session** with no visibility of the other arm's prompt, context, or output. The main
session did not pre-read source files for either arm, so neither inherited a warm analysis.

---

## Arm A — the qodo methodology

Reconstructed from `C:\Users\allti\OneDrive\Documents\ai_code_review_by_qodo`
(DeepLearning.AI × Qodo, *AI Code Review*, lessons 2–7 and the course glossary).

### A1. Context engine — `context-engine/chunk.mjs`
AST-based chunking, using the **real TypeScript compiler AST** (`ts.createSourceFile` +
`forEachChild`), not line splitting. The course chunked a Python repo with Python's `ast`; this is
the TypeScript equivalent. Extracts functions, classes, interfaces, type aliases, methods,
components and top-level consts, each carrying `file_path`, `start_line`, `end_line`.

```
31 files  ->  199 chunks  ->  106,988 chars
function 114 | const 44 | interface 27 | type 9 | class 4 | method 1
```

### A2. Embeddings + vector index — `context-engine/retrieve.py`
`all-MiniLM-L6-v2` (384-dim, local ONNX) via Chroma's default embedding function, indexed in an
ephemeral Chroma collection, cosine similarity.

> **Deviation from the course:** the course used OpenAI `text-embedding-3-large`. No OpenAI API key
> is available on this machine, so a local sentence-transformer stands in. Retrieval is still
> semantic and vector-based; absolute similarity scores are not comparable to the course's.

### A3. Selective retrieval
Each specialist issues its own six domain queries; results are unioned and cut to the top 30 chunks
by best similarity — roughly 15% of the index, matching the course's 15-of-99 ratio. This is the
course's central finding: **selective context beats full context**, because dumping the whole repo
dilutes the review.

| Specialist | Chunks | Chars | Reduction vs full context |
|---|---|---|---|
| security | 30 / 199 | 20,842 | 82.4% |
| pattern | 30 / 199 | 29,039 | 75.4% |
| requirements | 30 / 199 | 25,430 | 78.5% |

### A4. Task-level context (course best practice #3)
`definition_of_done.md` + `specification.json`, assembled into `bundles/task-context.md`. This is
what makes **requirements-gap findings structurally possible** — a reviewer with no acceptance
criteria cannot tell you the code fails to meet them.

### A5. Repo rules and standards (course best practice #4)
`bundles/standards.md` — the user's global `CLAUDE.md` engineering principles, `eslint.config.js`,
`tsconfig.json` strictness, and the `README.md` public claims. Findings are expected to cite the
specific rule they violate.

### A6. Specialist ensemble (course lesson 6)
Three agents, run **in parallel**, each with a long domain-specific prompt (the course notes
specialised prompts run ~4x the length of a general one):

- **Security agent** — OWASP framing, injection/XSS, path traversal, SSRF, headless-browser threat model, DoS, secrets.
- **Pattern-compliance agent** — deviations from conventions the codebase itself establishes, plus written-standard violations.
- **Requirements-gap agent** — implementation measured against the extracted acceptance-criteria checklist.

Each specialist is **retrieval-bound**: it may read only its own context bundle, the task context
and the standards. It cannot open source files, grep, or explore the repo. This is deliberate — it
is the architecture under test, and it is what makes the comparison against an agentic reviewer
meaningful.

### A7. Combine -> deduplicate -> triage (course lesson 6 + best practice #5)
Findings the specialists agree on are treated as high-confidence; unique high/medium findings are
carried through; overlaps are merged aggressively. Each surviving finding is then triaged as
**Action Required** or **Review Recommended**, with evidence linking to `file:line` and to the rule
or criterion it violates.

---

## Arm B — Claude Code's built-in review

```
/code-review high src server
```

Run at `high` effort: broad coverage, may include uncertain findings. This is Claude Code's own
command, unmodified — no extra prompt, no context bundle, no standards injected. It explores the
repo agentically with its own tools and decides for itself what to read.

`/code-review ultra` (the multi-agent cloud review) was **not** run: it is user-triggered and
separately billed, so it is outside what this session can launch.

---

## Known limitations of this comparison

1. **This is not the qodo product.** The qodo CLI is not installed and no qodo account is
   connected. Arm A implements the *methodology the course teaches*. The commercial product's PR
   integration, memory layer, cross-repository conflict analysis and learned-standards persistence
   are **not** reproduced. Any claim about "qodo the product" cannot be supported by this run.
2. **No ground truth.** The course computes precision/recall/F1 against 15 synthetic PRs with known
   planted issues. This repo has no labelled issue set, so those metrics cannot be computed. The
   comparison here is qualitative plus an overlap analysis, and every finding's *validity* is a
   judgement call, not a measurement.
3. **Asymmetric by design, and that asymmetry is the point.** Arm A is retrieval-bound and
   context-fed; Arm B explores freely and is context-starved. Neither handicap was added
   artificially — each reflects how that architecture actually works. But it does mean the arms are
   not interchangeable and a "winner" framing would be misleading.
4. **Single run, single repo, single day.** LLM output is non-deterministic. Re-running either arm
   would produce a somewhat different finding set.
5. **Same underlying model.** Both arms run on Claude Opus 5, which isolates *architecture* as the
   variable — but it also means this measures the review architecture, not qodo's model choices.
