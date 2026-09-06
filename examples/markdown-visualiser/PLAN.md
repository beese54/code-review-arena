# Code Review Comparison — Plan

**Repo under review:** `markdown-visualiser`
**Shared target:** `src/` + `server/` — 31 TS/TSX files, 4,265 LOC
**Working tree:** clean at `cc34345` (master). No PR diff exists, so both arms review the same path target.

## Arm A — qodo methodology
Source of the methodology: `C:\Users\allti\OneDrive\Documents\ai_code_review_by_qodo`
(DeepLearning.AI × Qodo, "AI Code Review", lessons 2–7 + glossary)

Pipeline, per the course:
1. **Context engine** (L5) — AST-based chunking of the repo -> vector embeddings -> vector index ->
   **selective** retrieval of top-N chunks per query. Course finding: selective beats full context.
2. **Task-level context** (L3, BP#3) — `specification.json`, `definition_of_done.md`,
   `progress_tracking.json`, `tasks/todo.md`. Gives the reviewer acceptance criteria to measure
   the code against -> enables *requirements gap* findings.
3. **Repo rules & standards** (L4, BP#4) — global `CLAUDE.md` working principles,
   `eslint.config.js`, `.claude/skills/mengto/*` design skills, `README.md` claims.
4. **Specialist ensemble** (L6) — domain agents run in parallel, long domain-specific prompts:
   - Security agent (OWASP, injection, auth, secrets, crypto)
   - Pattern-compliance agent (codebase conventions, established patterns)
   - Requirements-gap agent (code vs acceptance criteria / documented claims)
5. **Combine -> deduplicate -> risk triage** (L4, BP#5) — merge overlapping findings,
   label each **Action Required** vs **Review Recommended**, attach **Evidence**
   (file:line + the specific rule / criterion it violates).

## Arm B — Claude Code built-in
`/code-review high src server` — run at `high` effort (broad coverage).
`ultra` is user-triggered and billed, so it is out of scope for this run.

## Fairness controls
- Both arms run in **clean-room subagent sessions**. Neither sees the other's prompt, context or output.
- The main session does not pre-digest source files for either arm.
- Same target, same repo state, same day.
- Arm A's specialists each receive only their retrieved context bundle, not the whole repo.

## Honest limitations (to carry into the writeup)
- The **qodo SaaS product is not installed** and no qodo API key is present. Arm A is a faithful
  re-implementation of the *methodology taught in the course*, not the commercial product. The
  product's PR integration, memory layer and cross-repo analysis are not reproduced.
- No embedding API key is available, so the context engine's vectoriser is a local offline model /
  TF-IDF rather than `text-embedding-3-large`. Retrieval is still selective and vector-based.
- There is no ground-truth issue set for this repo, so precision/recall/F1 cannot be computed the way
  the course does against 15 synthetic PRs. Comparison is qualitative + overlap-based.

## Outputs
- `context-engine/` — the runnable context engine + its retrieval artefacts
- `arm-a-qodo/` — per-specialist findings, ensemble output, triaged report
- `arm-b-claude-code/` — verbatim `/code-review high` output
- `COMPARISON.md` — the differences analysis
- `METHODOLOGY.md` — exactly how each arm was run, for reproducibility
